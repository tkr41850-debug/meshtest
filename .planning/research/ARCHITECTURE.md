# Architecture Research

**Domain:** Distributed mesh connectivity testing (leader-node push model)
**Researched:** 2026-06-18
**Confidence:** HIGH

## Standard Architecture

### System Overview

The system follows a **centralized leader with distributed probing nodes** pattern. This is distinct from Prometheus Blackbox Exporter's pull model (leader scrapes targets). Instead, nodes proactively push results to the leader — analogous to Celery/Airflow worker heartbeats but for mesh connectivity health.

```
┌──────────────────────────────────────────────────────────────────────┐
│                          Leader (Quart Server)                         │
│                                                                        │
│  ┌──────────────────┐  ┌──────────────────┐  ┌────────────────────┐  │
│  │  Registration    │  │  Result Ingestion │  │  Data API /        │  │
│  │  Handler         │  │  Handler          │  │  Frontend          │  │
│  │  POST /register  │  │  POST /submit     │  │  GET /data         │  │
│  └────────┬─────────┘  └────────┬─────────┘  │  Streamlit         │  │
│           │                     │             └────────────────────┘  │
│           │                     │                                      │
│  ┌────────▼─────────────────────▼──────────────────────────────────┐  │
│  │                    State Manager (in-memory)                      │  │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌───────────┐  │  │
│  │  │ Node       │  │ Node IP    │  │ Check      │  │ Metrics   │  │  │
│  │  │ Registry   │  │ List Cache │  │ Results    │  │ Accumul.  │  │  │
│  │  └────────────┘  └────────────┘  └────────────┘  └───────────┘  │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│           │                                                           │
│  ┌────────▼──────────────────────────────────────────────────────────┐│
│  │                    Persistence Layer (hourly)                       ││
│  │    data/[yyyy]/[mm]/[dd].json  ←  Append hourly batch             ││
│  └──────────────────────────────────────────────────────────────────┘│
└──────────────────────────────────────────────────────────────────────┘
           │                          ▲
           │ POST /register          │ POST /submit
           │ GET /node-list           │ { results }
           ▼                          │
┌──────────────────────────────────────────────────────────────────────┐
│                          Node (Python script)                          │
│                                                                        │
│  ┌──────────────────────────────────────────────────────────────┐     │
│  │                    Check Scheduler (loop)                       │     │
│  │  Every N seconds (configurable, default 10s):                 │     │
│  │  1. Fetch latest node-list from leader                         │     │
│  │  2. For each peer:                                             │     │
│  │     a. ICMP ping (system `ping` binary, timeout)               │     │
│  │     b. HTTP GET /healthz (aiohttp, timeout)                    │     │
│  │  3. Submit results to leader                                   │     │
│  │  4. If submit fails: buffer in memory, retry next cycle        │     │
│  └──────────────────────────────────────────────────────────────┘     │
│                                                                        │
│  ┌──────────────────────────────────────────────────────────────┐     │
│  │                    Result Buffer                                │     │
│  │  In-memory list of failed submissions; retried each cycle      │     │
│  └──────────────────────────────────────────────────────────────┘     │
└──────────────────────────────────────────────────────────────────────┘
```

### Comparison to Established Patterns

| Pattern | Example | Our Model | Key Difference |
|---------|---------|-----------|----------------|
| **Multi-target exporter** | Prometheus Blackbox | Node-initiated push | Blackbox is pull (Prometheus scrapes); our nodes push results |
| **Worker heartbeat** | Celery, Airflow | Similar (push) | Our payload is per-peer check results, not just liveness |
| **Gossip protocol** | Consul, Serf | N/A (centralized) | Gossip is peer-to-peer; we have a central leader |
| **Centralized metrics** | StatsD, Telegraf | Similar (push) | Our nodes are also the probe origin — they measure TO peers |

## Recommended Project Structure

```
mesh-status/
├── leader/                    # Server-side application
│   ├── __init__.py
│   ├── app.py                 # Quart app creation, main entry point
│   ├── config.py              # Configuration (port, defaults)
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── registration.py    # POST /register, node management
│   │   ├── submission.py      # POST /submit, result ingestion
│   │   └── data.py            # GET /data, GET /health, data API
│   ├── services/
│   │   ├── __init__.py
│   │   ├── registry.py        # In-memory node registry (thread-safe)
│   │   ├── results.py         # Result aggregation, status calculation
│   │   └── persistence.py     # Hourly JSON file writer (background task)
│   └── templates/             # If Streamlit is separate, otherwise not needed
│       └── dashboard.py       # Streamlit app (runs as separate process)
├── node/                      # Node-side client
│   ├── __init__.py
│   ├── runner.py              # Main loop, orchestration
│   ├── checker.py             # ICMP ping + HTTP health check logic
│   ├── client.py              # HTTP client for leader communication
│   └── config.py              # CLI args, node-id, leader-ip, interval
├── register.py                # Registration script (argv/stdin)
├── requirements.txt
└── README.md
```

