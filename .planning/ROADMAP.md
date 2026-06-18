# Roadmap: mesh-status

## Overview

A distributed mesh connectivity testing tool for monitoring network health across VMs connected via VPN WAN. We start with the leader server (foundation), add node agents to collect data, persist results to disk, and finally visualize everything in a Streamlit dashboard. Each phase delivers a testable, self-contained capability — from "leader accepts registrations" to "full mesh visibility in a dashboard."

## Phases

- [ ] **Phase 1: Leader Core & Registration** — Quart server on port 58080 with node registration, peer list distribution, in-memory state, and health endpoints
- [ ] **Phase 2: Node Agent** — Async ping + HTTP health checks with semaphore-limited concurrency, result submission, and buffer-and-retry
- [ ] **Phase 3: Persistence & Data API** — Hourly JSON Lines persistence, date-partitioned files, query endpoints for 30-minute and 30-day windows
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
**Plans**: TBD

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
**Plans**: TBD

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
**Plans**: TBD

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
| 1. Leader Core & Registration | 0/0 | Not started | - |
| 2. Node Agent | 0/0 | Not started | - |
| 3. Persistence & Data API | 0/0 | Not started | - |
| 4. Streamlit Dashboard | 0/0 | Not started | - |
