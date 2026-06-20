# Architecture Research: Install & Start Scripts

**Domain:** Distributed mesh connectivity tool — install/start script integration
**Researched:** 2026-06-20
**Confidence:** HIGH (verified against existing codebase)

## Standard Architecture

### System Overview — Install & Start Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                        USER INTERACTION                               │
│  ┌──────────────────────┐     ┌──────────────────────────────┐       │
│  │  curl ... | bash      │     │  start.sh --leader / --node  │       │
│  │  (one-time install)   │     │  (daily operation)           │       │
│  └──────────┬───────────┘     └──────────────┬───────────────┘       │
│             │                                 │                       │
├─────────────┴─────────────────────────────────┴──────────────────────┤
│                        INSTALL SCRIPTS                                 │
│  ┌──────────────────────┐     ┌──────────────────────────────┐       │
│  │  deploy/install.sh    │     │  start.sh                    │       │
│  │  ┌──────────────────┐ │     │  ┌────────────────────────┐ │       │
│  │  │ clone repo       │ │     │  │ detect install dir     │ │       │
│  │  │ uv sync          │ │     │  │ parse --leader/--node  │ │       │
│  │  │ build frontend   │ │     │  │ load config file       │ │       │
│  │  │ create config    │ │     │  │ exec uv run ...        │ │       │
│  │  └──────────────────┘ │     │  └────────────────────────┘ │       │
│  └──────────────────────┘     └──────────────────────────────┘       │
├─────────────────────────────────────────────────────────────────────┤
│                          APPLICATION LAYER                             │
│  ┌──────────────────────┐     ┌──────────────────────────────┐       │
│  │  mesh_status.leader   │     │  node.py                     │       │
│  │  (Quart + Hypercorn)  │     │  (asyncio check agent)      │       │
│  └──────────┬───────────┘     └──────────────┬───────────────┘       │
│             │                                 │                       │
│  ┌──────────┴─────────────────────────────────┴───────────────┐      │
│  │  mesh_status/ (config.py, persistence.py, models.py, ...)  │      │
│  └──────────────────────────┬──────────────────────────────────┘      │
├─────────────────────────────┴────────────────────────────────────────┤
│                         DATA LAYER                                      │
│  ┌──────────────────────┐     ┌──────────────────────────────┐       │
│  │  config.json          │     │  data/ (JSON Lines files)    │       │
│  │  (~/.config/mesh-     │     │  (~/.local/share/mesh-      │       │
│  │   status/config.json) │     │   status/data/)             │       │
│  └──────────────────────┘     └──────────────────────────────┘       │
└─────────────────────────────────────────────────────────────────────┘
```

### Existing Component Boundaries

| Component | Responsibility | Entry Point |
|-----------|---------------|-------------|
| `mesh_status.leader:app` | Quart app with Hypercorn ASGI server | `entrypoint.sh` (Docker) or `python -m mesh_status.leader` |
| `node.py` | Node agent — periodic connectivity checks | `python node.py --leader-url ...` |
| `register.py` | CLI registration helper | Direct invocation |
| `entrypoint.sh` | Docker entrypoint (leader only) | `exec hypercorn mesh_status.leader:app` |
| `mesh_status/config.py` | Defaults overridden by env vars | Imported by leader + node |
| `mesh_status/persistence.py` | Appends check results to JSON Lines files | Uses `Path("data")` (CWD-relative) |

### New Component Boundaries (v0.8)

| Component | Responsibility | Entry Point |
|-----------|---------------|-------------|
| `deploy/install.sh` | Clone repo, `uv sync`, build frontend, create config | `curl ... | bash` or direct |
| `start.sh` | Unified runner: detect role, load config, exec app | `start.sh --leader` / `start.sh --node` |
| config.json | User config file (overrides env var defaults) | Read by `start.sh`, exposed as env vars |

## Recommended Project Structure (after install)

### Install Target Layout

```
~/.local/share/mesh-status/          # MESH_STATUS_HOME
├── .venv/                           # uv virtual environment
├── mesh_status/                     # Python package
│   ├── __init__.py
│   ├── __main__.py
│   ├── leader.py
│   ├── node.py                      # (copied from root)
│   ├── config.py
│   ├── persistence.py
│   ├── models.py
│   └── status.py
├── frontend/dist/                   # Pre-built frontend assets
├── start.sh                         # Unified runner
├── entrypoint.sh                    # Docker entrypoint (kept for Docker compat)
├── pyproject.toml
└── .python-version

