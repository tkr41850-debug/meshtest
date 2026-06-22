# Requirements: mesh-status

**Defined:** 2026-06-21
**Core Value:** A node must be able to detect and report whether it can reach every other node in the mesh, and the leader must present an accurate, up-to-date connectivity view.

## v0.10.1 Requirements

Fix all code review findings across the codebase. Every behavioral fix must follow TDD (write failing test first).

### Persistence & Data Integrity

- [x] **DATA-01**: `_append_results` appends new data to existing file instead of overwriting (direct append mode, discard invalid lines with warning on read)
- [x] **DATA-02**: `_read_results` does not sort (sole caller `load_into_memory` re-sorts anyway)
- [x] **DATA-03**: `_ensure_data_dir` removed (dead code, never called)
- [x] **DATA-04**: Default `DATA_ROOT` relative path documented or resolved to absolute

### Leader API

- [x] **LEAD-01**: `/data?window=90d` response deduplicates days with data split across `_day_aggregates` and `_results`
- [x] **LEAD-02**: `_results` and `_day_aggregates` accesses synchronized with `asyncio.Lock`
- [x] **LEAD-03**: `/updateConfig` validates input types and bounds (returns 400 on invalid input)
- [x] **LEAD-04**: Uptime percentage division by zero guarded (3 sites in `leader.py`)

### Node Agent

- [x] **NODE-01**: Buffer retry submits all current checks together instead of dropping current cycle on partial success
- [x] **NODE-02**: Ping stdout decoded with `errors="replace"` to prevent `UnicodeDecodeError`
- [x] **NODE-03**: `proc.wait()` before `communicate()` replaced with single `communicate(timeout=...)`
- [x] **NODE-04**: Bare `except: pass` in HTTP health check replaced with logged exception

### Install Script

- [x] **SHELL-01**: `command -v npm` checked alongside uv/git/curl
- [x] **SHELL-02**: `MESH_STATUS_HOME` resolved to absolute path before use
- [x] **SHELL-03**: Install URL in usage text points to `raw.githubusercontent.com`
- [x] **SHELL-04**: Temp file `/tmp/_mesh_env_backup` cleaned up after successful restore
- [x] **SHELL-05**: `-h` short flag added as alias for `--help`

### Start Script

- [x] **SHELL-06**: `LEADER_PORT` and `NODE_URL` persisted to `.env` by `persist_env`
- [x] **SHELL-07**: Dead trap handler removed (PID file not cleaned on exec)
- [x] **SHELL-08**: `NODE_ARGS` uses bash array instead of unquoted string concatenation
- [x] **SHELL-09**: `--leader-url` validates next arg exists and doesn't start with `--`
- [x] **SHELL-10**: `.env` template is role-specific (leader vs node)

### CI/Docker Config

- [x] **CI-01**: Makefile declares all phony targets in `.PHONY`
- [x] **CI-02**: `.dockerignore` excludes `frontend/node_modules/` and `frontend/dist/`
- [x] **CI-03**: `.gitignore` covers `.env`, `*.sw?`, and `*.log`
- [x] **CI-04**: uv version pinned in CI workflow and Dockerfile
- [x] **CI-05**: Explicit ruff lint rules in `pyproject.toml`

### Frontend

- [x] **UI-01**: Frontend shows `Degraded` (amber) status when one metric is below threshold and the other is above
- [x] **UI-02**: Dead TypeScript exports (`fetchData30m`, `Data30mResponse`) removed

### Test Infrastructure

- [x] **TEST-01**: `reset_leader_state` fixture clears `_day_aggregates`
- [x] **TEST-02**: `test_config_change_updates_state` restores global config on assertion failure (try/finally)
- [x] **TEST-03**: `test_data_api` tests use `client` fixture instead of `app.test_client()`
- [x] **TEST-04**: `_StopLoop` documented with comment or restructured

### Register CLI

- [x] **CLI-01**: `register.py` validates IP input with `ipaddress.ip_address()`

### Dead Code Removal

- [x] **DEAD-01**: `_peers_by_node` removed from `leader.py` (declared but never populated)
- [x] **DEAD-02**: `_push_peer_list_to_all` and `_push_config_to_all` consolidated (duplicate code)
- [x] **DEAD-03**: Unused `registry` parameter removed from `calculate_status`
- [x] **DEAD-04**: `Optional[str]` replaced with `str | None` syntax (Python 3.12+)

## Out of Scope

| Feature | Reason |
|---------|--------|
| HTTPS/TLS support | Infrastructure feature, not a code review fix |
| Systemd service units | Feature request, not a bug fix |
| Auto-update mechanism | Feature request, not a bug fix |

## Traceability

 | Requirement | Phase | Status |
|-------------|-------|--------|
| DATA-01 | Phase 26 | ✓ |
| DATA-02 | Phase 26 | ✓ |
| DATA-03 | Phase 26 | ✓ |
| DATA-04 | Phase 26 | ✓ |
| LEAD-01 | Phase 26 | ✓ |
| LEAD-02 | Phase 26 | ✓ |
| LEAD-03 | Phase 26 | ✓ |
| LEAD-04 | Phase 26 | ✓ |
| NODE-01 | Phase 27 | ✓ |
| NODE-02 | Phase 27 | ✓ |
| NODE-03 | Phase 27 | ✓ |
| NODE-04 | Phase 27 | ✓ |
| SHELL-01 | Phase 28 | ✓ |
| SHELL-02 | Phase 28 | ✓ |
| SHELL-03 | Phase 28 | ✓ |
| SHELL-04 | Phase 28 | ✓ |
| SHELL-05 | Phase 28 | ✓ |
| SHELL-06 | Phase 28 | ✓ |
| SHELL-07 | Phase 28 | ✓ |
| SHELL-08 | Phase 28 | ✓ |
| SHELL-09 | Phase 28 | ✓ |
| SHELL-10 | Phase 28 | ✓ |
| CI-01 | Phase 29 | ✓ |
| CI-02 | Phase 29 | ✓ |
| CI-03 | Phase 29 | ✓ |
| CI-04 | Phase 29 | ✓ |
| CI-05 | Phase 29 | ✓ |
| UI-01 | Phase 29 | ✓ |
| UI-02 | Phase 29 | ✓ |
| TEST-01 | Phase 29 | ✓ |
| TEST-02 | Phase 29 | ✓ |
| TEST-03 | Phase 29 | ✓ |
| TEST-04 | Phase 29 | ✓ |
| CLI-01 | Phase 29 | ✓ |
| DEAD-01 | Phase 26 | ✓ |
| DEAD-02 | Phase 26 | ✓ |
| DEAD-03 | Phase 26 | ✓ |
| DEAD-04 | Phase 26 | ✓ |

**Coverage:**
- v0.10.1 requirements: 38 total
- Mapped to phases: 38
- Unmapped: 0 ✓

---
*Requirements defined: 2026-06-21*
*Last updated: 2026-06-21 after initial definition*
