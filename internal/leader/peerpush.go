package leader

import (
	"bytes"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"strconv"
	"time"
)

type PeerPushPayload struct {
	Peers         []PeerDict `json:"peers"`
	CheckInterval int        `json:"check_interval"`
	BufferSize    int        `json:"buffer_size"`
}

func (l *Leader) PeerNotifyURL(nodeIP string) string {
	node := l.Registry.Get(nodeIP)
	if node == nil {
		return ""
	}
	if node.NodeURL != "" {
		return node.NodeURL + "/update-peers"
	}
	return fmt.Sprintf("http://%s:%d/update-peers", nodeIP, node.ListenPort)
}

func (l *Leader) notifyNode(nodeIP string) {
	url := l.PeerNotifyURL(nodeIP)
	if url == "" {
		return
	}

	payload := PeerPushPayload{
		Peers:         l.Registry.PeerDicts(),
		CheckInterval: l.CheckInterval,
		BufferSize:    l.BufferSize,
	}

	var buf bytes.Buffer
	if err := json.NewEncoder(&buf).Encode(payload); err != nil {
		log.Printf("Error encoding peer push payload: %v", err)
		return
	}

	client := &http.Client{Timeout: 5 * time.Second}
	resp, err := client.Post(url, "application/json", &buf)
	if err != nil {
		log.Printf("Failed to notify node %s: %v", nodeIP, err)
		return
	}
	resp.Body.Close()
	log.Printf("Peer notification sent to %s", nodeIP)
}

func (l *Leader) PushPeersToAll() {
	ips := l.Registry.AllIPs()
	for _, ip := range ips {
		l.notifyNode(ip)
	}
}

func (l *Leader) ListenForPeerPush() {
	for range l.peersCh {
		l.PushPeersToAll()
	}
}

func PeerNotifyURLForNode(nodeIP string, listenPort int, nodeURL string) string {
	if nodeURL != "" {
		return nodeURL + "/update-peers"
	}
	return "http://" + nodeIP + ":" + strconv.Itoa(listenPort) + "/update-peers"
}
