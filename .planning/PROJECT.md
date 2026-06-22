# mesh-status

## What This Is

A distributed mesh connectivity testing tool for monitoring network health across VMs connected via VPN WAN. A leader server orchestrates node registration and collects periodic connectivity check results (ICMP ping + HTTP /healthz) between all node pairs. A Streamlit dashboard visualizes mesh connectivity over rolling 30-minute or 30-day windows.

## Core Value

A node must be able to detect and report whether it can reach every other node in the mesh, and the leader must present an accurate, up-to-date connectivity view.

## Current State

**Shipped:** v0.10.1 — Code Review Cleanup (2026-06-22)

**Current:** v0.11 — Go Rewrite

**Context:** Both mesh-leader and mesh-node rewritten in Go for minimal container image size and memory footprint. Docker images use scratch/distroless base. Existing Python code preserved alongside. 23 spec/ integration tests validate HTTP API equivalence.

## Current Milestone: v0.11 Go Rewrite

**Goal:** Rewrite both mesh-leader and mesh-node in Go, produce minimal Docker images, and validate against the spec/ integration tests.

**Target features:**
- Go leader with full HTTP API equivalence (register, submit, data, health, updateConfig, peer push)
- Go node with ICMP ping + HTTP health checks, result submission, peer push listener
- JSON file persistence (same data format as Python version)
- Dockerfiles for Go leader and Go node (scratch/distroless base, <10MB images)
- Docker Compose config for full stack with Go backend + existing frontend
- spec/ integration tests pass against Docker-hosted Go leader
- TDD throughout — write failing Go test first

## Requirements

### Validated

- ✓ **LEAD-01**: Leader starts on port 58080 with Quart + Hypercorn ASGI server
- ✓ **LEAD-02**: Leader exposes `POST /register` accepting node IP registration
- ✓ **LEAD-03**: Leader maintains in-memory node registry protected by `asyncio.Lock`
- ✓ **LEAD-04**: Leader exposes `POST /submit` accepting per-cycle check results from nodes
- ✓ **LEAD-05**: Leader exposes `GET /node-list` returning all registered node IPs
- ✓ **LEAD-06**: Leader exposes `GET /livez` liveness endpoint
- ✓ **LEAD-07**: Leader exposes `GET /readyz` readiness endpoint
- ✓ **REGI-01**: `register.py` accepts `--node-ip` and `--leader-ip` via argv
- ✓ **REGI-02**: `register.py` accepts node-ip and leader-ip via stdin
- ✓ **REGI-03**: On registration, leader pushes full node IP list to all registered nodes
- ✓ **REGI-04**: Registration is idempotent
- ✓ **NODE-01**: Node fetches peer IP list from leader at start of each check cycle
- ✓ **NODE-02**: Node runs ICMP ping via system `ping` binary
- ✓ **NODE-03**: Node runs HTTP GET `/healthz` against all peers concurrently
- ✓ **NODE-04**: Ping and HTTP checks use independent timeout handling
- ✓ **NODE-05**: Node submits check results to leader after each cycle
- ✓ **NODE-06**: On submission failure, node buffers results and retries next cycle
- ✓ **NODE-07**: Check interval configurable on leader side (default 10s)
- ✓ **NODE-08**: Concurrent peer checks use semaphore limiting
- ✓ **NODE-09**: Node uses `asyncio.create_subprocess_exec` for ping
- ✓ **NODE-10**: Ping timeout uses `process.wait()` not `communicate()`
- ✓ **DATA-01**: Leader persists results to date-partitioned JSON files
- ✓ **DATA-02**: Data writes use append-only JSON Lines format
- ✓ **DATA-03**: Background task flushes in-memory results to disk every hour
- ✓ **DATA-04**: Leader exposes `GET /data?window=30m`
- ✓ **DATA-05**: Leader exposes `GET /data?window=30d`
- ✓ **DATA-06**: Node status calculated at query time: OK, Pending, NotAvailable
- ✓ **DATA-07**: Data API includes CORS headers
- ✓ **DASH-01**: Streamlit dashboard served standalone
- ✓ **DASH-02**: Dashboard shows 30-minute connectivity matrix
- ✓ **DASH-03**: Dashboard shows 30-day daily aggregated uptime view
- ✓ **DASH-04**: Each node pair shows per-peer connectivity status
- ✓ **DASH-05**: Dashboard uses `@st.cache_data(ttl=25)` for data loading
- ✓ **DASH-06**: Dashboard uses `@st.fragment` for live auto-refresh
- ✓ **NODE-HTTP**: Node HTTP server receives peer push and config updates
- ✓ **HEALTHZ**: Leader exposes `GET /healthz`
- ✓ **RETENTION**: 30-minute data window retains 30 min after flush
- ✓ **DOCK-01**: Dockerfile for leader+dashboard container (Quart + Streamlit) — v0.2
- ✓ **DOCK-02**: Dockerfile for node agent container — v0.2
- ✓ **DOCK-03**: docker-compose.yml for local dev/test — v0.2
- ✓ **DOCK-04**: Docker-specific config (environment variables, ports, volumes for data) — v0.2
- ✓ **DOCK-05**: README deployment docs for Docker-based deployment — v0.2
- ✓ **CI-01**: GitHub Actions workflow builds and pushes multi-arch images to Docker Hub — v0.2

