package node

import (
	"fmt"
	"net/http"
	"time"
)

func CheckHTTP(targetIP string, port int, timeout time.Duration) HTTPResult {
	client := &http.Client{Timeout: timeout}
	start := time.Now()
	resp, err := client.Get(fmt.Sprintf("http://%s:%d/healthz", targetIP, port))
	if err != nil {
		return HTTPResult{}
	}
	defer resp.Body.Close()
	latency := time.Since(start).Seconds() * 1000
	return HTTPResult{
		OK:        resp.StatusCode >= 200 && resp.StatusCode < 300,
		Status:    resp.StatusCode,
		LatencyMs: latency,
	}
}
