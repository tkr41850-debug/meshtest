package node

import (
	"encoding/json"
	"fmt"
	"log"
	"net/http"

	"github.com/tkr41850-debug/meshtest/internal/leader"
)

type ListenForPeersPayload struct {
	Peers         []leader.PeerDict `json:"peers"`
	CheckInterval int               `json:"check_interval"`
	BufferSize    int               `json:"buffer_size"`
}

func StartListener(n *Node, port int) (*http.Server, error) {
	mux := http.NewServeMux()
	mux.HandleFunc("GET /healthz", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		json.NewEncoder(w).Encode(map[string]string{"status": "alive"})
	})

	mux.HandleFunc("POST /update-peers", func(w http.ResponseWriter, r *http.Request) {
		var payload ListenForPeersPayload
		if err := json.NewDecoder(r.Body).Decode(&payload); err != nil {
			http.Error(w, `{"error":"invalid JSON"}`, http.StatusBadRequest)
			return
		}

		if payload.Peers != nil {
			n.UpdatePeers(payload.Peers)
		}
		if payload.CheckInterval > 0 {
			n.UpdateConfig(payload.CheckInterval, payload.BufferSize)
		}
		log.Printf("Updated via push: %d peers, interval=%d, buffer=%d",
			len(payload.Peers), payload.CheckInterval, payload.BufferSize)

		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		json.NewEncoder(w).Encode(map[string]string{"status": "ok"})
	})

	addr := fmt.Sprintf(":%d", port)
	srv := &http.Server{
		Addr:    addr,
		Handler: mux,
	}

	go func() {
		log.Printf("Node HTTP server listening on %s", addr)
		if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Printf("Listener error: %v", err)
		}
	}()

	return srv, nil
}