### v0.6 Validated

Now part of validated requirements — see v0.5 validated section.

### v0.7 Active

(none — all shipped)

### v0.7 Validated

- ✓ **FIX-04**: History bars show rolling 30-minute/30-day history instead of only the most recent check

- ✓ **FIX-01**: Fix `CheckResult` interface — use `ping_ok: boolean` / `http_ok: boolean` to match real API
- ✓ **FIX-02**: Fix `aggregateByMinute` checks `c.ping_status` (not in API data) → use `c.ping_ok`
- ✓ **FIX-03**: Backend infers `node_ip` from `_results` when disk data has empty `node_ip`
- ✓ **DASH-13**: Flat 30-day view — remove `<details>` expanders, use sticky headers
- ✓ **DASH-14**: Gap between matrix table and cards in 30m tab
- ✓ **DASH-15**: Two separate history bar rows per pair (ICMP + HTTP) in both views
- ✓ **DASH-16**: HSB-interpolated bar colors via shared `bars.ts` (`renderBars(bars: {percent, tooltip}[])`)
- ✓ **TEST-04**: Update all frontend test fixtures for new `CheckResult` type and bar format

### v0.10 Validated

- ✓ **UXTIP-01**: Remove `title` from bar spans, use `data-tooltip` — v0.10
- ✓ **UXTIP-02**: Each bar span wrapped in `.mesh-tooltip-group` with individual `.mesh-tooltip` div — per-bar hover, not row-level — v0.10
- ✓ **UXTIP-03**: Tooltip CSS classes in `style.css` (dark bg, positioned, arrow) — v0.10
- ✓ **UXTIP-04**: Matrix column headers use tooltip div instead of `title` — v0.10
- ✓ **UXTIP-05**: Tests updated — no `getAttribute("title")`, use `.mesh-tooltip` / `data-tooltip` — v0.10
- ✓ **UXTIP-06**: No visual regression — tooltips only on hover, no layout shift — v0.10

### v0.9 Validated

- ✓ **COLOR-01**: Extract shared `uptimeColor()` to `views/colors.ts` — v0.9
- ✓ **COLOR-02**: HSL gradient thresholds — v0.9
- ✓ **COLOR-03**: Remove duplicated color logic — v0.9
- ✓ **COLOR-04**: Test color consistency at boundary values — v0.9
- ✓ **WINDOW-01**: Backend retention 1800s→5400s — v0.9
- ✓ **WINDOW-02**: `/data?window=90h` endpoint — v0.9
- ✓ **WINDOW-03**: Frontend bars 30→90 — v0.9
- ✓ **WINDOW-04**: `api.ts` adds `fetchData90h()`, renames — v0.9
- ✓ **WINDOW-05**: `types.ts` adds HourData/Data90hResponse — v0.9
- ✓ **WINDOW-06**: `main.ts` wires third tab — v0.9
- ✓ **UNIFY-01**: Extract shared card template to `views/card.ts` — v0.9
- ✓ **UNIFY-02**: cards.ts includes split circle + check count — v0.9
- ✓ **UNIFY-03**: day30.ts renders per-pair cards — v0.9
- ✓ **UNIFY-04**: hourly.ts uses shared card template — v0.9

### v0.8 Validated

