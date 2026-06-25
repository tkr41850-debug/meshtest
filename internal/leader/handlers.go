package leader

import (
	"context"
	"encoding/json"
	"log"
	"net/http"
	"os"
	"os/signal"
	"sync"
	"syscall"
	"time"
)

type Leader struct {
	mu            sync.RWMutex
	Registry      *Registry
	Results       *ResultsStore
	CheckInterval int
	BufferSize    int
	peersCh       chan struct{}
}

func (l *Leader) GetCheckInterval() int {
	l.mu.RLock()
	defer l.mu.RUnlock()
	return l.CheckInterval
}

func (l *Leader) GetBufferSize() int {
	l.mu.RLock()
	defer l.mu.RUnlock()
	return l.BufferSize
}

func NewLeader() *Leader {
	l := &Leader{
		Registry:      NewRegistry(),
		Results:       NewResultsStore(),
		CheckInterval: DefaultCheckInterval,
		BufferSize:    DefaultBufferSize,
		peersCh:       make(chan struct{}, 1),
	}
	LoadIntoMemory(l.Results)
	StartFlushLoop(l.Results)
	go l.ListenForPeerPush()
	return l
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

	l.notifyPeers()

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

	if req.NodeURL != "" {
		parsedPort := DefaultListenPort
		_, existing := l.Registry.Register(RegisterRequest{
			NodeIP: req.NodeIP,
			NodeURL: req.NodeURL,
			ListenPort: parsedPort,
		})
		if !existing {
			l.notifyPeers()
		}
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
		l.mu.Lock()
		l.CheckInterval = *req.CheckInterval
		l.mu.Unlock()
	}
	if req.BufferSize != nil {
		if *req.BufferSize < 1 {
			l.writeError(w, http.StatusBadRequest, "buffer_size must be a positive integer")
			return
		}
		l.mu.Lock()
		l.BufferSize = *req.BufferSize
		l.mu.Unlock()
	}

	l.mu.RLock()
	ci := l.CheckInterval
	bs := l.BufferSize
	l.mu.RUnlock()

	l.writeJSON(w, http.StatusOK, map[string]any{
		"status": "config_updated",
		"config": map[string]any{
			"check_interval": ci,
			"buffer_size":    bs,
		},
	})

	l.notifyPeers()
}

func (l *Leader) Stop() {
	StopFlushLoop()
	flushOnce(l.Results)
}

func (l *Leader) notifyPeers() {
	select {
	case l.peersCh <- struct{}{}:
	default:
	}
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
	mux.Handle("GET /", staticHandler)
	return mux
}

func ServeLeader(bind string) error {
	leader := NewLeader()
	mux := leader.Mux()
	srv := &http.Server{
		Addr:    bind,
		Handler: mux,
	}

	go func() {
		sigCh := make(chan os.Signal, 1)
		signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)
		<-sigCh
		log.Printf("Shutting down...")
		leader.Stop()
		ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
		defer cancel()
		srv.Shutdown(ctx)
	}()

	log.Printf("Go leader starting on %s", bind)
	err := srv.ListenAndServe()
	if err == http.ErrServerClosed {
		return nil
	}
	return err
}
