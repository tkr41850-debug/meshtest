package leader

import (
	"encoding/json"
	"log"
	"net/http"
	"strconv"
	"time"
)

type Leader struct {
	Registry      *Registry
	Results       *ResultsStore
	CheckInterval int
	BufferSize    int
	peersCh       chan struct{}
}

func NewLeader() *Leader {
	return &Leader{
		Registry:      NewRegistry(),
		Results:       NewResultsStore(),
		CheckInterval: DefaultCheckInterval,
		BufferSize:    DefaultBufferSize,
		peersCh:       make(chan struct{}, 1),
	}
}

func (l *Leader) writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.Header().Set("Access-Control-Allow-Origin", "*")
	w.WriteHeader(status)
	if err := json.NewEncoder(w).Encode(v); err != nil {
		log.Printf("Error encoding JSON: %v", err)
	}
}

func (l *Leader) writeError(w http.ResponseWriter, status int, msg string) {
	l.writeJSON(w, status, map[string]any{"error": msg, "status": status})
}

func (l *Leader) HandleLivez(w http.ResponseWriter, r *http.Request) {
	l.writeJSON(w, http.StatusOK, map[string]string{"status": "alive"})
}

func (l *Leader) HandleReadyz(w http.ResponseWriter, r *http.Request) {
	l.writeJSON(w, http.StatusOK, map[string]string{"status": "ready"})
}

func (l *Leader) HandleHealthz(w http.ResponseWriter, r *http.Request) {
	l.writeJSON(w, http.StatusOK, map[string]string{"status": "alive"})
}

func (l *Leader) HandleRegister(w http.ResponseWriter, r *http.Request) {
	var req RegisterRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil || req.NodeIP == "" {
		l.writeError(w, http.StatusBadRequest, "Missing node_ip")
		return
	}

	peers, _ := l.Registry.Register(req)

	go func() {
		l.notifyPeers()
	}()

	l.writeJSON(w, http.StatusOK, map[string]any{
		"status": "registered",
		"peers":  peers,
	})
}

func (l *Leader) HandleNodeList(w http.ResponseWriter, r *http.Request) {
	peers := l.Registry.PeerDicts()
	l.writeJSON(w, http.StatusOK, map[string]any{
		"nodes": peers,
		"count": len(peers),
	})
}

func (l *Leader) HandleSubmit(w http.ResponseWriter, r *http.Request) {
	var req SubmitRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		l.writeError(w, http.StatusBadRequest, "Invalid payload: empty body")
		return
	}
	if req.NodeIP == "" {
		l.writeError(w, http.StatusBadRequest, "Invalid payload: node_ip must be a string")
		return
	}
	if len(req.Checks) == 0 {
		l.writeError(w, http.StatusBadRequest, "Invalid payload: checks must be a non-empty array")
		return
	}
	if req.Timestamp == nil {
		l.writeError(w, http.StatusBadRequest, "Invalid payload: timestamp must be a number")
		return
	}

	l.Results.Add(req.NodeIP, req.Checks, *req.Timestamp)

	if req.NodeURL != "" && l.Registry.Get(req.NodeIP) == nil {
		parsedPort := DefaultListenPort
		l.Registry.Register(RegisterRequest{
			NodeIP: req.NodeIP,
			NodeURL: req.NodeURL,
			ListenPort: parsedPort,
		})
		go func() {
			l.notifyPeers()
		}()
	}

	l.writeJSON(w, http.StatusAccepted, map[string]any{
		"status": "accepted",
		"count":  len(req.Checks),
	})
}

func (l *Leader) HandleData(w http.ResponseWriter, r *http.Request) {
	window := r.URL.Query().Get("window")

	switch window {
	case "90m":
		result := l.Results.Query90m(l.Registry)
		l.writeJSON(w, http.StatusOK, result)
	case "90h":
		result := l.Results.Query90h()
		l.writeJSON(w, http.StatusOK, result)
	case "90d", "30d":
		result := l.Results.Query90d()
		l.writeJSON(w, http.StatusOK, result)
	default:
		l.writeError(w, http.StatusBadRequest,
			"Invalid or missing window parameter. Use ?window=90m, ?window=90h, or ?window=90d")
	}
}

func (l *Leader) HandleUpdateConfig(w http.ResponseWriter, r *http.Request) {
	var req UpdateConfigRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		l.writeError(w, http.StatusBadRequest, "Empty body")
		return
	}
	if req.CheckInterval == nil && req.BufferSize == nil {
		l.writeError(w, http.StatusBadRequest, "Empty body")
		return
	}

	if req.CheckInterval != nil {
		if *req.CheckInterval < 1 {
			l.writeError(w, http.StatusBadRequest, "check_interval must be a positive integer")
			return
		}
		l.CheckInterval = *req.CheckInterval
	}
	if req.BufferSize != nil {
		if *req.BufferSize < 1 {
			l.writeError(w, http.StatusBadRequest, "buffer_size must be a positive integer")
			return
		}
		l.BufferSize = *req.BufferSize
	}

	l.writeJSON(w, http.StatusOK, map[string]any{
		"status": "config_updated",
		"config": map[string]any{
			"check_interval": l.CheckInterval,
			"buffer_size":    l.BufferSize,
		},
	})

	go func() {
		l.notifyPeers()
	}()
}

func (l *Leader) notifyPeers() {
	select {
	case l.peersCh <- struct{}{}:
	default:
	}
}

func (l *Leader) PeerNotifyURL(node NodeInfo) string {
	if node.NodeURL != "" {
		return node.NodeURL + "/update-peers"
	}
	return "http://" + node.NodeIP + ":" + strconv.Itoa(node.ListenPort) + "/update-peers"
}

func (l *Leader) Mux() http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("GET /livez", l.HandleLivez)
	mux.HandleFunc("GET /readyz", l.HandleReadyz)
	mux.HandleFunc("GET /healthz", l.HandleHealthz)
	mux.HandleFunc("POST /register", l.HandleRegister)
	mux.HandleFunc("GET /node-list", l.HandleNodeList)
	mux.HandleFunc("POST /submit", l.HandleSubmit)
	mux.HandleFunc("GET /data", l.HandleData)
	mux.HandleFunc("POST /updateConfig", l.HandleUpdateConfig)
	return mux
}

func ServeLeader(bind string) error {
	leader := NewLeader()
	mux := leader.Mux()
	srv := &http.Server{
		Addr:    bind,
		Handler: mux,
	}
	log.Printf("Go leader starting on %s", bind)
	return srv.ListenAndServe()
}

func init() {
	// Ensure timestamps are Unix epoch format
	_ = time.Now().Unix()
}
