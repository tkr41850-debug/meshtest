# Requirements: mesh-status

**Defined:** 2026-06-20
**Core Value:** A node must be able to detect and report whether it can reach every other node in the mesh, and the leader must present an accurate, up-to-date connectivity view.

## v0.8 Requirements

### Install Script (INST)

- [x] **INST-01**: `deploy/install.sh` installs mesh-status to `~/.local/meshtest`
- [x] **INST-02**: Prerequisite checks for `uv` and `git` with actionable messages
- [x] **INST-03**: Version-pinned git clone via `MESH_STATUS_VERSION` env var
- [x] **INST-04**: `uv sync` installs Python dependencies
- [x] **INST-05**: Frontend build during install (npm ci + npm run build)
- [x] **INST-06**: Idempotent reinstall — git pull in existing clone on re-run
- [x] **INST-07**: Success banner with install path, start commands, dashboard URL
- [x] **INST-08**: `-y` / `--yes` flag for non-interactive mode
- [x] **INST-09**: `--help` flag for install.sh

### Start Script (START)

- [x] **START-01**: `start.sh --leader` starts the leader via `uv run`
- [x] **START-02**: `start.sh --node` starts the node agent
- [x] **START-03**: Log output redirected to `$INSTALL_DIR/var/*.log`
- [x] **START-04**: PID file management for process tracking
- [x] **START-05**: Signal handling (SIGTERM/SIGINT traps for graceful shutdown)
- [x] **START-06**: `start.sh --help` flag
- [x] **START-07**: `start.sh --version` flag
- [x] **START-08**: `start.sh --uninstall` removes install and prints PATH cleanup

### Config & Setup (CONF)

- [x] **CONF-01**: `.env` config file generation with defaults during install
- [x] **CONF-02**: Interactive config wizard for first-run setup
- [x] **CONF-03**: `MESH_STATUS_HOME` env var to override install directory
- [x] **CONF-04**: CLI flag override for non-interactive config

### Docker CI Test (TEST)

- [x] **TEST-01**: Docker-based CI test verifies full install flow in fresh container
- [x] **TEST-02**: CI test runs `install.sh -y` with env vars for non-interactive mode
- [x] **TEST-03**: CI test verifies `start.sh` launches and process is healthy

### Infrastructure Fix (FIX)

- [x] **FIX-05**: Fix `persistence.py` to respect `DATA_DIR` env var instead of hardcoded `Path("data")`

## v0.9 Requirements

### COLOR — Consistent Color Scheme

- [x] **COLOR-01**: Extract shared `uptimeColor()` function from `cards.ts`/`day30.ts` into `views/colors.ts` — single source of truth
- [x] **COLOR-02**: Update `bars.ts` `barColor()` to use HSL gradient with <90%→red, 90–99%→amber ramp, ≥99.9%→green — same scheme applied to bars AND percentage numbers
- [x] **COLOR-03**: Remove duplicated `uptimeColor()` and `BADGE_MAP` color logic from individual view files — all views use `colors.ts`
- [x] **COLOR-04**: Test color consistency — bars and numbers use matching colors at boundary values (0%, 50%, 89.9%, 90%, 95%, 99%, 99.9%, 100%)

### WINDOW — 90m/90h/90d Windows

- [x] **WINDOW-01**: Backend extends in-memory retention from 1800s to 5400s in `persistence.py` to support 90-minute window
- [x] **WINDOW-02**: Backend adds `/data?window=90h` endpoint with hourly aggregation (reuses 30d aggregation pattern, groups by hour instead of day)
- [x] **WINDOW-03**: Frontend increases bar count from 30 to 90 in all time-window views
- [x] **WINDOW-04**: `api.ts` adds `fetchData90h()`, renames existing fetch functions to reflect new window sizes
- [x] **WINDOW-05**: `types.ts` adds 90h response/entry types (HourData with same shape as DayData)
- [x] **WINDOW-06**: `main.ts` wires up third tab for 90h view alongside 90m and 90d tabs

### UNIFY — Unified Cards Layout

- [x] **UNIFY-01**: Extract shared card template from `cards.ts` into `views/card.ts` — reusable across all three time windows
- [x] **UNIFY-02**: Refactor 30m `cards.ts` to include split circle + total check count on each card (adds missing info to existing card layout)
- [x] **UNIFY-03**: Refactor 90d `day30.ts` to render each pair as a card (not per-day rows), reusing the shared card template with same density as 30m view
- [x] **UNIFY-04**: Create `views/hourly.ts` for 90h view using the shared card template