~/.config/mesh-status/               # XDG_CONFIG_HOME
└── config.json                      # User configuration

~/.local/share/mesh-status/data/     # Runtime data (JSON Lines)

~/.local/bin/start.sh                # Symlink → ~/.local/share/mesh-status/start.sh
```

### Structure Rationale

- **`~/.local/share/mesh-status/`**: Follows XDG Base Directory spec. This is the install root (`MESH_STATUS_HOME`). Contains everything needed to run — the cloned repo, venv, built frontend.
- **`~/.config/mesh-status/config.json`**: XDG_CONFIG_HOME location for config. Separate from install directory so config survives reinstall.
- **`~/.local/share/mesh-status/data/`**: Runtime data (check results) in XDG_DATA_HOME. Separate from config.
- **`~/.local/bin/start.sh`**: Symlink to the real script. `~/.local/bin` is typically on PATH.
- **`frontend/` lives inside install dir**: Leader serves frontend from the same port (port 58080). The leader expects `dist/` relative to the install directory.
- **`node.py` lives inside `mesh_status/`**: Node.py currently lives at root. For installed layout, copy/move it into the mesh_status package so `python -m mesh_status.node` works. This avoids CWD assumptions.

### Why This Layout

1. **XDG compliance**: Standard, portable, respects user's existing conventions
2. **Self-contained**: The install directory has everything — clone the repo and `uv sync` once, run forever
3. **Config/data separation**: Config is user-editable, data is runtime, install dir is immutably versioned
4. **Symlink entry point**: `~/.local/bin/start.sh` is a symlink, so `start.sh --leader` works from any CWD
5. **Docker compatibility**: Inside Docker, the layout is `/app/...` (same structure, different root). The existing Dockerfiles use `WORKDIR /app` — the start.sh can detect this and adapt.

## Integration Points

### How `start.sh` Finds and Invokes Python Modules

The script MUST determine its install directory first — it lives at the root of the install:

```bash
# start.sh — self-locating pattern
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
MESH_STATUS_HOME="$SCRIPT_DIR"  # The script is at the install root
```

From there, it invokes:

| Role | Command | Why |
|------|---------|-----|
| `--leader` | `cd "$MESH_STATUS_HOME" && exec uv run python -m mesh_status.leader` | Uses `uv run` to activate venv, `-m mesh_status.leader` to invoke the ASGI entry point. `cd` ensures `Path("data")` in persistence.py resolves to install root. |
| `--node` | `cd "$MESH_STATUS_HOME" && exec uv run python -m mesh_status.node --leader-url "$LEADER_URL" --node-url "$NODE_URL"` | Same pattern, but for node.py as a module. |

**Alternative (direct venv):** If `.venv/bin/python` exists and uv is not installed:
```bash
exec "$MESH_STATUS_HOME/.venv/bin/python" -m mesh_status.leader
```

This is important because `uv run` is the primary mechanism but we should fall back to direct venv if uv is not available (though install pre-reqs require uv).

### Config File Location and Format

**Path:** `~/.config/mesh-status/config.json` (resolved via `$XDG_CONFIG_HOME` with fallback to `~/.config`)

**Format:** JSON — consistent with the rest of the project (JSON Lines for data, JSON for registration payloads).

```json
{
  "leader_url": "http://0.0.0.0:58080",
  "node_url": "",
  "check_interval": 10,
  "log_level": "INFO",
  "data_dir": "~/.local/share/mesh-status/data"
}
```

**How it's consumed by `start.sh`:**

```bash
# In start.sh — config is read and exported as env vars
CONFIG_FILE="${XDG_CONFIG_HOME:-$HOME/.config}/mesh-status/config.json"
if [ -f "$CONFIG_FILE" ]; then
    LEADER_URL=$(jq -r '.leader_url // "http://0.0.0.0:58080"' "$CONFIG_FILE")
    LOG_LEVEL=$(jq -r '.log_level // "INFO"' "$CONFIG_FILE")
    DATA_DIR=$(jq -r '.data_dir // ""' "$CONFIG_FILE")
    # ... export all as environment variables
