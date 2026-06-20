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

### 🔄 v0.8 — Non-Docker Install & Start Scripts

- [ ] **Phase 18: Install Script Core** — `deploy/install.sh` with prereq checks, git clone, uv sync, frontend build, config bootstrap, and idempotent reinstall
- [ ] **Phase 19: Start Script & Config Integration** — `start.sh --leader/--node`, signal handling, PID management, log redirection, config wizard, and persistence.py DATA_DIR fix
- [ ] **Phase 20: Docker CI Testing** — CI pipeline tests full install flow in fresh container, non-interactive mode, and start.sh health check

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
| 18 | v0.8 | Not started | — |
| 19 | v0.8 | Not started | — |
| 20 | v0.8 | Not started | — |

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

### Phase 19: Start Script & Config Integration
**Goal**: Users can start the leader or node agent with proper process management, and data files respect the configured directory
**Depends on**: Phase 18
**Requirements**: START-01, START-02, START-03, START-04, START-05, START-06, START-07, START-08, CONF-02, CONF-04, FIX-05
**Success Criteria** (what must be TRUE):
1. User runs `start.sh --leader` and the leader starts on port 58080 with logs written to `$INSTALL_DIR/var/leader.log` and PID tracked
2. User runs `start.sh --node` and the node agent starts with logs written to `$INSTALL_DIR/var/node.log` and PID tracked
3. Sending SIGTERM/SIGINT to the process gracefully shuts it down (no orphaned processes, port 58080 released)
4. User can run `start.sh --help` and `start.sh --version` for discoverability
5. User can configure mesh-status via an interactive wizard on first run, or via CLI flags in non-interactive mode
6. Data files are written to the directory specified by `DATA_DIR` env var (FIX-05), not hardcoded `Path("data")`
7. User runs `start.sh --uninstall` and the install directory is removed with PATH cleanup instructions printed
**Plans**: TBD

### Phase 20: Docker CI Testing
**Goal**: Install and start scripts are validated automatically in CI via Docker-based integration tests
**Depends on**: Phase 18, Phase 19
**Requirements**: TEST-01, TEST-02, TEST-03
**Success Criteria** (what must be TRUE):
1. CI builds a fresh container from a minimal base image, runs `install.sh -y`, and the install completes successfully
2. CI runs `install.sh -y` with env var overrides and verifies non-interactive mode works without stdin
3. CI validates `start.sh --leader` launches and the process is healthy
**Plans**: TBD
