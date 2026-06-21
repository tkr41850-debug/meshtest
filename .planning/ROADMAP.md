# Roadmap: mesh-status

## Overview

A distributed mesh connectivity testing tool for monitoring network health across VMs connected via VPN WAN.

## Milestones

- ✅ **v0.1** — mesh-status initial release (5 phases)
- ✅ **v0.2** — Containerize mesh-status (4 phases)
- ✅ **v0.3** — Dashboard Fixes (2 phases)
- ✅ **v0.4** — Dashboard UI Polish (2 phases)
- ✅ **v0.5** — Frontend Migration (4 phases)

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

### ✅ v0.5 — Frontend Migration

Completed 2026-06-19. See `.planning/milestones/v0.5-ROADMAP.md` for full details.

### ✅ v0.6 — Dashboard UX Improvements

- [x] Phase 12: Fix 30d endpoint to include in-memory data (Python TDD)
- [x] Phase 13: Flat card layout + uptime % (frontend TDD)
- [x] Phase 14: History bars in both tabs + remove old History tab (frontend TDD)

### ✅ v0.7 — Dashboard Bugfixes

- [x] Phase 15: Bar foundation + type fixes (TDD) — completed 2026-06-19
- [x] Phase 16: UI integration — flat 30d, dual rows, gap (TDD) — completed 2026-06-19
- [x] Phase 17: Fix history bars showing only most recent check (TDD) — completed 2026-06-20

### ✅ v0.8 — Non-Docker Install & Start Scripts

Completed 2026-06-20.
- [x] **Phase 18: Install Script Core** — `deploy/install.sh` with prereq checks, git clone, uv sync, frontend build, config bootstrap, and idempotent reinstall
- [x] **Phase 19: Start Script & Config Integration** — `start.sh --leader/--node`, signal handling, PID management, log redirection, config wizard, and persistence.py DATA_DIR fix
- [x] **Phase 20: Docker CI Testing** — CI pipeline tests full install flow in fresh container, non-interactive mode, and start.sh health check

### 🔄 v0.9 — UI Consolidation: History Bars, Color & Windows

- [ ] **Phase 21: Color Consistency (COLOR)** — Extract shared `uptimeColor()` to `views/colors.ts`, apply HSL gradient thresholds to bars and numbers, remove duplicated color logic
- [ ] **Phase 22: 90m/90h/90d Window Expansion (WINDOW)** — Backend extends retention to 5400s, adds `/data?window=90h` endpoint; frontend increases all bars to 90, adds third tab for 90h
- [ ] **Phase 23: Unified Cards Layout (UNIFY)** — Extract shared card template to `views/card.ts`, refactor all three views to use consistent card layout with split circle + total check count

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
| 8 | v0.5 | Complete | 2026-06-19 |
| 9 | v0.5 | Complete | 2026-06-19 |
| 10 | v0.5 | Complete | 2026-06-19 |
| 11 | v0.5 | Complete | 2026-06-19 |
| 12 | v0.6 | Complete | 2026-06-19 |
| 13 | v0.6 | Complete | 2026-06-19 |
| 14 | v0.6 | Complete | 2026-06-19 |
| 15 | v0.7 | Complete | 2026-06-19 |
| 16 | v0.7 | Complete | 2026-06-19 |
| 17 | v0.7 | Complete | 2026-06-20 |
| 18 | v0.8 | Complete | 2026-06-20 |
| 19 | v0.8 | Complete | 2026-06-20 |
| 20 | v0.8 | Complete | 2026-06-20 |
| 21 | v0.9 | Not started | — |
| 22 | v0.9 | Not started | — |
| 23 | v0.9 | Not started | — |

## v0.8 Phase Details

### Phase 18: Install Script Core
**Goal**: Users can install mesh-status on bare-metal VMs with a single curl-pipe-bash command
**Depends on**: Nothing
**Requirements**: INST-01, INST-02, INST-03, INST-04, INST-05, INST-06, INST-07, INST-08, INST-09, CONF-01, CONF-03
**Success Criteria** (what must be TRUE):
1. User can run `deploy/install.sh` and mesh-status is installed to `~/.local/meshtest` without sudo
2. User sees actionable error messages if `uv` or `git` are missing, before any filesystem changes
3. User can run `install.sh -y` or `install.sh --yes` to skip all prompts in non-interactive/CI mode
4. User can run `install.sh --help` to see usage info with all flags and env vars
5. User can pin a specific version via `MESH_STATUS_VERSION` env var for reproducible installs
6. Running install.sh a second time updates the existing install via `git pull` without errors (idempotent)
7. User sees a success banner with install path, start commands, and dashboard URL on completion
**Plans**: TBD

