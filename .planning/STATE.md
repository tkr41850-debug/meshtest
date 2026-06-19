# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-06-17)

**Core value:** A node must be able to detect and report whether it can reach every other node in the mesh, and the leader must present an accurate, up-to-date connectivity view.
**Current focus:** v0.2 — Dockerfile builds for leader+dashboard and node containers

## Current Position

Milestone: v0.2 (Containerize mesh-status)
Phase: None yet — milestone just initiated
Status: Ready to plan Phase 1
Last activity: 2026-06-18 — v0.1 complete and tagged (v0.1)

Progress: [░░░░░░░░░░] 0%

## Performance Metrics

**Velocity:**
- v0.1 total plans completed: 5
- v0.1 average duration: ~14 min
- v0.1 total execution time: ~70 min

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 03.1 | 2 | 45 min | 22 min |
| 4.1 | 1 | 5 min | 5 min |

**Recent Trend:** N/A

## Accumulated Context

### Decisions

Phase 4.1 decisions:
- aiohttp for node HTTP server (pure async, no threading)
- Shared state dict pattern for cross-coroutine config updates
- http_runner.cleanup() wrapped in try/except for test compatibility

Phase 4 decisions:
- Dashboard served standalone via `streamlit run` (port 58581), LEADER_URL env var
- Single `@st.fragment` wrapping both tabs with 30s sleep + `st.rerun(scope="fragment")`
- Three `@st.cache_data(ttl=30)` functions for 30m, 30d, and node-list
- Connectivity matrix as N×N HTML table with colored circles (green/amber/gray)
- Status combination: both OK→green, either NotAvailable→amber, else gray
- 30-Day uptime badges: >=99% green, >=95% amber, <95% red

Phase 3 decisions:
- JSON Lines append-only writes, hourly flush, non-blocking flush_loop started at leader boot
- Status calculated at query time per check type (ping_status, http_status)
- Per-check-type OK threshold: 3× check interval
- 30m response: raw checks + per-pair statuses; 30d response: daily aggregated per-pair uptime
- After hourly flush: keep last 10 min of in-memory results for 30m queries

### Roadmap Evolution

- Phase **3.1** inserted after Phase **3** (URGENT) — Add mocked integration tests for Phase 1 and 2
- Phase **4.1** inserted after Phase **4** (URGENT) — Fix cross-phase integration gaps (node HTTP server, /healthz, 30m data retention)

### Pending Todos

- [ ] Milestone v0.2: Define phases and requirements
- [ ] Phase 1: Dockerfile for leader+dashboard container
- [ ] Phase 2: Dockerfile for node agent container
- [ ] Phase 3: docker-compose.yml + docs

### Blockers/Concerns

None.

## Session Continuity

Last session: 2026-06-18
Stopped at: v0.2 milestone initiated — Dockerfile builds for leader+dashboard and node containers
Resume file: None
