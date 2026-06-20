# Project Research Summary

**Project:** mesh-status — Distributed mesh connectivity testing tool
**Domain:** Non-Docker install scripts + unified start runner for Python async mesh app
**Researched:** 2026-06-20
**Confidence:** HIGH

## Executive Summary

mesh-status is a distributed mesh connectivity testing tool — a Quart-based async HTTP server (leader) + asyncio check agent (node) + Streamlit dashboard. For v0.8, the priority is adding a **curl-pipe-bash install script** (`deploy/install.sh`) and a **unified runner** (`start.sh`) so users can install on bare-metal VMs (without Docker) alongside the existing Docker deployment. The resulting code works identically on both paths.

**The recommended approach** is a two-script architecture: a POSIX `sh` install script (`deploy/install.sh`) that handles prerequisite checks, git clone, `uv sync`, and config bootstrapping; and a Bash start script (`start.sh`) that handles role selection (`--leader`/`--node`), config loading (XDG-compliant JSON), signal trapping, and `exec`-based process launch. The user install layout follows XDG Base Directory spec (`~/.local/share/mesh-status/` for code, `~/.config/mesh-status/` for config, `~/.local/share/mesh-status/data/` for data). Config overrides follow a clear precedence chain: Python defaults → JSON config file → env vars → CLI flags.

**The three key risks to address:**
1. **Piped install fragility** — `curl ... | bash` silently fails without `set -o pipefail`; interactive `read` steals stdin from the piped script. Mitigation: force download-then-execute in docs, use the `main()`-at-bottom script structure, and use `/dev/tty` for any interactive prompts.
2. **Orphaned processes** — killing `start.sh` without signal propagation leaves Python processes on port 58080. Mitigation: use `exec` to replace the shell (no wrapper process) for foreground mode; use PID files + cleanup trap for daemon mode.
3. **Data directory confusion** — `persistence.py` hardcodes `Path("data")` (CWD-relative), which breaks when run from outside the install directory. Mitigation: fix `persistence.py` to read the `DATA_DIR` env var (which `entrypoint.sh` already sets but Python ignores).

## Key Findings

### Recommended Stack

The stack is a **Python 3.12+** runtime with **Quart 0.20.0** (ASGI-native Flask reimplementation using Hypercorn 0.18.0) and **Streamlit 1.58.0** for the dashboard. Supporting libraries (`aiofiles`, `httpx`, `quart-cors`) are already in `pyproject.toml`. For the shell scripts: `install.sh` uses strict POSIX `sh` (`#!/bin/sh`), `start.sh` uses Bash (`#!/usr/bin/env bash`). Shell scripts are tested with **bats-core 1.11** and linted with **shellcheck 0.10.0**. Dependency management uses **uv** (already a prerequisite). Config follows the existing env var pattern from `config.py` — no TOML/YAML needed.

**Core technologies:**
- **Python 3.12+**: Runtime — active security support through 2028, optimal balance of performance and ecosystem compatibility
- **Quart 0.20.0 + Hypercorn 0.18.0**: Async HTTP server — ASGI-native, `await` works in route handlers natively, companion ASGI server by same author
- **Streamlit 1.58.0**: Dashboard — `st.cache_data` for 10s API polling, eliminates callback spaghetti
- **bats-core 1.11.0**: Shell script testing — TAP-compliant, lightweight, community standard
- **uv**: Python package management — Rust-based, 10-100x faster than pip, prerequisite for install
- **Config: env vars only** (no TOML/YAML) — consistent with existing `config.py`, keeps install script simple, Docker-compatible

**Shell scripting convention:**
- `deploy/install.sh` → `#!/bin/sh` with `set -e` (POSIX subset, no bashisms)
- `start.sh` → `#!/usr/bin/env bash` with `set -euo pipefail` (arrays for PID tracking, `[[ ]]`, `trap`)

### Expected Features

The install/start experience draws from real-world production installers (rustup, nvm, pyenv-installer). The MVP is defined around the INST-01 through INST-04 requirements.

**Must have (table stakes) for v0.8:**
- **Prerequisite checks** (`uv`, `git`, `python3.12+`) — bail early with actionable messages before any filesystem operations
- **Git clone + version pinning** — `git clone --depth 1 --branch <tag>` with `MESH_STATUS_VERSION` env var support
- **`uv sync`** — install Python dependencies with virtualenv
- **Config bootstrap** — generate default `.env`/config with sensible defaults
- **`start.sh --leader` / `--node`** — launch the correct Python process with PID tracking, log to file, signal handling
- **`-y` / `--yes` flag** — non-interactive mode for CI/CD
- **`--help` / `--version`** — standard discoverability
- **Idempotent reinstall** — detecting existing install dir → `git pull` instead of fresh clone
- **Uninstall** — `start.sh --uninstall` removes files, prints cleanup instructions
- **Success banner** — print install path, start commands, dashboard URL after install
- **Signal handling** — SIGTERM/SIGINT trap for graceful shutdown
- **Default install to `~/.local/share/mesh-status/`** with `MESH_STATUS_HOME` override