### Structure Rationale

- **`leader/` separate from `node/`:** These are completely different deployment targets with different dependency profiles. The leader has Quart + Streamlit; the node only needs `aiohttp` and standard library. Clean separation prevents accidental cross-contamination.
- **`leader/routes/`:** Quart route handlers are thin — they validate input, call services, return responses. This keeps HTTP concerns separate from business logic.
- **`leader/services/`:** Pure business logic with no HTTP awareness. Testable independently. The `registry` and `results` services are in-memory dicts protected by `asyncio.Lock`.
- **`node/checker.py`:** Houses the two probe types (ping, HTTP) as isolated async functions. Easy to add more probe types later (TCP port check, DNS resolve, etc.).

## Architectural Patterns

### Pattern 1: Push-Based Result Collection

**What:** Nodes initiate all communication. They register with the leader, periodically fetch the peer list, run checks, and POST results. The leader never initiates connections to nodes.

**When to use:** When nodes are behind NAT/VPN, have dynamic IPs, or the leader shouldn't need inbound connectivity to every node. This is the correct fit for mesh-status (VMs across geographies over VPN WAN).

**Trade-offs:**
- + Leader is simpler (no connection management, no reverse-connect)
- + Works through firewalls (outbound HTTP from nodes only)
- - Leader cannot detect node failure instantly (must infer from absence of submissions)
- - Node must poll for peer list changes (eventual consistency)

**Example (node check loop):**
```python
async def check_loop():
    """Node main loop: fetch peers, check, submit, sleep."""
    while True:
        try:
            peers = await client.fetch_node_list()
            results = await checker.run_all_checks(peers)
            await client.submit_results(results)
            # Clear any buffered failures from previous cycles
            client.clear_buffer()
        except SubmissionError:
            # Buffer results for retry
            client.buffer_results(results)
        await asyncio.sleep(interval)
```

### Pattern 2: In-Memory State with Periodic Snapshot Persistence

**What:** The leader holds all state (node registry, latest results) in memory. A background asyncio task snapshots the state to JSON files every hour. On leader restart, state starts fresh — only the persisted JSON history survives.

**When to use:** When state is ephemeral by nature (current connectivity status) and persistence is for audit/history, not for recovery. The "source of truth" is each node's current report, not the on-disk archive.

**Trade-offs:**
- + Extremely simple — no database, no migrations, no connection pools
- + JSON files are human-readable and debuggable
- + Writes are batched (hourly), so no per-submission disk I/O
- - Leader restart = lost in-memory state (nodes must re-register and re-report)
- - JSON file grows unbounded if no rotation/retention policy
- - Not suitable for high-write-volume or strong durability requirements

**Example (background persistence task in Quart):**
```python
@app.before_serving
async def start_persistence_task():
    """Start hourly persistence as a background asyncio task."""
    async def persist_loop():
        while True:
            await asyncio.sleep(3600)
            await persistence.write_snapshot(
                registry=app.registry,
                results=app.results_accumulator
            )
    app.bg_tasks.append(asyncio.create_task(persist_loop()))
```

### Pattern 3: Concurrent Semaphore-Limited Probe Execution

**What:** On the node, checks against all peers run concurrently but with a semaphore cap to prevent overwhelming the node's network stack or CPU with too many simultaneous `ping` subprocesses.

**When to use:** When the number of peers can be large (10+), and running 50+ concurrent subprocesses could degrade node performance or skew timing measurements.

**Trade-offs:**
- + Prevents resource exhaustion (too many subprocesses, socket buffers)
- + Still takes advantage of concurrency for latency hiding
- - Semaphore adds a small scheduling overhead
- - If semaphore is too small, check cycle takes too long

**Example:**
```python
async def run_all_checks(peers: list[str], max_concurrent: int = 10) -> list[CheckResult]:
    """Run ping + HTTP health checks against all peers concurrently, 
    limited by semaphore."""
    sem = asyncio.Semaphore(max_concurrent)
    
    async def check_one(peer_ip: str) -> CheckResult:
        async with sem:
            ping_ok, ping_ms = await run_ping(peer_ip)
            http_ok, http_ms = await run_healthz(peer_ip)
            return CheckResult(
                target=peer_ip,
                ping_success=ping_ok,
                ping_latency_ms=ping_ms,
                http_success=http_ok,
                http_latency_ms=http_ms,
                timestamp=time.time()
            )
    
    return await asyncio.gather(*[check_one(p) for p in peers])
```

