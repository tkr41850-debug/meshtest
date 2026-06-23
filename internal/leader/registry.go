package leader

import (
	"sync"
	"time"
)

type Registry struct {
	mu    sync.RWMutex
	nodes map[string]*NodeInfo
}

func NewRegistry() *Registry {
	return &Registry{
		nodes: make(map[string]*NodeInfo),
	}
}

func (r *Registry) Register(req RegisterRequest) ([]PeerDict, bool) {
	r.mu.Lock()
	defer r.mu.Unlock()

	port := req.ListenPort
	if port == 0 {
		port = DefaultListenPort
	}

	existing := true
	if _, ok := r.nodes[req.NodeIP]; !ok {
		existing = false
	}

	r.nodes[req.NodeIP] = &NodeInfo{
		NodeIP:     req.NodeIP,
		Hostname:   req.Hostname,
		LastSeen:   float64(time.Now().Unix()),
		ListenPort: port,
		NodeURL:    req.NodeURL,
	}

	return r.peerDictsLocked(), existing
}

func (r *Registry) Get(nodeIP string) *NodeInfo {
	r.mu.RLock()
	defer r.mu.RUnlock()
	return r.nodes[nodeIP]
}

func (r *Registry) All() map[string]*NodeInfo {
	r.mu.RLock()
	defer r.mu.RUnlock()
	result := make(map[string]*NodeInfo, len(r.nodes))
	for k, v := range r.nodes {
		result[k] = v
	}
	return result
}

func (r *Registry) AllIPs() []string {
	r.mu.RLock()
	defer r.mu.RUnlock()
	ips := make([]string, 0, len(r.nodes))
	for ip := range r.nodes {
		ips = append(ips, ip)
	}
	return ips
}

func (r *Registry) PeerDicts() []PeerDict {
	r.mu.RLock()
	defer r.mu.RUnlock()
	return r.peerDictsLocked()
}

func (r *Registry) peerDictsLocked() []PeerDict {
	peers := make([]PeerDict, 0, len(r.nodes))
	for ip, info := range r.nodes {
		peers = append(peers, PeerDict{IP: ip, Port: info.ListenPort})
	}
	return peers
}
