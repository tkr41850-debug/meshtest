---
phase: 33-go-node-agent
reviewed: 2026-06-22T22:00:00Z
depth: standard
files_reviewed: 7
files_reviewed_list:
  - internal/node/node.go
  - internal/node/ping.go
  - internal/node/httpcheck.go
  - internal/node/listener.go
  - internal/node/node_test.go
  - cmd/node/main.go
  - internal/leader/handlers.go
findings:
  critical: 3
  warning: 6
  info: 3
  total: 12
status: issues_found
---

# Phase 33: Go Node Agent — Code Review Report

**Reviewed:** 2026-06-22T22:00:00Z
**Depth:** standard
**Files Reviewed:** 7
**Status:** issues_found

## Summary

This review covers the Go node agent implementation: ICMP ping via os/exec, HTTP health checks, result submission, peer listener HTTP server, and cycle orchestration. Three blocker bugs were found: a channel double-close that panics on every shutdown, a hardcoded `127.0.0.1` node IP that makes all nodes indistinguishable to the leader, and an `srcIP` parameter unused in `checkPairStatus` that produces incorrect per-pair status results. Additionally, the buffer/retry mechanism declared in the struct is unimplemented, latency data is computed but discarded, and there are several code quality issues.

## Critical Issues

### CR-01: Double close of `done` channel causes panic on shutdown

