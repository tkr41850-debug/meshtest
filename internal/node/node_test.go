package node

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	"github.com/tkr41850-debug/meshtest/internal/leader"
)

func TestCheckHTTPHealthy(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		json.NewEncoder(w).Encode(map[string]string{"status": "alive"})
	}))
	defer server.Close()

	port := strings.TrimPrefix(server.URL, "http://")
	port = port[strings.Index(port, ":")+1:]
	portInt := 0
	for _, c := range port {
		portInt = portInt*10 + int(c-'0')
	}

	result := CheckHTTP("127.0.0.1", portInt, 5*time.Second)
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

	port := strings.TrimPrefix(server.URL, "http://")
	port = port[strings.Index(port, ":")+1:]
	portInt := 0
	for _, c := range port {
		portInt = portInt*10 + int(c-'0')
	}

	result := CheckHTTP("127.0.0.1", portInt, 5*time.Second)
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

	port := strings.TrimPrefix(server.URL, "http://")
	port = port[strings.Index(port, ":")+1:]
	portInt := 0
	for _, c := range port {
		portInt = portInt*10 + int(c-'0')
	}

	result := CheckHTTP("127.0.0.1", portInt, 100*time.Millisecond)
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
	// Start a test HTTP server to check
	healthServer := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
	}))
	defer healthServer.Close()

	healthPort := strings.TrimPrefix(healthServer.URL, "http://")
	healthPort = healthPort[strings.Index(healthPort, ":")+1:]
	portInt := 0
	for _, c := range healthPort {
		portInt = portInt*10 + int(c-'0')
	}

	n := NewNode("http://localhost:58080", "", 0)
	n.UpdatePeers([]leader.PeerDict{
		{IP: "127.0.0.1", Port: portInt},
	})

	results := n.RunCheckCycle(5 * time.Second)
	if len(results) != 1 {
		t.Fatalf("expected 1 result, got %d", len(results))
	}
	if !results[0].HTTPOK {
		t.Errorf("expected HTTP OK, got false")
	}
}
