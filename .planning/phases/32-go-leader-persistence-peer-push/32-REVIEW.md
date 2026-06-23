---
phase: 32-go-leader-persistence-peer-push
reviewed: 2026-06-22T20:20:00Z
depth: standard
files_reviewed: 6
files_reviewed_list:
  - internal/leader/persistence.go
  - internal/leader/peerpush.go
  - internal/leader/handlers.go
  - internal/leader/results.go
  - internal/leader/persistence_test.go
  - internal/leader/peerpush_test.go
findings:
  critical: 2
  warning: 7
  info: 5
  total: 14
status: issues_found
---

# Phase 32: Code Review Report — Leader Persistence & Peer Push

**Reviewed:** 2026-06-22T20:20:00Z
**Depth:** standard
**Files Reviewed:** 6
**Status:** issues_found

## Summary

This phase adds JSON Lines file persistence with date-partitioned directories, a peer notification system, and wires them into the Leader. Two critical bugs were found: (1) `checkPairStatus` ignores the `srcIP` parameter entirely, producing a wrong connectivity matrix, and (2) the flush loop re-flushes the same in-memory data every cycle, causing massive data duplication on disk. Seven warnings cover race conditions, unchecked errors, resource leaks, and dead code.

---

## Critical Issues

### CR-01: `checkPairStatus` ignores `srcIP` — produces incorrect connectivity matrix

**File:** `internal/leader/results.go:101-115`
**Issue:** The `checkPairStatus` function receives `srcIP` as a parameter but never uses it. Instead of checking results specific to the source node, it iterates over ALL nodes' results and returns true if ANY node has a successful check to `dstIP`. For example, if nodeA has a successful ping to nodeB, the status matrix incorrectly reports that nodeC is also connected to nodeB via ping.

```go
func checkPairStatus(results map[string][]CheckResult, srcIP, dstIP string, cutoff float64, checkType string) bool {
    for _, checks := range results {  // BUG: iterates all nodes, not just srcIP
        for _, c := range checks {
            if c.TargetIP == dstIP && c.Timestamp >= cutoff {
                if checkType == "ping" && c.PingOK {
                    return true
                }
                if checkType == "http" && c.HTTPOK {
                    return true
                }
            }
        }
    }
    return false
}
```

This makes `Query90m`/`HandleData?window=90m` return a meaningless status matrix. In a mesh with N nodes, the statuses would show every node as connected to a target if any single node can reach it.

**Fix:** Filter by `srcIP` in the outer loop:

```go
func checkPairStatus(results map[string][]CheckResult, srcIP, dstIP string, cutoff float64, checkType string) bool {
    for _, c := range results[srcIP] {
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

### CR-02: `flushOnce` re-flushes same data every cycle, causing progressive data duplication on disk

**File:** `internal/leader/persistence.go:166-221`
**Issue:** `flushOnce` drains ALL of `store.results` into a batch, writes it to disk, then trims the in-memory results to only the recent 90h window. Data within the 90h window remains in `store.results` and is flushed AGAIN on every subsequent cycle (default 3600s = 1 hour). Over 90 hours, each result is written up to 90 times.

This causes:
- Disk usage inflated up to 90× for recent data
- `ReadResults` returns duplicated data
- `LoadIntoMemory` (called on startup) loads all duplicates, inflating `dayAggregates` and `results` counts for the entire lifetime of the process
- Each restart compounds the inflation because disk data (already duplicated) is re-read and re-written

The root cause: `flushOnce` has no mechanism to track which data has already been flushed. Every cycle treats the entire 90h window as "new."

**Fix:** Track the last flush timestamp and only flush data with `Timestamp > lastFlushTimestamp`. After flushing, clear the flushed portion (or mark it). One approach:

```go
var lastFlushTimestamp float64

