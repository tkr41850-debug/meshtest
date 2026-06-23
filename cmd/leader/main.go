package main

import (
	"log"
	"os"

	"github.com/tkr41850-debug/meshtest/internal/leader"
)

func main() {
	port := os.Getenv("LEADER_PORT")
	if port == "" {
		port = "58080"
	}
	bind := "0.0.0.0:" + port
	log.Printf("mesh-status Go leader starting on %s", bind)
	if err := leader.ServeLeader(bind); err != nil {
		log.Fatalf("Server error: %v", err)
	}
}
