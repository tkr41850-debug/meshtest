package node

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"log"
	"net"
	"net/http"
	"net/url"
	"os"
	"sync"
	"time"

	"github.com/tkr41850-debug/meshtest/internal/leader"
)

var (
	DefaultCheckInterval = 10
	DefaultBufferSize    = 20000
	DefaultListenPort    = 58081
)

type PingResult struct {
	OK        bool
	LatencyMs float64
}

type HTTPResult struct {
	OK        bool
	Status    int
	LatencyMs float64
}

type CheckCycleResult = leader.CheckResult

func ResolveNodeIP(nodeURL string) string {
	if ip := os.Getenv("NODE_IP"); ip != "" {
		return ip
	}
	if nodeURL != "" {
		parsed, err := url.Parse(nodeURL)
		if err == nil && parsed.Hostname() != "" {
			return parsed.Hostname()
		}
	}
	addrs, err := net.InterfaceAddrs()
	if err == nil {
		for _, addr := range addrs {
			if ipnet, ok := addr.(*net.IPNet); ok && !ipnet.IP.IsLoopback() && ipnet.IP.To4() != nil {
				return ipnet.IP.String()
			}
		}
	}
	return "127.0.0.1"
}

type Node struct {
	mu            sync.RWMutex
	LeaderURL     string
	NodeIP        string
	NodeURL       string
	ListenPort    int
	Peers         []leader.PeerDict
	ExtraTargets  []string
	CheckInterval int
	BufferSize    int
	resultBuffer []CheckCycleResult
	client        *http.Client
}

func NewNode(leaderURL, nodeURL string, listenPort int) *Node {
	return &Node{
		LeaderURL:     leaderURL,
		NodeIP:        "127.0.0.1",
		NodeURL:       nodeURL,
		ListenPort:    listenPort,
		CheckInterval: DefaultCheckInterval,
		BufferSize:    DefaultBufferSize,
		client: &http.Client{
			Timeout: 10 * time.Second,
		},
	}
}

func (n *Node) SubmitResults(checks []CheckCycleResult, timestamp float64) bool {
	// Combine buffer with new results
	n.mu.Lock()
	if len(n.resultBuffer) > 0 {
		allChecks := n.resultBuffer
		space := n.BufferSize - len(allChecks)
		if space > 0 {
			if len(checks) < space {
				space = len(checks)
			}
			allChecks = append(allChecks, checks[:space]...)
		}
		checks = allChecks
		n.resultBuffer = nil
	}
	n.mu.Unlock()

	var buf bytes.Buffer
	payload := map[string]interface{}{
		"node_ip":   n.NodeIP,
		"node_url":  n.NodeURL,
		"checks":    checks,
		"timestamp": timestamp,
	}
	if err := json.NewEncoder(&buf).Encode(payload); err != nil {
		log.Printf("Failed to encode submit payload: %v", err)
		return false
	}

	resp, err := n.client.Post(n.LeaderURL+"/submit", "application/json", &buf)
	if err != nil {
		log.Printf("Submit failed: %v", err)
		n.bufferResults(checks)
		return false
	}
	defer resp.Body.Close()
	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		log.Printf("Submit failed: HTTP %d", resp.StatusCode)
		n.bufferResults(checks)
		return false
	}
	return true
}

func (n *Node) bufferResults(checks []CheckCycleResult) {
	n.mu.Lock()
	defer n.mu.Unlock()
	if n.BufferSize <= 0 {
		return
	}
	n.resultBuffer = append(n.resultBuffer, checks...)
	if len(n.resultBuffer) > n.BufferSize {
		excess := len(n.resultBuffer) - n.BufferSize
		n.resultBuffer = n.resultBuffer[excess:]
	}
}