func flushOnce(store *ResultsStore) {
    store.mu.Lock()
    defer store.mu.Unlock()

    if len(store.results) == 0 {
        return
    }

    cutoff := float64(time.Now().Add(-90 * time.Hour).Unix())
    var batch []CheckResultWithNode

    for nodeIP, checks := range store.results {
        var remaining []CheckResult
        for _, c := range checks {
            if c.Timestamp > lastFlushTimestamp && c.Timestamp >= cutoff {
                batch = append(batch, CheckResultWithNode{
                    NodeIP: nodeIP,
                    TargetIP: c.TargetIP,
                    PingOK: c.PingOK,
                    HTTPOK: c.HTTPOK,
                    Timestamp: c.Timestamp,
                    LatencyMs: c.LatencyMs,
                })
            }
            if c.Timestamp >= cutoff {
                remaining = append(remaining, c)
            } else {
                // aggregate into dayAggregates
                ...
            }
        }
        if len(remaining) > 0 {
            store.results[nodeIP] = remaining
        } else {
            delete(store.results, nodeIP)
        }
    }

    if len(batch) > 0 {
        AppendResults(batch)
    }
    lastFlushTimestamp = float64(time.Now().Unix())
}
```

---

## Warnings

### WR-01: Data race on `Leader.CheckInterval` and `Leader.BufferSize`

**File:** `internal/leader/handlers.go:157,164` and `internal/leader/peerpush.go:38-39`

**Issue:** `HandleUpdateConfig` writes to `l.CheckInterval` and `l.BufferSize` without any synchronization (mutex or atomic). Meanwhile, `notifyNode` reads these same fields without synchronization. Access can happen concurrently because `notifyPeers()` is triggered in a goroutine after `HandleUpdateConfig` returns, and `ListenForPeerPush()` runs in its own goroutine. This is a data race under the Go memory model.

**Fix:** Protect with `sync.RWMutex` or use `atomic.Int64`. For example:

```go
type Leader struct {
    mu            sync.RWMutex
    Registry      *Registry
    Results       *ResultsStore
    CheckInterval int
    BufferSize    int
    peersCh       chan struct{}
}

func (l *Leader) notifyNode(nodeIP string) {
    l.mu.RLock()
    ci := l.CheckInterval
    bs := l.BufferSize
    l.mu.RUnlock()
    // use ci, bs
}
```

### WR-02: `scanner.Err()` never checked in `ReadResults`

**File:** `internal/leader/persistence.go:82-93`

**Issue:** After the `scanner.Scan()` loop, the code never checks `scanner.Err()`. If scanning stops because of a read error (e.g., I/O error, line too long for the scanner buffer), results are silently truncated. Callers receive a partial data set with no indication of failure.

```go
for scanner.Scan() {
    // ... process line
}
// scanner.Err() is not checked
f.Close()
```

**Fix:** After the loop, check `scanner.Err()` and log the error:

```go
for scanner.Scan() {
    // ... process line
}
if err := scanner.Err(); err != nil {
    log.Printf("Error reading file %s: %v", path, err)
}
f.Close()
```

### WR-03: `f.Close()` errors silently dropped in `AppendResults` and `ReadResults`

**File:** `internal/leader/persistence.go:65,94`

**Issue:** Both `AppendResults` and `ReadResults` call `f.Close()` without checking the error. On `AppendResults`, a failed `Close()` (e.g., due to disk full or I/O error) means data may not be fully flushed from the OS buffer to disk, resulting in silent data loss.

**Fix:** Log close errors, at minimum:

```go
if err := f.Close(); err != nil {
    log.Printf("Error closing file %s: %v", path, err)
}
```

### WR-04: `time.After` timer leak in `FlushLoop`

**File:** `internal/leader/persistence.go:160`

**Issue:** `time.After(interval)` creates a new `time.Timer` on each loop iteration. If `FlushLoop` exits via the `stop` channel, the pending timer is not stopped/released. The timer will fire (wasting a wakeup) and then be garbage collected. In normal operation the leak is small, but repeated stop/start cycles accumulate leaked timers.

**Fix:** Use `time.NewTimer` with explicit `timer.Stop()`:

```go
timer := time.NewTimer(interval)
for {
    select {
    case <-stop:
        timer.Stop()
        return
    case <-timer.C:
        flushOnce(store)
        timer.Reset(interval)
    }
}
```

### WR-05: `flushStopOnce` declared but never used; `StartFlushLoop`/`StopFlushLoop` unsafe under concurrent calls

**File:** `internal/leader/persistence.go:223-237`

**Issue:** `flushStopOnce` is declared as `sync.Once` at line 224 but `flushStopOnce.Do(...)` is never called — it is dead code. Additionally, `StartFlushLoop` unconditionally overwrites the package-level `stopFlush` channel. If called twice, the first goroutine's stop channel is orphaned and the goroutine leaks. `StopFlushLoop` only closes the most recent channel.

**Fix:** Remove the unused `flushStopOnce`. Guard `StartFlushLoop` to prevent multiple calls:

```go
var (
    stopFlush chan struct{}
    startOnce sync.Once
)