fi

# CLI flags override config file values (order: defaults → config file → CLI flags)
```

**Why JSON not TOML/YAML:** The project already speaks JSON everywhere — registration payloads, submit payloads, peer push, JSON Lines data storage. Using JSON for config is consistent and avoids pulling in a TOML/YAML parser (jq is ubiquitous). If YAML were needed, Python can read it, but `start.sh` is shell and `jq` is the most portable structured data tool.

**Env var mapping** (what config.py already expects):

| Config Key | Env Var | Default |
|------------|---------|---------|
| `leader_url` | `LEADER_URL` | `http://0.0.0.0:58080` |
| `check_interval` | `MESH_STATUS_INTERVAL` | `10` |
| `log_level` | `MESH_STATUS_LOG_LEVEL` | `INFO` |
| `data_dir` | `DATA_DIR` | `~/.local/share/mesh-status/data` |
| `buffer_size` | `MESH_STATUS_BUFFER_SIZE` | `20000` |
| `peer_push_timeout` | `MESH_STATUS_PEER_PUSH_TIMEOUT` | `5` |
| `grace_period` | `MESH_STATUS_GRACE_PERIOD` | `120` |

### Relationship Between Docker `entrypoint.sh` and New `start.sh`

| Aspect | `entrypoint.sh` (Docker) | `start.sh` (Unified) |
|--------|--------------------------|----------------------|
| **Role** | Leader only | Leader OR Node |
| **Environment** | Assumes venv on PATH (`/app/.venv/bin`) | Locates install dir, uses `uv run` |
| **Config source** | Env vars only | Config file → Env vars → CLI flags |
| **Data directory** | `$DATA_DIR` (env) | Configurable via config file |
| **Execution style** | `exec hypercorn ...` (direct) | `exec uv run python -m ...` |
| **PID 1 behavior** | Yes (Docker CMD) | Yes (general process) |
| **CWD handling** | None needed (WORKDIR /app) | `cd` to install dir |

