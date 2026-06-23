---
phase: 32-go-leader-persistence-peer-push
fixed_at: 2026-06-22T21:22:00Z
review_path: .planning/phases/32-go-leader-persistence-peer-push/32-REVIEW.md
iteration: 1
findings_in_scope: 9
fixed: 9
skipped: 0
status: all_fixed
---

# Phase 32: Code Review Fix Report

**Fixed at:** 2026-06-22T21:22:00Z
**Source review:** .planning/phases/32-go-leader-persistence-peer-push/32-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 9
- Fixed: 9
- Skipped: 0

## Fixed Issues

### CR-01: `checkPairStatus` ignores `srcIP` — produces incorrect connectivity matrix

**Files modified:** `internal/leader/results.go`
**Commit:** f1d2d7f
**Applied fix:** Changed the outer loop from iterating over ALL nodes (`for _, checks := range results`) to filtering by `srcIP` (`for _, c := range results[srcIP]`). The status matrix now correctly reflects each source node's own perspective rather than returning true if ANY node can reach the destination.

### CR-02: `flushOnce` re-flushes same data every cycle, causing progressive data duplication on disk

**Files modified:** `internal/leader/persistence.go`
**Commit:** 4d08f1b
**Applied fix:** Added package-level `lastFlushTimestamp float64` variable. Modified `flushOnce` to only include results with `c.Timestamp > lastFlushTimestamp` in the flush batch. After flushing, `lastFlushTimestamp` is updated to `time.Now()`. The two separate loops (build batch + trim/aggregate) were merged into a single pass for efficiency. If no new data exists since last flush, `AppendResults` is skipped entirely.

### WR-01: Data race on `Leader.CheckInterval` and `Leader.BufferSize`

**Files modified:** `internal/leader/handlers.go`, `internal/leader/peerpush.go`
**Commit:** 04fe091
**Applied fix:** Added `mu sync.RWMutex` to the `Leader` struct. In `HandleUpdateConfig`, config writes (`l.CheckInterval`, `l.BufferSize`) are protected with `l.mu.Lock()/Unlock()`. In `notifyNode`, config reads are protected with `l.mu.RLock()/RUnlock()` and stored in local variables before use.

### WR-02: `scanner.Err()` never checked in `ReadResults`

**Files modified:** `internal/leader/persistence.go`
**Commit:** d8ed51f
**Applied fix:** Added `if err := scanner.Err(); err != nil { log.Printf(...) }` check after the `scanner.Scan()` loop in `ReadResults`. If scanning stops due to an I/O error or line-too-long, the error is now visible in the logs.

### WR-03: `f.Close()` errors silently dropped in `AppendResults` and `ReadResults`

**Files modified:** `internal/leader/persistence.go`
**Commit:** cd110b8
**Applied fix:** Changed both `f.Close()` calls (in `AppendResults` and `ReadResults`) to `if err := f.Close(); err != nil { log.Printf(...) }`. Failed file close (e.g., disk full) is now logged.

### WR-04: `time.After` timer leak in `FlushLoop`

**Files modified:** `internal/leader/persistence.go`
**Commit:** d4781e2
**Applied fix:** Replaced `time.After(interval)` with `time.NewTimer(interval)` and `defer timer.Stop()`. On each iteration, the timer channel is used in the `select`, and `timer.Reset(interval)` is called after the flush. If `FlushLoop` exits via the `stop` channel, the deferred `Stop()` prevents the timer from firing.

### WR-05: `flushStopOnce` declared but never used; `StartFlushLoop`/`StopFlushLoop` unsafe under concurrent calls

**Files modified:** `internal/leader/persistence.go`
**Commit:** dac257f
**Applied fix:** Removed the unused `flushStopOnce sync.Once` variable. Added `startOnce sync.Once` to guard `StartFlushLoop` — subsequent calls are no-ops, preventing orphaned goroutines.

### WR-06: HTTP response status never checked in `notifyNode`

**Files modified:** `internal/leader/peerpush.go`
**Commit:** fdb90f8
**Applied fix:** Changed `resp.Body.Close()` to `defer resp.Body.Close()` and added a status code check after the HTTP POST in `notifyNode`. Non-2xx responses are logged and the function returns early.

### WR-07: `HandleSubmit` auto-registration has TOCTOU race

**Files modified:** `internal/leader/handlers.go`
**Commit:** efc6385
**Applied fix:** Replaced the TOCTOU pattern (`l.Registry.Get(req.NodeIP) == nil` check followed by separate `Register` call) with a single atomic `l.Registry.Register(...)` call. Uses the returned `existing` bool to determine whether to notify peers. Removed the unnecessary goroutine for `notifyPeers()` — calls it directly. Passes `ListenPort: 0` (registry defaults to `DefaultListenPort`).

## Skipped Issues

None — all 9 in-scope findings were successfully fixed.

---

_Fixed: 2026-06-22T21:22:00Z_
_Fixer: OpenCode (gsd-code-fixer)_
_Iteration: 1_