func StartFlushLoop(store *ResultsStore) {
    startOnce.Do(func() {
        stopFlush = make(chan struct{})
        go FlushLoop(store, time.Duration(FlushInterval)*time.Second, stopFlush)
    })
}
```

### WR-06: HTTP response status never checked in `notifyNode`

**File:** `internal/leader/peerpush.go:48-55`

**Issue:** `notifyNode` calls `client.Post`, then closes the response body immediately without checking `resp.StatusCode`. If the target node returns an error (e.g., 404, 500), the leader silently assumes the peer push succeeded. Failed notifications are invisible.

```go
resp, err := client.Post(url, "application/json", &buf)
if err != nil {
    log.Printf("Failed to notify node %s: %v", nodeIP, err)
    return
}
resp.Body.Close()  // status code never checked
```

**Fix:** Check the status code and log non-2xx responses:

```go
resp, err := client.Post(url, "application/json", &buf)
if err != nil {
    log.Printf("Failed to notify node %s: %v", nodeIP, err)
    return
}
defer resp.Body.Close()
if resp.StatusCode < 200 || resp.StatusCode >= 300 {
    log.Printf("Peer notification to %s returned status %d", nodeIP, resp.StatusCode)
}
```

### WR-07: `HandleSubmit` auto-registration has TOCTOU race

**File:** `internal/leader/handlers.go:104-106`

**Issue:** Between `l.Registry.Get(req.NodeIP)` (the check) and `l.Registry.Register(...)` (the insert), another goroutine could register the same node. While `Register` is idempotent (it overwrites), the race means `notifyPeers()` may not be called when a genuinely new node registers concurrently with a different request.

Additionally, `RegisterRequest.ListenPort` defaults to `DefaultListenPort` when 0, so the explicit `parsedPort := DefaultListenPort` at line 105 is redundant (but harmless). More importantly, the condition `req.NodeURL != ""` means a node submitting checks without a URL will never be auto-registered, even if it has a valid `node_ip`. This is by design but worth noting.

**Fix:** Use a single atomic operation. The simplest fix is to always call Register and check the returned `existing` bool:

```go
if req.NodeURL != "" {
    _, existing := l.Registry.Register(RegisterRequest{
        NodeIP:     req.NodeIP,
        NodeURL:    req.NodeURL,
        ListenPort: 0,  // registry defaults to DefaultListenPort
    })
    if !existing {
        go l.notifyPeers()
    }
}
```

---

## Info

### IN-01: Unused type `sortableByDate`

**File:** `internal/leader/results.go:273-275`

**Issue:** `sortableByDate` is defined but never referenced anywhere in the codebase. It is dead code that creates compilation noise.

**Fix:** Remove the unused type.

### IN-02: Unused function `PeerNotifyURLForNode`

**File:** `internal/leader/peerpush.go:71-76`

**Issue:** `PeerNotifyURLForNode` is exported but never called within the `leader` package or anywhere else in the codebase. It is dead code. If intended for external use, add a consumer; otherwise remove it.

**Fix:** Remove or add a consumer.

### IN-03: Unnecessary goroutine in `HandleRegister`

**File:** `internal/leader/handlers.go:65-67`

**Issue:** `HandleRegister` launches a goroutine solely to call `l.notifyPeers()`, which does a non-blocking send on a buffered channel. The send cannot block (capacity 1, non-blocking send via `select/default`). The goroutine creates unnecessary scheduling overhead.

**Fix:** Call `l.notifyPeers()` directly (same for `HandleSubmit` line 111-113 and `HandleUpdateConfig` line 175-177):

```go
l.notifyPeers()
```

### IN-04: `FlushInterval` not configurable via environment variable

**File:** `internal/leader/persistence.go:18`

**Issue:** `FlushInterval` is a package-level variable hardcoded to 3600 seconds. `DataDir` on the other hand is configurable via `DATA_DIR` env var. This inconsistency makes deployment configuration harder — operators cannot tune the flush interval without code changes.

**Fix:** Add env-var support:

```go
var FlushInterval = 3600

func init() {
    if v := os.Getenv("FLUSH_INTERVAL"); v != "" {
        if i, err := strconv.Atoi(v); err == nil && i > 0 {
            FlushInterval = i
        }
    }
    if DataDir == "" {
        DataDir = "data"
    }
}
```

### IN-05: Missing `Hostname` passthrough in `HandleSubmit` auto-registration

**File:** `internal/leader/handlers.go:106-110`

**Issue:** When `HandleSubmit` auto-registers a node, it constructs a `RegisterRequest` with only `NodeIP`, `NodeURL`, and `ListenPort`. The `SubmitRequest` struct does not include a `Hostname` field, so hostname information is lost for auto-registered nodes. This is a minor gap — explicit `/register` calls can still provide hostnames.

**Fix:** Consider adding a `Hostname` field to `SubmitRequest` and plumbing it through to `RegisterRequest` in the auto-registration path.

---

**Critical findings: 2 | Warnings: 7 | Info: 5 | Total: 14**

_Reviewed: 2026-06-22T20:20:00Z_
_Reviewer: OpenCode (gsd-code-reviewer)_
_Depth: standard_