**Shared patterns:**
- Both use `exec` to replace the shell process with the Python process
- Both set `LEADER_URL` as an env var before exec
- Both respect `DATA_DIR` env var (though persistence.py currently doesn't read it — see Critical Integration Issue below)
- Both use `set -e` for fail-fast behavior

**Key difference:** `entrypoint.sh` is intentionally minimal — just env parsing + exec. `start.sh` is richer — config file loading, role selection, interactive config setup. This is appropriate: Docker containers get config via environment (the Docker way), while bare-metal installs benefit from a config file.

### How `start.sh` Works Both Inside and Outside Docker

**Detection logic:**
```bash
# If /app exists and contains mesh-status, we're inside Docker
if [ -d "/app/mesh_status" ] && [ -f "/app/pyproject.toml" ]; then
    MESH_STATUS_HOME="/app"
else
    # Self-locate: start.sh lives at install root
    SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
    MESH_STATUS_HOME="$SCRIPT_DIR"
fi
```

**Inside Docker:** The existing `Dockerfile.node` already uses `CMD exec uv run python node.py ...`. When migrating to `start.sh`, it would become `CMD ["/app/start.sh", "--node"]` or equivalent. The `entrypoint.sh` remains for backward compatibility but `start.sh` could eventually replace it.

**Outside Docker:** `start.sh` does its self-location dance, loads config from `~/.config/mesh-status/config.json`, and execs the right Python module.

### What Existing Code Paths Need Modification

| File | Change Required | Why | Risk |
|------|----------------|------|------|
| `mesh_status/persistence.py` | **READ `DATA_DIR` env var** | Currently uses `Path("data")` (CWD-relative). The start.sh works around this by `cd`-ing to install dir, but the proper fix is to check `os.environ.get("DATA_DIR", ...)` to respect the env var that `entrypoint.sh` already sets. Without this fix, non-Docker runs could write data to unexpected locations. | **Low** — env var with fallback to current behavior |
| `node.py` location | **Move into `mesh_status/` package OR copy in install.sh** | Currently at root (`root/node.py`). For `python -m mesh_status.node` to work, node.py must be a module. Either move it OR have `install.sh` copy it into the install dir. Moving it (and adding `if __name__ == "__main__"` back) is cleaner long-term. | **Low** — mechanical change |
| `leader.py` `dist_dir` | **Verify path resolution** | `Path(__file__).resolve().parent.parent / "dist"` resolves to `root/dist/` when run from root, but under install layout it becomes `mesh_status/../../dist/` which also resolves to the install root. This actually works correctly already. | **None** — already correct |
| `entrypoint.sh` | **No change needed** | Remains the Docker entrypoint. `start.sh` is additive. | **None** |
| `Dockerfile.node` | **Optional: switch to start.sh** | Could use `CMD ["/app/start.sh", "--node"]` for consistency. Not required. | **Low** — pure refactor |

**Critical Integration Issue — DATA_DIR in persistence.py:**

```python
# Current (bug): ignores DATA_DIR env var
DATA_ROOT = Path("data")

# Fix: respect DATA_DIR env var
DATA_ROOT = Path(os.environ.get("DATA_DIR", "data"))
```

This is the single most important code change. Without it:
- Docker already sets `DATA_DIR=/app/data` (but persistence ignores it)
- start.sh must `cd` to install dir for relative `Path("data")` to work
- Users who run from a different CWD lose data

### Repository Cloning vs Direct Download

**Recommendation: Clone with git.**

| Approach | Pros | Cons |
|----------|------|------|
| **Clone** (git clone) | - Prereq git already installed<br>- Easy updates (`git pull`)<br>- User can inspect full source<br>- Version pinning via tags | - Larger download<br>- Requires git |
| **Direct download** (curl tarball) | - Smaller initial download | - No easy update path<br>- Harder to verify integrity<br>- Need to handle tarball extraction |
| **Git archive / tarball** | - Smaller than full clone | - No update path<br>- Still need to download |

Since git is already a prerequisite, **clone is the clear winner**. The install.sh workflow:

```bash
git clone --depth 1 --branch <tag> https://github.com/<org>/mesh-status.git "$MESH_STATUS_HOME"
uv sync --directory "$MESH_STATUS_HOME"
uv run --directory "$MESH_STATUS_HOME" node frontend/build.js  # or npm run build
```

## Architectural Patterns

### Pattern 1: Self-Locating Shell Script

**What:** The shell script determines its own install directory at runtime, so it can find sibling files (venv, Python modules) regardless of the user's CWD.

```bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
```

**When to use:** Any script that needs to reference files relative to its own location. Critical for `start.sh` — users may run it from any directory.

**Trade-offs:** Resolving symlinks requires `readlink -f` (Linux) or `-f` flag which isn't POSIX. For the symlink case (`~/.local/bin/start.sh` → `~/.local/share/mesh-status/start.sh`), we follow the link:

```bash
# Follow symlink to real location
if [ -L "$0" ]; then
    SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
else
    SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
fi
```

### Pattern 2: Config Layering (Defaults → File → Env → CLI)

**What:** Configuration is resolved in a precedence chain where each layer overrides the previous.

```
Defaults (hardcoded in config.py)
    ↓ (overridden by)
Config file (~/.config/mesh-status/config.json)
    ↓ (overridden by)
Environment variables (set by user or Docker)
    ↓ (overridden by)
CLI flags (--leader-url, etc.)
```

**When to use:** Any application that needs to support multiple deployment modes (Docker, bare-metal, dev).

**Trade-offs:** More complex than a single config source, but necessary for this project's hybrid deployment model (Docker env vars + bare-metal config files).

### Pattern 3: Config File → Env Var Bridge

**What:** The shell script reads a JSON config file and exports the values as environment variables before exec'ing the Python process. The Python code reads env vars (as it already does in `config.py`).

```bash
# start.sh — bridge config file to env vars
CONFIG_FILE="${XDG_CONFIG_HOME:-$HOME/.config}/mesh-status/config.json"
if command -v jq &>/dev/null && [ -f "$CONFIG_FILE" ]; then
    export MESH_STATUS_INTERVAL=$(jq -r '.check_interval // 10' "$CONFIG_FILE")
    export MESH_STATUS_LOG_LEVEL=$(jq -r '.log_level // "INFO"' "$CONFIG_FILE")
    export DATA_DIR=$(jq -r '.data_dir // ""' "$CONFIG_FILE")
fi
```

**When to use:** When the Python app already uses env vars for config (as `mesh_status/config.py` does), and you want to add config file support without rewriting the Python config layer.

**Trade-offs:** Requires `jq` for JSON parsing in shell. If jq is not available, fall back to env-only. For minimal-footprint installs, consider shipping a tiny JSON parser or using Python itself to parse the config file (but that's chicken-and-egg for `start.sh`).

## Data Flow

### Install Flow

```
User runs: curl https://raw.githubusercontent.com/.../deploy/install.sh | bash
    ↓
install.sh:
  1. Parse MESH_STATUS_HOME (default: ~/.local/share/mesh-status)
  2. Verify prerequisites: uv, git
  3. Clone repo: git clone --depth 1 <url> "$MESH_STATUS_HOME"
  4. Create venv + install deps: uv sync
  5. Build frontend: cd frontend && npm ci && npm run build
  6. Create config dir: mkdir -p ~/.config/mesh-status
  7. Interactive config prompt (or --non-interactive with flags)
  8. Write config.json
  9. Create data dir: mkdir -p "$DATA_DIR"
  10. Install start.sh symlink: ln -s "$MESH_STATUS_HOME/start.sh" ~/.local/bin/start.sh
  11. Print success message with usage instructions
```

### Runtime Flow (Leader)

```
User runs: start.sh --leader [--port 58080]
    ↓
start.sh:
  1. Resolve install directory (self-locate)
  2. Parse --leader flag + optional args
  3. Load config file → export env vars
  4. CLI flags override env vars
  5. cd to MESH_STATUS_HOME
  6. exec uv run python -m mesh_status.leader
    ↓
mesh_status.leader.main():
  7. Reads LEADER_URL from env → determines port
  8. Starts Quart app on Hypercorn
  9. Serves API + frontend from port 58080
  10. Persists data to DATA_DIR/data/
```

### Runtime Flow (Node)

```
User runs: start.sh --node --leader-url http://leader:58080 --node-url http://node1:58081
    ↓
start.sh:
  1. Resolve install directory
  2. Parse --node flag + --leader-url, --node-url
  3. Load config file → export env vars
  4. CLI flags override env vars
  5. cd to MESH_STATUS_HOME
  6. exec uv run python -m mesh_status.node --leader-url "$LEADER_URL" --node-url "$NODE_URL"
    ↓
node.py (as module):
  7. Parses --leader-url and --node-url
  8. Registers with leader
  9. Begins periodic check cycles
  10. Buffers results, submits to leader
```

## Scaling Considerations

| Concern | Single VM (current) | Multi-VM with install script | Notes |
|---------|---------------------|------------------------------|-------|
| **Config distribution** | Manual per-VM | Install.sh per-VM is the distribution mechanism | Each VM runs its own install; config connects them |
| **Data directory** | CWD-relative | Absolute path in config | Must fix DATA_DIR in persistence.py |
| **Updates** | git pull in install dir | git pull in MESH_STATUS_HOME | Consider adding --update flag to start.sh |
| **Multiple instances** | Not supported | Not supported | Each VM runs one leader or one node |
| **Config file conflicts** | N/A | Single config.json | Simple JSON, no merge complexity |

### Scaling Priorities

1. **First bottleneck: Data directory confusion** — persistence.py's `Path("data")` breaks when run from wrong CWD. Fix before v0.8 ships.
2. **Second bottleneck: Non-interactive install** — CI/testing needs `--non-interactive` mode from day one. Include in install.sh.

## Anti-Patterns

### Anti-Pattern 1: Requiring CWD to Be Install Directory

**What people do:** Assuming the user runs `start.sh` from the install directory, so relative paths work.

**Why it's wrong:** Users symlink `start.sh` to `~/.local/bin/` and run it from anywhere (`/tmp`, home directory, etc.). Relative paths break.

**Do this instead:** Self-locate the script directory, `cd` to it before running, or use absolute paths resolved from the script location.

### Anti-Pattern 2: Hardcoding Data Path in Persistence

**What people do:** Using a hardcoded relative path like `Path("data")` in persistence code.

**Why it's wrong:** The existing `entrypoint.sh` already sets `DATA_DIR` env var, but `persistence.py` ignores it. This creates an invisible coupling between the shell script's `cd` and the Python module's behavior.

**Do this instead:** Read `DATA_DIR` from env var with fallback to `Path("data")`. This makes the behavior explicit and overridable.

### Anti-Pattern 3: Config File in Install Directory

**What people do:** Writing config.json inside the cloned repo directory.

**Why it's wrong:** A `git pull` update could overwrite user config. User edits to config are lost on reinstall.

**Do this instead:** Use XDG config path (`~/.config/mesh-status/config.json`). Config lives outside the install directory so it survives reinstalls.

### Anti-Pattern 4: Shell Script Doing Too Much

**What people do:** Putting complex logic (validation, networking, parsing) in the shell script.

**Why it's wrong:** Shell is fragile, hard to test, and error messages are cryptic. Complex logic belongs in Python.

**Do this instead:** Shell script handles: directory detection, config loading, env var export, exec. Python handles: validation, networking, complex config logic. The line between `start.sh` and `mesh_status/` is: shell = platform integration + exec; Python = everything else.

## Integration Points

### External Services

| Service | Integration | Notes |
|---------|-------------|-------|
| GitHub (repo clone) | `git clone` in install.sh | Shallow clone (`--depth 1`) minimizes download |
| **Existing Dockerfiles** | `CMD` can use start.sh or stay as-is | No migration needed; start.sh is additive |
| **Existing entrypoint.sh** | Unchanged | Docker-specific; start.sh is for bare-metal |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| `start.sh` → `mesh_status` module | Env vars + CLI args | The bridge pattern: shell sets env vars, Python reads them |
| `start.sh` → `config.json` | Shell reads with `jq` (if available) | Falls back to env-only if `jq` not present |
| `install.sh` → filesystem | Creates directories, clones repo | Non-interactive mode uses CLI flags instead of prompts |
| `deploy/install.sh` ↔ `start.sh` | Shared install directory convention | Both know about `MESH_STATUS_HOME` |

## Sources

- **Existing codebase**: Verified against `entrypoint.sh`, `Dockerfile.leader`, `Dockerfile.node`, `node.py`, `leader.py`, `persistence.py`, `config.py`, `compose.yml`
- **XDG Base Directory Specification**: `~/.config/`, `~/.local/share/`, `~/.local/bin/` — standard for Linux user-level installs
- **uv documentation**: `uv run` activates project venv automatically — used as primary runner mechanism; `uv sync --directory` for non-CWD projects
- **uv run patterns**: Projects like Homebrew, Rustup, Tailscale use curl|bash for initial install + a binary/script for daily use
- **jq ubiquity**: jq is the de-facto standard for JSON in shell scripts (pre-installed on Ubuntu, Debian, Fedora, RHEL, macOS)

---

*Architecture research for: mesh-status v0.8 install/start scripts*
*Researched: 2026-06-20*
