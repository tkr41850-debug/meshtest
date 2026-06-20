# mesh-status

## What This Is

A distributed mesh connectivity testing tool for monitoring network health across VMs connected via VPN WAN. A leader server orchestrates node registration and collects periodic connectivity check results (ICMP ping + HTTP /healthz) between all node pairs. A Streamlit dashboard visualizes mesh connectivity over rolling 30-minute or 30-day windows.

## Core Value

A node must be able to detect and report whether it can reach every other node in the mesh, and the leader must present an accurate, up-to-date connectivity view.

## Current Milestone: v0.8 Non-Docker Install & Start Scripts

**Goal:** Provide a production-ready install experience — `curl ... | bash` installs mesh-status, `start.sh --leader` runs the leader, `start.sh --node` runs the node.

**Target features:**
- `deploy/install.sh` — curl-pipe-bash installer (prereqs: uv + git)
- `start.sh` — unified runner with `--leader` / `--node` roles
- Interactive config setup (CLI flags for non-interactive mode, CI-friendly)
- Docker-based CI testing of the full install flow
- Works both inside and outside Docker



## Requirements

### Validated

- ✓ **LEAD-01**: Leader starts on port 58080 with Quart + Hypercorn ASGI server
- ✓ **LEAD-02**: Leader exposes `POST /register` accepting node IP registration
- ✓ **LEAD-03**: Leader maintains in-memory node registry protected by `asyncio.Lock`
- ✓ **LEAD-04**: Leader exposes `POST /submit` accepting per-cycle check results from nodes
- ✓ **LEAD-05**: Leader exposes `GET /node-list` returning all registered node IPs
- ✓ **LEAD-06**: Leader exposes `GET /livez` liveness endpoint
- ✓ **LEAD-07**: Leader exposes `GET /readyz` readiness endpoint
- ✓ **REGI-01**: `register.py` accepts `--node-ip` and `--leader-ip` via argv
- ✓ **REGI-02**: `register.py` accepts node-ip and leader-ip via stdin
- ✓ **REGI-03**: On registration, leader pushes full node IP list to all registered nodes
- ✓ **REGI-04**: Registration is idempotent
- ✓ **NODE-01**: Node fetches peer IP list from leader at start of each check cycle
- ✓ **NODE-02**: Node runs ICMP ping via system `ping` binary
- ✓ **NODE-03**: Node runs HTTP GET `/healthz` against all peers concurrently
- ✓ **NODE-04**: Ping and HTTP checks use independent timeout handling
- ✓ **NODE-05**: Node submits check results to leader after each cycle
- ✓ **NODE-06**: On submission failure, node buffers results and retries next cycle
- ✓ **NODE-07**: Check interval configurable on leader side (default 10s)
- ✓ **NODE-08**: Concurrent peer checks use semaphore limiting
- ✓ **NODE-09**: Node uses `asyncio.create_subprocess_exec` for ping
- ✓ **NODE-10**: Ping timeout uses `process.wait()` not `communicate()`
- ✓ **DATA-01**: Leader persists results to date-partitioned JSON files
- ✓ **DATA-02**: Data writes use append-only JSON Lines format
- ✓ **DATA-03**: Background task flushes in-memory results to disk every hour
- ✓ **DATA-04**: Leader exposes `GET /data?window=30m`
- ✓ **DATA-05**: Leader exposes `GET /data?window=30d`
- ✓ **DATA-06**: Node status calculated at query time: OK, Pending, NotAvailable
- ✓ **DATA-07**: Data API includes CORS headers
- ✓ **DASH-01**: Streamlit dashboard served standalone
- ✓ **DASH-02**: Dashboard shows 30-minute connectivity matrix
- ✓ **DASH-03**: Dashboard shows 30-day daily aggregated uptime view
- ✓ **DASH-04**: Each node pair shows per-peer connectivity status
- ✓ **DASH-05**: Dashboard uses `@st.cache_data(ttl=25)` for data loading
- ✓ **DASH-06**: Dashboard uses `@st.fragment` for live auto-refresh
- ✓ **NODE-HTTP**: Node HTTP server receives peer push and config updates
- ✓ **HEALTHZ**: Leader exposes `GET /healthz`
- ✓ **RETENTION**: 30-minute data window retains 30 min after flush
- ✓ **DOCK-01**: Dockerfile for leader+dashboard container (Quart + Streamlit) — v0.2
- ✓ **DOCK-02**: Dockerfile for node agent container — v0.2
- ✓ **DOCK-03**: docker-compose.yml for local dev/test — v0.2
- ✓ **DOCK-04**: Docker-specific config (environment variables, ports, volumes for data) — v0.2
- ✓ **DOCK-05**: README deployment docs for Docker-based deployment — v0.2
- ✓ **CI-01**: GitHub Actions workflow builds and pushes multi-arch images to Docker Hub — v0.2

