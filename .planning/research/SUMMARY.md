# Project Research Summary

**Project:** mesh-status
**Domain:** Distributed mesh connectivity testing tool (leader-node push model)
**Researched:** 2026-06-18
**Confidence:** HIGH

## Executive Summary

mesh-status is a distributed mesh connectivity testing tool for monitoring ICMP and HTTP(S) reachability between VMs across a VPN WAN. Unlike Prometheus-based pull models (which require the leader to reach every target), mesh-status uses a **node-initiated push model**: each node independently pings all peers and submits results to a central leader. This mirrors patterns found in SignalScope, DNMS, and Celery heartbeats — but avoids the operational complexity of a full observability stack (no Prometheus, no Grafana, no database). The recommended stack is **Python 3.12 + Quart 0.20 + Streamlit 1.58**, with JSON file persistence and system `ping` binary via asyncio subprocess.

The research is consistent across all four dimensions: the stack is battle-tested, the features are well-understood (validated against 10+ competitor tools), the architecture follows established distributed systems patterns, and the pitfalls cite verified bug reports from production systems (Netflix Metaflow, Docker Moby, CPython, etc.). The recommended approach is to build in 5 phases following dependency order: **Leader Core → Node Agent → Persistence & Data API → Dashboard → Hardening**.

**Key risks and mitigations:**
1. **Concurrent JSON file writes losing data** → Use append-only JSON Lines format and atomic file writes (`write temp + fsync + replace`), never read-modify-write on shared files.
2. **Synchronous ping subprocess blocking the event loop** → Always use `asyncio.create_subprocess_exec()` with `asyncio.wait_for()` timeout — never `subprocess.run()` in async code.
3. **Streamlit dashboard becoming unusable as data accumulates** → Use `@st.cache_data(ttl=60)` from day one; pre-aggregate data at write time; use `@st.fragment` for live-updating sections.
4. **Ping subprocess zombie processes on timeout** → Use the cancellation-safe pattern (`wait_for(process.wait())` instead of `wait_for(communicate())`) to avoid orphaned processes and lost output.
5. **Node registration races corrupting mesh state** → Serialize registration handlers with `asyncio.Lock()` and use idempotent registration design.

## Key Findings

### Recommended Stack

**See full details:** [STACK.md](./STACK.md)

The stack is deliberately minimal — each choice eliminates unnecessary dependencies for a small-scale prototype.

**Core technologies:**
- **Python 3.12**: Runtime language — balance of performance (faster startup than 3.13/3.14) and ecosystem compatibility. Active security support through 2028. All major dependencies target it.
- **Quart 0.20**: Async HTTP server — reimplements the Flask API with native `async/await` support (Pallets project). Critical for concurrent registration + result ingestion without thread pool overhead. Avoids pulling in Starlette/Pydantic as forced dependencies.
- **Hypercorn 0.18**: ASGI production server — canonical companion to Quart (same author). Supports HTTP/1, HTTP/2, HTTP/3. Listens on port 58080.
- **Streamlit 1.58**: Frontend dashboard — de facto standard for Python dashboards (Snowflake-backed). The "script rerun on interaction" model eliminates callback spaghetti for polling dashboards.

**Supporting libraries:**
- `aiofiles 24.1.0` — async file I/O (avoids blocking event loop on JSON writes)
- `httpx 0.28.x` — async HTTP client for node-side health checks (replaces `requests`)
- `quart-cors 0.8.0` — CORS headers for cross-origin frontend (Streamlit on 8501, API on 58080)
- `pydantic 2.x` — optional data validation for registration/check models

**What NOT to use:** `requests` (sync-only), Flask (WSGI, no async), `gunicorn` (WSGI server), `numpy/pandas` (overkill for tiny data), `Celery/Redis` (massive overengineering), system `ping` libraries with raw sockets (root required).

### Expected Features

**See full details:** [FEATURES.md](./FEATURES.md)

