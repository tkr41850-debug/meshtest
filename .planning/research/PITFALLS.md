# Pitfalls Research

**Domain:** Distributed mesh connectivity testing over VPN WAN
**Researched:** 2026-06-18
**Confidence:** HIGH (research cross-referenced with official docs, real issue trackers, and production post-mortems)

## Critical Pitfalls

### Pitfall 1: Concurrent JSON File Writes Without Locking (Read-Modify-Write Race)

**What goes wrong:**
Multiple nodes submit check results concurrently. The leader's hourly write handler reads the day's JSON file, appends new results, and writes it back. Without synchronization, two concurrent writes interleave: Writer A reads state S₀, Writer B reads the same S₀, both modify, both write. One write silently overwrites the other. Data is lost — no error, no log, no indication. In the worst case, the file ends up truncated or contains interleaved JSON fragments (`{"checks":[...]}{"checks":[...]`), causing `JSONDecodeError` on every subsequent read.

**Why it happens:**
JSON persistence to a single file is a classic read-modify-write pattern. Python's `json.load()` then `json.dump()` is not atomic. The OS provides no inter-process coordination by default. Developers assume "Python's GIL protects me" — but the GIL protects in-memory operations, not file I/O between processes or between async tasks in the same process that yield at `await`.

This is exactly the bug Netflix Metaflow found in their JSON state files (PR #3006), the P0 session state corruption in QwenPaw (PR #3278), and the silent data loss in Hive's state.json (Issue #6696). All are variations of the same pattern: non-atomic read-modify-write on shared JSON files.

**How to avoid:**
1. **Atomic write pattern (minimum):** Write to a temporary file in the same directory, `os.fsync()`, then `os.replace()` to atomically swap. This prevents readers from seeing a half-written file but does NOT prevent lost writes from concurrent writers.
2. **File locking for writer exclusion (recommended):** Acquire an exclusive `fcntl.flock()` (POSIX) on a dedicated `.lock` file (NOT the data file, because `os.replace` changes the inode) around the entire read-modify-write cycle. The lock file has a stable inode; the data file can be atomically replaced underneath it.
3. **Separate lock + atomic write (best):** Use a `.lock` file for `flock` serialization AND write to a temp file + `os.replace` for crash safety. This provides both writer exclusion and crash durability.
4. **Simpler alternative for this project:** Write each check result as an **append-only JSON line** (one JSON object per line) instead of rewriting the full file. Each writer just appends. The daily aggregation can read the whole file after rotation. This avoids the read-modify-write problem entirely.

**Warning signs:**
- Intermittent "missing" check results in the dashboard that don't correlate with actual node failures
- `JSONDecodeError: Extra data` or `JSONDecodeError: Expecting value` on the leader when reading day files
- Files that start with valid JSON but have garbage at the end
- File size not matching expected data volume

**Phase to address:**
Phase 1 (Core Leader Implementation) — the file writing path must be correct from the first commit. Retrofitting atomic writes is harder once data accumulates.

---

### Pitfall 2: Synchronous `ping` Subprocess Blocking the Quart Event Loop

**What goes wrong:**
The node check loop shells out to `ping` using `subprocess.run()` or `subprocess.Popen().communicate()` (both blocking calls). While the ping runs, the entire asyncio event loop is blocked — no HTTP requests are served, no registrations processed, no health checks answered. With 10+ nodes and 10-second check intervals, the node becomes unresponsive for seconds at a time. The leader sees the node as unhealthy because its `/healthz` endpoint doesn't respond. The node is marked down and removed from the mesh, even though the node itself is fine — it was just busy pinging.

**Why it happens:**
Quart runs on a single-threaded asyncio event loop. Any blocking call (synchronous `subprocess.run()`, `time.sleep()`, `requests.get()` without `await`) pauses the entire loop. The official Quart docs explicitly warn: *"If a task does not need to wait on IO it will instead block the event loop and Quart could become unresponsive."*

Developers default to `subprocess.run()` because it's simpler than `asyncio.create_subprocess_exec()`. The `ping` command is particularly dangerous because even with `-c 1`, a non-responsive host can cause `ping` to hang for its full timeout (often 5-10 seconds by default).

**How to avoid:**
1. **Always use `asyncio.create_subprocess_exec()`** for shelling out to `ping`, never `subprocess.run()`.
2. **Wrap with `asyncio.wait_for()`** to enforce a per-ping timeout (e.g., 3 seconds max).
3. **Crucially: in the timeout handler, call `process.kill()` AND `await process.wait()`** — otherwise the zombie ping process leaks. Python's asyncio subprocess docs confirm that `communicate()` and `wait()` have no built-in timeout parameter; you must use `wait_for()` and handle cleanup yourself.
4. **Consider `asyncio.to_thread(subprocess.run, ...)` as a simpler escape hatch** for teams not comfortable with the asyncio subprocess API — but this adds thread overhead and should be avoided for frequent (every 10s) operations.

**Warning signs:**
- Node `/healthz` endpoint intermittently slow or unresponsive
- "Event loop blocked" warnings in logs
- `ping` processes accumulating in `ps aux` on the node
- Check intervals taking longer than the configured period (10s check running for 15s)

**Phase to address:**
Phase 2 (Node Agent Implementation) — must be correct from the start. The node's entire value is checking reachability without becoming unreachable itself.

---

### Pitfall 3: Subprocess Cleanup After Ping Timeout (Zombie Processes and Lost Output)

**What goes wrong:**
When `asyncio.wait_for(process.communicate(), timeout=3)` times out, `wait_for` cancels the `communicate()` coroutine. But the subprocess (ping) continues running in the OS. The process is orphaned — it's still sending ICMP packets, still consuming a PID, and if enough accumulate, the process table fills up. Worse, because `communicate()` was cancelled mid-stream, any partial output already read from stdout is lost. When the next check cycle tries to `kill()` the PID, it may get `ProcessLookupError` or kill an unrelated process that reused the PID.

This is a known Python bug/limitation (cpython issues #139373, #103847). The asyncio subprocess implementation is explicitly *not cancellation-safe*. `communicate()`'s cancellation means the transport buffer has already been drained but `process.wait()` hasn't run — you get neither the output nor a clean process exit.

**Why it happens:**
Python's `asyncio.subprocess.Process.communicate()` reads stdout and stderr internally. When cancelled via `wait_for`, it stops mid-stream. The standard cleanup pattern:

```python
try:
    stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=3)
except asyncio.TimeoutError:
    proc.kill()
```

...kills the process but the already-read-but-not-returned stdout data is gone inside the cancelled coroutine. Calling `proc.communicate()` again after killing returns nothing because the transport buffer was already drained.

**How to avoid:**
Use the cancellation-safe pattern (from cpython issue #139373 discussion):

```python
async def ping_with_timeout(host, timeout=3):
    proc = await asyncio.create_subprocess_exec(
        'ping', '-c', '1', host,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    io_task = asyncio.create_task(proc.communicate())
    try:
        await asyncio.wait_for(proc.wait(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()  # Must wait after kill to avoid PID leak
    stdout, stderr = await io_task  # Retrieve partial output safely
    return stdout.decode() if stdout else None
```

This pattern uses `process.wait()` for timeout detection (not `communicate()`), so if the timeout fires, `communicate()` is NOT cancelled and can finish after the process is killed. No data loss, no zombie processes.

**Warning signs:**
- Growing number of `ping` processes in `ps aux` over time
- `OSError: [Errno 24] Too many open files` (PIDs are a limited resource)
- Intermittent `ProcessLookupError` when trying to kill PIDs

**Phase to address:**
Phase 2 (Node Agent Implementation) — the ping handler must use the cancellation-safe pattern from day one.

---

### Pitfall 4: Streamlit Full-Script Rerun With Unbounded JSON Data Loading

**What goes wrong:**
The Streamlit dashboard reads all JSON result files for the selected time window on every page interaction (button click, slider move, dropdown change). With 30-day data and frequent checks, the JSON file accumulates millions of entries. Every single user interaction triggers: (1) reading 10-50 MB of JSON from disk, (2) parsing it into Python dicts, (3) transforming into a DataFrame, (4) rendering. The dashboard becomes unusable — 5-15 second lag on every click.

**Why it happens:**
Streamlit reruns the entire script from top to bottom on every widget interaction (this is by design — it's Streamlit's core execution model). Without `@st.cache_data`, every rerun reloads and reparses all the data. The Streamlit docs and community guidance are explicit: "Without caching and fragments, your app reruns everything on every interaction."

JSON is particularly expensive here because `json.load()` deserializes every single entry, even if you only need summary statistics (uptime percentages, not every ping result).

**How to avoid:**
1. **Use `@st.cache_data(ttl=60)` on the data loading function** — the file is read and parsed once, cached, and only refreshed when the TTL expires or the file changes.
2. **Pre-aggregate at write time** — When the leader writes the hourly file, also write a pre-aggregated summary (e.g., `summary_30min.json`, `summary_30d.json`) so the dashboard only needs to load small aggregations, not raw check data.
3. **Use `st.fragment(run_every="10s")`** for auto-refreshing components so only the live metrics section reruns, not the entire page.
4. **Use Arrow-native loading** — Streamlit's `st.dataframe` supports Arrow natively. Convert your cached DataFrame to Arrow format to reduce serialization overhead.
5. **For very large datasets (>150k rows)**, Streamlit >= June 2026 adds automatic lazy row loading for `st.dataframe` — but you need to ensure the data is in a pandas/Polars DataFrame, not raw JSON.

**Warning signs:**
- Dashboard takes >2 seconds to respond after any widget interaction
- Browser spinner appears on every click
- High CPU usage on the leader during dashboard use
- Streamlit warning about slow rerender

**Phase to address:**
Phase 3 (Dashboard Implementation) — caching must be built in from the first dashboard commit. Retrofitting is possible but painful (users already have bad expectations).

---

### Pitfall 5: Node Registration Race Condition (TOCTOU)

**What goes wrong:**
Two nodes register simultaneously. The leader checks "does node IP exist?" → no → assigns a node ID. Both nodes get the same ID, or the registry state file gets corrupted. The leader sends the node list to each, but they disagree on which nodes exist. Nodes appear and disappear from the mesh. Check results reference node IDs that don't exist in the registry. The entire connectivity map becomes unreliable.

**Why it happens:**
The registration handler follows a classic time-of-check-to-time-of-use (TOCTOU) pattern:

```python
# Handler A: reads registry → sees no node with IP X
# Handler B: reads registry → sees no node with IP X
# Handler A: "Registering node X..."
# Handler B: "Registering node Y..." (or same node X again)
# Handler A: writes registry with node X
# Handler B: writes registry with node Y — but may overwrite A's write
```

This is the same pattern documented in the ICN identity registry race (Issue #397), Docker Swarm overlay network sync (Moby PR #52665), and the registry server concurrent publishing fix (PR #528).

In a single-process Quart server, the handlers run as asyncio tasks. They interleave at every `await`. If the registration handler does any async I/O (file read, HTTP request to validate), it yields the event loop, and another registration can sneak in.

**How to avoid:**
1. **Use an `asyncio.Lock()` at the app level** — create a single lock in the app factory and acquire it in every registration handler before reading the registry state. This serializes registrations within a single process.
2. **Use atomic file operations combined with locking** — the registry file write (if JSON) must use the same atomic+locked pattern as Pitfall 1.
3. **Use unique constraints at the storage level** — if you store node IPs in a dict, ensure the dict itself enforces uniqueness. But this only protects in-memory; you need the lock for the file write.
4. **Use registration tokens or idempotency keys** — nodes can send a unique registration token. If the registration is retried with the same token, the leader can safely no-op instead of duplicating.

**MINIMUM VIABLE:**
```python
_app_registry_lock = asyncio.Lock()

@app.route('/register', methods=['POST'])
async def register():
    async with _app_registry_lock:
        data = await request.get_json()
        node_ip = data['node_ip']
        # read registry, check, modify, write — all inside the lock
```

**Warning signs:**
- Two nodes with the same node ID appearing in the dashboard
- "Node ID already exists" or key constraint errors
- Intermittent registration failures under load
- Nodes disappearing from the mesh shortly after registering

**Phase to address:**
Phase 1 (Core Leader Implementation) — the registration endpoint is the entry point for all nodes. Data races here cascade into every downstream component (check distribution, result collection, dashboard).

---

### Pitfall 6: Hourly File Rotation Data Loss and Integrity Issues

**What goes wrong:**
At the top of every hour, the leader rotates the data file: renames `dd.json` to `dd.json.bak` (or similar) and creates a new `dd.json`. Between the rename and the new file being written, incoming check results are lost — they go to a file that's about to be closed or the new file that doesn't exist yet. In the worst case, a crash during rotation leaves the data file truncated (opened with `'w'` mode but never written), destroying the entire hour's data.

**Why it happens:**
Custom rotation logic often has exactly these failure modes:
1. **Crash during write** — `open('w')` truncates the file before any data is written. Crash between truncation and write = empty file.
2. **Rename race** — renaming the active log file while writers are appending to it. On Windows this can fail with file-lock errors. On POSIX, the rename succeeds silently and the old file descriptor continues writing to the now-unlinked file.
3. **File overwrite collision** — Python's `TimedRotatingFileHandler` has a known bug (cpython Issue #88352) where files rotated at the same timestamp overwrite each other.

The project spec says "writes aggregated data every hour." This means the rotation is both time-triggered AND data-aggregation-triggered — a window where data loss can occur.

**How to avoid:**
1. **Append-only, never rewrite the active file.** Write each check result as a new line in `dd.jsonl` (JSON Lines format). Each line is an independent JSON object. No rotation needed during the hour because there's no read-modify-write.
2. **For hourly aggregation, read the complete file after it's been closed.** Once the hour boundary passes, close the current file, open the next hour's file. The old file is now immutable. Aggregate from the completed file.
3. **If you must rotate, use atomic rename** — close the file, THEN rename it. Never rename an open file.
4. **Use `os.replace()` (atomic on POSIX) instead of `os.rename()`** — on some systems `rename` fails if the target exists. `replace` overwrites atomically.

**Recommended pattern for this project:**
```
data/2026/06/18/14.jsonl   ← current hour, append-only
data/2026/06/18/13.jsonl   ← completed hour, immutable
data/2026/06/18/13.aggregated.json  ← aggregation of completed hour
```

**Warning signs:**
- Hourly files that are empty or smaller than expected
- Check results that disappear at the top of each hour
- Corrupted or truncated JSON at rotation boundaries
- First few minutes of each hour showing no data

**Phase to address:**
Phase 1 (Core Leader Implementation) — the file storage design must be append-only from the start. Changing from rewriting to append-only is a storage migration that's painful to do after data has accumulated.

---

### Pitfall 7: Healthz Endpoint Confusing Liveness With Readiness

**What goes wrong:**
The leader exposes `/healthz` which returns 200 if the process is running. Nodes use this endpoint to verify the leader is healthy. But the endpoint doesn't check critical dependencies: can the leader still write to disk? Is the event loop responsive? Has the background check-collection task crashed? The health endpoint returns 200 while the leader is silently failing to persist results. Nodes think everything is fine, but the dashboard shows stale data. Conversely, an overeager health check that checks disk I/O fails during a transient NFS hiccup, nodes think the leader is down and start buffering, creating a thundering herd on recovery.

**Why it happens:**
The project spec says "Node runs HTTP GET /healthz" as a connectivity check. It's tempting to make `/healthz` a trivial "return 200" endpoint. But this gives a false sense of safety — the mesh continues operating against a leader that's accumulating data in memory but can't persist it.

The Kubernetes community has standardized on three separate probes for this exact reason:
- **Liveness** (`/livez`): Is the process running and responsive? If no, restart.
- **Readiness** (`/readyz`): Can this instance handle traffic? If no, drain connections.
- **Startup** (`/startup`): Has initialization completed? If no, don't kill yet.

A single `/healthz` endpoint mixes these concerns, and you can't tell if "healthy" means "responding to HTTP" or "fully operational."

**How to avoid:**
1. **Implement at least two endpoints:**
   - `/livez` — shallow, returns 200 immediately on any HTTP response. Used by nodes to check leader reachability.
   - `/readyz` — deep, checks disk writability, checks that the background collection task is running, checks that recent (within 5 minutes) data was persisted. Used by operators and for self-diagnosis.
2. **Use separate HTTP status codes:** 200 = ready/healthy, 503 = not ready, never return 200 with error in body (monitoring systems route on status codes, not body content).
3. **Background health check pattern:** For expensive checks (disk I/O), perform them in a background thread every 30 seconds and cache the result. The `/readyz` handler reads the cached status and responds quickly (<50ms).
4. **Timebound all checks:** Each dependency check must have its own timeout (e.g., disk check: 500ms). Aggressive timeouts prevent cascading failures.

**Warning signs:**
- Leader `/healthz` returns 200 but dashboard data is hours old
- Check results being accepted by the leader but not persisted
- Nodes marking the leader as "down" based on the same `/healthz` that everyone else says is fine
- Thundering herd on leader recovery (all nodes reconnect simultaneously)

**Phase to address:**
Phase 1 (Core Leader Implementation) — the `livez` endpoint is needed for basic operation. The `readyz` endpoint should be added before any real deployment to avoid false confidence.

---

### Pitfall 8: VPN MTU Blackholes and Packet Loss Misinterpretation as "Node Down"

**What goes wrong:**
ICMP ping packets exceed the effective MTU of the VPN tunnel. The ping with DF (Don't Fragment) set is silently dropped because Path MTU Discovery (PMTUD) is broken — the VPN device or an intermediate firewall blocks ICMP "Fragmentation Needed" messages. The ping timeout is interpreted as "node is unreachable." The dashboard shows the node as DOWN. But the node is perfectly reachable for TCP traffic (which negotiates MSS and avoids the MTU issue). The false positive cascades: dependent nodes stop checking, operator gets paged, investigation shows "works fine, ping just times out."

**Why it happens:**
VPN tunnel encapsulation adds overhead (WireGuard: 60 bytes, IPsec: ~73 bytes, OpenVPN: ~60 bytes). Standard Ethernet MTU is 1500. After encapsulation, the effective payload MTU is 1500 - overhead = ~1420-1440. A standard ping with 1472 bytes of payload + 28 bytes ICMP header = 1500 bytes total — which exceeds the tunnel MTU. With DF set (default on modern systems), the packet is dropped. With PMTUD broken (ICMP blocked by firewall — extremely common, as documented in enterprise VPN guides), the sender never learns about the smaller MTU.

The VPN community has endless post-mortems on this exact pattern: "ping fails, everything else works" (cr0x.net MTU guide, BigIron's MTU Mystery, Lineman's VPN MTU article).

**How to avoid:**
1. **Use smaller ping payloads:** `ping -s 1400 -M do <host>` to test within the tunnel MTU. Standard ping uses 56 or 64 bytes by default, which should fit, BUT the real problem is that ping with default size may work while ping with larger payload (or TCP with DF) doesn't. The fix is to test what you depend on.
2. **Supplement ICMP ping with a TCP-based check:** HTTP GET to `/healthz` on the target port uses TCP, which negotiates MSS during the three-way handshake. TCP will automatically avoid MTU issues (assuming MSS clamping is in place). This is why the project already uses both ping + HTTP health check — but the ping results alone should never be the sole health indicator.
3. **MTU baseline measurement:** Before deployment, run `ping -M do -s <size>` (binary search from 1500 down to 1200) through the VPN to find the actual path MTU. Configure nodes to use the known-safe MTU.
4. **Expect asymmetric MTU:** The path MTU may differ by direction. Test both ways.
5. **Document the "ping fails, HTTP works" scenario** in the runbook so operators don't page unnecessarily.

**Warning signs:**
- ICMP ping to a node fails but HTTP/healthz succeeds
- Pings with default size work, pings with larger payloads fail
- Large file transfers through the VPN stall while small web requests work fine
- TCP retransmission rates >2% on VPN traffic
- `Frag needed` ICMP messages being blocked (check firewall rules)

**Phase to address:**
Phase 2 (Node Agent Implementation) — the check logic must treat ping and HTTP as independent signals and not let a ping failure alone mark a node as DOWN. Phase 5 (Operational Readiness) — MTU baseline testing before production deployment.

---

### Pitfall 9: Ping Check Loop Thundering Herd and Self-Inflicted Congestion Collapse

**What goes wrong:**
All N nodes check all other N-1 nodes simultaneously every 10 seconds. At 10 nodes, that's 90 ping + 90 HTTP checks every 10 seconds = 18 concurrent outbound checks per node. The VPN link becomes saturated with control traffic. Real application traffic gets pushed out. The VPN concentrator's CPU spikes due to the ICMP and HTTP load. Latency increases for legitimate traffic. The checks start timing out because the VPN itself is congested. Nodes report each other as DOWN — a self-inflicted false positive.

**Why it happens:**
The check interval is global and synchronized. If all nodes start their checks at time T, they all finish at approximately the same time and reschedule for T+10s. The pattern repeats. The result is a traffic pattern that alternates between idle and burst — the worst possible pattern for a VPN link with limited bandwidth.

This is the same phenomenon that causes "monitoring storm" or "alert fatigue cascade" in distributed systems: the monitoring itself becomes the cause of the failure it's trying to detect.

**How to avoid:**
1. **Jitter the check interval:** Add a random offset (0-N seconds) to each node's initial start time so they don't synchronize. Even better: add ±20% jitter to every check interval so the pattern is never periodic.
2. **Stagger per-node checks:** Instead of checking all nodes at once, use a per-node async loop that pings one node at a time. This spreads the load evenly across the interval.
3. **Cap total concurrent outbound checks per node:** Use an `asyncio.Semaphore(N)` to limit simultaneous checks (e.g., max 3 concurrent pings). This also prevents the node from overwhelming its own outbound bandwidth.
4. **Use an adaptive check interval:** If the last check timed out, back off the next check (exponential backoff with cap). If the node is flaky, don't hammer it.
5. **Independent check for "up/down" vs. "latency":** Use frequent lightweight checks (single ping, short timeout) for liveness, and less frequent full checks (multiple pings, latency measurement) for performance data.

**Warning signs:**
- VPN link utilization spikes every 10 seconds
- Check timeouts correlate with times when many checks run simultaneously
- Node CPU spikes matching the check interval
- False positive "node down" detections during normal operation
- Improving after reducing the number of nodes (fewer checks = less congestion)

**Phase to address:**
Phase 2 (Node Agent Implementation) — jitter and concurrency control must be in the initial check loop design. Adding them later means adjusting every node's configuration.

---

### Pitfall 10: Leader Memory Growth From Unbounded In-Memory Buffers

**What goes wrong:**
Nodes buffer check results in memory when they can't reach the leader. The leader also buffers incoming results before the hourly file write. Over days of operation (or during a prolonged network partition), these buffers grow without bound. The leader runs out of memory and is OOM-killed. The node OOM-killed. All buffered results are lost. After restart, the leader has no historical data. The dashboard shows empty. The hourly aggregation files are missing chunks of history — and nobody knows which hours are complete and which have gaps.

**Why it happens:**
The project spec explicitly says: "On submission failure, node buffers results in memory and retries next cycle." And "Leader writes JSON files hourly to avoid memory/disk pressure" — but "hourly" only protects disk, not memory. If the leader accumulates results in memory for the full hour, a node with 20 peers checking every 10 seconds produces 6 results/minute × 60 minutes × 20 peers = 7,200 entries in memory. For N nodes, multiply by N. At 100 nodes, that's 720,000 entries.

The spec doesn't define a maximum buffer size or a buffer eviction policy. Without one, the buffer is O(n) in time.

**How to avoid:**
1. **Bounded write-behind buffer:** Use a fixed-size queue (e.g., `asyncio.Queue(maxsize=5000)`) for check results. If the queue is full, drop old results (not new ones). Log a warning.
2. **Write every check result immediately (append-only), don't batch in memory:** If using append-only JSON Lines (Pitfall 1), there's no reason to batch — just `fsync` periodically (every 100 writes or every 30 seconds). This eliminates the in-memory buffer entirely.
3. **Bounded node-side buffer:** Node-side buffer must have a max size (e.g., 10,000 entries). On overflow, drop oldest first. The node should also implement exponential backoff for retries, not retry every cycle.
4. **Memory usage monitoring:** Add a background task that logs buffer sizes and memory usage every minute. Set an alert if memory exceeds 70% of available RAM.

**Warning signs:**
- Leader memory usage increasing monotonically
- Node buffer size growing without bound during network partitions
- OOM kills on the leader or nodes
- Dashboard data gaps that correspond to leader restart events

**Phase to address:**
Phase 1 (Core Leader Implementation) — buffer sizing limits must be part of the initial design. Phase 2 (Node Agent Implementation) — node-side buffer limits.

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| **Shelling out to system `ping`** | Avoids root/capabilities for raw ICMP sockets | Platform-dependent output parsing, zombie process risk, no way to set TTL/flags cleanly | MVP only. Replace with `icmplib` or `ping3` for Phase 4+ |
| **JSON file storage with single-file rewrite** | Quick to implement, human-readable | Read-modify-write data loss, no concurrency, slow at scale | MVP only. Must use append-only or SQLite by Phase 4+ |
| **Single `/healthz` endpoint** | Simple to implement, one less route | Cannot distinguish "process alive" from "ready to serve" | Never acceptable beyond local dev. Add `/livez` and `/readyz` in Phase 1 |
| **No auth/access control** | Faster prototype, no key management | Anyone on VPN can register rogue nodes, inject fake results | Acceptable for trusted-VPN prototype only. Must add node authentication before multi-team deployment |
| **Global polling with fixed interval** | Simple scheduling logic | Wastes bandwidth when nodes are idle, misses patterns during congestion | Acceptable for <=10 nodes. Need adaptive intervals by Phase 4 |
| **Streamlit polling (no cache)** | Fast to build, always "fresh" | Scrapes parsing cost on every interaction. UI becomes unusable at scale. | Never acceptable beyond prototype. Must use `@st.cache_data` from Phase 3 |
| **In-memory buffer without eviction** | Simple implementation, no data loss on leader reachable | OOM under partition, multi-hour data loss on crash | Never acceptable. Always use bounded buffer from Phase 1 |

## Integration Gotchas

Common mistakes when connecting to external services.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| **System `ping` binary** | Parsing `ping` output with string splitting across platforms (Linux vs macOS vs Windows formats differ wildly) | Use `icmplib` (Python library) or parse with platform-aware regex. `ping` on macOS has different output format than Linux. `ping` on Windows has yet another format. |
| **HTTP `/healthz` on nodes** | Expecting 200 from `/healthz` to mean "node can reach me." If the node's own server is down, it can't serve health checks — so you lose the ability to ping AND HTTP check simultaneously. | The HTTP health check tests the **target node's** HTTP server, not the checking node's. This is correct, but the node's HTTP server itself is a single point of failure for the HTTP check path. |
| **VPN tunnel interface** | Using the public (tunnel endpoint) IP instead of the private (tunnel interface) IP for checks | Must use the tunnel-private IP. The public IP may not be routable from within the VPN, or may route through the internet instead of the tunnel (destroying the purpose of the mesh test). |
| **File system for data persistence** | Assuming `os.rename` across filesystems is atomic | `os.rename` fails if source and target are on different filesystems (e.g., Docker overlay mount). Use `shutil.move` or explicitly write to same directory. |
| **Multiple nodes reading leader state** | Each node independently reading the full node list from the leader on every check cycle | Leader should push changes (node list diff) as part of the check submission response, or nodes should cache the node list and only request updates on registration changes. |

## Performance Traps

Patterns that work at small scale but fail as usage grows.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| **Loading full month of JSON into memory** | Dashboard load time >10s, leader OOM on data query | Pre-aggregate daily/hourly summaries. Dashboard loads aggregates, not raw data. | ~50 nodes, ~7 days of data |
| **Check-all-nodes-in-parallel (N-1 concurrent checks)** | Node CPU 100%, network saturation, false negatives | Limit concurrent checks per node (asyncio.Semaphore). Stagger start times with jitter. | ~20+ nodes |
| **No ping timeout limit** | One unresponsive node blocks the entire check cycle for all nodes | Set aggressive per-ping timeout (3s max). Wrap in `asyncio.wait_for()`. | Any number of nodes — one flaky peer can tank the mesh |
| **Single-threaded JSON deserialization** | Leader request latency spikes during file write/read cycles | Write to temp file + replace. Use append-only JSON lines so reads can stream. | ~10 nodes, hourly file >5MB |
| **Global check interval (synchronized)** | Traffic pattern alternates idle-spike-idle, VPN bandwidth wasted | Jitter each node's start time ±30%. Add per-node adaptive backoff. | ~5+ nodes (visible at any >1 node) |
| **Streamlit rendering all raw data** | Browser freezes, huge WebSocket messages | Pass pre-aggregated data to Streamlit. Use `st.dataframe(lazy=True)` for large tables. | ~150k rows (Streamlit's lazy threshold) |
| **Without `@st.cache_data` on Streamlit** | Every widget interaction triggers JSON reload+reparse | Use `@st.cache_data(ttl=60)` on data loading. Use `@st.fragment` for auto-refresh sections. | Any multi-page Streamlit app |

## Security Mistakes

Domain-specific security issues beyond general web security.

| Mistake | Risk | Prevention |
|---------|------|------------|
| **Accepting registrations from any node without validation** | Rogue node registers, poisons the mesh with fake check results, causes network-wide misconfiguration | Add a registration token (shared secret) distributed out-of-band. The project spec says "no auth" — at minimum require a pre-shared token in the registration payload. |
| **Exposing raw check file paths in API responses** | Attacker can read arbitrary files on the leader via path traversal in the data API endpoint | Validate path components (date parts) against expected values. Use `os.path.basename()` and check against a whitelist. Never concatenate user input into file paths. |
| **ICMP-based DoS amplification** | All nodes ping each other simultaneously, creating an ICMP flood that can exceed VPN bandwidth | Rate-limit outbound pings per node. Cap concurrent checks. Jitter intervals. |
| **Node injection via registration replay** | If registration is not idempotent, replaying a registration request can create duplicate nodes or overwrite legitimate nodes | Registration must be idempotent. Use `asyncio.Lock` (Pitfall 5) and design registration to be safe to replay (same IP → same node ID, no side effects). |
| **Serving `/healthz` with detailed debug info** | Node health endpoint reveals system information (Python version, file paths, uptime) to any network peer | Health endpoint should return 200 or 503 with minimal body (e.g., `{"status":"ok"}`). Detailed diagnostics on a separate authenticated endpoint. |
| **No validation of submitted check results** | A compromised or buggy node submits results with fabricated timestamps, IPs, or status values | Validate that: node ID exists in registry, timestamp is plausible (not >30 seconds in the future, not >1 hour in the past), reported IP matches the node's registered IP (or is a valid mesh IP). |

## UX Pitfalls

Common user experience mistakes in this domain.

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| **Showing raw ping RTT values without context** | "Why is latency 200ms? Is that bad?" — users panic about normal WAN latency | Show RTT relative to baseline (e.g., "within normal range: 180-220ms"). Show trends, not raw values. For VPN WAN, 100-300ms is normal inter-region. |
| **Dashboard shows "DOWN" for nodes that just registered** | Operator thinks a node is failing. Node was registered 5 seconds ago and hasn't completed its first check cycle | Use the `Pending` status spec. Display nodes as "Initializing" for the first check interval. Don't show DOWN until at least one full interval has elapsed with no data. |
| **Red/green color blindness for connectivity status** | ~8% of male operators can't distinguish red from green indicators | Use icons (checkmark/X/question mark) AND color. Use shape in addition to color (circle = OK, octagon = DOWN, diamond = Pending). |
| **Same visualization for 30-min and 30-day views** | 30-day view is unreadable — too many data points, chart is a solid blob | For 30-day view, show daily aggregate (uptime % per day, not every check). Only show raw check events in the 30-min view. Use heatmaps or summary statistics for long windows. |
| **No explanation of what "Ping" vs "HTTP" means** | "Ping shows FAIL but HTTP shows OK — is the node up or down?" | Display both metrics independently. Add tooltips explaining each. Present the combined assessment (e.g., "Unreachable via ICMP, but HTTP responds") rather than a single status. |

## "Looks Done But Isn't" Checklist

Things that appear complete but are missing critical pieces.

- [ ] **Node registration:** Looks like it works with one node. Test with 3+ nodes registering simultaneously within 100ms. The race (Pitfall 5) won't show with sequential registrations.
- [ ] **Ping check:** Looks like it works when the target responds. Test with a non-responsive target. Without a timeout (Pitfall 2), the blocking call freezes the entire node.
- [ ] **Data persistence:** Looks like it works when writing normally. Test with simultaneous writes (Pitfall 1) or a crash during write (Pitfall 6). Without atomic writes, data loss is invisible but real.
- [ ] **Node down detection:** Looks like it works when a node actually goes down. Verify the alert doesn't fire when just the ping fails but HTTP succeeds (Pitfall 8: MTU blackhole). Need to confirm the combined check logic handles this.
- [ ] **Dashboard loading:** Looks fast on first load with no data. Test with 7+ days of accumulated data. Without caching (Pitfall 4), it will slow to a crawl.
- [ ] **Leader recovery after crash:** Looks like it restarts fine. Check if in-flight check results from the last hour are lost. Verify the hourly file wasn't truncated by the crash.
- [ ] **Network partition recovery:** Looks fine when all nodes restart together. Test: partition the network for 10 minutes, restore it. Do all nodes reconnect? Do they resume checking? Is buffered data replayed without duplication?
- [ ] **Health endpoint:** Returns 200. Test it after the node's event loop is blocked by a long-running synchronous operation (Pitfall 2). Does it still return? If not, the health check is lying.

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| **Corrupted JSON data file** | MEDIUM (lose 1 hour of data max) | 1. Identify the corrupted file from the error. 2. If the file has garbage at the end: truncate to the last valid JSON object. 3. If the file is completely gone: data for that hour is lost. 4. Add a data-repair CLI command for future incidents. |
| **Zombie ping processes** | LOW | 1. `pkill -f "ping.*-c 1"` to kill all orphaned pings. 2. Fix the timeout handler to use the cancellation-safe pattern. 3. Add `prlimit --pid=$PID --nproc=...` to limit max processes per user. |
| **OOM from unbounded buffer** | HIGH (all in-memory data lost) | 1. Restart leader/node. 2. Accept data loss from the buffer. 3. Add explicit max buffer size. 4. Add memory monitoring with alerting. |
| **False positive "node DOWN" from MTU blackhole** | MEDIUM (wasted investigation time) | 1. Verify: does HTTP health check also fail? If not, it's likely an MTU issue. 2. Run `ping -M do -s 1400 <target>` to confirm MTU. 3. Adjust tunnel MTU or add MSS clamping. |
| **Registration state corruption** | HIGH (may need to re-register all nodes) | 1. Stop all nodes. 2. Clear the registry file. 3. Restart leader. 4. Re-register all nodes. 5. Add locking (Pitfall 5). |
| **Leader disk full from unbounded JSON growth** | MEDIUM (archive/compress old data) | 1. Identify largest data files. 2. Compress/archive files older than 30 days. 3. Add retention policy (auto-delete after N days). 4. Add disk usage monitoring. |
| **Dashboard unusably slow** | LOW (UX issue, no data loss) | 1. Add `@st.cache_data` with TTL. 2. Pre-aggregate data. 3. Limit displayed data to last 1000 rows. 4. Provide "reset to defaults" button. |

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| **P1: Concurrent JSON file writes** | Phase 1 (Leader: file storage) | Write a test with 10 concurrent async tasks writing to the same file. Assert all 10 writes are preserved and file is valid JSON. |
| **P2: Sync ping blocking event loop** | Phase 2 (Node Agent: ping loop) | Start Quart server, send a ping to a non-responsive IP with timeout. Verify the `/healthz` endpoint still responds within 100ms during the check. |
| **P3: Zombie subprocesses on timeout** | Phase 2 (Node Agent: timeout handler) | Set ping timeout to 1ms. Verify `process.kill()` + `await process.wait()` is called. Assert no ping processes remain after the test. |
| **P4: Streamlit unbounded data load** | Phase 3 (Dashboard: data loading) | Load 1M entries into the data file. Measure dashboard rerender time. Must be <500ms per interaction with caching. |
| **P5: Node registration race** | Phase 1 (Leader: registration endpoint) | Send 10 concurrent registration requests for the same IP. Assert exactly 1 node is registered. All others return "already registered." |
| **P6: Hourly file rotation data loss** | Phase 1 (Leader: file rotation logic) | 1. Kill the leader mid-write during rotation. Verify the old data file is intact. 2. Simulate rotation boundary: verify all 60 minutes of data exist, none lost. |
| **P7: Healthz confusion (liveness vs readiness)** | Phase 1 (Leader: `/livez` and `/readyz`) | `/readyz` should fail when disk is full. `/livez` should succeed as long as the process responds. Unit test both scenarios. |
| **P8: MTU blackhole misinterpretation** | Phase 2 (Node Agent: combined check logic) | Scenario test: simulate ping failure + HTTP success. Dashboard must NOT show node as DOWN — show "degraded" or "partial." |
| **P9: Thundering herd / synchronized checks** | Phase 2 (Node Agent: check scheduling) | 10 nodes start simultaneously. Measure peak checks/second over 60 seconds. Must be evenly distributed, not bursty. |
| **P10: Unbounded memory buffers** | Phase 1 (Leader: buffer design) + Phase 2 (Node: buffer design) | Fill buffer to max capacity. Assert oldest entries are dropped. Assert memory usage stabilizes, not grows. |

## Sources

- **Pitfall 1 (JSON file races):** Netflix Metaflow PR #3006 (atomic_json_update), QwenPaw PR #3278 (session state corruption), Hive Issue #6696 (state.json data loss), Aperant Issue #488 (implementation_plan.json races)
- **Pitfall 2 (Sync ping blocking):** Quart official docs (background tasks warning), Quart sync code guide, Quart issue #700 scheduling periodic tasks
- **Pitfall 3 (Subprocess cleanup):** Python cpython Issues #139373 and #103847 (communicate() cancellation safety), Python asyncio subprocess docs, runebook.dev asyncio subprocess deadlock guide
- **Pitfall 4 (Streamlit performance):** Streamlit agent-skills optimizing-streamlit-performance, Streamlit PR #15189 (lazy loading), blog posts by Zachary Blackwood and Moncef Ajmani
- **Pitfall 5 (Registration race):** ICN Identity Issue #397 (VUI registration race), Moby PR #52665 (networkdb bulkSyncNode race), registry PR #528 (concurrent server publishing)
- **Pitfall 6 (File rotation):** cpython Issue #88352 (TimedRotatingFileHandler overwrite), D-SafeLogger append-only routing, Papyra rotation backend docs, safeatomic v2.0.3
- **Pitfall 7 (Healthz design):** Azure Health Endpoint Monitoring pattern, AWS builders library health checks, RFC Health Check Response Format (inadarei), Velprove/Vercron blog health check guides
- **Pitfall 8 (VPN MTU):** cr0x.net VPN MTU tuning guide, bigiron.cc MTU Mystery, thelineman.ca VPN MTU & MSS, cr0x.net VPN quality tests
- **Pitfall 9 (Thundering herd):** cr0x.net VPN quality tests (jitter/loss), karpenter Issue #2920 (registration timeout race)
- **Pitfall 10 (Memory buffers):** Hive Issue #6696 (buffer overflow pattern), general asyncio bounded queue patterns

---

*Pitfalls research for: distributed mesh connectivity testing*
*Researched: 2026-06-18*