**Should have (add post-v0.8 validation):**
- **Systemd service unit generation** — template and install `.service` files
- **Health check after start** — poll `/livez` before reporting success
- **Offline detection** — check GitHub reachability before try clone
- **Pre-built dist archive** — skip Node.js build step with release artifact
- **Docker CI test** — full install flow test in fresh `ubuntu:24.04` container

**What to defer (v0.9+):**
- Official apt/homebrew packages
- Auto-update mechanism
- Windows support (PowerShell installer)
- Container-native install (`docker run mesh-status`)

### Architecture Approach

The architecture introduces two new components (`deploy/install.sh` and `start.sh`) that integrate cleanly with the existing codebase. Install script clones the repo, syncs deps, and bootstraps config. Start script self-locates, loads config via JSON→env bridge, and `exec`-replaces itself with the Python process (avoiding orphan issues). The file layout follows XDG spec so config survives reinstall.

**Major components:**
1. **`deploy/install.sh`** (POSIX sh) — prerequisite validation, git clone with version pinning, `uv sync`, config generation, symlink setup, sentinel file as last step
2. **`start.sh`** (Bash) — self-locating script directory, role detection (`--leader`/`--node`), config loading (XDG config path + `jq` or env fallback), env var export for Python, signal trap for cleanup, `exec` for foreground mode, PID file for daemon mode
3. **`mesh_status/persistence.py`** (requires fix) — must read `DATA_DIR` env var instead of hardcoded `Path("data")`; this is the single most critical code integration point

**Key architectural patterns:**
- **Self-locating shell script** — `SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"` with symlink resolution via `readlink -f`
- **Config layering** — Python defaults → JSON config file → env vars → CLI flags
- **Config file → env var bridge** — `start.sh` reads `~/.config/mesh-status/config.json` with `jq` and exports as env vars
- **`exec` for foreground** — `exec uv run python -m mesh_status.leader` replaces shell process, clean signal propagation

**Critical integration issue:** `persistence.py` currently uses `Path("data")` (CWD-relative). The `entrypoint.sh` already sets `DATA_DIR` env var, but Python ignores it. Must fix before v0.8 ships: `Path(os.environ.get("DATA_DIR", "data"))`.

### Critical Pitfalls

13 pitfalls documented. Top 5 for roadmap planning:

1. **Missing `pipefail` in curl|bash causes silent install failure** — curl fails but bash exits 0, user thinks install worked. Prevention: document download-then-execute pattern; post-install verification with `command -v`.

2. **Interactive `read` stdin theft in piped install** — `curl ... | bash` shares stdin between shell parser and `read` calls, corrupting function names. Prevention: structure with `main()` at bottom, use `/dev/tty` for prompts, or download-then-execute.

3. **Orphaned processes when script killed (no signal propagation)** — killing `start.sh` leaves Python on port 58080 causing "Address in use" on restart. Prevention: use `exec` (replaces shell, no orphan risk) for foreground; PID file + cleanup trap for daemon.

4. **Concurrent/partial config file writes** — interleaved writes from parallel starts corrupt config; crash during write leaves truncated file that blocks regeneration. Prevention: atomic write (temp file + `mv`), validate JSON after write, use `flock` for concurrent guard.

5. **Docker CI cache masking install flow bugs** — pre-built Docker images with cached deps skip exactly the install steps that break on fresh VMs. Prevention: use `python:3.12-slim` fresh base, `--no-cache`, test with no uv/git pre-installed.

**Phase mapping for all pitfalls:**
- Phase 1 (`install.sh`): #1 pipefail, #3 strict mode, #7 version drift, #8 prereqs first, #9 cross-platform, #11 hardcoded paths
- Phase 2 (`start.sh`): #2 stdin theft, #4 orphaned processes, #5 partial config writes, #10 upgrade path, #12 uv/venv validation, #13 logging collision
- Phase 3 (CI testing): #6 Docker cache masking

## Implications for Roadmap