## Data Flow

### Registration Flow

```
Node Starts
    │
    ▼
Read CLI args: --node-ip=<IP> --leader-ip=<IP>
    │
    ▼
POST /register  {"node_id": "<hostname>", "node_ip": "<IP>"}
    │
    ▼
Leader Handler:
    1. Validate IP format
    2. Add/update entry in Node Registry (in-memory dict)
    3. Set status = "Pending" (no results yet, future data expected)
    4. Return 200 + full peer list
         │
         ▼
Node receives peer list → begins check loop
```

### Check + Submit Flow (per cycle)

```
Node Check Cycle (every N seconds, default 10s):
    │
    ├── 1. GET /node-list (fetch updated peer list from leader)
    │         Returns: {"nodes": [{"id": "vm1", "ip": "10.x.x.1"}, ...]}
    │
    ├── 2. For each peer (concurrent, semaphore-limited):
    │         │
    │         ├── a. system ping -c 1 -W <timeout> <peer_ip>
    │         │       → success(bool), latency_ms(float|None)
    │         │
    │         ├── b. HTTP GET http://<peer_ip>:58080/healthz
    │         │       → success(bool), latency_ms(float|None)
    │         │
    │         └── c. Produce CheckResult object
    │
    ├── 3. POST /submit {"node_id": "vm1", "checks": [...], "timestamp": ...}
    │         │
    │         ├── Success → clear in-memory retry buffer ✓
    │         └── Failure → append checks to retry buffer ✗
    │
    └── 4. Sleep for remaining interval time
```

### Data Retrieval Flow

```
Streamlit Frontend (or any HTTP client)
    │
    ▼
GET /data?window=30m
    │
    ▼
Leader:
    1. Read in-memory results accumulator (last ~30 min worth)
    2. For each node, calculate status:
         - If result exists → OK (with latency stats)
         - If no result, but node registered → Pending
         - If node not registered → NotAvailable
    3. Return JSON response
         │
         ▼
Streamlit renders connectivity matrix:
    - Green/red cells for each node→node pair
    - Latency tooltips
    - Aggregated uptime for 30-day view
```

### State Management

```
┌─────────────────────────────────────────────────────────┐
│              Leader In-Memory State                       │
│                                                           │
│  node_registry: dict[str, NodeInfo]                       │
│    {"vm1": {"ip": "10.0.0.1", "registered_at": ...,       │
│             "last_seen": ..., "status": "Pending"}}        │
│                                                           │
│  check_results: dict[str, list[CheckResult]]              │
│    {"vm1": [CheckResult, ...], "vm2": [CheckResult, ...]} │
│    Keyed by source node_id. Each list ordered by time.    │
│    Retained in memory for the data API window.            │
│                                                           │
│  On-disk: data/2026/06/18.json                          │
│    Hourly snapshot of accumulated results.                │
│    Format: timestamped array of CheckResults.             │
└─────────────────────────────────────────────────────────┘
```

### Key Data Flows

1. **Node Registration:** Node → POST /register → Leader adds to in-memory registry → Returns peer list. Only happens once per node process start (unless leader restarts and cache is lost).

2. **Periodic Check Cycle:** Node fetches peer list → Runs N concurrent checks → POSTs results → Leader accumulates in memory → Background task persists to JSON hourly.

3. **Frontend Query:** Streamlit → GET /data → Leader reads in-memory results → Computes statuses → Returns JSON → Streamlit renders matrix.

4. **Node Failure Detection (implied):** Leader marks node as `NotAvailable` if no submission received within (3 × check_interval). This is a soft detection — no explicit health check from leader to node. The threshold is computed at query time based on `last_seen` vs current time.

## Threading / Async Model

### Leader (Quart)

- **Single process, single event loop.** Quart is fully async (ASGI). All request handlers are `async def`.
- **Background tasks are asyncio Tasks.** The hourly persistence writer runs as a `create_task` started in `@app.before_serving`. No threading needed.
- **Shared state protected by `asyncio.Lock`.** The node registry dict and results accumulator are accessed from multiple coroutines (registration, submission, data query, persistence). Use `async with lock:` for any write and for read+write operations.
- **Streamlit runs as a separate process.** Streamlit is synchronous and blocks its own process. It runs as a subprocess or separate systemd unit, calling the leader's HTTP API. Do NOT embed Streamlit in the Quart process.

