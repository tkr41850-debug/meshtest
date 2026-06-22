# Roadmap: mesh-status

## Overview

A distributed mesh connectivity testing tool for monitoring network health across VMs connected via VPN WAN.

## Milestones

- ✅ **v0.1** — mesh-status initial release (5 phases)
- ✅ **v0.2** — Containerize mesh-status (4 phases)
- ✅ **v0.3** — Dashboard Fixes (2 phases)
- ✅ **v0.4** — Dashboard UI Polish (2 phases)
- ✅ **v0.5** — Frontend Migration (4 phases)
- ✅ **v0.6** — Dashboard UX Improvements (3 phases)
- ✅ **v0.7** — Dashboard Bugfixes (3 phases)
- ✅ **v0.8** — Non-Docker Install & Start Scripts (3 phases)
- ✅ **v0.9** — UI Consolidation: History Bars, Color & Windows (3 phases)
- ✅ **v0.10** — Custom Hover Tooltips (Phase 24, Phase 25)
- ✅ **v0.10.1** — Code Review Cleanup (Phases 26-30) — SHIPPED 2026-06-22

## Phases

<details>
<summary>✅ v0.10.1 Code Review Cleanup (Phases 26-30) — SHIPPED 2026-06-22</summary>

- [x] Phase 26: Persistence & Leader Core — Fix data integrity, leader API robustness, dead code removal
- [x] Phase 27: Node Agent — Fix buffer retry, subprocess/HTTP error handling in node agent
- [x] Phase 28: Shell Scripts — Harden install.sh and start.sh with proper validation, quoting, and path handling
- [x] Phase 29: Config, Frontend & Test Infra — Harden CI/Docker config, add Degraded status, fix test infrastructure, validate register CLI
- [x] Phase 30: Setup Integration Tests (spec) — HTTP-only integration tests against local mesh-leader, optional restart-to-test-persistence command

</details>

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|---------------|--------|-----------|
| 26 — Persistence & Leader Core | v0.10.1 | — | ✅ Complete | 2026-06-21 |
| 27 — Node Agent | v0.10.1 | — | ✅ Complete | 2026-06-22 |
| 28 — Shell Scripts | v0.10.1 | — | ✅ Complete | 2026-06-22 |
| 29 — Config, Frontend & Test Infra | v0.10.1 | — | ✅ Complete | 2026-06-22 |
| 30 — Setup Integration Tests (spec) | v0.10.1 | — | ✅ Complete | 2026-06-22 |

See `.planning/milestones/v0.10.1-ROADMAP.md` for full phase details.