Based on the combined research, the v0.8 milestone should be structured in 3 phases reflecting dependency order: install script first (no dependencies), then start script runner (depends on install script's directory structure), then CI validation (validates both install and start).

### Phase 1: `deploy/install.sh` — Install Script Core
**Rationale:** The install script has zero dependencies on other v0.8 components. It must exist first because Phase 2 depends on the directory layout and config it produces.
**Delivers:** A production-quality curl-pipe-bash install script that clones the repo, creates a venv, installs deps, bootstraps config, and prints a success banner.
**Addresses (from FEATURES.md):** Prerequisite checks, git clone + version pinning, `uv sync`, config bootstrap, `-y`/`--yes` flag, `--help`/`--version`, idempotent reinstall, uninstall, success banner, sentinel file, FHS/XDG directory layout.
**Uses (from STACK.md):** `#!/bin/sh` POSIX shebang, `set -e` only, `command -v` for prereq checks, `git clone --depth 1 --branch`, `uv sync --no-dev`, `mktemp` for atomic writes.
**Avoids (from PITFALLS.md):** #1 (pipefail — document download-then-execute), #3 (strict mode), #7 (version pinning from tag), #8 (prereqs before ops), #9 (POSIX utilities + platform branching), #11 (configurable `MESH_STATUS_HOME`).
**Implementation details:**
- `deploy/install.sh` at repo root, tested via `test/install.bats`
- Create sentinel file (`.mesh-installed`) as absolute last step
- Accept `MESH_STATUS_VERSION`, `MESH_STATUS_HOME`, `--yes`, `--prefix`, `--help` flags
- Shellcheck with `-s sh`

### Phase 2: `start.sh` — Unified Runner + Config Integration
**Rationale:** Depends on Phase 1's directory layout (install dir, XDG config path, venv). Must exist before Phase 3 can test.
**Delivers:** A unified Bash runner that handles `--leader`/`--node`, loads config from XDG path, exports env vars, manages signals, and `exec`s the Python process.
**Addresses (from FEATURES.md):** `start.sh --leader`, `start.sh --node`, signal handling, log output to file, health check after start (P2), `--stop` flag, PID file management.
**Uses (from STACK.md):** `#!/usr/bin/env bash` shebang, `set -euo pipefail`, `jq` for JSON config reading, `exec uv run python -m ...` pattern, `trap` for cleanup, `lsof` for port conflict detection.
**Implements (from ARCHITECTURE.md):** Self-locating script pattern, config→env var bridge pattern, config layering (defaults → file → env → CLI), XDG-compliant path resolution.
**Avoids (from PITFALLS.md):** #2 (stdin theft — main-at-bottom, `/dev/tty` for prompts), #4 (orphaned processes — exec for foreground, PID file + trap for daemon), #5 (atomic writes with temp file + `mv` + `flock`), #10 (backup config before upgrade, version detection), #12 (validate `.venv`, recreate on failure), #13 (exec pattern avoids log mixing).
**Code integration points to modify:**
- **`mesh_status/persistence.py`** — CRITICAL: read `DATA_DIR` env var with fallback to `Path("data")`
- **`node.py`** — move into `mesh_status/` package or copy during install so `python -m mesh_status.node` works
- **`pyproject.toml`** — bump version from `0.1.0` to match install script version (prevents drift)

### Phase 3: Docker CI Testing — Install Flow Validation
**Rationale:** Depends on Phases 1 and 2 being implemented. Validates both scripts end-to-end in a production-like environment.
**Delivers:** A CI pipeline (GitHub Actions) that builds a fresh `python:3.12-slim` container, runs the install script, validates the start script, and cleans up.
**Addresses (from FEATURES.md):** Docker CI test, non-interactive install verification, shellcheck in CI.
**Uses (from STACK.md):** `Dockerfile.test`, `bats` test suite, `shellcheck`, GitHub Actions with `--no-cache`.
**Avoids (from PITFALLS.md):** #6 (Docker cache masking — `--no-cache`, fresh base image, no pre-installed uv/git, upgrade scenario testing).
**Test scenarios to implement:**
1. Fresh install from scratch (no uv, no git in base)
2. Idempotent reinstall (run install.sh twice)
3. Upgrade from previous version (if applicable)
4. `start.sh --leader` can parse flags and print help
5. Uninstall cleans up files
6. Cross-platform matrix (ubuntu-latest + macos-latest)

### Phase Ordering Rationale

- **Phase 1 → Phase 2 → Phase 3** is the natural dependency chain: install produces the layout that start consumes, and CI tests validate both.
- Phase 1 and Phase 2 are independent of the existing Docker infrastructure (`entrypoint.sh`, `Dockerfile.*`) — they add new capabilities without modifying existing deployment paths. The `entrypoint.sh` remains unchanged.
- The `persistence.py` DATA_DIR fix in Phase 2 is the single code change that touches the existing Python codebase; all other changes are additive.

### Research Flags

Phases likely needing deeper research during planning:
- **None.** All three phases have well-documented patterns with HIGH confidence sources (rustup, nvm, pyenv-installer for install scripts; OpenRC init patterns for start scripts; existing codebase analysis for integration points).

Phases with standard patterns (skip research-phase):
- **Phase 1 (install.sh):** curl-pipe-bash patterns are mature and documented (rustup, nvm). POSIX sh subset is well-defined. No research needed.
- **Phase 2 (start.sh):** Init script patterns (PID files, signal handling, exec) are decades-old Unix conventions. Config layering is standard. No research needed.
- **Phase 3 (CI testing):** Docker-in-Docker testing is well-documented. bats + shellcheck are standard CI tools. No research needed.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All technologies verified against official PyPI releases, Python.org, and Pallets docs. Python 3.12 version rationale cross-referenced with release cadence. Shell tools (bats, shellcheck) verified against GitHub releases. |
| Features | HIGH | Verified against real-world install scripts (rustup-init.sh, nvm install.sh, pyenv-installer) — all three read full source. Feature prioritization cross-referenced with v0.8 requirements INST-01 through INST-04. Anti-features validated against documented security incidents (Codecov 2021 breach). |
| Architecture | HIGH | Verified against existing codebase: `entrypoint.sh`, `Dockerfile.*`, `persistence.py`, `config.py`, `compose.yml`. XDG Base Directory paths confirmed against freedesktop.org standard. Config layering pattern validated against real-world Python/CLI apps. |
| Pitfalls | HIGH | Each pitfall cross-referenced with real issue trackers (claude-code-action #1136, OpenClaw PR #82918), Unix StackExchange, and production post-mortems. Recovery strategies validated against documented patterns. |

**Overall confidence:** HIGH

### Gaps to Address

- **`DATA_DIR` env var in persistence.py:** The fix is trivial but must not break existing Docker behavior where `DATA_DIR` is set but `entrypoint.sh` currently relies on `cd /app` + relative `Path("data")`. The fix (`os.environ.get("DATA_DIR", "data")`) preserves backward compatibility.
- **`node.py` module location:** Moving `node.py` into `mesh_status/` package requires adding `if __name__ == "__main__"` guard. Verify no existing Docker CMD references to `python node.py` need updating (current `Dockerfile.node` uses `python node.py` which breaks under the new package structure).
- **macOS testing scope:** Cross-platform support (Pitfall #9) is documented but macOS is not a v0.8 target. The POSIX sh choice and platform-branching functions provide forward compatibility without testing overhead.
- **`pyproject.toml` version bump:** Currently at `0.1.0` but codebase is at v0.8. This version gap will cause confusion if `start.sh` does version verification. Needs bump to match expected release tag.

## Sources

### Primary (HIGH confidence)
- **Quart 0.20.0** — https://pypi.org/project/Quart/ (official PyPI, async patterns from Quart docs)
- **Streamlit 1.58.0** — https://pypi.org/project/streamlit/ (official PyPI, caching docs, release notes)
- **bats-core 1.11.0** — https://github.com/bats-core/bats-core (official GitHub, TAP patterns)
- **rustup-init.sh** — https://raw.githubusercontent.com/rust-lang/rustup/master/rustup-init.sh (canonical curl-pipe-bash reference)
- **nvm install.sh** — https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh (idempotent git update pattern)
- **pyenv-installer** — https://github.com/pyenv/pyenv-installer (multi-plugin install pattern)
- **XDG Base Directory Specification** — https://freedesktop.org/software/systemd/man/latest/file-hierarchy.html (official spec for `~/.local/share/`, `~/.config/`)
- **FHS 3.0** — https://refspecs.linuxfoundation.org/FHS_3.0/ (official standard for `/opt`, `/usr/local`)
- **OpenRC service script guide** — https://github.com/martinetd/openrc (PID files, signal handling, daemon patterns)
- **Existing codebase** — Verified against `entrypoint.sh`, `Dockerfile.*`, `persistence.py`, `config.py`, `node.py`, `leader.py`, `compose.yml`

### Secondary (MEDIUM confidence)
- **claude-code-action issue #1136** — Silent install failure on curl 429; real-world pipefail bug
- **OpenClaw PR #82918** — stdin theft in piped install; pipe guard design
- **Unix StackExchange #806014** — Orphaned processes on bash script kill; process group signals
- **Better CLI: Self-executing installation scripts** — https://bettercli.org/design/distribution/self-executing-installer/ (curl-pipe-bash design guidance)
- **Unix SE: ~/.local/bin vs /usr/local vs /opt** — Community consensus on install directory choice
- **Bash Strict Mode Guide** (linuxize.com) — `set -euo pipefail` + IFS patterns
- **ShellSpec vs bats comparison** — https://shellspec.info/comparison.html (feature comparison)

### Tertiary (LOW confidence)
- **"Why My One-Line Installer Worked Everywhere Except WSL"** — WSL-specific edge cases (CRLF, curl.exe vs curl). Low priority for v0.8 (no Windows target).
- **The PipePunisher attack** (SNAKE Security) — Server-side curl|bash detection. Informational; no action needed for v0.8.

---

*Research completed: 2026-06-20*
*Ready for roadmap: yes*