**Must have (table stakes — P1, launch with v1):**
- Node registration via simple Python script (`register.py --node-ip --leader-ip`)
- Peer list auto-distribution to all nodes on registration
- ICMP ping checks + HTTP `/healthz` checks against all peers
- Results submitted to leader with buffer-and-retry on failure
- Leader persists results to date-partitioned JSON files (`data/[yyyy]/[mm]/[dd].json`, hourly)
- Data API endpoint (`GET /data?window=30m`)
- Streamlit dashboard showing mesh connectivity with 30-minute time window
- Node status: OK, Pending (registered, no data yet), NotAvailable (expected data missing)
- Configurable check interval (default 10s)

**Should have (competitive differentiators — P2, add after validation):**
- Push model (node-initiated checks submit to passive leader — key for VPN WAN where leader can't reach nodes)
- No database dependency — entire durable state is a `data/` directory
- Dual time window (30min real-time + 30day daily aggregated uptime)
- Pending vs NotAvailable distinction (critical UX: don't show DOWN for freshly registered nodes)
- Meshing without Kubernetes — works on any Linux VMs on any VPN
- Registration via stdin for automation (`echo "10.0.0.1" | python register.py --leader-ip 10.0.0.2`)

**Defer (v2+):**
- MTR/traceroute integration for path diagnostics
- Alert webhooks (Slack, email) — dashboard is the alerting mechanism for prototype
- Docker deployment — ship as Python package initially
- Prometheus `/metrics` endpoint — expose if demand arises
- Authentication — VPN is the trust boundary; revisit if exposed beyond VPN
- Multi-leader HA — deferred until leader becomes a real SPOF concern

### Architecture Approach

**See full details:** [ARCHITECTURE.md](./ARCHITECTURE.md)

The architecture follows a **centralized leader with distributed probing nodes** pattern. All communication is node-initiated (push model). The leader is a passive collector — it never initiates connections to nodes. This is critical for VPN WAN topologies where leader may not have inbound connectivity to all nodes.

**Major components:**
1. **Leader (Quart server, ASGI on port 58080):** Handles node registration (`POST /register`), result ingestion (`POST /submit`), and data API (`GET /data`). Maintains in-memory state (node registry, check results) with `asyncio.Lock` protection. Runs a background task for hourly JSON persistence. Streamlit runs as a separate process calling the data API.
2. **Node (Python async script):** Runs the check scheduler loop: fetch peer list from leader → run concurrent ICMP ping + HTTP `/healthz` checks against all peers (semaphore-limited via `asyncio.gather`) → submit results to leader → buffer in memory on failure, retry next cycle. No disk persistence on nodes.
3. **Persistence layer:** Date-partitioned JSON files written hourly by a background asyncio task. In-memory state serves the data API; JSON files are the historical archive.

**Key patterns:**
- Push-based result collection (leader never polls)
- In-memory state with hourly snapshot persistence
- Concurrent semaphore-limited probe execution on nodes
- Node failure detection by absence (NotAvailable if no submission within 3× interval)
- Single event loop per process; Streamlit as separate HTTP-consumer

### Critical Pitfalls

**See full details:** [PITFALLS.md](./PITFALLS.md)

All 10 pitfalls are verified against real bug reports, production post-mortems, and official documentation. Top 5:

1. **Concurrent JSON file writes without locking (data loss):** Multiple writers reading-modifying-writing the same file → silent overwrites. *Mitigation:* Use append-only JSON Lines format or atomic write pattern (write temp → `os.fsync()` → `os.replace()`). Never rewrite the active file. Add `fcntl.flock()` on a separate `.lock` file for writer exclusion. Must be correct from Phase 1.

2. **Synchronous `ping` blocking the event loop:** Using `subprocess.run()` instead of `asyncio.create_subprocess_exec()` → node becomes unresponsive during checks, own health endpoint fails. *Mitigation:* Always use `asyncio.create_subprocess_exec()` with `asyncio.wait_for()` timeout and `process.kill()` + `await process.wait()` cleanup. Must be correct from Phase 2.

3. **Streamlit full-script rerun with unbounded JSON loading:** Every widget interaction reloads all JSON → dashboard unusable with accumulated data. *Mitigation:* `@st.cache_data(ttl=60)` on data loading, pre-aggregate at write time, use `@st.fragment` for auto-refresh sections. Must be built in from Phase 3.

4. **Ping subprocess zombie accumulation on timeout:** `asyncio.wait_for()` on `communicate()` creates orphaned pings → PID exhaustion. *Mitigation:* Use cancellation-safe pattern: `wait_for(process.wait())` instead of `wait_for(communicate())`. Kill process first, then read output. Must be correct from Phase 2.

5. **Node registration race (TOCTOU):** Two simultaneous registrations read "no such IP," both register, one overwrites the other → mesh state corrupted. *Mitigation:* `asyncio.Lock()` around the entire registration handler (read-check-write). Design for idempotent registrations. Must be correct from Phase 1.

## Implications for Roadmap

Based on combined research, the following phase structure is recommended. This follows the dependency order identified in ARCHITECTURE.md (build order), maps to FEATURES.md P1-P3 priorities, and embeds pitfall mitigations where they belong.

### Phase 1: Leader Core Foundation
**Rationale:** Everything depends on the leader — nodes need a leader to register with, check results need a leader to submit to, the dashboard needs a data API. Phase 1 must also get the persistence layer right because retrofitting atomic file writes is painful after data accumulates.
**Delivers:** Running Quart server on port 58080 with node registration, result ingestion, in-memory state, robust file storage, and health endpoints.
**Addresses:** Node registration, peer list distribution, basic submission endpoint, `GET /node-list`, data API skeleton, `GET /livez` + `GET /readyz`
**Avoids:** Pitfall 1 (concurrent JSON writes → append-only design), Pitfall 5 (registration race → `asyncio.Lock`), Pitfall 6 (file rotation data loss → per-hour immutable files), Pitfall 7 (healthz confusion → separate `/livez` and `/readyz`), Pitfall 10 (unbounded buffers → bounded-async-queue design)
**Stack:** Python 3.12, Quart 0.20, Hypercorn 0.18, `aiofiles 24.1.0`, `quart-cors 0.8.0`
**Research flag:** No deeper research needed — Quart + asyncio patterns are well-documented. Standard patterns.

### Phase 2: Node Agent
**Rationale:** Leader exists but has no data without nodes running checks. Node must be built correctly because every pitfall in this phase (sync ping, zombie subprocesses, thundering herd) creates silent failures that are hard to debug later.
**Delivers:** Fully functional node agent that registers, fetches peer lists, runs concurrent ICMP ping + HTTP health checks with semaphore limiting, submits results, buffers on failure with bounded retry.
**Addresses:** ICMP ping checks, HTTP `/healthz` checks, buffer-and-retry on submission failure, combined check logic (ping + HTTP as independent signals)
**Avoids:** Pitfall 2 (sync ping blocking → `asyncio.create_subprocess_exec`), Pitfall 3 (zombie subprocesses → cancellation-safe timeout), Pitfall 8 (MTU blackhole → independent ping/HTTP status, never mark DOWN based on ping alone), Pitfall 9 (thundering herd → jittered intervals, semaphore-limited concurrency)
**Stack:** `httpx 0.28.x`, system `ping` binary, `asyncio` subprocess
**Research flag:** Needs deeper research during planning — platform-specific ping output parsing (Linux vs macOS vs Windows). Linux and Windows have different flag conventions (`-c` vs `-n`) and output formats. The parser must be abstracted from the start (ARCHITECTURE.md already flags this).

### Phase 3: Persistence & Data API
**Rationale:** Core leader and node exist but data only lives in memory. Phase 3 adds the persistence layer that enables historical queries and the 30-day dashboard view. The data API is the contract between leader storage and Streamlit frontend.
**Delivers:** Hourly JSON persistence (append-only JSON Lines), pre-aggregated daily summaries, data API with `GET /data?window=30m` and `GET /data?window=30d`, node status calculation (OK/Pending/NotAvailable at query time).
**Addresses:** JSON file persistence (hourly), data API endpoint, node status (OK/Pending/NotAvailable), 30-day aggregated view preparation
**Avoids:** Pitfall 10 (unbounded memory → hourly flush + bounded buffers)
**Stack:** `aiofiles 24.1.0`, Pydantic 2.x (optional model validation), `json` stdlib
**Research flag:** No deeper research needed — JSON file I/O patterns are standard. The per-hour immutable file design eliminates rotation complexity.

### Phase 4: Streamlit Dashboard
**Rationale:** The tool is invisible without a frontend. Streamlit sits on top of the data API, so Phase 1-3 must be stable. Dashboard performance is critical — users judge the entire tool by how the dashboard behaves.
**Delivers:** Streamlit dashboard with 30-minute connectivity matrix, node status indicators (OK/Pending/NotAvailable), latency tooltips, 30-day aggregated uptime view, proper caching and fragment-based auto-refresh.
**Addresses:** Dashboard with 30min view, dashboard with 30day view, latency matrix, peer-to-peer visualization
**Avoids:** Pitfall 4 (unbounded data loading → `@st.cache_data(ttl=60)` from first commit, pre-aggregated summary data, `@st.fragment` for auto-refresh)
**Stack:** Streamlit 1.58, `st.cache_data`, `st.fragment`, Arrow-native `st.dataframe`
**Research flag:** May need research into Streamlit 1.58's lazy loading for large datasets (lazy row loading threshold at ~150k rows). Verify `st.fragment(run_every="10s")` works with the data API pattern.

### Phase 5: Hardening & Operational Readiness
**Rationale:** The prototype works but needs resilience, observability, and operational tooling before it's deployable in production. This phase addresses edge cases and long-running behavior.
**Delivers:** Robust error handling throughout, structured logging, MTU baseline testing script, node de-registration/cleanup, configurable check interval, adaptive backoff for retries, recovery strategies documented.
**Addresses:** Node de-registration, configurable check interval, check timeout configuration, operational runbook
**Avoids:** Pitfall 8 (MTU baseline testing before deployment), Pitfall 9 (adaptive backoff), recovery strategies for all 10 pitfalls
**Research flag:** Add a `/gsd-research-phase` before Phase 5 if alert webhooks, Docker deployment, or Prometheus integration become priorities — these are deferred to v2+ and not needed for prototype.

### Phase Ordering Rationale

- **Dependency-driven order:** Leader (P1) → Node (P2) → Persistence (P3) → Dashboard (P4) → Hardening (P5). Each phase produces something testable. P1 and P2 could be built in parallel with stubs, but the first integration test requires both.
- **Persistence before Dashboard:** The 30-minute view can work from in-memory data alone, but the 30-day view requires persisted daily files. Building persistence first ensures the dashboard has data.
- **Embedding pitfall mitigations early:** 6 of 10 critical pitfalls must be addressed in Phases 1-2. Retrofitting file locking, async subprocess patterns, or registration locks is harder than building them in from the start.
- **Feature delivery per phase:** Phase 1 delivers 3 P1 features (registration, peer list, basic API), Phase 2 delivers 4 P1 features (ping, healthz, submit, buffer-retry), Phase 3 delivers 2 P1 features (persistence, data API), Phase 4 delivers 2 P1 features (dashboard, node status). This gives a clear checkpoint after each phase.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 2:** Node agent needs platform-specific ping output parsing. The `ping` binary behaves differently on Linux, macOS, and Windows (flags, output format, timeout behavior). An abstraction layer is required. Dedicate a `/gsd-research-phase` to the ping parser interface before implementation.
- **Phase 4:** Streamlit 1.58's lazy loading for large DataFrames and the `st.fragment` auto-refresh pattern. While well-documented, the combination of caching + fragment + live data source has edge cases (cache invalidation, reconnection after leader restart). Quick `/gsd-research-phase` recommended.
- **Phase 5:** If alert webhooks, Docker deployment, or Prometheus `/metrics` become priorities during validation, add a research phase before implementing. These are deferred to v2+ by default.

Phases with standard patterns (skip research-phase):
- **Phase 1 (Leader Core):** Quart route handlers, `asyncio.Lock` patterns, and JSON file I/O are well-documented with official docs. No pre-implementation research needed.
- **Phase 3 (Persistence & Data API):** JSON Lines append pattern, hourly cron-like background tasks, and HTTP data APIs are standard patterns. Proceed directly to planning.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All versions verified on PyPI. Version compatibility explicitly checked (Python 3.9+ for Quart, 3.10+ for Streamlit). Alternatives compared with trade-off analysis. |
| Features | HIGH | Cross-referenced against 10+ competitor tools (Goldpinger, DNMS, Meshping, Smokeping, Prometheus BBE, SignalScope, Gatus, Uptime Kuma, etc.). Feature dependencies mapped explicitly. Anti-features identified and justified. |
| Architecture | HIGH | Validated against established patterns (Prometheus BBE pull model, Celery/Airflow heartbeat push, Microsoft Pingmesh paper, Goldpinger K8s mesh). Anti-patterns identified with explanations. Async model trade-offs documented. |
| Pitfalls | HIGH | Each pitfall sourced to real bug reports (Netflix Metaflow PR #3006, CPython Issues #139373/#103847, Docker Moby PR #52665, etc.), official documentation warnings (Quart sync code guide, Streamlit caching docs), and production post-mortems. |

**Overall confidence:** HIGH

### Gaps to Address

The following areas were not fully resolved during research and need attention during planning/execution:

- **Cross-platform ping output parsing:** The node agent's ping parser needs to handle Linux, macOS, and Windows output formats. The research recommends platform-aware regex but does not provide verified parsers for all three. This should be researched and validated during Phase 2 planning. A test suite with sample outputs from each platform would prevent production surprises.
- **Cancellation-safe subprocess pattern verification:** The recommended pattern for Pitfall 3 (using `wait_for(process.wait())` instead of `wait_for(communicate())`) comes from CPython issue discussion, not official API documentation. While logically sound, this should be verified with integration tests during Phase 2 implementation (test: timeout ping, verify no zombie processes, verify partial output is retrievable).
- **Streamlit lazy loading threshold:** The research notes that Streamlit >= June 2026 adds automatic lazy row loading for `st.dataframe` at ~150k rows. The exact threshold and behavior should be verified during Phase 4 against Streamlit 1.58.0 specifically.
- **Node buffer overflow semantics:** The bounded buffer design prevents OOM but the behavior on overflow needs a specific policy decision: drop oldest or newest? Block the producer? The research recommends dropping oldest — this should be confirmed during Phase 2 planning.
- **30-day aggregation format:** The research recommends pre-aggregated summaries at write time but does not prescribe the exact format. This design decision (daily uptime percentages vs. hourly buckets vs. decimated raw data) should be made during Phase 3 planning based on expected dashboard queries.

## Sources

### Primary (HIGH confidence)
- Quart 0.20.0 — https://pypi.org/project/Quart/ (verified PyPI release)
- Hypercorn 0.18.0 — https://pypi.org/project/Hypercorn/ (verified PyPI release)
- Streamlit 1.58.0 — https://pypi.org/project/streamlit/ (verified PyPI release May 2026)
- Python asyncio subprocess docs — https://docs.python.org/3/library/asyncio-subprocess.html
- Quart async patterns docs — https://quart.palletsprojects.com/
- Streamlit caching docs — https://docs.streamlit.io/develop/concepts/architecture/caching
- httpx async client docs — https://www.python-httpx.org/
- Goldpinger (Bloomberg) — https://github.com/bloomberg/goldpinger — mesh connectivity testing
- Prometheus Blackbox Exporter — https://github.com/prometheus/blackbox_exporter — v0.28.0
- DNMS distributed ping — https://pkg.go.dev/github.com/jacksontj/dnms
- ACM SIGCOMM '15 Pingmesh paper — https://conferences.sigcomm.org/sigcomm/2015/pdf/papers/p139.pdf
- Python cpython Issues #139373 and #103847 — subprocess communicate() cancellation safety

### Secondary (MEDIUM confidence)
- Meshping — https://github.com/Svedrin/meshping — distributed ping with traceroute
- Smokeping — https://oss.oetiker.ch/smokeping/ — classic latency monitoring
- cr0x.net VPN MTU tuning guide — VPN MTU blackhole patterns
- Heartbeats in Distributed Systems — https://arpitbhayani.me/blogs/heartbeats-in-distributed-systems
- Simon Willison — asyncio subprocess time limit — https://til.simonwillison.net/python/subprocess-time-limit
- Best Open Source Monitoring Tools in 2026 — https://dev.to/devhelm/... (blog comparison)
- Network exporter — https://github.com/syepes/network_exporter — ICMP/MTR/TCP/HTTP Prometheus exporter

---
*Research completed: 2026-06-18*
*Ready for roadmap: yes*
