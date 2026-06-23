# Phase 33: Go Node Agent — Context

**Gathered:** 2026-06-22
**Status:** Ready for planning
**Mode:** Auto-generated (discuss skipped per autonomous flow)

<domain>
## Phase Boundary

Phase 33 implements the Go mesh node agent — ICMP ping via os/exec, HTTP health checks against all peers, result submission to the leader, and full cycle orchestration.

The node must:
1. Fetch peer list from leader via GET /node-list
2. Run ICMP ping against all peers concurrently with configurable timeout, parse ping stdout safely
3. Run HTTP GET /healthz against all peers concurrently with semaphore limiting
4. Submit results to leader via POST /submit after each cycle
5. Buffer results on submission failure and retry on next cycle, combining accumulated + current results
6. Full cycle: fetch peers → ping all → HTTP check all → submit results, on configurable interval

Requirements: GO-NODE-PING, GO-NODE-HTTP-CHECK, GO-NODE-SUBMIT, GO-NODE-CYCLE

</domain>

<decisions>
## Implementation Decisions

### OpenCode's Discretion
All implementation choices at OpenCode's discretion. Use Go standard library, net/http for checks, os/exec for ping. Match Python node behavior exactly.

</decisions>

<code_context>
## Existing Code Insights

Leader Go code exists at internal/leader/. Node will be at internal/node/. The node is simpler than the leader — it runs a loop with ping/HTTP checks against the peer list from the leader. Results are submitted via HTTP POST to the leader URL.

</code_context>

<specifics>
## Specific Ideas

- internal/node package with Node struct (LeaderURL, Peers, CheckInterval, Buffer, HTTP client)
- ICMP ping via `os/exec.CommandContext("ping", "-c", "1", "-W", timeout, ip)` with timeout
- HTTP health checks via `net/http` with semaphore (buffered chan) for concurrency limiting
- Submit via POST/submit to leader with JSON payload
- Buffer for failed submissions
- Main cycle: fetch peers → ping → HTTP → submit → sleep

</specifics>

<deferred>
## Deferred Ideas

None.

</deferred>
