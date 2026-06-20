# Phase 19: Start Script & Config Integration - Context

**Gathered:** 2026-06-20
**Status:** Ready for planning

<domain>
## Phase Boundary

Create `start.sh` — a unified Bash runner that starts the leader (`--leader`) or node agent (`--node`) with proper process management, signal handling, logging, and PID tracking. Also: interactive config wizard (skipped if CLI flags provided), `--uninstall` and `--version` flags, and fix `persistence.py` to respect the `DATA_DIR` env var.

</domain>

<decisions>
## Implementation Decisions

### Process Management (Grey Area 1)
- Foreground exec by default — `start.sh` replaces the shell with the Python process (Docker/CI friendly)
- PID files at `$INSTALL_DIR/var/leader.pid` and `$INSTALL_DIR/var/node.pid`
- On stale PID: check if process exists by PID before starting; clean stale on startup
- Trap SIGTERM/SIGINT → forward to child PID → wait for child → exit

### Config Wizard & Flags (Grey Area 2)
- Wizard runs **always by default** — prompts interactively for config values
- If any CLI flags are passed (`--leader-url`, `--node-ip`, `--leader-ip`, etc.), skip the wizard (flags imply non-interactive mode)
- Config file is `.env` (key=value) in `$INSTALL_DIR/` — consistent with install.sh generation

### persistence.py Fix & Uninstall (Grey Area 3)
- Fix: `DATA_ROOT = Path(os.environ.get("DATA_DIR", "data"))` — backward compatible with Docker
- Uninstall removes the entire `$INSTALL_DIR` (config + data + install)
- `start.sh --version` reads `.mesh-status.install` sentinel file

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `deploy/install.sh` — POSIX sh installer, referenced for `$INSTALL_DIR` resolution
- `entrypoint.sh` — existing Docker entrypoint, has `exec hypercorn` pattern for leader
- `node.py` — node agent entry point, accepts `--leader-url`, `--node-ip` CLI args
- `mesh_status/leader.py:main()` — leader entry point via `hypercorn mesh_status.leader:app`
- `mesh_status/persistence.py` — has hardcoded `Path("data")` that needs fixing
- `mesh_status/config.py` — reads env vars for all config

### Established Patterns
- Env vars for configuration (config.py pattern)
- POSIX `sh` with `set -e` for entry points
- `entrypoint.sh` uses `exec` for process replacement

### Files to Fix
- `mesh_status/persistence.py` — change `DATA_ROOT = Path("data")` to read from env var
- New file: `start.sh` at repo root

</code_context>

<specifics>
## Specific Ideas

- start.sh should self-locate (resolve `$INSTALL_DIR` from its own path after following symlinks)
- Config wizard should reuse existing MESH_STATUS_* env var names from config.py
- On --uninstall, print "To remove $INSTALL_DIR from your PATH, remove this line from ~/.bashrc: export PATH=$INSTALL_DIR:$PATH"
- Use `#!/usr/bin/env bash` for arrays and signal trap reliability

</specifics>

<deferred>
## Deferred Ideas

- Systemd service unit generation (deferred to v0.8.x)
- Health check polling after start (deferred — rely on process exit code for now)

</deferred>
