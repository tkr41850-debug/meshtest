# Phase 18: Install Script Core - Context

**Gathered:** 2026-06-20
**Status:** Ready for planning

<domain>
## Phase Boundary

Create `deploy/install.sh` — a curl-pipe-bash installer that clones the mesh-status repository to `~/.local/meshtest`, installs Python dependencies via `uv sync`, builds the frontend, and generates a default `.env` config file. Must support prereq checks, version pinning, idempotent reinstall, non-interactive mode, and display a success banner.

</domain>

<decisions>
## Implementation Decisions

### Prereq Check Behavior (Grey Area 1)
- Check `uv` and `git` and `curl` — all are required: uv for Python deps, git for clone/update, curl for pipe-mode download verification
- Bail with actionable error showing install URL for each missing tool
- Check happens before any filesystem modifications

### Version Detection & Update (Grey Area 2)
- Default to `main` branch when `MESH_STATUS_VERSION` is unset
- Detect existing install via `$INSTALL_DIR/.mesh-status.install` sentinel file (not `.git` — avoids confusion with git operations)
- On reinstall: `git fetch --tags && git checkout <version>` (supports switching versions, not just git pull)

### Config & Success Banner (Grey Area 3)
- Always generate `.env` during install with commented defaults (even on reinstall)
- Success banner: full path, start commands for leader and node, dashboard URL, uninstall note
- Install script lives at `<repo-root>/deploy/install.sh`

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `entrypoint.sh` — existing POSIX `sh` entrypoint with `set -e`, env var pattern (`LEADER_HOST`, `LEADER_URL`, `DATA_DIR`)
- `pyproject.toml` — Python project config (uv-based)
- `Dockerfile.leader` / `Dockerfile.node` — Docker images with `uv sync` and frontend build commands

### Established Patterns
- POSIX `sh` with `set -e` for entry points (entrypoint.sh)
- Env vars for all configuration (`config.py` reads `MESH_STATUS_*`, `DATA_DIR`, etc.)
- `entrypoint.sh` uses `exec hypercorn ...` for process replacement

### Integration Points
- `deploy/install.sh` is a new file — no existing code to modify
- Install outputs `$INSTALL_DIR/.mesh-status.install` as sentinel
- Generated `.env` file at `$INSTALL_DIR/.env` with `MESH_STATUS_*` vars

</code_context>

<specifics>
## Specific Ideas

- Use POSIX `sh` only (no bashisms) — a pipe-to-sh install script should work on any POSIX shell
- Run `git clone --depth 1` for speed, fetch tags for version switching on reinstall
- Sentinel file `.mesh-status.install` contains version string for `start.sh --version`
- Install to `~/.local/meshtest` by default, override via `MESH_STATUS_HOME` env var

</specifics>

<deferred>
## Deferred Ideas

- Pre-built frontend artifact (deferred to future milestone — build from source in v0.8)
- Offline detection (deferred — rely on git/curl errors for now)
- Checksum verification of downloaded script (deferred to v0.8.x)

</deferred>
