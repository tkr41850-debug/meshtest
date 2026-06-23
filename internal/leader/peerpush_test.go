package leader

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
)

func TestPeerNotifyURL(t *testing.T) {
	l := NewLeader()
	l.Registry.Register(RegisterRequest{
		NodeIP:     "10.0.0.1",
		ListenPort: 58080,
	})

	url := l.PeerNotifyURL("10.0.0.1")
	expected := "http://10.0.0.1:58080/update-peers"
	if url != expected {
		t.Errorf("expected %s, got %s", expected, url)
	}
}

func TestPeerNotifyURLWithNodeURL(t *testing.T) {
	l := NewLeader()
	l.Registry.Register(RegisterRequest{
		NodeIP:  "10.0.0.1",
		NodeURL: "http://10.0.0.1:59080",
	})

	url := l.PeerNotifyURL("10.0.0.1")
	expected := "http://10.0.0.1:59080/update-peers"
	if url != expected {
		t.Errorf("expected %s, got %s", expected, url)
	}
}

func TestPeerNotifyURLReturnsEmptyForUnknownNode(t *testing.T) {
	l := NewLeader()
	url := l.PeerNotifyURL("10.0.0.99")
	if url != "" {
		t.Errorf("expected empty, got %s", url)
	}
}

func TestNotifyNodeSendsCorrectPayload(t *testing.T) {
	var received PeerPushPayload
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		json.NewDecoder(r.Body).Decode(&received)
		w.WriteHeader(http.StatusOK)
	}))
	defer server.Close()

	l := NewLeader()
	l.Registry.Register(RegisterRequest{NodeIP: "10.0.0.1", NodeURL: server.URL})
	l.CheckInterval = 15
	l.BufferSize = 5000

	l.notifyNode("10.0.0.1")

	if len(received.Peers) != 1 {
		t.Errorf("expected 1 peer, got %d", len(received.Peers))
	}
	if received.CheckInterval != 15 {
		t.Errorf("expected check_interval 15, got %d", received.CheckInterval)
	}
	if received.BufferSize != 5000 {
		t.Errorf("expected buffer_size 5000, got %d", received.BufferSize)
	}
}

func TestPushPeersToAllSendsToAllNodes(t *testing.T) {
	count := 0
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		count++
		w.WriteHeader(http.StatusOK)
	}))
	defer server.Close()

	l := NewLeader()
	l.Registry.Register(RegisterRequest{NodeIP: "10.0.0.1", NodeURL: server.URL})
	l.Registry.Register(RegisterRequest{NodeIP: "10.0.0.2", NodeURL: server.URL})
	l.Registry.Register(RegisterRequest{NodeIP: "10.0.0.3", NodeURL: server.URL})

	l.PushPeersToAll()

	if count != 3 {
		t.Errorf("expected 3 notifications, got %d", count)
	}
}
