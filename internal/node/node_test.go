package node

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"net/url"
	"strconv"
	"testing"
	"time"

	"github.com/tkr41850-debug/meshtest/internal/leader"
)

func getPort(server *httptest.Server) int {
	u, _ := url.Parse(server.URL)
	portStr := u.Port()
	port, _ := strconv.Atoi(portStr)
	return port
}

func TestCheckHTTPHealthy(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		json.NewEncoder(w).Encode(map[string]string{"status": "alive"})
	}))
	defer server.Close()

	port := getPort(server)
	result := CheckHTTP("127.0.0.1", port, 5*time.Second)
	if !result.OK {
		t.Errorf("expected HTTP OK, got false")
	}
	if result.LatencyMs <= 0 {
		t.Errorf("expected positive latency, got %f", result.LatencyMs)
	}
}

func TestCheckHTTPUnhealthy(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusInternalServerError)
	}))
	defer server.Close()

	port := getPort(server)
	result := CheckHTTP("127.0.0.1", port, 5*time.Second)
	if result.OK {
		t.Errorf("expected HTTP not OK, got true")
	}
	if result.Status != 500 {
		t.Errorf("expected status 500, got %d", result.Status)
	}
}

func TestCheckHTTPTimeout(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		time.Sleep(2 * time.Second)
	}))
	defer server.Close()

	port := getPort(server)
	result := CheckHTTP("127.0.0.1", port, 100*time.Millisecond)
	if result.OK {
		t.Errorf("expected HTTP not OK on timeout, got true")
	}
}

func TestSubmitSuccess(t *testing.T) {
	var received bool
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		received = true
		w.WriteHeader(http.StatusAccepted)
	}))
	defer server.Close()

	n := NewNode(server.URL, "", 0)
	ok := n.SubmitResults([]CheckCycleResult{
		{TargetIP: "10.0.0.2", PingOK: true, HTTPOK: true, Timestamp: 1000},
	}, 1000)

	if !ok {
		t.Errorf("expected submit success, got false")
	}
	if !received {
		t.Errorf("expected server to receive request")
	}
}

func TestSubmitFailureHTTPError(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusInternalServerError)
	}))
	defer server.Close()

	n := NewNode(server.URL, "", 0)
	ok := n.SubmitResults([]CheckCycleResult{}, 1000)
	if ok {
		t.Errorf("expected submit failure, got true")
	}
}

func TestSubmitFailureConnectionRefused(t *testing.T) {
	n := NewNode("http://127.0.0.1:1", "", 0)
	ok := n.SubmitResults([]CheckCycleResult{}, 1000)
	if ok {
		t.Errorf("expected submit failure, got true")
	}
}

func TestRegisterSuccess(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		json.NewEncoder(w).Encode(map[string]interface{}{
			"peers": []map[string]interface{}{
				{"ip": "10.0.0.2", "port": 58080},
			},
		})
	}))
	defer server.Close()

	n := NewNode(server.URL, "", 58081)
	err := n.Register(nil)
	if err != nil {
		t.Fatalf("Register failed: %v", err)
	}
	peers := n.GetPeers()
	if len(peers) != 1 {
		t.Errorf("expected 1 peer, got %d", len(peers))
	}
}

func TestRegisterHTTPError(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusBadRequest)
	}))
	defer server.Close()

	n := NewNode(server.URL, "", 58081)
	err := n.Register(nil)
	if err == nil {
		t.Fatal("expected register error, got nil")
	}
}

func TestFetchPeersSuccess(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		json.NewEncoder(w).Encode(map[string]interface{}{
			"nodes": []map[string]interface{}{
				{"ip": "10.0.0.2", "port": 58080},
				{"ip": "10.0.0.3", "port": 58080},
			},
		})
	}))
	defer server.Close()

	n := NewNode(server.URL, "", 0)
	peers, err := n.FetchPeers(nil)
	if err != nil {
		t.Fatalf("FetchPeers failed: %v", err)
	}
	if len(peers) != 2 {
		t.Errorf("expected 2 peers, got %d", len(peers))
	}
}

func TestRunCheckCycleEmptyPeers(t *testing.T) {
	n := NewNode("http://localhost:58080", "", 0)
	results := n.RunCheckCycle(5 * time.Second)
	if results != nil {
		t.Errorf("expected nil for empty peers, got %d results", len(results))
	}
}