### v0.6 Validated

Now part of validated requirements — see v0.5 validated section.

### v0.7 Active

(none — all shipped)

### v0.7 Validated

- ✓ **FIX-04**: History bars show rolling 30-minute/30-day history instead of only the most recent check

- ✓ **FIX-01**: Fix `CheckResult` interface — use `ping_ok: boolean` / `http_ok: boolean` to match real API
- ✓ **FIX-02**: Fix `aggregateByMinute` checks `c.ping_status` (not in API data) → use `c.ping_ok`
- ✓ **FIX-03**: Backend infers `node_ip` from `_results` when disk data has empty `node_ip`
- ✓ **DASH-13**: Flat 30-day view — remove `<details>` expanders, use sticky headers
- ✓ **DASH-14**: Gap between matrix table and cards in 30m tab
- ✓ **DASH-15**: Two separate history bar rows per pair (ICMP + HTTP) in both views
- ✓ **DASH-16**: HSB-interpolated bar colors via shared `bars.ts` (`renderBars(bars: {percent, tooltip}[])`)
- ✓ **TEST-04**: Update all frontend test fixtures for new `CheckResult` type and bar format

### v0.8 Active

- [ ] **INST-01**: `deploy/install.sh` installs mesh-status from GitHub (prereqs: uv + git)
- [ ] **INST-02**: `start.sh` starts leader or node based on `--leader` / `--node` flag
- [ ] **INST-03**: Interactive config setup with CLI flag override for non-interactive mode
- [ ] **INST-04**: Docker-based CI test verifies install flow in fresh container

### Out of Scope

- Authentication / access control — VPN is trusted network for prototype
- Database backend — JSON file storage sufficient for prototype scale
- Real-time push/WebSocket — Frontend polls the data endpoint
- Encryption of data in transit or at rest — prototype
- Kubernetes / orchestration — Docker Compose sufficient for prototype

## Context

- Python backend (Quart) on port 58080, frontend (Vite + TS + Tailwind) served from same port
- Deployed across multiple VMs on different geographies connected via VPN WAN
- Data is small per check, retained in memory on nodes between submissions
- Leader writes JSON files hourly to avoid memory/disk pressure
- System `ping` binary used for ICMP (shelled out)
- Frontend fetches from same-origin API endpoints

## Constraints

- **Port**: Leader must listen on 58080 (serving both API and frontend)
- **Language**: Python (Quart) + TypeScript (React/Vanilla TS frontend)
- **Framework**: Quart (async HTTP server), Vite + Tailwind CSS (frontend)
- **Deployment**: Multi-VM over VPN WAN
- **Base image**: python:3.12-slim with Node.js build stage

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Quart instead of FastAPI | Simpler async server, fewer dependencies for prototype | — Pending |
| JSON file persistence | Quick to implement, inspectable, no DB setup | — Pending |
| System ping binary | Avoids root/capabilities for raw ICMP sockets | — Pending |
| No auth | VPN is trusted, prototype speed | — Pending |
| Port 58080 | Avoids privileged ports, unlikely to conflict | ✓ Good |
| Vite + Tailwind for frontend | Modern tooling, fast dev iteration, type-safe | — Pending |
| Leader serves frontend from same port | Simpler deployment, no CORS, one port to manage | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-06-19 after v0.8 milestone start*