## v0.10 Requirements

### UXTIP — Custom Hover Tooltips

- [x] **UXTIP-01**: Remove native `title` attributes from bar `<span>` elements in `renderBars()` — tooltips handled at container level in card template, not per-bar
- [x] **UXTIP-02**: Add CSS-only tooltip containers around bar rows in `card.ts` — hovering over a bar row (ICMP or HTTP) shows a styled tooltip with protocol label, avoiding 90 individual overlapping tooltips
- [x] **UXTIP-03**: Tooltip CSS classes defined in `style.css` — positioned absolutely above the bar row with dark bg, white text, small font, rounded corners, and arrow indicator
- [x] **UXTIP-04**: Matrix view column headers (`matrix.ts`) use the same CSS tooltip pattern — replace native `title` attribute with custom tooltip div for consistency
- [x] **UXTIP-05**: Update all test assertions — tests that check `getAttribute("title")` now check tooltip div content or container-level attributes instead
- [x] **UXTIP-06**: No visual regression — tooltips are only visible on hover, don't affect layout dimensions, and all other UI elements remain unchanged

## v2 Requirements

None deferred.

## Out of Scope

| Feature | Reason |
|---------|--------|
| Systemd service units | Deferred to v0.8.x or v0.9 — install.sh + start.sh are sufficient for v0.8 |
| Package manager support (apt/brew) | Distribution-specific packaging deferred — curl-pipe-bash is the primary path |
| Auto-update mechanism | Requires background process coordination — future milestone |
| Windows/Git Bash support | Python ecosystem on Windows is a separate concern |
| Mutual TLS between nodes | Config stubs deferred — no auth in prototype |
| Pre-built frontend artifact | Requires release CI workflow — build from source in v0.8 |
| Performance safeguards for 50+ nodes | Beyond current deployment scale — CSS containment deferred |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| INST-01 | Phase 18 | Complete |
| INST-02 | Phase 18 | Complete |
| INST-03 | Phase 18 | Complete |
| INST-04 | Phase 18 | Complete |
| INST-05 | Phase 18 | Complete |
| INST-06 | Phase 18 | Complete |
| INST-07 | Phase 18 | Complete |
| INST-08 | Phase 18 | Complete |
| INST-09 | Phase 18 | Complete |
| START-01 | Phase 19 | Complete |
| START-02 | Phase 19 | Complete |
| START-03 | Phase 19 | Complete |
| START-04 | Phase 19 | Complete |
| START-05 | Phase 19 | Complete |
| START-06 | Phase 19 | Complete |
| START-07 | Phase 19 | Complete |
| START-08 | Phase 19 | Complete |
| CONF-01 | Phase 18 | Complete |
| CONF-02 | Phase 19 | Complete |
| CONF-03 | Phase 18 | Complete |
| CONF-04 | Phase 19 | Complete |
| TEST-01 | Phase 20 | Complete |
| TEST-02 | Phase 20 | Complete |
| TEST-03 | Phase 20 | Complete |
| FIX-05 | Phase 19 | Complete |
| COLOR-01 | Phase 21 | Complete |
| COLOR-02 | Phase 21 | Complete |
| COLOR-03 | Phase 21 | Complete |
| COLOR-04 | Phase 21 | Complete |
| UXTIP-01 | Phase 24 | Complete |
| UXTIP-02 | Phase 24 | Complete |
| UXTIP-03 | Phase 24 | Complete |
| UXTIP-04 | Phase 24 | Complete |
| UXTIP-05 | Phase 24 | Complete |
| UXTIP-06 | Phase 24 | Complete |
| WINDOW-01 | Phase 22 | Complete |
| WINDOW-02 | Phase 22 | Complete |
| WINDOW-03 | Phase 22 | Complete |
| WINDOW-04 | Phase 22 | Complete |
| WINDOW-05 | Phase 22 | Complete |
| WINDOW-06 | Phase 22 | Complete |
| UNIFY-01 | Phase 23 | Complete |
| UNIFY-02 | Phase 23 | Complete |
| UNIFY-03 | Phase 23 | Complete |
| UNIFY-04 | Phase 23 | Complete |

**Coverage:**
- v0.8 requirements: 25 total
- v0.9 requirements: 14 total
- v0.10 requirements: 6 total
- Mapped to phases: 6
- Unmapped: 0

---
*Requirements defined: 2026-06-21*
*Last updated: 2026-06-21 after v0.10 requirements definition*