**File:** `cmd/node/main.go:50` and `cmd/node/main.go:84`
**Issue:** The `done` channel is closed twice — once by `close(done)` on line 84 (signal handler) and once by `defer close(done)` on line 50 (goroutine's deferred cleanup). When the signal is received:

1. Main goroutine calls `close(done)` (line 84)
2. Worker goroutine's `select` detects closed `done`, returns from the loop/function
3. `defer close(done)` at line 50 executes → **panic: close of closed channel**

This will panic on every graceful shutdown (SIGINT/SIGTERM).

**Fix:** Remove the `defer close(done)` from line 50. The main goroutine already owns closing `done`.

```go
// Before (line 49-50):
go func() {
    defer close(done)    // ← BUG: double close
    for {
        ...
    }
}()

// After:
go func() {
    for {
        ...
    }
}()
```

### CR-02: NodeIP hardcoded to 127.0.0.1 — all nodes indistinguishable

**File:** `internal/node/node.go:57`
**Issue:** `NewNode` hardcodes `NodeIP` to `"127.0.0.1"`. This value is sent to the leader in both `Register` (line 181) and `SubmitResults` (line 71) as the `node_ip` identifier. Since every node sends `"127.0.0.1"`, the leader's registry (keyed by `NodeIP`) can only track one node — all registrations overwrite each other, and all submitted results are attributed to a single node.

The plan explicitly called for "determine own IP" behavior. No env var or network interface discovery is implemented.

**Fix:** Either read `NODE_IP` from environment or discover the node's IP from a network interface. At minimum:

```go
// In main.go or NewNode:
nodeIP := os.Getenv("NODE_IP")
if nodeIP == "" {
    // Discover from network interface
    addrs, err := net.InterfaceAddrs()
    if err == nil {
        for _, addr := range addrs {
            if ipnet, ok := addr.(*net.IPNet); ok && !ipnet.IP.IsLoopback() && ipnet.IP.To4() != nil {
                nodeIP = ipnet.IP.String()
                break
            }
        }
    }
}
if nodeIP == "" {
    nodeIP = "127.0.0.1" // fallback only
}
```

### CR-03: `checkPairStatus` ignores `srcIP` — yields incorrect per-pair status

**File:** `internal/leader/results.go:101-115`
**Issue:** The function `checkPairStatus` accepts a `srcIP` parameter but never uses it. It iterates over **all** nodes' results to determine if a specific source→destination pair is healthy:

```go
func checkPairStatus(results map[string][]CheckResult, srcIP, dstIP string, ...) bool {
    for _, checks := range results {  // iterates ALL nodes, not srcIP's
        for _, c := range checks {
            if c.TargetIP == dstIP && c.Timestamp >= cutoff {
```

This means `pingOK` for pair (A, B) returns true if **any** node reports a successful ping to B — even if A itself failed. The status matrix in `Query90m` will show false positives.

**Fix:** Look up only the source node's results:

```go
func checkPairStatus(results map[string][]CheckResult, srcIP, dstIP string, cutoff float64, checkType string) bool {
    nodeResults, ok := results[srcIP]
    if !ok {
        return false
    }
    for _, c := range nodeResults {
        if c.TargetIP == dstIP && c.Timestamp >= cutoff {
            if checkType == "ping" && c.PingOK {
                return true
            }
            if checkType == "http" && c.HTTPOK {
                return true
            }
        }
    }
    return false
}
```

## Warnings

### WR-01: Latency data computed but discarded

**File:** `internal/node/node.go:127-132`
**Issue:** `PingNode` returns `PingResult` with `LatencyMs` populated (ping.go:28). `CheckHTTP` returns `HTTPResult` with `LatencyMs` populated (httpcheck.go:17). But in `RunCheckCycle`, neither latency value is stored in the `CheckCycleResult`:

```go
ch <- result{i, CheckCycleResult{
    TargetIP:  p.IP,
    PingOK:    pingRes.OK,
    HTTPOK:    httpRes.OK,
    Timestamp: now,
    // LatencyMs omitted — defaults to 0
}}
```

Since `CheckCycleResult.LatencyMs` has `json:"latency_ms,omitempty"`, a zero value is omitted from the submission payload entirely, so the leader never sees latency data.

**Fix:** Set `LatencyMs` from the ping result. (Or both, if needed — but at minimum ping latency should be submitted.)

```go
ch <- result{i, CheckCycleResult{
    TargetIP:  p.IP,
    PingOK:    pingRes.OK,
    HTTPOK:    httpRes.OK,
    Timestamp: now,
    LatencyMs: pingRes.LatencyMs,
}}
```

### WR-02: Buffer/retry mechanism not implemented

**File:** `internal/node/node.go:50` and `internal/node/node.go:68-92`
**Issue:** The `Node` struct declares `resultBuffer` (line 50) and `BufferSize` (line 49), but neither is ever used. `SubmitResults` (line 68) simply returns false on failure — the caller in main.go (line 67-71) logs and moves on, dropping the results entirely. The plan explicitly requires: "On failure, buffer results (deque maxlen=BufferSize)" and "Combine buffered + current on each cycle."

Without buffering, transient leader failures cause permanent data loss.

**Fix:** Implement the buffer mechanism in `SubmitResults`:

```go
func (n *Node) SubmitResults(checks []CheckCycleResult, timestamp float64) bool {
    // Combine buffer with new results
    n.mu.Lock()
    if len(n.resultBuffer) > 0 {
        allChecks := n.resultBuffer
        space := n.BufferSize - len(allChecks)
        if len(checks) < space {
            space = len(checks)
        }
        allChecks = append(allChecks, checks[:space]...)
        checks = allChecks
        n.resultBuffer = nil
    }
    n.mu.Unlock()

    var buf bytes.Buffer
    // ... encode and submit ...

    if submitFails {
        // Buffer on failure
        n.mu.Lock()
        n.resultBuffer = append(n.resultBuffer, checks...)
        if len(n.resultBuffer) > n.BufferSize {
            n.resultBuffer = n.resultBuffer[len(n.resultBuffer)-n.BufferSize:]
        }
        n.mu.Unlock()
        return false
    }
    return true
}
```

### WR-03: HTTP response body not drained before close

**File:** `internal/node/httpcheck.go:16`
**Issue:** `resp.Body.Close()` is called without first reading the body to EOF. Per Go's `net/http` documentation, if the body is not read to EOF before closing, the Client's underlying `RoundTripper` may not reuse the TCP connection for keep-alive. Under repeated health-check load, this will degrade to opening a new connection per check, increasing latency and resource usage.

**Fix:** Discard and close the body properly:

```go
defer func() {
    io.Copy(io.Discard, resp.Body)
    resp.Body.Close()
}()
```

Or more concisely:

```go
defer resp.Body.Close()
// Drain body for connection reuse
_, _ = io.Copy(io.Discard, resp.Body)
```

### WR-04: Regex compiled on every ping call

**File:** `internal/node/ping.go:21`
**Issue:** `regexp.MustCompile` is called inside `PingNode`, which recompiles the regex on every invocation. Since `ping` runs every check cycle against every peer, this is unnecessarily expensive.

**Fix:** Move the regex to a package-level compiled variable:

```go
var pingRx = regexp.MustCompile(`time=(\d+\.?\d*)\s*ms`)
```

### WR-05: Duplicate struct definitions between node and leader packages

**File:** `internal/node/node.go:33-39` and `internal/leader/models.go:11-17`
**Issue:** `CheckCycleResult` (node) and `CheckResult` (leader) are byte-for-byte identical in structure and JSON tags. They are serialized by one package and deserialized by the other. If either struct is modified independently, the cross-package JSON contract will silently break.

**Fix:** Either move the shared type to a common package, or have the node package import the leader type:

- Option A: Define a single `CheckResult` type in `internal/leader/models.go` and reference it from `internal/node/node.go`.
- Option B: Create a shared `internal/types` package or use `leader.CheckResult` directly in the node's `SubmitResults`.

### WR-06: Fragile port parsing in tests

**File:** `internal/node/node_test.go:21-26` (and repeated lines 43-48, 65-70, 208-213)
**Issue:** Port parsing from `httptest.Server.URL` uses manual string manipulation instead of `net/url` parsing or `server.Listener.Addr()`. This breaks if `httptest.NewServer` ever returns an IPv6 address (which includes brackets, e.g., `http://[::1]:58080`). The custom `for` loop character-by-character conversion is also fragile and unnecessary.

**Fix:** Use `net/url` to parse or the listener's address directly:

```go
// Option A: Using net/url
u, _ := url.Parse(server.URL)
portStr := u.Port()
portInt, _ := strconv.Atoi(portStr)

// Option B: Using Listener.Addr (Go 1.x)
portInt := server.Listener.Addr().(*net.TCPAddr).Port
```

## Info

### IN-01: Package-level defaults should be `const`, not `var`

**File:** `internal/node/node.go:16-18`
**Issue:** `DefaultCheckInterval`, `DefaultBufferSize`, and `DefaultListenPort` are declared as `var` but are never mutated (they serve as immutable defaults). The corresponding values in `internal/leader/models.go:78-81` are also `var`.

**Fix:** Use `const` for immutable default values:

```go
const (
    DefaultCheckInterval = 10
    DefaultBufferSize    = 20000
    DefaultListenPort    = 58081
)
```

Note: requires changing the `Node` struct field types for `CheckInterval` and `BufferSize` if they need to differ from defaults, but the constructor already handles this.

### IN-02: `Run(ctx)` method not implemented per plan

**File:** `cmd/node/main.go:48-81`
**Issue:** The plan specifies a `Run(ctx)` method on the `Node` struct as the infinite check loop entry point (plan line 15: `Run(ctx)` — infinite check loop: fetchPeers → runCheckCycle → submitResults → sleep). Instead, this loop is inline in `main.go`. Moving it to a method would improve testability and allow the main function to be simpler.

**Fix:** Move the cycle loop to a method on `Node`:

```go
// In internal/node/node.go
func (n *Node) Run(ctx context.Context, done chan struct{}) {
    // loop: fetchPeers → runCheckCycle → submitResults → sleep
}
```

### IN-03: `NODE_LISTEN_PORT` env var silently misparsed

**File:** `cmd/node/main.go:22-28`
**Issue:** If `NODE_LISTEN_PORT` is set to an invalid value (e.g., `"abc"` or `"0"`), the error is silently swallowed and the default port 58081 is used. While this is a reasonable fallback, the silent swallow means a configuration typo goes unnoticed.

```go
if p, err := strconv.Atoi(listenPortStr); err == nil && p > 0 {
    listenPort = p
}
```

**Fix:** Log a warning when the env var is present but invalid:

```go
if listenPortStr != "" {
    if p, err := strconv.Atoi(listenPortStr); err == nil && p > 0 {
        listenPort = p
    } else if err != nil {
        log.Printf("Warning: invalid NODE_LISTEN_PORT %q, using default %d", listenPortStr, listenPort)
    }
}
```

---

_Reviewed: 2026-06-22T22:00:00Z_
_Reviewer: OpenCode (gsd-code-reviewer)_
_Depth: standard_
