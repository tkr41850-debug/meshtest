# Requirements: mesh-status

**Defined:** 2026-06-17
**Core Value:** A node must be able to detect and report whether it can reach every other node in the mesh, and the leader must present an accurate, up-to-date connectivity view.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Leader Core

- [ ] **LEAD-01**: Leader starts on port 58080 with Quart + Hypercorn ASGI server
- [ ] **LEAD-02**: Leader exposes `POST /register` accepting node IP registration
- [ ] **LEAD-03**: Leader maintains in-memory node registry protected by `asyncio.Lock`
- [ ] **LEAD-04**: Leader exposes `POST /submit` accepting per-cycle check results from nodes
- [ ] **LEAD-05**: Leader exposes `GET /node-list` returning all registered node IPs
- [ ] **LEAD-06**: Leader exposes `GET /livez` liveness endpoint
- [ ] **LEAD-07**: Leader exposes `GET /readyz` readiness endpoint

### Node Registration

- [ ] **REGI-01**: `register.py` accepts `--node-ip` and `--leader-ip` via argv
- [ ] **REGI-02**: `register.py` accepts node-ip and leader-ip via stdin (`input()`) when args omitted
- [ ] **REGI-03**: On registration, leader pushes full node IP list to all registered nodes
- [ ] **REGI-04**: Registration is idempotent (re-registering same IP updates state without error)

### Node Agent

- [ ] **NODE-01**: Node fetches peer IP list from leader at start of each check cycle
- [ ] **NODE-02**: Node runs ICMP ping via system `ping` binary against all peers concurrently
- [ ] **NODE-03**: Node runs HTTP GET `/healthz` against all peers concurrently
- [ ] **NODE-04**: Ping and HTTP checks use independent timeout handling
- [ ] **NODE-05**: Node submits check results (status, latency, timestamp) to leader after each cycle
- [ ] **NODE-06**: On submission failure, node buffers results in memory and retries next cycle
- [ ] **NODE-07**: Check interval is configurable on leader side (default 10s)
- [ ] **NODE-08**: Concurrent peer checks use semaphore limiting to avoid resource exhaustion
- [ ] **NODE-09**: Node uses `asyncio.create_subprocess_exec` for ping (never `subprocess.run`)
- [ ] **NODE-10**: Ping subprocess timeout uses cancellation-safe pattern (`process.wait()` not `communicate()`)

### Persistence & Data API

- [ ] **DATA-01**: Leader persists check results to date-partitioned JSON files: `data/[yyyy]/[mm]/[dd].json`
- [ ] **DATA-02**: Data writes use append-only JSON Lines format (never read-modify-write)
- [ ] **DATA-03**: A background asyncio task flushes in-memory results to disk every hour
- [ ] **DATA-04**: Leader exposes `GET /data?window=30m` returning last 30 minutes of raw checks
- [ ] **DATA-05**: Leader exposes `GET /data?window=30d` returning daily aggregated uptime statistics
- [ ] **DATA-06**: Node status calculated at query time: OK, Pending, NotAvailable
- [ ] **DATA-07**: Data API includes CORS headers for cross-origin Streamlit access

### Dashboard

- [ ] **DASH-01**: Streamlit dashboard served alongside (or separately from) the Quart server
- [ ] **DASH-02**: Dashboard shows 30-minute connectivity matrix (last 30 checks)
- [ ] **DASH-03**: Dashboard shows 30-day daily aggregated uptime view
- [ ] **DASH-04**: Each node pair shows per-peer connectivity status
- [ ] **DASH-05**: Dashboard uses `@st.cache_data(ttl=60)` for data loading
- [ ] **DASH-06**: Dashboard uses `@st.fragment` for live auto-refresh sections

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Node Agent

- **NODE-11**: Node de-registration endpoint (`POST /deregister`)
- **NODE-12**: Cross-platform ping output parser (Linux, macOS, Windows)

### Dashboard

- **DASH-07**: MTR/traceroute path diagnostics on demand
- **DASH-08**: Alert webhooks (Slack, email)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Authentication / access control | VPN is trusted network for prototype |
| Database backend | JSON file storage sufficient for prototype scale |
| WebSocket real-time push | Frontend polls data endpoint |
| Encryption (in transit or at rest) | Prototype, VPN provides transport security |
| Docker deployment | Ship as Python package initially |
| Prometheus `/metrics` endpoint | Expose if demand arises in v2+ |
| Multi-leader HA | Deferred until leader becomes real SPOF concern |
| MTR/traceroute integration | v2 feature |
| Alert webhooks (Slack, email) | v2 feature |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| LEAD-01 | Phase 1 | Pending |
| LEAD-02 | Phase 1 | Pending |
| LEAD-03 | Phase 1 | Pending |
| LEAD-04 | Phase 1 | Pending |
| LEAD-05 | Phase 1 | Pending |
| LEAD-06 | Phase 1 | Pending |
| LEAD-07 | Phase 1 | Pending |
| REGI-01 | Phase 1 | Pending |
| REGI-02 | Phase 1 | Pending |
| REGI-03 | Phase 1 | Pending |
| REGI-04 | Phase 1 | Pending |
| NODE-01 | Phase 2 | Pending |
| NODE-02 | Phase 2 | Pending |
| NODE-03 | Phase 2 | Pending |
| NODE-04 | Phase 2 | Pending |
| NODE-05 | Phase 2 | Pending |
| NODE-06 | Phase 2 | Pending |
| NODE-07 | Phase 2 | Pending |
| NODE-08 | Phase 2 | Pending |
| NODE-09 | Phase 2 | Pending |
| NODE-10 | Phase 2 | Pending |
| DATA-01 | Phase 3 | Pending |
| DATA-02 | Phase 3 | Pending |
| DATA-03 | Phase 3 | Pending |
| DATA-04 | Phase 3 | Pending |
| DATA-05 | Phase 3 | Pending |
| DATA-06 | Phase 3 | Pending |
| DATA-07 | Phase 3 | Pending |
| DASH-01 | Phase 4 | Pending |
| DASH-02 | Phase 4 | Pending |
| DASH-03 | Phase 4 | Pending |
| DASH-04 | Phase 4 | Pending |
| DASH-05 | Phase 4 | Pending |
| DASH-06 | Phase 4 | Pending |

**Coverage:**
- v1 requirements: 34 total
- Mapped to phases: 34
- Unmapped: 0 ✓

---
*Requirements defined: 2026-06-17*
*Last updated: 2026-06-17 after initial definition*
