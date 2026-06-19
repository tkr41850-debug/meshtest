# Requirements: mesh-status

**Defined:** 2026-06-18
**Core Value:** A node must be able to detect and report whether it can reach every other node in the mesh, and the leader must present an accurate, up-to-date connectivity view.

## v5 Requirements

### Frontend Scaffold & Build Pipeline

- [ ] **FRNT-01**: Vite + TypeScript + Tailwind CSS project initialized in `frontend/` with working dev server
- [ ] **FRNT-02**: Project includes Vitest for unit/component testing
- [ ] **FRNT-03**: TypeScript strict mode, ESLint, and Prettier configured
- [ ] **FRNT-04**: `npm run build` produces a static bundle in `frontend/dist/`

### Leader Static Serving

- [ ] **LEAD-01**: Leader (Quart) serves the built `./dist` folder on port 58080 at `/` and `/assets/*`
- [ ] **LEAD-02**: API routes (`/data`, `/node-list`, `/livez`, etc.) remain unchanged at 58080
- [ ] **LEAD-03**: Frontend uses relative API URLs (same-origin, no CORS needed)

### Build Pipeline

- [ ] **BUILD-01**: Dockerfile.leader uses multi-stage build: Node.js stage for `npm run build`, Python stage for runtime, copies `dist/` into the final image
- [ ] **BUILD-02**: `entrypoint.sh` removes Streamlit startup — leader starts Hypercorn only, serving both API and static files
- [ ] **BUILD-03**: `compose.yml` removes port 58581 (only 58080 exposed)
- [ ] **BUILD-04**: GitHub Actions workflow builds frontend alongside leader image

### Dashboard Views

- [ ] **DASH-01**: Dashboard shows the 30-minute connectivity matrix as an N×N HTML table with color-coded status dots (green=OK, amber=NotAvailable, gray=Pending)
- [ ] **DASH-02**: Dashboard shows per-node-pair detail cards with: status badge, ping latency, HTTP latency, last check timestamp, inline uptime % (per check type)
- [ ] **DASH-03**: Dashboard shows the 30-day daily aggregated uptime view with per-check-type percentages
- [ ] **DASH-04**: Dashboard auto-refreshes every 10s via browser `setInterval`
- [ ] **DASH-05**: Matrix column headers show short numeric labels with full hostname on hover (matching v0.4 behavior)
- [ ] **DASH-06**: Cards match the visual design from v0.4 (color-coded left border, status pill, monospace IP)

### Streamlit Removal

- [ ] **CLEAN-01**: `mesh_status/dashboard.py` deleted
- [ ] **CLEAN-02**: `streamlit` and `requests` (dashboard-only) removed from `pyproject.toml`
- [ ] **CLEAN-03**: Port 58581 removed from EXPOSE in Dockerfile.leader
- [ ] **CLEAN-04**: All existing 53 Python tests still pass (no backend regressions)

### Uptime History Visualization

- [ ] **DASH-07**: Dashboard shows an UptimeRobot-style history visualization per node pair
- [ ] **DASH-08**: Ping and HTTP uptime displayed as separate metrics
- [ ] **DASH-09**: Visualization shows uptime % trend over the 30-day window (bars, sparkline, or similar)

### Testing

- [ ] **TEST-01**: Vitest tests for frontend data fetching and rendering components
- [ ] **TEST-02**: Test coverage for connectivity matrix, detail cards, and 30-day view

## v2+ Requirements

Deferred to future release. Tracked but not in current roadmap.

(None yet)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Authentication / access control | VPN is trusted network for prototype |
| Real-time push/WebSocket | Polling at 10s is sufficient for prototype |
| Node agent changes | v0.5 is dashboard-only migration |
| Backend API changes (beyond static serving) | Existing API contract preserved |
| Mobile-responsive design | Web-first, desktop primary use case |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| FRNT-01 | 8 | Pending |
| FRNT-02 | 8 | Pending |
| FRNT-03 | 8 | Pending |
| FRNT-04 | 8 | Pending |
| LEAD-01 | 8 | Pending |
| LEAD-02 | 8 | Pending |
| LEAD-03 | 8 | Pending |
| BUILD-01 | 8 | Pending |
| BUILD-02 | 8 | Pending |
| BUILD-03 | 8 | Pending |
| BUILD-04 | 8 | Pending |
| DASH-01 | 9 | Pending |
| DASH-02 | 9 | Pending |
| DASH-03 | 9 | Pending |
| DASH-04 | 9 | Pending |
| DASH-05 | 9 | Pending |
| DASH-06 | 9 | Pending |
| CLEAN-01 | 10 | Pending |
| CLEAN-02 | 10 | Pending |
| CLEAN-03 | 10 | Pending |
| CLEAN-04 | 10 | Pending |
| DASH-07 | 11 | Pending |
| DASH-08 | 11 | Pending |
| DASH-09 | 11 | Pending |
| TEST-01 | 10 | Pending |
| TEST-02 | 10 | Pending |

**Coverage:**
- v5 requirements: 26 total
- Mapped to phases: 26
- Unmapped: 0 ✓

---
*Requirements defined: 2026-06-18*
*Last updated: 2026-06-18 after initial definition*
