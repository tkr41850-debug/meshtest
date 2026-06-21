# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-06-19)

**Core value:** A node must be able to detect and report whether it can reach every other node in the mesh, and the leader must present an accurate, up-to-date connectivity view.
**Current focus:** Planning next milestone

## Current Position

Milestone: v0.10 (Custom Hover Tooltips)
Phase: 24
Plan: Complete
Status: Shipped 2026-06-21
Last activity: 2026-06-21 — v0.10 shipped (all 6 UXTIP requirements satisfied)

## Performance Metrics

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

### Decisions (v0.6)

- 30d endpoint merges in-memory `_results` with disk data for correct daily aggregation
- Flush now stores `node_ip` in each check dict to fix node_ip grouping in disk data
- Cards use flat layout with `data-source-group` divs and sticky headers (replaces `<details>`)
- History bars are 8px wide, 20px tall, with diagonal gradient split color for Ping/HTTP
- 30m history bars aggregated by minute from raw `CheckResult[]` data
- 30d history bars computed from daily `DayData[]` with padding for missing days
- Old separate History tab removed; bars shown inline in both card and day30 views
- Scroll-to from 30-day split circles targets cards tab (30m) with sticky header navigation
- Frontend tests use `data-history-bar` attribute for bar selection

### Decisions (v0.7)

- Separate bar rows for ICMP and HTTP (two rows per card/pair) instead of single gradient bar
- Bar color uses HSB interpolation: `hsl(hue, 85%, 40%)` where `hue = percent * 120` (0° red at 0% → 120° green at 100%)
- Shared `bars.ts` utility with `renderBars(bars: {percent: number, tooltip: string}[])` used by both views
- 30-day view always expanded (flat layout, no `<details>`)
- Backend infers `node_ip` by matching against `_results` keys for disk records with empty `node_ip`
- All changes TDD: write Vitest tests first, then implementation

### Roadmap Evolution

- Phase **17** added: Fix history bars showing only most recent check (TDD)
- Phase **3.1** inserted after Phase **3** (URGENT) — Add mocked integration tests for Phase 1 and 2
- Phase **4.1** inserted after Phase **4** (URGENT) — Fix cross-phase integration gaps (node HTTP server, /healthz, 30m data retention)
- Phase **4** added to v0.2: GitHub Actions CI/CD — Build & Push to Docker Hub
- v0.4 replaces original v3.5+ deferred items with dashboard UI polish

### Milestone v0.7 Status

- [x] Phase 15: Bar foundation + type fixes (TDD) — Complete
- [x] Phase 16: UI integration — flat 30d, dual rows, gap (TDD) — Complete
- [x] Phase 17: Fix history bars showing only most recent check (TDD) — Complete

### Milestone v0.8 Status

- [x] Phase 18: Install Script Core — Complete
- [x] Phase 19: Start Script & Config Integration — Complete
- [x] Phase 20: Docker CI Testing — Complete

### Milestone v0.9 Status

- [x] Phase 21: Color Consistency — Complete
- [x] Phase 22: 90m/90h/90d Window Expansion — Complete
- [x] Phase 23: Unified Cards Layout — Complete

### Decisions (v0.9)

- **Phase numbering**: v0.9 starts at Phase 21 (continuing from v0.8's Phase 20)
- **Color scheme**: HSL gradient with <90%→red (0°), 90-99%→amber ramp (45°→120°), ≥99.9%→green (120°). Same scheme for bars AND numbers.
- **Window structure**: 90m (90 × 1-min bars), 90h (90 × 1-hour bars), 90d (90 × 1-day bars) — replacing 30m/30d
- **Layout**: Cards layout with split circle + total check count used consistently across all three windows
- **Shared color function**: Extract to `views/colors.ts` — single source of truth
- **Backend**: Extend in-memory retention to 5400s; add `/data?window=90h` endpoint
- **All changes TDD**: Write Vitest tests first, then implementation

### Decisions (v0.8 — roadmap creation)

- **Phase numbering**: v0.8 starts at Phase 18 (continuing from v0.7's Phase 17)
- **Granularity**: Coarse — 3 phases for 25 requirements (INST, START, CONF, TEST, FIX)
- **Install directory**: `~/.local/meshtest` per INST-01 (not `~/.local/opt/mesh-status` from research)
- **install.sh must work without stdin**: No interactive prompts in pipe mode; config wizard uses env var fallback and `/dev/tty` for prompts
- **Start script pattern**: `exec`/foreground by default (not daemonize), PID file for tracking, signal traps for cleanup
- **persistence.py fix**: Must read `DATA_DIR` env var with `Path(os.environ.get("DATA_DIR", "data"))` fallback — preserves backward compat with Docker
- **Test framework**: bats-core for shell script testing
- **Script shebangs**: `deploy/install.sh` uses `#!/bin/sh` (POSIX), `start.sh` uses `#!/usr/bin/env bash`
- **Config approach**: Env vars only (no TOML/YAML), consistent with existing `config.py` pattern; `.env` file generated during install

### Decisions (v0.10 — roadmap creation)

- **CSS-only tooltips**: No JS event listeners or mouse-tracking — uses `:hover` on parent container + positioned div
- **Group-based hover for bars**: One tooltip per bar row (ICMP/HTTP), not 90 individual tooltips
- **Tooltip content**: Protocol label (ICMP/HTTP) — simple, always available, no extra data passing needed
- **Tooltip classes in `style.css`**: Dark background, white text, small font, rounded corners with arrow indicator
- **Arrow indicator**: CSS border trick via `::after` pseudo-element
- **Matrix view covered**: Column header `title` attributes replaced with same CSS tooltip pattern
- **Phase numbering**: v0.10 starts at Phase 24 (continuing from v0.9's Phase 23)
- **All changes TDD**: Write Vitest tests first, then implementation

### Blockers/Concerns

None.

## Session Continuity

Last session: 2026-06-21
Stopped at: v0.10 requirements defined, Phase 24 planned
Resume file: None
Next action: Execute Phase 24 — Custom Hover Tooltips
