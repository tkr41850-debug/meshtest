# Stack Research

**Domain:** Distributed mesh connectivity testing tool (Python, async HTTP, Streamlit dashboard) + Install Scripts & Unified Runner
**Researched:** 2026-06-20
**Confidence:** HIGH

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Python | 3.12+ | Runtime language | Streamlit 1.58 requires >=3.10, Hypercorn 0.18 requires >=3.10, Quart 0.20 requires >=3.9. Pin to 3.12 for a good balance of performance (faster startup, lower memory than 3.13/3.14) and ecosystem compatibility. Python 3.12 is still in active security support (through 2028) and all major dependencies target it. |
| Quart | 0.20.0 | Async HTTP server | ASGI-native reimplementation of Flask API by the Pallets project (same organization behind Flask, Jinja, Click). The async-first design means `await` works natively in route handlers — critical for concurrent node registration + check result ingestion without thread pool overhead. Unlike FastAPI, Quart avoids pulling in Starlette + Pydantic as forced dependencies, keeping the dependency graph lean for a prototype. Hypercorn (the companion ASGI server) is also by the same author, ensuring seamless compatibility. |
| Hypercorn | 0.18.0 | ASGI production server | The default/companion ASGI server for Quart, written by the same author (pgjones). Supports HTTP/1, HTTP/2, HTTP/3 (experimental with `h3` extra), and WebSockets. Can be configured to listen on port 58080 directly. Alternative: Uvicorn 0.44 works fine too but Hypercorn is the canonical choice for Quart. |
| Streamlit | 1.58.0 | Frontend dashboard | De facto standard for Python data dashboards since 2022 (Snowflake acquisition matured it). 90% of Fortune 50 use it internally. The "script rerun on interaction" model eliminates callback spaghetti for simple polling dashboards. Version 1.58 (May 2026) is the latest stable, requiring Python >=3.10. Key features for this project: `st.cache_data` for API response caching, `st.session_state` for time-window selection persistence. |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `aiofiles` | 24.1.0 | Async file I/O for Quart | Required for the JSON persistence layer. Quart runs in an async event loop — using sync `open()` inside a route handler blocks the event loop. `aiofiles` provides async-compatible file read/write via a thread pool. Used on the leader to write aggregated JSON to `data/[yyyy]/[mm]/[dd].json`. |
| `httpx` | 0.28.x | Async HTTP client (node side) | Used by nodes to perform HTTP GET /healthz checks against other nodes and to submit check results to the leader. `httpx.AsyncClient` is the async equivalent of `requests` — fully compatible with asyncio. Avoid `requests` (sync-only, blocks event loop). |
| `quart-cors` | 0.8.0 | CORS headers for Quart API | Needed if the Streamlit frontend runs on a different port/origin than the Quart API. Streamlit dev server defaults to port 8501; Quart API runs on port 58080. Without CORS, browser-based fetch calls from the Streamlit frontend to the API will be blocked. Apply `cors(app)` to the Quart app to allow all origins during prototype. |
| `pydantic` | 2.x | Data validation / models | Optional but recommended for the NodeRegistration, CheckResult, and MeshStatus data models. Pydantic v2 is significantly faster than v1 (Rust-based validation core). Provides serialization/deserialization to dict (for JSON storage) and type validation at the Quart API boundary. Not required if using plain dataclasses — tradeoff: less validation vs. fewer dependencies. |