func (n *Node) RunCheckCycle(timeout time.Duration) []CheckCycleResult {
	n.mu.RLock()
	peers := make([]leader.PeerDict, len(n.Peers))
	copy(peers, n.Peers)
	extras := make([]string, len(n.ExtraTargets))
	copy(extras, n.ExtraTargets)
	n.mu.RUnlock()

	totalChecks := len(peers) + len(extras)
	if totalChecks == 0 {
		return nil
	}

	type result struct {
		idx int
		r   CheckCycleResult
	}
	ch := make(chan result, totalChecks)
	sem := make(chan struct{}, 10)

	now := float64(time.Now().Unix())
	var wg sync.WaitGroup

	// Peer checks (normal targets)
	for i, p := range peers {
		wg.Add(1)
		go func(i int, p leader.PeerDict) {
			defer wg.Done()
			sem <- struct{}{}
			defer func() { <-sem }()

			port := p.Port
			if port == 0 {
				port = leader.DefaultListenPort
			}

			pingRes := PingNode(p.IP, timeout)
			httpRes := CheckHTTP(p.IP, port, timeout)
			ch <- result{i, CheckCycleResult{
				TargetIP:  p.IP,
				PingOK:    pingRes.OK,
				HTTPOK:    httpRes.OK,
				Timestamp: now,
				LatencyMs: pingRes.LatencyMs,
			}}
		}(i, p)
	}

	// Extra target checks
	for i, ip := range extras {
		wg.Add(1)
		go func(i int, ip string) {
			defer wg.Done()
			sem <- struct{}{}
			defer func() { <-sem }()

			pingRes := PingNode(ip, timeout)
			httpRes := CheckHTTP(ip, 80, timeout)
			idx := len(peers) + i
			ch <- result{idx, CheckCycleResult{
				TargetIP:  ip,
				PingOK:    pingRes.OK,
				HTTPOK:    httpRes.OK,
				Timestamp: now,
				LatencyMs: pingRes.LatencyMs,
				IsExtra:   true,
			}}
		}(i, ip)
	}

	go func() {
		wg.Wait()
		close(ch)
	}()

	results := make([]CheckCycleResult, totalChecks)
	for r := range ch {
		results[r.idx] = r.r
	}
	return results
}

func (n *Node) FetchPeers(ctx context.Context) ([]leader.PeerDict, error) {
	if ctx == nil {
		ctx = context.Background()
	}
	req, err := http.NewRequestWithContext(ctx, "GET", n.LeaderURL+"/node-list", nil)
	if err != nil {
		return nil, err
	}
	resp, err := n.client.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		return nil, fmt.Errorf("fetch peers: HTTP %d", resp.StatusCode)
	}

	var result struct {
		Nodes []leader.PeerDict `json:"nodes"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, err
	}
	return result.Nodes, nil
}

func (n *Node) Register(ctx context.Context) error {
	if ctx == nil {
		ctx = context.Background()
	}
	var buf bytes.Buffer
	payload := map[string]interface{}{
		"node_ip":     n.NodeIP,
		"listen_port": n.ListenPort,
		"node_url":    n.NodeURL,
	}
	if err := json.NewEncoder(&buf).Encode(payload); err != nil {
		return err
	}

	req, err := http.NewRequestWithContext(ctx, "POST", n.LeaderURL+"/register", &buf)
	if err != nil {
		return err
	}
	req.Header.Set("Content-Type", "application/json")
	resp, err := n.client.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		return fmt.Errorf("register: HTTP %d", resp.StatusCode)
	}

	var regResp struct {
		Peers []leader.PeerDict `json:"peers"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&regResp); err != nil {
		return err
	}
	if regResp.Peers != nil {
		n.mu.Lock()
		n.Peers = regResp.Peers
		n.mu.Unlock()
	}
	return nil
}

func (n *Node) UpdatePeers(peers []leader.PeerDict) {
	n.mu.Lock()
	defer n.mu.Unlock()
	n.Peers = peers
}

func (n *Node) UpdateConfig(checkInterval, bufferSize int) {
	n.mu.Lock()
	defer n.mu.Unlock()
	if checkInterval > 0 {
		n.CheckInterval = checkInterval
	}
	if bufferSize > 0 {
		n.BufferSize = bufferSize
	}
}

func (n *Node) GetCheckInterval() int {
	n.mu.RLock()
	defer n.mu.RUnlock()
	return n.CheckInterval
}

func (n *Node) GetBufferCount() int {
	n.mu.RLock()
	defer n.mu.RUnlock()
	return len(n.resultBuffer)
}

func (n *Node) GetPeers() []leader.PeerDict {
	n.mu.RLock()
	defer n.mu.RUnlock()
	peers := make([]leader.PeerDict, len(n.Peers))
	copy(peers, n.Peers)
	return peers
}

func (n *Node) SetExtraTargets(extraTargets []string) {
	n.mu.Lock()
	defer n.mu.Unlock()
	n.ExtraTargets = extraTargets
}
