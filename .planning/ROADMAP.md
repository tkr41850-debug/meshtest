# Roadmap: mesh-status

## Overview

A distributed mesh connectivity testing tool for monitoring network health across VMs connected via VPN WAN.

## Milestones

- ✅ **v0.1** — mesh-status initial release (5 phases)
- ✅ **v0.2** — Containerize mesh-status (4 phases)
- ✅ **v0.3** — Dashboard Fixes (2 phases)
- ✅ **v0.4** — Dashboard UI Polish (2 phases)
- 🚧 **v0.5** — Frontend Migration (4 phases)

## Phases

<details>
<summary>✅ v0.1 — mesh-status initial release (Phases 1-4, 3.1, 4.1)</summary>

- [x] Phase 1: Leader Core & Registration
- [x] Phase 2: Node Agent
- [x] Phase 3: Persistence & Data API
- [x] Phase 3.1: Integration Tests (inserted)
- [x] Phase 4: Streamlit Dashboard
- [x] Phase 4.1: Cross-phase Integration Fix (inserted)

See archived roadmap: `.planning/milestones/v0.1-ROADMAP.md`
</details>

<details>
<summary>✅ v0.2 — Containerize mesh-status</summary>

- [x] Phase 5: Dockerfile leader+dashboard
- [x] Phase 6: Dockerfile node agent
- [x] Phase 7: Docker Compose + Deployment Docs
- [x] Phase 8: GitHub Actions CI/CD

See archived roadmap: `.planning/milestones/v0.2-ROADMAP.md`
</details>

<details>
<summary>✅ v0.3 — Dashboard Fixes</summary>

- [x] Phase 5: Backend — Data Latency Grace Period
- [x] Phase 6: Frontend — Dashboard Bug Fix + UptimeRobot-style Details

See archived roadmap: `.planning/milestones/v0.3-phases/`
</details>

<details>
<summary>✅ v0.4 — Dashboard UI Polish (SHIPPED 2026-06-18)</summary>

- [x] Phase 7a: Display & Refresh Tuning
- [x] Phase 7b: HTML Rendering Fix

See archived roadmap: `.planning/milestones/v0.4-ROADMAP.md`
</details>

### 🚧 v0.5 — Frontend Migration (In Progress)

- [ ] Phase 8: Frontend Scaffold + Build Pipeline
- [ ] Phase 9: Dashboard Views
- [ ] Phase 10: Streamlit Cleanup
- [ ] Phase 11: Uptime History Visualization

### Phase 8: Frontend Scaffold + Build Pipeline

**Goal:** Initialize Vite + TS + Tailwind project and integrate with Docker build pipeline

**Requirements:** FRNT-01, FRNT-02, FRNT-03, FRNT-04, LEAD-01, LEAD-02, LEAD-03, BUILD-01, BUILD-02, BUILD-03, BUILD-04

**Success criteria:**
- [ ] `npm run dev` in `frontend/` starts a working Vite dev server with TS + Tailwind
- [ ] `vitest run` executes without errors (stub test)
- [ ] Docker build runs `npm run build` and serves `dist/` from Quart
- [ ] `entrypoint.sh` starts only Hypercorn (no Streamlit)
- [ ] GHA workflow builds frontend

### Phase 9: Dashboard Views

**Goal:** Port all three Streamlit views to the Vite frontend

**Requirements:** DASH-01, DASH-02, DASH-03, DASH-04, DASH-05, DASH-06

**Success criteria:**
- [ ] Connectivity matrix renders with correct status dots and short labels with hover
- [ ] Node-pair expanders show detail cards with badge, latencies, inline uptime %
- [ ] 30-day view shows daily aggregated uptime per pair
- [ ] Auto-refresh every 10s via `setInterval`
- [ ] Visual design matches v0.4 (color scheme, layout)

### Phase 10: Streamlit Cleanup

**Goal:** Remove Streamlit from the codebase and add frontend tests

**Requirements:** CLEAN-01, CLEAN-02, CLEAN-03, CLEAN-04, TEST-01, TEST-02

**Success criteria:**
- [ ] `dashboard.py` deleted
- [ ] `streamlit` and `requests` removed from dependencies
- [ ] Port 58581 removed from EXPOSE
- [ ] All 53 Python tests still pass
- [ ] Vitest tests for matrix, cards, 30-day view

### Phase 11: Uptime History Visualization

**Goal:** Add UptimeRobot-style history visualization per node pair

**Requirements:** DASH-07, DASH-08, DASH-09

**Success criteria:**
- [ ] Each node pair shows uptime % history over the 30-day window
- [ ] Ping and HTTP displayed as separate metrics
- [ ] Visualization is meaningful and readable at a glance

## Progress

| Phase | Milestone | Status | Completed |
|-------|-----------|--------|-----------|
| 1 | v0.1 | Complete | 2026-06-18 |
| 2 | v0.1 | Complete | 2026-06-18 |
| 3 | v0.1 | Complete | 2026-06-18 |
| 3.1 | v0.1 | Complete | 2026-06-18 |
| 4 | v0.1 | Complete | 2026-06-18 |
| 4.1 | v0.1 | Complete | 2026-06-18 |
| 5 | v0.2/v0.3 | Complete | 2026-06-18 |
| 6 | v0.2/v0.3 | Complete | 2026-06-18 |
| 7 | v0.2 | Complete | 2026-06-18 |
| 8 | v0.2 | Complete | 2026-06-18 |
| 7a | v0.4 | Complete | 2026-06-18 |
| 7b | v0.4 | Complete | 2026-06-18 |
| 8 | v0.5 | Not started | — |
| 9 | v0.5 | Not started | — |
| 10 | v0.5 | Not started | — |
| 11 | v0.5 | Not started | — |
