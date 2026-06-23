package main

import (
	"context"
	"log"
	"net"
	"os"
	"os/signal"
	"strconv"
	"syscall"
	"time"

	"github.com/tkr41850-debug/meshtest/internal/node"
)

func getNodeIP() string {
	if ip := os.Getenv("NODE_IP"); ip != "" {
		return ip
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

func main() {
	leaderURL := os.Getenv("LEADER_URL")
	if leaderURL == "" {
		leaderURL = "http://localhost:58080"
	}

	nodeURL := os.Getenv("NODE_URL")
	listenPortStr := os.Getenv("NODE_LISTEN_PORT")
	listenPort := node.DefaultListenPort
	if listenPortStr != "" {
		if p, err := strconv.Atoi(listenPortStr); err == nil && p > 0 {
			listenPort = p
		} else {
			log.Printf("Warning: invalid NODE_LISTEN_PORT %q, using default %d", listenPortStr, listenPort)
		}
	}

	n := node.NewNode(leaderURL, nodeURL, listenPort)
	n.NodeIP = getNodeIP()

	srv, err := node.StartListener(n, listenPort)
	if err != nil {
		log.Fatalf("Failed to start listener: %v", err)
	}

	ctx := context.Background()
	if err := n.Register(ctx); err != nil {
		log.Fatalf("Registration failed: %v", err)
	}
	log.Printf("Registered as %s with leader at %s", n.NodeIP, leaderURL)

	sigCh := make(chan os.Signal, 1)
	signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)

	timeout := 5 * time.Second

	done := make(chan struct{})
	go func() {
		for {
			select {
			case <-done:
				return
			default:
			}

			peers, err := n.FetchPeers(ctx)
			if err == nil && peers != nil {
				n.UpdatePeers(peers)
			}

			results := n.RunCheckCycle(timeout)

			now := float64(time.Now().Unix())
			ok := n.SubmitResults(results, now)
			if ok {
				log.Printf("Submitted %d results", len(results))
			} else {
				log.Printf("Submit failed, will retry next cycle")
			}

			interval := n.GetCheckInterval()

			select {
			case <-time.After(time.Duration(interval) * time.Second):
			case <-done:
				return
			}
		}
	}()

	<-sigCh
	close(done)

	shutdownCtx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	srv.Shutdown(shutdownCtx)
	log.Println("Node shut down")
}
