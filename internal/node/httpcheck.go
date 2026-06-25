package node

import (
	"fmt"
	"io"
	"net"
	"net/http"
	"time"
)

func CheckHTTP(targetIP string, port int, timeout time.Duration) HTTPResult {
	client := &http.Client{Timeout: timeout}
	start := time.Now()
	url := fmt.Sprintf("http://%s/healthz", net.JoinHostPort(targetIP, fmt.Sprintf("%d", port)))
	resp, err := client.Get(url)
	if err != nil {
		return HTTPResult{}
	}
	defer resp.Body.Close()
	io.Copy(io.Discard, resp.Body)
	latency := time.Since(start).Seconds() * 1000
	return HTTPResult{
		OK:        resp.StatusCode >= 200 && resp.StatusCode < 300,
		Status:    resp.StatusCode,
		LatencyMs: latency,
	}
}
