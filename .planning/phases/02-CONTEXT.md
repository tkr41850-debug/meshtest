# Phase 2: Node Agent - Context

**Gathered:** 2026-06-18
**Status:** Ready for planning

<domain>
## Phase Boundary

A standalone `node.py` script that registers with the leader, then runs an async loop: fetches peer list from leader, runs ICMP ping + HTTP GET /healthz against all peers concurrently with semaphore limiting, submits results to leader's POST /submit, and buffers results in memory on submission failure with retry next cycle. The leader pushes config updates to nodes via POST /updateConfig.

What this phase does NOT include: persistence (Phase 3), dashboard (Phase 4). This phase only builds the node-side agent.
</domain>

<decisions>
## Implementation Decisions

### Node Agent Architecture
- Agent script type: Standalone `node.py` at repo root (separate process from leader)
- Loop design: `async def run_checks()` with `asyncio.sleep(interval)` in a forever loop
- Config push: Leader pushes config via POST /updateConfig to node (same port 58080)
- Logging: Same pattern as leader — `logging` to stderr at INFO level

### Ping Integration
- Ping timeout: 5 seconds per ping (`-W 5` on Linux via system `ping`)
- Output parsing: Parse `time=XX ms` from stdout with regex
- Cancellation-safe pattern: `asyncio.wait_for(process.wait(), timeout=5)` + `process.kill()` then `await process.wait()`

### HTTP Health Check
- HTTP client: `httpx.AsyncClient` with timeout per request
- Timeout per target: 5 seconds
- Expected response: Any 2xx from GET /healthz
- Method: GET /healthz

### Buffer & Retry
- Buffer capacity: Configurable cycle count, default 20000 cycles (~1.16 days at 5s)
- Retry strategy: Retry next cycle — attempt submit every cycle
- Overflow behavior: Drop oldest (FIFO eviction)
- What's buffered: Entire SubmitPayload for the last cycle that failed

### OpenCode's Discretion
- Exact regex pattern for ping output parsing
- Semaphore concurrency limit value
- Logging detail level per operation
</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `mesh_status/models.py` — CheckResult, SubmitPayload models already exist
- `mesh_status/config.py` — CHECK_INTERVAL, LEADER_PORT config
- `mesh_status/leader.py` — POST /submit and GET /node-list endpoints

### Established Patterns
- Async pattern from leader: `asyncio.create_subprocess_exec`, `httpx.AsyncClient`
- Logging to stderr at INFO level
- JSON payload format for /submit

### Integration Points
- Phase 1: Uses POST /submit and GET /node-list from leader
- Phase 3: Persistence will consume the data flowing through /submit
- Phase 4: Dashboard will display node check results
</code_context>

<specifics>
## Specific Ideas

- Node listens for config updates on POST /updateConfig on same port (58080)
- Configurable buffer length (default 20000 cycles)
- Leader pushes config changes alongside peer list pushes
</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.
</deferred>
