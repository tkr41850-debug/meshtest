package node

import (
	"context"
	"fmt"
	"os/exec"
	"regexp"
	"time"
)

var pingRx = regexp.MustCompile(`time=(\d+\.?\d*)\s*ms`)

func PingNode(targetIP string, timeout time.Duration) PingResult {
	ctx, cancel := context.WithTimeout(context.Background(), timeout+500*time.Millisecond)
	defer cancel()

	cmd := exec.CommandContext(ctx, "ping", "-c", "1", "-W", fmt.Sprintf("%d", int(timeout.Seconds())), targetIP)
	stdout, err := cmd.Output()
	if err != nil {
		return PingResult{}
	}

	match := pingRx.FindStringSubmatch(string(stdout))
	if match == nil {
		return PingResult{OK: true}
	}
	var latency float64
	fmt.Sscanf(match[1], "%f", &latency)
	return PingResult{OK: true, LatencyMs: latency}
}