- ✓ **INST-01**: `deploy/install.sh` installs mesh-status to `~/.local/meshtest` — v0.8
- ✓ **INST-02**: Prerequisite checks for `uv` and `git` with actionable messages — v0.8
- ✓ **INST-03**: Version-pinned git clone via `MESH_STATUS_VERSION` env var — v0.8
- ✓ **INST-04**: `uv sync` installs Python dependencies — v0.8
- ✓ **INST-05**: Frontend build during install (npm ci + npm run build) — v0.8
- ✓ **INST-06**: Idempotent reinstall — git pull in existing clone on re-run — v0.8
- ✓ **INST-07**: Success banner with install path, start commands, dashboard URL — v0.8
- ✓ **INST-08**: `-y` / `--yes` flag for non-interactive mode — v0.8
- ✓ **INST-09**: `--help` flag for install.sh — v0.8
- ✓ **START-01**: `start.sh --leader` starts the leader via `uv run` — v0.8
- ✓ **START-02**: `start.sh --node` starts the node agent — v0.8
- ✓ **START-03**: Log output redirected to `$INSTALL_DIR/var/*.log` — v0.8
- ✓ **START-04**: PID file management for process tracking — v0.8
- ✓ **START-05**: Signal handling (SIGTERM/SIGINT traps for graceful shutdown) — v0.8
- ✓ **START-06**: `start.sh --help` flag — v0.8
- ✓ **START-07**: `start.sh --version` flag — v0.8
- ✓ **START-08**: `start.sh --uninstall` removes install and prints PATH cleanup — v0.8
- ✓ **CONF-01**: `.env` config file generation with defaults during install — v0.8
- ✓ **CONF-02**: Interactive config wizard for first-run setup — v0.8
- ✓ **CONF-03**: `MESH_STATUS_HOME` env var to override install directory — v0.8
- ✓ **CONF-04**: CLI flag override for non-interactive config — v0.8
- ✓ **TEST-01**: Docker-based CI test verifies full install flow in fresh container — v0.8
- ✓ **TEST-02**: CI test runs `install.sh -y` with env vars for non-interactive mode — v0.8
- ✓ **TEST-03**: CI test verifies `start.sh` launches and process is healthy — v0.8
- ✓ **FIX-05**: Fix `persistence.py` to respect `DATA_DIR` env var — v0.8

### v0.10.1 Validated

- ✓ **FIX-APPEND**: `_append_results` preserves existing data across append calls (direct append mode, discard invalid lines with warning) — v0.10.1
- ✓ **FIX-BUFFER**: Node buffer retry submits all-or-nothing instead of dropping current cycle results on partial success — v0.10.1
- ✓ **FIX-LOCKS**: `_results` and `_day_aggregates` accesses synchronized with `asyncio.Lock` — v0.10.1
- ✓ **FIX-DECODE**: Ping output handled with `errors="replace"` to prevent `UnicodeDecodeError` — v0.10.1
- ✓ **FIX-WAIT**: `proc.wait()` before `communicate()` replaced with single `communicate(timeout=...)` — v0.10.1
- ✓ **FIX-HTTP-EXCEPT**: Bare `except: pass` in HTTP check replaced with logged exception — v0.10.1
- ✓ **FIX-UNGUARDED**: Uptime division by zero guarded (3 sites in `leader.py`) — v0.10.1
- ✓ **FIX-UPGRADE**: `/updateConfig` validates input types and bounds — v0.10.1
- ✓ **FIX-90D-DEDUP**: 90d API response deduplicates days with data in both `_day_aggregates` and `_results` — v0.10.1
- ✓ **FIX-DEGRADED**: Frontend adds `Degraded` (amber) status for partially-available nodes — v0.10.1
- ✓ **FIX-INSTALL**: Install script fixes (npm prereq, relative path, install URL, temp cleanup, -h flag) — v0.10.1
- ✓ **FIX-START**: Start script fixes (persist LEADER_PORT/NODE_URL, dead trap, quoting, arg validation, role-specific .env) — v0.10.1
- ✓ **FIX-CI**: CI/Docker fixes (Makefile PHONY, dockerignore, gitignore, uv pinning, ruff rules) — v0.10.1
- ✓ **FIX-REGISTER**: Register CLI validates IP input — v0.10.1
- ✓ **FIX-TEST-FIXTURES**: Test fixture clears `_day_aggregates`, config test uses try/finally — v0.10.1
- ✓ **FIX-TEST-CLIENT**: `test_data_api` uses client fixture instead of creating own — v0.10.1
- ✓ **FIX-DEADCODE**: Remove dead code (`_peers_by_node`, `_ensure_data_dir`, dead TS exports, unused registry param, duplicate push functions) — v0.10.1
- ✓ **FIX-SPEC-INTEGRATION**: HTTP-only integration tests under spec/ with optional restart-to-persistence — v0.10.1

### v0.11 Active