func TestUpdatePeersAndConfig(t *testing.T) {
	n := NewNode("http://localhost:58080", "", 0)

	n.UpdatePeers([]leader.PeerDict{
		{IP: "10.0.0.2", Port: 58080},
	})
	if len(n.GetPeers()) != 1 {
		t.Errorf("expected 1 peer after update, got %d", len(n.GetPeers()))
	}

	n.UpdateConfig(30, 5000)
	if n.GetCheckInterval() != 30 {
		t.Errorf("expected interval 30, got %d", n.GetCheckInterval())
	}
}

func TestRunCheckCycleWithPeers(t *testing.T) {
	healthServer := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
	}))
	defer healthServer.Close()

	port := getPort(healthServer)

	n := NewNode("http://localhost:58080", "", 0)
	n.UpdatePeers([]leader.PeerDict{
		{IP: "127.0.0.1", Port: port},
	})

	results := n.RunCheckCycle(5 * time.Second)
	if len(results) != 1 {
		t.Fatalf("expected 1 result, got %d", len(results))
	}
	if !results[0].HTTPOK {
		t.Errorf("expected HTTP OK, got false")
	}
}

func TestBufferOnSubmitFailure(t *testing.T) {
	n := NewNode("http://127.0.0.1:1", "", 0)
	n.BufferSize = 100

	ok := n.SubmitResults([]CheckCycleResult{
		{TargetIP: "10.0.0.2", PingOK: true, HTTPOK: true, Timestamp: 1000},
	}, 1000)
	if ok {
		t.Errorf("expected submit failure, got true")
	}

	bufLen := n.GetBufferCount()
	if bufLen != 1 {
		t.Errorf("expected 1 buffered result, got %d", bufLen)
	}
}

func TestBufferLimit(t *testing.T) {
	n := NewNode("http://127.0.0.1:1", "", 0)
	n.BufferSize = 3

	for i := 0; i < 5; i++ {
		n.SubmitResults([]CheckCycleResult{
			{TargetIP: "10.0.0.2", PingOK: true, HTTPOK: true, Timestamp: float64(i)},
		}, float64(i))
	}

	bufLen := n.GetBufferCount()
	if bufLen != 3 {
		t.Errorf("expected buffer size 3, got %d", bufLen)
	}
}

func TestSetExtraTargets(t *testing.T) {
	n := NewNode("http://localhost:58080", "", 0)
	n.SetExtraTargets([]string{"10.0.0.99", "10.0.0.100"})
	n.mu.RLock()
	if len(n.ExtraTargets) != 2 {
		t.Errorf("expected 2 extra targets, got %d", len(n.ExtraTargets))
	}
	if n.ExtraTargets[0] != "10.0.0.99" {
		t.Errorf("expected 10.0.0.99, got %s", n.ExtraTargets[0])
	}
	if n.ExtraTargets[1] != "10.0.0.100" {
		t.Errorf("expected 10.0.0.100, got %s", n.ExtraTargets[1])
	}
	n.mu.RUnlock()
}

func TestRunCheckCycleWithExtraTargetsOnly(t *testing.T) {
	n := NewNode("http://localhost:58080", "", 0)
	n.SetExtraTargets([]string{"127.0.0.1"})

	results := n.RunCheckCycle(5 * time.Second)
	if len(results) != 1 {
		t.Fatalf("expected 1 result, got %d", len(results))
	}
	if !results[0].IsExtra {
		t.Error("expected extra target result to have IsExtra=true")
	}
	if results[0].TargetIP != "127.0.0.1" {
		t.Errorf("expected target IP 127.0.0.1, got %s", results[0].TargetIP)
	}
}

func TestRunCheckCycleWithPeersAndExtraTargets(t *testing.T) {
	healthServer := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
	}))
	defer healthServer.Close()

	port := getPort(healthServer)

	n := NewNode("http://localhost:58080", "", 0)
	n.UpdatePeers([]leader.PeerDict{
		{IP: "127.0.0.1", Port: port},
	})
	n.SetExtraTargets([]string{"127.0.0.1"})

	results := n.RunCheckCycle(5 * time.Second)
	if len(results) != 2 {
		t.Fatalf("expected 2 results, got %d", len(results))
	}

	peerResult := results[0]
	extraResult := results[1]

	if peerResult.IsExtra {
		t.Error("expected peer result to have IsExtra=false")
	}
	if !extraResult.IsExtra {
		t.Error("expected extra target result to have IsExtra=true")
	}
	if peerResult.TargetIP != extraResult.TargetIP {
		t.Error("both should target the same IP")
	}
}
