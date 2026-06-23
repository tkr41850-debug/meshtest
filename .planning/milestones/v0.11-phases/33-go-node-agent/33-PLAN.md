# Phase 33: Go Node Agent — Plan

## Goal
Implement Go mesh node agent matching Python node.py behavior: ICMP ping, HTTP checks, result submission, buffer/retry, cycle orchestration.

## Files to Create

### `cmd/node/main.go`
- Entry point, parses `LEADER_URL` and `NODE_URL` env vars
- Creates Node, starts HTTP peer listener, registers with leader, runs check loop

### `internal/node/node.go`
- Node struct: LeaderURL, NodeIP, NodeURL, ListenPort, Peers, CheckInterval, BufferSize, resultBuffer, client
- `NewNode(leaderURL, nodeURL string) *Node` — determine own IP, parse node URL
- `Run(ctx)` — infinite check loop: fetchPeers → runCheckCycle → submitResults → sleep
- `UpdatePeers(peers []PeerDict)` — update peer list
- `UpdateConfig(interval, bufferSize int)` — update config

### `internal/node/ping.go`
- `pingNode(targetIP string, timeout time.Duration) PingResult`
- Uses `os/exec` with `ping -c 1 -W <timeout> <ip>`
- Parses `time=` from stdout for latency
- Returns ping_ok, latency_ms

### `internal/node/httpcheck.go`
- `httpCheck(targetIP string, port int, timeout time.Duration) HTTPResult`
- GET `http://{ip}:{port}/healthz`
- Returns http_ok, http_status, latency_ms

### `internal/node/submit.go`
- `SubmitResults(checks []CheckResult) bool`
- POST to `{leaderURL}/submit` with node_ip, node_url, checks, timestamp
- On failure, buffer results (deque maxlen=BufferSize)
- Combine buffered + current on each cycle

### `internal/node/listener.go`
- HTTP server for GET /healthz and POST /update-peers
- POST /update-peers updates Peers, CheckInterval, BufferSize

## Test Strategy
- Ping: mock exec.Command, test parsing
- HTTP check: test with httptest server
- Submit: test with httptest server (success + failure)
- Node cycle: test full cycle with mocked components
