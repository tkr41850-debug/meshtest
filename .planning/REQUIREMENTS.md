# Requirements: mesh-status

**Defined:** 2026-06-20
**Core Value:** A node must be able to detect and report whether it can reach every other node in the mesh, and the leader must present an accurate, up-to-date connectivity view.

## v0.8 Requirements

### Install Script (INST)

- [ ] **INST-01**: `deploy/install.sh` installs mesh-status to `~/.local/meshtest`
- [ ] **INST-02**: Prerequisite checks for `uv` and `git` with actionable messages
- [ ] **INST-03**: Version-pinned git clone via `MESH_STATUS_VERSION` env var
- [ ] **INST-04**: `uv sync` installs Python dependencies
- [ ] **INST-05**: Frontend build during install (npm ci + npm run build)
- [ ] **INST-06**: Idempotent reinstall — git pull in existing clone on re-run
- [ ] **INST-07**: Success banner with install path, start commands, dashboard URL
- [ ] **INST-08**: `-y` / `--yes` flag for non-interactive mode
- [ ] **INST-09**: `--help` flag for install.sh

### Start Script (START)

- [ ] **START-01**: `start.sh --leader` starts the leader via `uv run`
- [ ] **START-02**: `start.sh --node` starts the node agent
- [ ] **START-03**: Log output redirected to `$INSTALL_DIR/var/*.log`
- [ ] **START-04**: PID file management for process tracking
- [ ] **START-05**: Signal handling (SIGTERM/SIGINT traps for graceful shutdown)
- [ ] **START-06**: `start.sh --help` flag
- [ ] **START-07**: `start.sh --version` flag
- [ ] **START-08**: `start.sh --uninstall` removes install and prints PATH cleanup

### Config & Setup (CONF)

- [ ] **CONF-01**: `.env` config file generation with defaults during install
- [ ] **CONF-02**: Interactive config wizard for first-run setup
- [ ] **CONF-03**: `MESH_STATUS_HOME` env var to override install directory
- [ ] **CONF-04**: CLI flag override for non-interactive config

### Docker CI Test (TEST)

- [ ] **TEST-01**: Docker-based CI test verifies full install flow in fresh container
- [ ] **TEST-02**: CI test runs `install.sh -y` with env vars for non-interactive mode
- [ ] **TEST-03**: CI test verifies `start.sh` launches and process is healthy

### Infrastructure Fix (FIX)

- [ ] **FIX-05**: Fix `persistence.py` to respect `DATA_DIR` env var instead of hardcoded `Path("data")`

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

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| INST-01 | | Pending |
| INST-02 | | Pending |
| INST-03 | | Pending |
| INST-04 | | Pending |
| INST-05 | | Pending |
| INST-06 | | Pending |
| INST-07 | | Pending |
| INST-08 | | Pending |
| INST-09 | | Pending |
| START-01 | | Pending |
| START-02 | | Pending |
| START-03 | | Pending |
| START-04 | | Pending |
| START-05 | | Pending |
| START-06 | | Pending |
| START-07 | | Pending |
| START-08 | | Pending |
| CONF-01 | | Pending |
| CONF-02 | | Pending |
| CONF-03 | | Pending |
| CONF-04 | | Pending |
| TEST-01 | | Pending |
| TEST-02 | | Pending |
| TEST-03 | | Pending |
| FIX-05 | | Pending |

**Coverage:**
- v0.8 requirements: 25 total
- Mapped to phases: 0
- Unmapped: 25

---
*Requirements defined: 2026-06-20*
*Last updated: 2026-06-20 after initial definition*