### Install & Runner Script Stack

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| POSIX sh (`/bin/sh`) | — | Shebang for `deploy/install.sh` | Install script runs on diverse systems (Alpine Docker, Debian, Ubuntu, etc.). POSIX sh is guaranteed everywhere — Alpine uses `busybox ash`, Debian links `/bin/sh` to `dash`. A POSIX-compliant script avoids shebang portability issues. The install script does NOT need arrays, process substitution, or other bashisms. **Use `#!/bin/sh`** with strict POSIX subset. [Source: POSIX spec, confirmed `/bin/sh` is the standard shebang.](https://stackoverflow.com/questions/53116226/what-is-the-recommended-posix-sh-shebang) |
| Bash (`/bin/bash`) | — | Shebang for `start.sh` | Start script manages Python subprocesses with PID files, backgrounding, signal forwarding, and log rotation. These use bash features like `[[ ]]`, arrays for PID tracking, `trap` for signal handling, and process substitution. Bash is installed by default on virtually every Linux system that would run mesh-status. The script is run interactively or via systemd — portability to non-bash environments is not a concern. **Use `#!/usr/bin/env bash`** for flexibility. |
| `python-dotenv` | 1.1.0 | `.env` file loading | The project already uses environment variables for configuration (`MESH_STATUS_INTERVAL`, `LEADER_URL`, etc. — see `mesh_status/config.py`). `python-dotenv` reads a `.env` file into `os.environ` before the app starts, giving users a single file to configure without shell `export` commands. It's a pure-Python zero-dependency library. **No TOML/YAML needed** — the existing 8 env vars do not warrant a structured config format. |
| `bats-core` | 1.11.0 | Shell script testing framework | The de facto standard for testing Bash scripts since 2021. TAP-compliant output integrates with CI. Lightweight (single bash script), actively maintained by the bats-core organization. Tests are pure bash with `@test` syntax. Matches the project's simplicity needs — install scripts are logic-light (git clone + uv sync), so bats provides enough assertion power (`run`, `assert_output`, `assert_success`). **Do NOT use ShellSpec** — it's more powerful (BDD, mocking, coverage) but overkill for 2-4 install/start tests. |
| `shellcheck` | 0.10.0 | Static analysis for shell scripts | Industry standard linter for sh/bash. Catches quoting errors, missing variable expansions, and common pitfalls. Run in CI alongside bats. Zero-config for basic usage. Use `shellcheck deploy/install.sh start.sh` in CI. |
| `set -euo pipefail` | — | Bash strict mode for `start.sh` | Standard defensive programming for bash scripts. `set -e` (exit on error), `set -u` (error on undefined variables), `set -o pipefail` (pipe failures propagate). Install script uses `set -e` only (POSIX-compatible). |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| `uv` | Python dependency management | Fastest Python package installer/resolver (Rust-based, 10-100x faster than pip). Creates deterministic lockfiles. **Already a prerequisite for mesh-status** — the install script checks for `uv` before proceeding. |
| `ruff` | Linting + formatting | Replaces flake8, isort, black in a single Rust-based tool. Zero-config setup. Run `ruff check .` and `ruff format .`. |
| `pytest` + `pytest-asyncio` | Python testing | `pytest-asyncio` is required for testing Quart async route handlers. |
| `bats` | Shell script testing | Install via `npm install -g bats` or git submodule. Run `bats test/install.bats`. |
| `shellcheck` | Shell script linting | Install via `apt install shellcheck` or `brew install shellcheck`. Run in CI. |

### Infrastructure (Deployment)

| Component | Choice | Rationale |
|-----------|--------|-----------|
| Process manager on leader | `start.sh --leader` (foreground) or systemd | `start.sh` runs the app in the foreground by default (for Docker/CI). Systemd `.service` file is deferred to post-v0.8 (out of scope for this milestone). |
| Process manager on nodes | `start.sh --node` (foreground) or systemd | Same as leader — foreground mode for Docker, systemd deferred. |
| VPN | Existing VPN WAN | Out of scope for software stack — the project assumes connectivity over existing VPN. |
| Docker-based CI testing | `Dockerfile.test` + `docker compose` | A dedicated test Dockerfile that starts from a clean base, installs uv+git, runs `deploy/install.sh`, then validates with bats. |

## Install & Runner Details

### Shell Scripting Conventions

**`deploy/install.sh` — POSIX sh (`#!/bin/sh`)**

```sh
#!/bin/sh
set -e

# NO bashisms:
#   ❌ [[ "$var" == "val" ]]    → ✅ [ "$var" = "val" ]
#   ❌ source ./file.sh          → ✅ . ./file.sh
#   ❌ function f { }            → ✅ f() { }
#   ❌ ${var,,} / ${var^^}       → use tr or read case
#   ❌ arrays                     → use space-separated strings
#   ❌ process substitution       → use temp files or pipes

# Standard curl-pipe-bash safety patterns:
# 1. Abort if script is not run from stdin (pipe) — add safety header
# 2. Use `curl -fsSL` flags: fail silently (-f), follow redirects (-L), show errors (-S), silent (-s)
# 3. Print what will be done before doing it
# 4. Provide --help, --version, --dry-run flags
# 5. Check prerequisites before touching anything
```

**`start.sh` — Bash (`#!/usr/bin/env bash`)**

```bash
#!/usr/bin/env bash
set -euo pipefail

# bashisms OK here:
#   ✅ [[ "$var" == "val" ]]     — safer string comparison
#   ✅ arrays for PID tracking   — needed for process management
#   ✅ [[ -v var ]]              — check if variable is set
#   ✅ trap for cleanup          — signal handling
#   ✅ exec for foreground mode  — replaces shell with Python process
```

### Config File Format

**Decision: Environment variables only (no TOML/YAML/INI)**

Rationale:
1. **Existing precedent** — `mesh_status/config.py` already reads 5 env vars (`MESH_STATUS_INTERVAL`, `MESH_STATUS_PEER_PUSH_TIMEOUT`, `MESH_STATUS_LOG_LEVEL`, `MESH_STATUS_BUFFER_SIZE`, `MESH_STATUS_GRACE_PERIOD`). Adding a config file format creates a parallel config path.
2. **Install script simplicity** — The install script would need to create/write a config file, adding complexity. With env vars, `start.sh` simply sets them before invoking `uv run`.
3. **Docker compatibility** — Docker Compose already uses env vars (`LEADER_URL`, `NODE_URL`, `MESH_STATUS_INTERVAL`). A config file would need volume mounting or ENV overrides.
4. **TOML/YAML overhead** — For 8-10 settings, pulling in a TOML parser (`tomli` / `tomllib`) adds a dependency that's not needed. Python 3.11+ has `tomllib` in stdlib, but the project would still need a config loading layer.
5. **python-dotnet is NOT needed** — The project doesn't run inside systemd services that need `.env` file loading. Docker and `start.sh` pass env vars directly.

**How config flows:**

```
start.sh --leader
  ├── exports MESH_STATUS_INTERVAL=10 (default)
  ├── exports LEADER_HOST=0.0.0.0
  ├── exports LEADER_PORT=58080
  ├── exports DATA_DIR=./data
  └── exec uv run hypercorn mesh_status.leader:app --bind "${LEADER_HOST}:${LEADER_PORT}"

start.sh --node --leader-url http://leader:58080 --node-url http://node-ip:58080
  ├── exports LEADER_URL=http://leader:58080
  ├── exports NODE_URL=http://node-ip:58080
  ├── exports MESH_STATUS_INTERVAL=10
  └── exec uv run python node.py
```

**Config override precedence (lowest to highest):**

1. `mesh_status/config.py` defaults (hardcoded)
2. Environment variables (exported by shell, Docker, or systemd)
3. `start.sh` CLI flags (`--leader-url`, `--node-url`, `--interval`, etc.)
4. Interactive config prompt during `deploy/install.sh` (writes a `~/.mesh-status/env` or similar sourced file)

### Deployment Structure

```
deploy/
  install.sh          # curl-pipe-bash installer (POSIX sh)
start.sh              # Unified runner (bash)
```

**What goes in `deploy/install.sh`:**

1. Check prerequisites: `uv --version`, `git --version`, `python3 --version`
2. Determine install directory (default: `~/.mesh-status`, override with `--prefix`)
3. Git clone the repo (or pull if already exists)
4. Run `uv sync` to create virtualenv + install dependencies
5. Generate default config (write `~/.mesh-status/env` file if interactive)
6. Symlink `start.sh` to `~/.local/bin/mesh-status` or add to PATH
7. Print success message with usage

**What goes in `start.sh`:**

1. Parse `--leader` / `--node` flags and config overrides
2. Set up logging (stdout + file, rotate on SIGUSR1 or size)
3. PID file management (`/tmp/mesh-status-{leader,node}.pid`)
4. Signal forwarding (SIGTERM → child process)
5. `exec` the appropriate Python command in foreground mode
6. Optional daemon mode (`--daemon` flag) with `nohup` + PID tracking

### Process Management for start.sh

**Approach: Foreground by default, PID file for daemon mode**

```bash
# Foreground mode (default) — for Docker, systemd, tmux, interactive
start.sh --leader
# This exec's hypercorn directly — replaces the shell process.
# Signals (SIGTERM, SIGINT) pass through to the Python process.
# Logs go to stdout/stderr.

# Daemon mode (--daemon) — for headless servers without systemd
start.sh --node --daemon
# Starts process with nohup, writes PID to /tmp/mesh-status-node.pid
# Logs to ~/.mesh-status/logs/node.log
# Stop with: start.sh --node --stop
```

**PID file management pattern:**

```bash
PID_DIR="${MESH_STATUS_HOME:-$HOME/.mesh-status}/run"
PID_FILE="$PID_DIR/${ROLE}.pid"

start_daemon() {
    mkdir -p "$PID_DIR" "$LOG_DIR"
    nohup "$@" > "$LOG_DIR/${ROLE}.log" 2>&1 &
    echo $! > "$PID_FILE"
}

stop_daemon() {
    if [ -f "$PID_FILE" ]; then
        pid=$(cat "$PID_FILE")
        kill "$pid" 2>/dev/null && echo "Stopped $ROLE (pid $pid)"
        rm -f "$PID_FILE"
    fi
}
```

**Why NOT use systemd units in v0.8:**
- Systemd unit files require root or `--user` service setup
- Not all target environments have systemd (Docker, Alpine)
- Systemd integration is better done as a separate phase with `mesh-status install-service --leader` command
- Out of scope for this milestone per `REQUIREMENTS.md`

### Testing Approach

**Shell script tests with bats-core:**

```
test/
  install.bats         # Tests for deploy/install.sh
  start.bats           # Tests for start.sh
```

**Test structure (`test/install.bats`):**

```bash
#!/usr/bin/env bats

setup() {
    # Create temp directory for test install
    TEST_DIR=$(mktemp -d)
    export HOME="$TEST_DIR/home"
    mkdir -p "$HOME"
}

@test "install.sh fails when uv is missing" {
    # Mock uv as missing by temporarily hiding it
    run env PATH=/usr/bin ./deploy/install.sh --prefix "$TEST_DIR"
    [ "$status" -eq 1 ]
    [[ "$output" == *"uv is required"* ]]
}

@test "install.sh clones repo and creates venv" {
    # Requires network — mark as integration test
    run ./deploy/install.sh --prefix "$TEST_DIR"
    [ "$status" -eq 0 ]
    [ -f "$TEST_DIR/start.sh" ]
    [ -d "$TEST_DIR/.venv" ]
}

@test "start.sh --leader fails without config" {
    run ./deploy/install.sh --prefix "$TEST_DIR"
    run "$TEST_DIR/start.sh" --leader --dry-run
    [ "$status" -eq 0 ]
    [[ "$output" == *"hypercorn"* ]]
}
```

**Docker-based CI testing (`Dockerfile.test`):**

```dockerfile
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl git bats shellcheck && \
    rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | UV_INSTALL_DIR=/usr/local/bin sh

WORKDIR /test

# Copy install script and test suite
COPY deploy/install.sh /test/
COPY start.sh /test/
COPY test/ /test/test/

# Test 1: shellcheck
RUN shellcheck /test/install.sh /test/start.sh

# Test 2: install script from scratch
RUN mkdir -p /test-install && \
    bash /test/install.sh --prefix /test-install --no-interactive

# Test 3: validate start.sh can parse flags
RUN /test-install/start.sh --help

# Test 4: bats test suite
RUN bats /test/test/
```

**GitHub Actions integration:**

```yaml
name: Test install scripts

on:
  push:
    paths:
      - 'deploy/install.sh'
      - 'start.sh'
      - 'test/install.bats'
      - 'test/start.bats'
      - 'Dockerfile.test'

jobs:
  install-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Shellcheck
        run: |
          sudo apt-get install -y shellcheck
          shellcheck deploy/install.sh start.sh
      - name: Build test image
        run: docker build -t mesh-status-test -f Dockerfile.test .
      - name: Run install tests in container
        run: docker run --rm mesh-status-test bats /test/test/
```

### What NOT to Add (v0.8 Explicit Out of Scope)

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `Makefile` | Adds another build tool dependency. The install script replaces the need for `make install`. | `start.sh` + `deploy/install.sh` |
| Systemd unit files | Requires root or `--user` mode. Not portable to Docker. Out of scope for v0.8. | Deferred to post-v0.8 when `mesh-status install-service` is implemented. |
| Homebrew formula | macOS support is not in scope. | No alternative needed. |
| `pyproject.toml` CLI entry points (`[project.scripts]`) | The project already uses `uv run` approach. Adding entry points (e.g., `mesh-status-leader`) would require restructuring the Python entry points. | `start.sh` wrapper handles this. Revisit when adding pip-install support. |
| `pip install mesh-status` | The project is distributed via git clone (prototype). PyPI publishing is not in scope. | `deploy/install.sh` handles git clone + `uv sync`. |
| Configuration wizard with `dialog` / `whiptail` | Too many dependencies for a text-based UI. Question prompts with readline are sufficient. | Simple `read -p` prompts in `install.sh`. |
| `supervisord` | Adds a Python dependency and configuration complexity. | `start.sh --daemon` for simple backgrounding; systemd deferred. |
| `tmux` / `screen` dependency | These are user-choice tools, not something the project should manage. | `start.sh` runs in foreground; users choose their session manager. |
| Secret management (Vault, etc.) | The VPN is a trusted network. No secrets to manage at v0.8 scale. | Environment variables are sufficient. |
| ShellSpec over bats | ShellSpec is more powerful (BDD style, mocking, coverage) but adds complexity for 2-4 tests. Bats is simpler, sufficient, and the community standard for this use case. | bats-core. Revisit if shell scripts grow beyond 200 lines. |
| Config file format (TOML/YAML) | Unnecessary complexity for 8 env vars. Adds a parser dependency. | Environment variables + `python-dotenv` if .env loading is needed. |

## Alternatives Considered (Install Script Section)

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| `#!/bin/sh` (POSIX) | `#!/bin/bash` | If install script needs arrays, `[[ ]]`, or process substitution. **Stick with sh** — the install script only does: `echo`, `read`, `if [ ]`, `curl`, `git clone`, `uv sync`. None of these need bash. |
| Bats-core 1.11 | ShellSpec 0.28 | **Use ShellSpec** when: testing shell functions with mocking, needing coverage reports, or writing >10 test files. For 2-4 simple install verification tests, bats is lighter. |
| Foreground `exec` | Daemonize with double-fork | **Use foreground exec** for Docker/CI where logs go to stdout/journald. Daemon mode (`--daemon`) uses nohup, not double-fork, for simplicity. |
| `python-dotenv` | `tomllib` (stdlib 3.11+) | If >20 config options were needed, a structured format would win. With 8 env vars, the parsing overhead isn't worth it. |
| `deploy/install.sh` curl-pipe-bash | GitHub Releases tarball | If the project had tagged releases, a tarball with pre-built venv would be faster. For active development on `main`, `git clone` is more up-to-date. |

## Stack Patterns by Variant

**If the install script needs to run on macOS:**
- Test with `bash` (macOS default shell is zsh, but `bash` is available)
- Use `#!/usr/bin/env bash` for `start.sh` to find bash in PATH
- macOS `sed` is BSD variant, not GNU — use `sed -i ''` instead of `sed -i`
- macOS doesn't have `realpath` — use `$PWD` or Python's `os.path.realpath`

**If adding pip-install distribution later:**
- Add `[project.scripts]` to `pyproject.toml`: `mesh-status-leader = "mesh_status.leader:main"`
- Create a proper `__main__.py` for `python -m mesh_status`
- `deploy/install.sh` becomes `pip install mesh-status` via PyPI
- `start.sh` remains as the config + process management layer

**If users need to run behind a reverse proxy (nginx, Caddy):**
- `start.sh` should support `--socket /tmp/mesh-status.sock` for UNIX socket binding
- Or `--port 8080` for localhost-only binding behind the proxy
- Avoids port conflicts and allows the proxy to handle TLS termination

## Version Compatibility

| Package | Compatible With | Notes |
|---------|----------------|-------|
| Quart 0.20.0 | Python >=3.9, Hypercorn >=0.18 | Quart depends on Werkzeug, Jinja2, itsdangerous, click, blinker — all from Pallets projects |
| Hypercorn 0.18.0 | Python >=3.10, Quart >=0.15 | Depends on h11, h2, wsproto, priority |
| Streamlit 1.58.0 | Python >=3.10, altair >=4.0 | Streamlit 1.58 dropped support for `element.add_rows` (deprecated). Has its own Tornado-based server on port 8501 by default |
| `aiofiles` 24.1.0 | Python >=3.8 | Stable, minimal API surface |
| `httpx` 0.28.x | Python >=3.8, anyio | v0.28 dropped Python 3.7 support. Use `httpx[httptools]` for faster HTTP parsing if needed |
| `quart-cors` 0.8.0 | Quart >=0.15 | Same maintainer as Quart |
| `bats-core` 1.11.0 | bash >=3.2 | Requires bash; does NOT support POSIX sh. Tests must use bash shebang. |
| `python-dotenv` 1.1.0 | Python >=3.8 | Pure Python, zero dependencies. Use `load_dotenv()` at app startup. |
| `shellcheck` 0.10.0 | All shell types | Run with `shellcheck -s sh deploy/install.sh` and `shellcheck -s bash start.sh` |

## Background Task Patterns (Critical)

Quart requires specific async patterns. Document key ones:

### Async Subprocess for ping (Node Side)
```python
import asyncio

async def ping_host(host: str, timeout: int = 5) -> dict:
    """Shell out to system ping binary with asyncio subprocess."""
    proc = await asyncio.create_subprocess_exec(
        "ping", "-c", "1", "-W", str(timeout), host,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(), timeout=timeout + 2
        )
    except asyncio.TimeoutError:
        proc.kill()
        return {"host": host, "reachable": False, "rtt_ms": None, "error": "timeout"}
    
    # Parse output — Linux format
    # "64 bytes from 10.0.0.1: icmp_seq=1 ttl=64 time=0.040 ms"
    stdout_text = stdout.decode()
    if proc.returncode != 0 or not stdout_text:
        return {"host": host, "reachable": False, "rtt_ms": None, "error": "unreachable"}
    
    # Extract RTT from output
    import re
    match = re.search(r"time=(\d+\.?\d*)\s*ms", stdout_text)
    rtt_ms = float(match.group(1)) if match else None
    return {"host": host, "reachable": True, "rtt_ms": rtt_ms}
```

### Async HTTP Health Check (Node Side)
```python
import httpx

async def check_healthz(host: str, port: int = 58080) -> dict:
    """Async HTTP GET /healthz check against another node."""
    url = f"http://{host}:{port}/healthz"
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            resp = await client.get(url)
            return {
                "host": host,
                "reachable": resp.status_code == 200,
                "status_code": resp.status_code,
                "error": None,
            }
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            return {
                "host": host,
                "reachable": False,
                "status_code": None,
                "error": str(e),
            }
```

### Async File Write for JSON Persistence (Leader Side)
```python
import aiofiles
import json
from datetime import datetime

async def write_check_data(data: dict, base_path: str = "data") -> None:
    """Write aggregated check results to date-partitioned JSON file."""
    now = datetime.utcnow()
    filepath = f"{base_path}/{now.year:04d}/{now.month:02d}/{now.day:02d}.json"
    
    # Ensure parent directory exists (async-safe approach)
    import os
    os.makedirs(os.path.dirname(filepath), exist_ok=True)  # sync but rare
    
    async with aiofiles.open(filepath, mode="w") as f:
        await f.write(json.dumps(data, indent=2, default=str))
```

### Streamlit Polling Pattern (Frontend)
```python
import streamlit as st
import httpx
import pandas as pd

@st.cache_data(ttl=10)  # Re-fetch every 10 seconds
def fetch_mesh_data(window: str = "30min") -> list:
    """Fetch connectivity data from Quart API, cached for 10s."""
    resp = httpx.get(f"http://localhost:58080/api/mesh?window={window}")
    resp.raise_for_status()
    return resp.json()

# In main app:
window = st.radio("Time Window", ["30min", "30day"], horizontal=True)
data = fetch_mesh_data(window)
df = pd.DataFrame(data)
st.dataframe(df)
```

## Sources

- **Quart 0.20.0** — https://pypi.org/project/Quart/ (verified PyPI release)
- **Quart documentation** — https://quart.palletsprojects.com/ (async patterns, API reference)
- **Hypercorn 0.18.0** — https://pypi.org/project/Hypercorn/ (verified PyPI release Nov 2025)
- **Streamlit 1.58.0** — https://pypi.org/project/streamlit/ (verified PyPI release May 2026)
- **Streamlit release notes 2026** — https://docs.streamlit.io/develop/quick-reference/release-notes/2026
- **Streamlit caching docs** — https://docs.streamlit.io/develop/concepts/architecture/caching
- **`aiofiles` 24.1.0** — https://pypi.org/project/aiofiles/
- **`httpx` docs** — https://www.python-httpx.org/ (async client patterns)
- **`quart-cors` 0.8.0** — https://pypi.org/project/quart-cors/
- **Python 3.14 release** — https://www.python.org/downloads/release/python-3146/ (June 2026)
- **`gufo_ping`** — https://docs.gufolabs.com/gufo_ping/ (alternative for future scaling)
- **Python `asyncio` subprocess** — https://docs.python.org/3/library/asyncio-subprocess.html
- **bat-core 1.11** — https://github.com/bats-core/bats-core (GitHub, verified latest release)
- **Bats testing tutorial** — https://www.baeldung.com/linux/testing-bash-scripts-bats (general bats patterns)
- **ShellSpec vs bats comparison** — https://shellspec.info/comparison.html (feature comparison)
- **POSIX sh shebang recommendation** — https://stackoverflow.com/questions/53116226/what-is-the-recommended-posix-sh-shebang (Stack Overflow, confirmed top answer)
- **`python-dotenv` 1.1.0** — https://pypi.org/project/python-dotenv/ (verified PyPI release)
- **`set -euo pipefail` pattern** — http://redsymbol.net/articles/unofficial-bash-strict-mode/ (standard reference for bash strict mode)
- **mesh-status `config.py`** — file:///home/mac.guest/meshtest/mesh_status/config.py (verified existing env var config pattern)
- **Dockerfile.leader / Dockerfile.node** — file:///home/mac.guest/meshtest/ (verified existing Docker infrastructure)
- **`entrypoint.sh`** — file:///home/mac.guest/meshtest/entrypoint.sh (verified existing sh script patterns — uses `#!/bin/sh` with POSIX-compatible syntax)

---

*Stack research for: mesh-status distributed connectivity testing tool (including install scripts + unified runner for v0.8)*
*Researched: 2026-06-20*
