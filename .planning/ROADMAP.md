# Roadmap: mesh-status — v0.10.1 Code Review Cleanup

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
- 🔄 **v0.10.1** — Code Review Cleanup (Phases 26-29)

## Phases

- [ ] **Phase 26: Persistence & Leader Core** — Fix data integrity, leader API robustness, dead code removal
- [ ] **Phase 27: Node Agent** — Fix buffer retry, subprocess/HTTP error handling in node agent
- [ ] **Phase 28: Shell Scripts** — Harden install.sh and start.sh with proper validation, quoting, and path handling
- [ ] **Phase 29: Config, Frontend & Test Infra** — Harden CI/Docker config, add Degraded status, fix test infrastructure, validate register CLI

## Phase Details

### Phase 26: Persistence & Leader Core

**Goal**: Data persistence is reliable, leader API is robust against edge cases, and dead code is removed.

**Depends on**: Nothing (independent code cleanup)

**Requirements**: DATA-01, DATA-02, DATA-03, DATA-04, LEAD-01, LEAD-02, LEAD-03, LEAD-04, DEAD-01, DEAD-02, DEAD-03, DEAD-04

**Success Criteria** (what must be TRUE):

1. `_append_results` appends new data to existing file (not overwrite) and discards invalid lines with a warning log — data is never lost across append calls or leader restarts
2. `/data?window=90d` response deduplicates days whose data straddles `_day_aggregates` and `_results` — users see accurate per-day aggregates without double-counting
3. `/updateConfig` rejects invalid input types and out-of-bounds values with HTTP 400 — config cannot be corrupted via the API
4. Uptime percentage never raises `ZeroDivisionError` — if zero checks exist, uptime displays as 0.0% instead of crashing
5. `_results` and `_day_aggregates` are synchronized with `asyncio.Lock` — no race conditions under concurrent API access
6. Dead code (`_peers_by_node`, `_ensure_data_dir`, `_push_peer_list_to_all`/`_push_config_to_all` consolidated, unused `registry` param, `Optional[str]` → `str | None`) is removed — codebase is cleaner with no stale or duplicate logic

**Plans**: TBD

---

### Phase 27: Node Agent

**Goal**: Node agent reliably submits check results and handles edge cases in subprocess/HTTP communication without crashes.

**Depends on**: Nothing (independent code cleanup)

**Requirements**: NODE-01, NODE-02, NODE-03, NODE-04

**Success Criteria** (what must be TRUE):

1. Node buffer retry submits all accumulated results together instead of dropping the current cycle when a partial submission succeeds — no data loss on transient submission failures
2. Ping stdout is decoded with `errors="replace"` — non-UTF-8 ping output never raises `UnicodeDecodeError`
3. Ping subprocess uses a single `communicate(timeout=...)` instead of `proc.wait()` then `communicate()` — no race condition on subprocess I/O, clean timeout handling
4. HTTP health check exception handler logs the error instead of using bare `except: pass` — HTTP failures are observable in node agent logs

**Plans**: TBD

---

### Phase 28: Shell Scripts

**Goal**: Install and start scripts are robust against edge cases, with proper validation, path handling, quoting, and clean state management.

**Depends on**: Nothing (independent code cleanup)

**Requirements**: SHELL-01, SHELL-02, SHELL-03, SHELL-04, SHELL-05, SHELL-06, SHELL-07, SHELL-08, SHELL-09, SHELL-10

**Success Criteria** (what must be TRUE):

1. Install script checks for `npm` alongside `uv`/`git`/`curl` with actionable error messages before making any filesystem changes — user sees clear feedback if any prerequisite is missing
2. `MESH_STATUS_HOME` is resolved to an absolute path before use — no relative-path confusion in start/install logic
3. Install URL in usage text points to `raw.githubusercontent.com` — curl-pipe-bash instructions work correctly when copied
4. Temp file `/tmp/_mesh_env_backup` is reliably cleaned up after restore or on script exit — no stale temp files
5. `install.sh -h` works as a short alias for `--help`
6. `LEADER_PORT` and `NODE_URL` are persisted to `.env` by `persist_env` — settings survive restart without re-entry
7. Dead trap handler (PID file not cleaned on exec) is removed — no stale or misleading error messages on shutdown
8. `NODE_ARGS` uses bash array instead of unquoted string concatenation — multi-word arguments are properly quoted and split
9. `--leader-url` flag validates the next argument exists and does not start with `--` — user gets a clear error on misuse
10. `.env` template is role-specific (leader vs node) — only relevant environment variables are written for each role

**Plans**: TBD

---

### Phase 29: Config, Frontend & Test Infra

**Goal**: CI/Docker config is hardened, frontend shows degraded status, test infrastructure is reliable, and register CLI validates input.

**Depends on**: Nothing (independent code cleanup)

**Requirements**: CI-01, CI-02, CI-03, CI-04, CI-05, UI-01, UI-02, TEST-01, TEST-02, TEST-03, TEST-04, CLI-01

**Success Criteria** (what must be TRUE):

1. All Makefile phony targets are declared in `.PHONY` — no spurious "up to date" errors on clean/phony targets
2. `.dockerignore` excludes `frontend/node_modules/` and `frontend/dist/` — Docker builds skip irrelevant frontend artifacts
3. `.gitignore` covers `.env`, `*.sw?`, and `*.log` — no accidental commits of environment files or editor swap files
4. uv version is pinned in CI workflow and Dockerfile — reproducible builds across environments
5. Ruff lint rules are explicitly declared in `pyproject.toml` — consistent linting regardless of environment's ruff config
6. Frontend shows `Degraded` (amber) status when one metric (ICMP/HTTP) is below threshold and the other is above — users can distinguish partially-available nodes from fully-available or fully-unavailable ones
7. Dead TypeScript exports (`fetchData30m`, `Data30mResponse`) are removed — no confusing stale exports in the API layer
8. Test fixture `reset_leader_state` clears `_day_aggregates` — no fixture pollution across tests using that fixture
9. `test_config_change_updates_state` restores global config with try/finally — config is restored even on assertion failure
10. `test_data_api` tests use the `client` fixture instead of `app.test_client()` — consistent test patterns across the suite
11. `_StopLoop` is documented with a comment — code clarity for future developers
12. `register.py` validates IP input with `ipaddress.ip_address()` — invalid IPs are rejected early with a clear error message

**Plans**: TBD
**UI hint**: yes

---

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 26 — Persistence & Leader Core | 0/0 | Not started | — |
| 27 — Node Agent | 0/0 | Not started | — |
| 28 — Shell Scripts | 0/0 | Not started | — |
| 29 — Config, Frontend & Test Infra | 0/0 | Not started | — |
