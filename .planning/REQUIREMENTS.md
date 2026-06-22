# Requirements: mesh-status

**Defined:** 2026-06-21
**Core Value:** A node must be able to detect and report whether it can reach every other node in the mesh, and the leader must present an accurate, up-to-date connectivity view.

## v0.10.1 Requirements

Fix all code review findings across the codebase. Every behavioral fix must follow TDD (write failing test first).

### Persistence & Data Integrity

- [ ] **DATA-01**: `_append_results` appends new data to existing file instead of overwriting (direct append mode, discard invalid lines with warning on read)
- [ ] **DATA-02**: `_read_results` does not sort (sole caller `load_into_memory` re-sorts anyway)
- [ ] **DATA-03**: `_ensure_data_dir` removed (dead code, never called)
- [ ] **DATA-04**: Default `DATA_ROOT` relative path documented or resolved to absolute

### Leader API

- [ ] **LEAD-01**: `/data?window=90d` response deduplicates days with data split across `_day_aggregates` and `_results`
- [ ] **LEAD-02**: `_results` and `_day_aggregates` accesses synchronized with `asyncio.Lock`
- [ ] **LEAD-03**: `/updateConfig` validates input types and bounds (returns 400 on invalid input)
- [ ] **LEAD-04**: Uptime percentage division by zero guarded (3 sites in `leader.py`)

### Node Agent

- [ ] **NODE-01**: Buffer retry submits all current checks together instead of dropping current cycle on partial success
- [ ] **NODE-02**: Ping stdout decoded with `errors="replace"` to prevent `UnicodeDecodeError`
- [ ] **NODE-03**: `proc.wait()` before `communicate()` replaced with single `communicate(timeout=...)`
- [ ] **NODE-04**: Bare `except: pass` in HTTP health check replaced with logged exception

### Install Script

- [ ] **SHELL-01**: `command -v npm` checked alongside uv/git/curl
- [ ] **SHELL-02**: `MESH_STATUS_HOME` resolved to absolute path before use
- [ ] **SHELL-03**: Install URL in usage text points to `raw.githubusercontent.com`
- [ ] **SHELL-04**: Temp file `/tmp/_mesh_env_backup` cleaned up after successful restore
- [ ] **SHELL-05**: `-h` short flag added as alias for `--help`

### Start Script

- [ ] **SHELL-06**: `LEADER_PORT` and `NODE_URL` persisted to `.env` by `persist_env`
- [ ] **SHELL-07**: Dead trap handler removed (PID file not cleaned on exec)
- [ ] **SHELL-08**: `NODE_ARGS` uses bash array instead of unquoted string concatenation
- [ ] **SHELL-09**: `--leader-url` validates next arg exists and doesn't start with `--`
- [ ] **SHELL-10**: `.env` template is role-specific (leader vs node)

### CI/Docker Config

- [ ] **CI-01**: Makefile declares all phony targets in `.PHONY`
- [ ] **CI-02**: `.dockerignore` excludes `frontend/node_modules/` and `frontend/dist/`
- [ ] **CI-03**: `.gitignore` covers `.env`, `*.sw?`, and `*.log`
- [ ] **CI-04**: uv version pinned in CI workflow and Dockerfile
- [ ] **CI-05**: Explicit ruff lint rules in `pyproject.toml`

### Frontend

- [ ] **UI-01**: Frontend shows `Degraded` (amber) status when one metric is below threshold and the other is above
- [ ] **UI-02**: Dead TypeScript exports (`fetchData30m`, `Data30mResponse`) removed

### Test Infrastructure

- [ ] **TEST-01**: `reset_leader_state` fixture clears `_day_aggregates`
- [ ] **TEST-02**: `test_config_change_updates_state` restores global config on assertion failure (try/finally)
- [ ] **TEST-03**: `test_data_api` tests use `client` fixture instead of `app.test_client()`
- [ ] **TEST-04**: `_StopLoop` documented with comment or restructured

### Register CLI

- [ ] **CLI-01**: `register.py` validates IP input with `ipaddress.ip_address()`

### Dead Code Removal

- [ ] **DEAD-01**: `_peers_by_node` removed from `leader.py` (declared but never populated)
- [ ] **DEAD-02**: `_push_peer_list_to_all` and `_push_config_to_all` consolidated (duplicate code)
- [ ] **DEAD-03**: Unused `registry` parameter removed from `calculate_status`
- [ ] **DEAD-04**: `Optional[str]` replaced with `str | None` syntax (Python 3.12+)

## Out of Scope

| Feature | Reason |
|---------|--------|
| HTTPS/TLS support | Infrastructure feature, not a code review fix |
| Systemd service units | Feature request, not a bug fix |
| Auto-update mechanism | Feature request, not a bug fix |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| DATA-01 | Phase 26 | Pending |
| DATA-02 | Phase 26 | Pending |
| DATA-03 | Phase 26 | Pending |
| DATA-04 | Phase 26 | Pending |
| LEAD-01 | Phase 26 | Pending |
| LEAD-02 | Phase 26 | Pending |
| LEAD-03 | Phase 26 | Pending |
| LEAD-04 | Phase 26 | Pending |
| NODE-01 | Phase 27 | Pending |
| NODE-02 | Phase 27 | Pending |
| NODE-03 | Phase 27 | Pending |
| NODE-04 | Phase 27 | Pending |
| SHELL-01 | Phase 28 | Pending |
| SHELL-02 | Phase 28 | Pending |
| SHELL-03 | Phase 28 | Pending |
| SHELL-04 | Phase 28 | Pending |
| SHELL-05 | Phase 28 | Pending |
| SHELL-06 | Phase 28 | Pending |
| SHELL-07 | Phase 28 | Pending |
| SHELL-08 | Phase 28 | Pending |
| SHELL-09 | Phase 28 | Pending |
| SHELL-10 | Phase 28 | Pending |
| CI-01 | Phase 29 | Pending |
| CI-02 | Phase 29 | Pending |
| CI-03 | Phase 29 | Pending |
| CI-04 | Phase 29 | Pending |
| CI-05 | Phase 29 | Pending |
| UI-01 | Phase 29 | Pending |
| UI-02 | Phase 29 | Pending |
| TEST-01 | Phase 29 | Pending |
| TEST-02 | Phase 29 | Pending |
| TEST-03 | Phase 29 | Pending |
| TEST-04 | Phase 29 | Pending |
| CLI-01 | Phase 29 | Pending |
| DEAD-01 | Phase 26 | Pending |
| DEAD-02 | Phase 26 | Pending |
| DEAD-03 | Phase 26 | Pending |
| DEAD-04 | Phase 26 | Pending |

**Coverage:**
- v0.10.1 requirements: 38 total
- Mapped to phases: 38
- Unmapped: 0 ✓

---
*Requirements defined: 2026-06-21*
*Last updated: 2026-06-21 after initial definition*