### Phase 19: Start Script & Config Integration (COMPLETE)
**Goal**: Users can start the leader or node agent with proper process management, and data files respect the configured directory
**Depends on**: Phase 18
**Requirements**: START-01, START-02, START-03, START-04, START-05, START-06, START-07, START-08, CONF-02, CONF-04, FIX-05
**Success Criteria** (what must be TRUE):
1. ✅ User runs `start.sh --leader` and the leader starts on port 58080 with logs written to `$INSTALL_DIR/var/leader.log` and PID tracked
2. ✅ User runs `start.sh --node` and the node agent starts with logs written to `$INSTALL_DIR/var/node.log` and PID tracked
3. ✅ Sending SIGTERM/SIGINT to the process gracefully shuts it down (no orphaned processes, port 58080 released)
4. ✅ User can run `start.sh --help` and `start.sh --version` for discoverability
5. ✅ User can configure mesh-status via an interactive wizard on first run, or via CLI flags in non-interactive mode
6. ✅ Data files are written to the directory specified by `DATA_DIR` env var (FIX-05), not hardcoded `Path("data")`
7. ✅ User runs `start.sh --uninstall` and the install directory is removed with PATH cleanup instructions printed

### Phase 20: Docker CI Testing (COMPLETE)
**Goal**: Install and start scripts are validated automatically in CI via Docker-based integration tests
**Depends on**: Phase 18, Phase 19
**Requirements**: TEST-01, TEST-02, TEST-03
**Success Criteria** (what must be TRUE):
1. ✅ CI builds a fresh container from a minimal base image, runs `install.sh -y`, and the install completes successfully
2. ✅ CI runs `install.sh -y` with env var overrides and verifies non-interactive mode works without stdin
3. ✅ CI validates `start.sh --leader` launches and the process is healthy

---

## v0.9 — UI Consolidation: History Bars, Color & Windows

### Phase 21: Color Consistency (COLOR)
**Goal**: Bar and number colors are consistent across all views using a shared HSL gradient color function
**Depends on**: Nothing (pure frontend refactor — no backend changes needed)
**Requirements**: COLOR-01, COLOR-02, COLOR-03, COLOR-04
**Success Criteria** (what must be TRUE):
1. Bars and percentage numbers use matching colors at boundary values (0%, 50%, 89.9%, 90%, 95%, 99%, 99.9%, 100%) — no mismatch between bar fill and number text coloring
2. Colors follow HSL thresholds: <90% → red (~0°), 90-99% → amber ramp (45°→120°), ≥99.9% → green (120°) — applied to both bars AND percentage numbers
3. All views (30m, 90d, 90h) call the shared `uptimeColor()` from `views/colors.ts` — zero duplicate color logic in individual view files
4. Removing `COLOR-01`/`COLOR-03` refactored code does not change any existing UI appearance — visual regression is zero
**Plans**: TBD
**UI hint**: yes

### Phase 22: 90m/90h/90d Window Expansion (WINDOW)
**Goal**: All three time windows display 90 bars each; backend supports 90-minute retention and a new 90-hour endpoint
**Depends on**: Nothing (backend + frontend; independent of Phase 21 color refactor)
**Requirements**: WINDOW-01, WINDOW-02, WINDOW-03, WINDOW-04, WINDOW-05, WINDOW-06
**Success Criteria** (what must be TRUE):
1. Backend retains in-memory check results for 5400 seconds (90 minutes) — user can see all 90 one-minute bars in the 90m view
2. Backend serves `/data?window=90h` returning hourly aggregated data — user can fetch a 90-hour window of hourly summaries
3. All three time windows (90m, 90h, 90d) display exactly 90 bars each (increased from 30) with correct time-axis labeling
4. Frontend has a third tab for 90h view alongside 90m and 90d tabs, with `fetchData90h()` in the API layer and matching `HourData` types
**Plans**: TBD
**UI hint**: yes

### Phase 23: Unified Cards Layout (UNIFY)
**Goal**: All three time windows use a consistent card layout with split circle + total check count, sharing a single card template
**Depends on**: Phase 22 (90h view must exist before card refactor), Phase 21 (shared colors used in new cards)
**Requirements**: UNIFY-01, UNIFY-02, UNIFY-03, UNIFY-04
**Success Criteria** (what must be TRUE):
1. 30m cards show a split circle (ICMP/HTTP status) + total check count on each card — users can see both per-protocol status and aggregate check count at a glance
2. 90d view renders each node pair as a single card (not per-day rows), reusing the shared card template — visual density matches 30m view
3. 90h view renders cards using the same shared `views/card.ts` template — all three windows produce visually consistent cards
4. All three views import from `views/card.ts` — zero duplicated card rendering logic across `cards.ts`, `day30.ts`, and `hourly.ts`
**Plans**: TBD
**UI hint**: yes
