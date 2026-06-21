# mesh-status — Project Guide

This file provides workflow-enforcement guidance and current project context.

## Project

**mesh-status** — A distributed mesh connectivity testing tool for monitoring network health across VMs connected via VPN WAN.

## Workflow Mode

- **Mode**: YOLO (auto-approve)
- **Granularity**: Coarse (3-5 phases)
- **Execution**: Sequential
- **Planning docs**: Committed to git

## Current State

- Phase: 1 of 4 (Leader Core & Registration)
- Status: Ready to plan
- 34 v1 requirements mapped across 4 phases

## Commands

- `/gsd-discuss-phase 1` — discuss Phase 1 before planning
- `/gsd-plan-phase 1` — plan Phase 1 directly
- `/gsd-progress` — check project progress
- `/gsd-settings` — update workflow preferences

## Before pushing — run heavy checks

Run `make ci` before every push to catch CI failures locally. This runs:

```
make ci           # full pipeline: lint → format-check → test-backend → test-frontend → build
```

Individual targets are also available:

```
make lint              # ruff check (Python lint)
make format            # ruff format (auto-fix)
make format-check      # ruff format --check
make test-backend      # pytest
make test-frontend     # vitest
make test              # both test-backend + test-frontend
make build             # frontend tsc + vite build
make typecheck-frontend  # tsc --noEmit
```

## Artifacts

| File | Description |
|------|-------------|
| `.planning/PROJECT.md` | Project context and goals |
| `.planning/config.json` | Workflow preferences |
| `.planning/REQUIREMENTS.md` | v1 requirements with traceability |
| `.planning/ROADMAP.md` | Phase structure and success criteria |
| `.planning/STATE.md` | Project memory and progress |
| `.planning/research/SUMMARY.md` | Research synthesis |
