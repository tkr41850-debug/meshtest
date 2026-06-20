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

- [x] Phase 15: Bar foundation + type fixes (TDD)
- [x] Phase 16: UI integration — flat 30d, dual rows, gap (TDD)

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