### Node (Python script)

- **Primarily async with some sync bits.** The main loop is async (uses `aiohttp` for HTTP), but `ping` subprocesses are spawned via `asyncio.create_subprocess_exec` (which is async).
- **Concurrent checks via `asyncio.gather`.** All peer checks run concurrently in a single event loop iteration, not sequentially. This is the key performance design decision — for a 10-peer mesh, checks complete in ~max(ping_timeout) not ~10×ping_timeout.
- **Subprocess timeout via `asyncio.wait_for`.** Each `ping` subprocess is wrapped in `asyncio.wait_for(proc.communicate(), timeout=5)` to prevent hung pings from blocking the cycle.
- **No threading, no multiprocessing.** The node is lightweight — async handles I/O concurrency (HTTP to leader, subprocess I/O for ping). Threading would add complexity without benefit for I/O-bound probing.

### Async Model Trade-offs

| Concern | Decision | Rationale |
|---------|----------|-----------|
| Node check concurrency | `asyncio.gather` + semaphore | Maximizes latency hiding; semaphore prevents subprocess overload |
| Ping subprocess | `asyncio.create_subprocess_exec` | Non-blocking; event loop continues while ping runs |
| Subprocess timeout | `asyncio.wait_for` | Prevents stuck pings from accumulating; mandatory for robustness |
| Leader state locking | `asyncio.Lock` | Simple, sufficient for single-process leader |
| Background I/O (disk) | `aiofiles` or run in executor | `aiofiles` for async file writes; fallback to `run_in_executor` for sync JSON serialization |
| Streamlit integration | Separate process + HTTP | Streamlit is synchronous; embedding would block Quart's event loop |

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| 1–20 nodes (prototype) | Single leader process, in-memory state, hourly JSON writes. No changes needed. |
| 20–200 nodes | Add result retention policy (delete daily files older than X days). Potential memory pressure from in-memory results — cap rings per node. |
| 200+ nodes | Move to SQLite or PostgreSQL for persistence. Consider partitioning the leader into separate ingestion and query services. |

### Scaling Priorities

1. **First bottleneck: Node check cycle length.** As peers grow, `asyncio.gather` with semaphore keeps cycle time bounded by `max(ping_timeout)`, not `N * ping_timeout`. The semaphore's max_concurrent may need tuning upward. At extreme scale (500+ nodes), consider staggered check cycles or sampling only a subset of peers per cycle.

2. **Second bottleneck: Leader result ingestion.** At high submission frequency (many nodes, short intervals), the leader's `POST /submit` handler and `asyncio.Lock` contention could become a bottleneck. Mitigation: batch results in-memory and use lock-free structures (e.g., `deque` per node with atomic append).

3. **Third bottleneck: JSON persistence.** Hourly writes of accumulated results could become large. Mitigation: split per-node files or per-hour files. At prototype scale this is irrelevant.

## Anti-Patterns

### Anti-Pattern 1: Leader Polls Nodes

**What people do:** Having the leader send health checks to every node (pull model).

**Why it's wrong:** Requires the leader to have inbound connectivity to all nodes. In a VPN WAN with dynamic IPs, this adds complexity (reverse tunnel, dynamic DNS) and a single point of network failure. If the leader is behind NAT, it flat-out doesn't work.

**Do this instead:** Push model — nodes initiate all contact. The leader is a passive collector. Node failure is inferred from absence of reports.

### Anti-Pattern 2: Synchronous Sequential Checks

**What people do:** Looping through peers one at a time: `for peer in peers: ping(peer)`.

**Why it's wrong:** For a 10-peer mesh with 5-second ping timeout, the check cycle takes 50+ seconds. The node barely finishes one cycle before the next is due. This makes the check interval meaningless and misses the point of distributed probing.

**Do this instead:** Run all peer checks concurrently via `asyncio.gather` with a semaphore. The cycle time becomes `max(ping_timeout)` plus HTTP overhead, which is typically 5–10 seconds regardless of peer count.

### Anti-Pattern 3: Too Much State on Nodes

**What people do:** Having nodes buffer hours of results, implement their own persistence, or maintain complex retry queues.

**Why it's wrong:** Nodes should be stateless probes — they ping, report, forget. The leader owns state and history. If a node crashes, the leader detects the absence and marks it `NotAvailable`. Buffering only the current cycle's results for retry is sufficient.

