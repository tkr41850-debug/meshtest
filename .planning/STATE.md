# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-06-18)

**Core value:** A node must be able to detect and report whether it can reach every other node in the mesh, and the leader must present an accurate, up-to-date connectivity view.
**Current focus:** Defining requirements for v0.3 Dashboard Fixes

## Current Position

Milestone: v0.3 (Dashboard Fixes)
Current Phase: Not started (defining requirements)
Plan: —
Status: Defining requirements
Last activity: 2026-06-18 — Milestone v0.3 started

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
| 01 | 1 | ~20 min | 20 min |

**Recent Trend:** N/A

## Accumulated Context

### Decisions

Phase 1 decisions (Dockerfile leader+dashboard):
- UV installed via `curl -LsSf https://astral.sh/uv/install.sh | UV_INSTALL_DIR=/usr/local/bin sh` (auto-detects arch for multi-arch support)
- Both Hypercorn and Streamlit run as background processes with PID wait loop (not `exec`)
- Non-root user `meshstatus` (uid 1001) for runtime
- `/app/data` created at build time and owned by meshstatus
- HEALTHCHECK via `curl -f http://localhost:58080/livez`
- Entrypoint retries Hypercorn startup check up to 10 times (1s apart) via /livez endpoint
- Signal trap (TERM/INT) kills both processes; exit code propagated from process that died first
- `.dockerignore` extended with tests/, coverage, and build artifacts

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

Phase 4 (CI/CD) decisions:
- Matrix build strategy for parallel leader+node builds
- docker/metadata-action for tag generation (latest, semver, branch, PR)
- Fail-fast: false for matrix (one image can fail independently)
- Push only on non-PR events (PR builds without push for verification)
- Cache via `type=gha` with `mode=max` for maximum layer reuse
- QEMU + Buildx for multi-arch (linux/amd64, linux/arm64)

### Roadmap Evolution

- Phase **3.1** inserted after Phase **3** (URGENT) — Add mocked integration tests for Phase 1 and 2
- Phase **4.1** inserted after Phase **4** (URGENT) — Fix cross-phase integration gaps (node HTTP server, /healthz, 30m data retention)
- Phase **4** added to v0.2: GitHub Actions CI/CD — Build & Push to Docker Hub

### Pending Todos

- [ ] Define v0.3 requirements
- [ ] Create v0.3 roadmap

### Blockers/Concerns

None.

## Session Continuity

Last session: 2026-06-18
Stopped at: v0.2 complete — starting v0.3 Dashboard Fixes
Resume file: None