- [ ] **GO-LEAD-API**: Go leader implements POST /register, POST /submit, GET /data (90m/90h/90d), GET /node-list, GET /livez, GET /readyz, GET /healthz, POST /updateConfig — matching Python endpoint behavior
- [ ] **GO-LEAD-PERSIST**: Go leader persists results to date-partitioned JSON Lines files (same format as Python implementation)
- [ ] **GO-LEAD-PEER-PUSH**: Go leader pushes peer list and config updates to all registered nodes after registration/config changes
- [ ] **GO-LEAD-REGISTRY**: Go leader maintains thread-safe in-memory node registry with asyncio-equivalent synchronization
- [ ] **GO-NODE-PING**: Go node runs ICMP ping via os/exec against all peers with configurable timeout
- [ ] **GO-NODE-HTTP-CHECK**: Go node runs HTTP GET /healthz against all peers concurrently with configurable timeout
- [ ] **GO-NODE-SUBMIT**: Go node submits check results to leader after each cycle, buffers on failure and retries
- [ ] **GO-NODE-PEER-LISTENER**: Go node runs HTTP server to receive peer push and config updates from leader
- [ ] **GO-NODE-CYCLE**: Go node orchestrates full check cycle: fetch peers → run checks → submit results, on configurable interval
- [ ] **GO-DOCKER-LEADER**: Dockerfile for Go leader producing minimal (<10MB) image
- [ ] **GO-DOCKER-NODE**: Dockerfile for Go node producing minimal (<10MB) image
- [ ] **GO-DOCKER-COMPOSE**: docker-compose.yml running Go leader + Go node + existing frontend
- [ ] **GO-SPEC-TESTS**: spec/ integration tests pass against Docker-hosted Go leader
- [ ] **GO-KEEP-PYTHON**: Python source files remain in the repository (not deleted)

### Out of Scope

- Authentication / access control — VPN is trusted network for prototype
- Database backend — JSON file storage sufficient for prototype scale
- Real-time push/WebSocket — Frontend polls the data endpoint
- Encryption of data in transit or at rest — prototype
- Kubernetes / orchestration — Docker Compose sufficient for prototype
- Systemd service units — v0.8 uses start.sh directly; systemd deferred
- Package manager (apt/brew) — curl-pipe-bash is the primary install path
- Auto-update mechanism — requires background process, future milestone
- Windows/Git Bash support — separate concern, not in scope
- Pre-built frontend artifact — build from source in v0.8

## Context

- Python backend (Quart) on port 58080, frontend (Vite + TS + Tailwind) served from same port
- Go backend being built alongside (same API, same data format)
- Deployed across multiple VMs on different geographies connected via VPN WAN
- Data is small per check, retained in memory on nodes between submissions
- Leader writes JSON files hourly to avoid memory/disk pressure
- System `ping` binary used for ICMP (shelled out)
- Frontend fetches from same-origin API endpoints

## Constraints

- **Port**: Leader must listen on 58080 (serving both API and frontend)
- **Language**: Go (new backend) + Python (existing, preserved) + TypeScript (frontend)
- **Framework**: Go standard library / Chi (backend), Vite + Tailwind CSS (frontend)
- **Deployment**: Multi-VM over VPN WAN, minimal Docker images
- **Base image**: scratch or distroless for Go binaries

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Quart instead of FastAPI | Simpler async server, fewer dependencies for prototype | ✓ Good |
| JSON file persistence | Quick to implement, inspectable, no DB setup | ✓ Good |
| System ping binary | Avoids root/capabilities for raw ICMP sockets | ✓ Good |
| No auth | VPN is trusted, prototype speed | ⚠️ Revisit |
| Port 58080 | Avoids privileged ports, unlikely to conflict | ✓ Good |
| Vite + Tailwind for frontend | Modern tooling, fast dev iteration, type-safe | ✓ Good |
| Leader serves frontend from same port | Simpler deployment, no CORS, one port to manage | ✓ Good |
| Degraded (amber) for partial availability | Distinguishes partially-available from fully-unavailable | ✓ Good |
| TDD for all behavioral changes | Ensures fix is reproducible, prevents regressions | ✓ Good |
| `_append_results` direct append (not atomic-replace) | Simpler implementation, invalid lines discarded on read with warning | ✓ Good |
| CORS `*` | Acceptable for prototype; simplifies frontend dev | ⚠️ Revisit |
| uv version pinned (0.6.10) | Reproducible builds, avoids surprise update breaks | ✓ Good |
| Explicit ruff lint rules | Consistent linting regardless of env config | ✓ Good |
| Spec integration tests via external commands | Clean separation from unit tests, truly exercises HTTP layer | ✓ Good |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-06-22 after v0.11 milestone initialization*