**Do this instead:** In-memory buffer on the node for failed submissions (one cycle's worth). Discard on successful submission. No disk persistence on nodes.

### Anti-Pattern 4: JSON Write Per Submission

**What people do:** Opening and writing to the JSON file on every `POST /submit`.

**Why it's wrong:** Disk I/O is orders of magnitude slower than in-memory operations. With frequent submissions (every 10s × N nodes), this causes thundering-herd writes, filesystem contention, and leader slowdown. JSON serialization is CPU-bound and blocks the event loop.

**Do this instead:** Accumulate results in memory for the duration of the write window (1 hour). Write once per hour in a background asyncio task. The in-memory structures serve the data API; the JSON files are a historical archive.

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| System `ping` binary | Subprocess (`asyncio.create_subprocess_exec`) | Use `-c 1 -W <timeout>` flags. Parse stdout for latency. Handle missing binary gracefully. |
| Node `/healthz` endpoint | HTTP GET via `aiohttp` | Lightweight HTTP server on each node (could be a trivial Python one-liner or just Quart's health route). Timeout is critical. |
| Leader HTTP API | HTTP POST/GET via `aiohttp` (node side), Quart routes (server side) | Both sides use JSON payloads. Use `aiohttp.ClientSession` with connection pooling on the node. |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| Routes → Services | Direct async function call within same process | Routes import service functions, await them. No RPC or message bus needed for single-process leader. |
| Services → State | In-memory dicts + `asyncio.Lock` | Keep locks fine-grained. A single global lock hurts concurrency; prefer per-structure locks. |
| State → Persistence | Background asyncio task reads state, writes file | Persistence task accesses state dicts (with lock guard). Writes via `aiofiles.open()` or `loop.run_in_executor()`. |
| Leader → Streamlit | HTTP (leader serves data API, Streamlit calls it) | Streamlit runs as separate process. Leader exposes `GET /data?window=30m` and `GET /data?window=30d`. |

## Build Order Implications

Because components have clear dependency relationships, the build order matters:

```
Phase 1: Leader Core (Foundation)
  ├── app.py (Quart scaffold) — nothing works without this
  ├── config.py
  ├── routes/registration.py — POST /register
  ├── services/registry.py — in-memory node registry
  └── routes/submission.py — POST /submit
  → Can verify: curl register → curl submit → see in-memory state

Phase 2: Node Core (Foundation)
  ├── config.py (CLI args)
  ├── client.py (HTTP to leader)
  ├── checker.py (ping + healthz probes)
  └── runner.py (main loop)
  → Can verify: register node → see checks submitted to leader

Phase 3: Persistence + Data API
  ├── services/persistence.py (hourly JSON writer)
  ├── services/results.py (aggregation, status calc)
  └── routes/data.py (GET /data endpoint)
  → Can verify: data flows from node → leader memory → JSON file

Phase 4: Frontend
  ├── templates/dashboard.py (Streamlit app)
  → Can verify: dashboard queries /data, renders matrix

Phase 5: Hardening
  ├── Node result buffer + retry logic
  ├── Leader NotAvailable detection
  ├── Error handling, logging, timeouts
  → Can verify: kill node → see NotAvailable; kill leader → node re-registers
```

**Key dependency:** Phase 1 must be complete before Phase 2 can be tested end-to-end (node needs leader to POST to). Phase 1 and Phase 2 could be built in parallel if stubs are used, but the first integration test requires both.

## Sources

- [Prometheus Blackbox Exporter architecture](https://github.com/prometheus/blackbox_exporter) — multi-target probe pattern (HIGH confidence)
- [Heartbeats in Distributed Systems](https://arpitbhayani.me/blogs/heartbeats-in-distributed-systems) — push vs pull heartbeat models (MEDIUM confidence, blog source)
- [Python asyncio subprocess docs](https://docs.python.org/3/library/asyncio-subprocess.html) — async subprocess.create_subprocess_exec for ping (HIGH confidence)
- [Python asyncio task docs](https://docs.python.org/3/library/asyncio-task.html) — asyncio.gather, asyncio.timeout, TaskGroup (HIGH confidence)
- [Simon Willison — subprocess time limit with asyncio](https://til.simonwillison.net/python/subprocess-time-limit) — async subprocess timeout pattern (MEDIUM confidence, blog)
- [Quart docs](https://quart.palletsprojects.com/en/latest/) — async request handlers, background tasks (HIGH confidence)

---
*Architecture research for: mesh-status distributed connectivity testing*
*Researched: 2026-06-18*
