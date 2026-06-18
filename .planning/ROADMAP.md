# Roadmap: mesh-status

## Overview

A distributed mesh connectivity testing tool for monitoring network health across VMs connected via VPN WAN. We start with the leader server (foundation), add node agents to collect data, persist results to disk, and finally visualize everything in a Streamlit dashboard. Each phase delivers a testable, self-contained capability — from "leader accepts registrations" to "full mesh visibility in a dashboard."

## Phases

- [x] **Phase 1: Leader Core & Registration** — Quart server on port 58080 with node registration, peer list distribution, in-memory state, and health endpoints
- [x] **Phase 2: Node Agent** — Async ping + HTTP health checks with semaphore-limited concurrency, result submission, and buffer-and-retry
- [x] **Phase 3: Persistence & Data API** — Hourly JSON Lines persistence, date-partitioned files, query endpoints for 30-minute and 30-day windows
- [ ] **Phase 4: Streamlit Dashboard** — Connectivity matrix with 30-minute and 30-day views, cached data loading, fragment-based auto-refresh

## Phase Details

### Phase 1: Leader Core & Registration
**Goal**: A running leader that accepts node registrations, maintains the node registry, distributes peer lists, and exposes health endpoints
**Depends on**: Nothing (first phase)
**Requirements**: LEAD-01, LEAD-02, LEAD-03, LEAD-04, LEAD-05, LEAD-06, LEAD-07, REGI-01, REGI-02, REGI-03, REGI-04
**Success Criteria** (what must be TRUE):
  1. Leader starts on port 58080 with Quart + Hypercorn and responds to `GET /livez` (liveness) and `GET /readyz` (readiness)
  2. A node can register with the leader via `register.py` (argv or stdin), receiving the full peer IP list in response
  3. Re-registering the same node IP is idempotent — updates state without error or duplicate entry
  4. When a new node registers, the leader pushes the updated node IP list to all currently registered nodes
   5. `GET /node-list` returns all registered node IPs; `POST /submit` accepts check results into in-memory state
**Plans**: 3 plans across 2 waves

```
Plans:
- [x] 01-01-PLAN.md — Project Foundation & Core Server (pyproject.toml, package, config, models, /livez, /readyz)
- [x] 01-02-PLAN.md — Registration & Submission Endpoints (POST /register, POST /submit, GET /node-list, peer push)
- [x] 01-03-PLAN.md — register.py CLI Script (argv + stdin registration)
```

### Phase 2: Node Agent
**Goal**: Registered nodes can probe all peers via ICMP ping and HTTP `/healthz`, then submit results to the leader, with resilience against submission failures
**Depends on**: Phase 1
**Requirements**: NODE-01, NODE-02, NODE-03, NODE-04, NODE-05, NODE-06, NODE-07, NODE-08, NODE-09, NODE-10
**Success Criteria** (what must be TRUE):
   1. Node fetches peer IP list from leader at the start of each check cycle and runs ICMP ping + HTTP `GET /healthz` against all peers concurrently
   2. Ping and HTTP checks use independent timeout handling; concurrent peer checks are limited by a semaphore to avoid resource exhaustion
   3. Check results (status, latency, timestamp) are submitted to the leader's `POST /submit` after each cycle completes
   4. On submission failure, results are buffered in memory and automatically retried on the next check cycle
   5. The check interval is configurable on the leader side (default 10s); ping subprocess uses `asyncio.create_subprocess_exec` with cancellation-safe timeout
**Plans**: 2 plans across 2 waves

```
Plans:
- [x] 02-01-PLAN.md — Node Agent Core (async loop, ping + HTTP checks, semaphore, submission)
- [x] 02-02-PLAN.md — Buffer/Retry + Config Push (UpdateConfig on leader, node HTTP listener)
```

### Phase 3: Persistence & Data API
**Goal**: Check results persist to disk and become queryable through a data API that supports real-time and historical views with calculated node status
**Depends on**: Phase 2
**Requirements**: DATA-01, DATA-02, DATA-03, DATA-04, DATA-05, DATA-06, DATA-07
**Success Criteria** (what must be TRUE):
  1. Check results are persisted to date-partitioned JSON Lines files at `data/[yyyy]/[mm]/[dd].json` using append-only format (never read-modify-write)
  2. A background asyncio task flushes in-memory results to disk every hour
  3. `GET /data?window=30m` returns the last 30 minutes of raw check results
  4. `GET /data?window=30d` returns daily aggregated uptime statistics
  5. Node status values (OK, Pending, NotAvailable) are calculated at query time based on submission recency and data presence
  6. All data API responses include CORS headers for cross-origin access from the Streamlit frontend
**Plans**: TDD (tests then implementation)

```
Plans:
- [x] 03-01-PLAN.md — Persistence Layer (TDD)
- [x] 03-02-PLAN.md — Data API & Status Calculation (TDD)
```

### Phase 3.1: Add mocked integration tests for Phase 1 and 2 (INSERTED)
**Goal**: Add mocked integration tests covering leader registration flow, peer push, node check cycles, and buffer/retry behavior to ensure regression safety before Phase 4
**Depends on**: Phase 3
**Urgent**: Discovered mid-milestone — existing coverage only unit-tests internals, leaving critical integration paths untested
**Plans**: 2 plans across 1 wave

```
Plans:
- [ ] 03.1-01-PLAN.md — Mocked Leader Integration Tests (conftest, registration, peer push, submit, config push, data flow)
- [ ] 03.1-02-PLAN.md — Mocked Node Integration Tests (check_node, check cycle, buffer/retry, submission HTTP)
```

### Phase 4: Streamlit Dashboard
**Goal**: Users can visualize mesh connectivity in real-time (30-minute window) and historically (30-day window) through a cached, auto-refreshing Streamlit dashboard
**Depends on**: Phase 3
**Requirements**: DASH-01, DASH-02, DASH-03, DASH-04, DASH-05, DASH-06
**Success Criteria** (what must be TRUE):
  1. Streamlit dashboard loads (served alongside or separately from Quart) and displays a 30-minute connectivity matrix showing per-peer status for each node pair
  2. Dashboard displays a 30-day daily aggregated uptime view with per-peer breakdown
  3. Each node pair shows connectivity status (OK, Pending, NotAvailable) with clear visual distinction
  4. Dashboard uses `@st.cache_data(ttl=60)` for efficient data loading and `@st.fragment` for live auto-refreshing sections
  5. Dashboard refresh interval works cleanly with the data API — updates appear without full-page reload
**Plans**: TBD
**UI hint**: yes

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Leader Core & Registration | 3/3 | ✓ Complete | 2026-06-18 |
| 2. Node Agent | 2/2 | ✓ Complete | 2026-06-18 |
| 3. Persistence & Data API | 2/2 | ✓ Complete | 2026-06-18 |
| 3.1. Integration tests | 2/2 | ◆ Ready to execute | - |
| 4. Streamlit Dashboard | 0/0 | Not started | - |
