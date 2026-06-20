# Pitfalls Research

**Domain:** Adding curl-pipe-bash install scripts, start.sh runner, and interactive config to existing Python (Quart) application
**Researched:** 2026-06-20
**Confidence:** HIGH (research cross-referenced with official docs, real issue trackers, production post-mortems, and project-specific codebase analysis)

## Critical Pitfalls

### Pitfall 1: Missing `pipefail` in curl-pipe-bash Pipeline Causes Silent Install Failure

**What goes wrong:**
`curl -fsSL https://example.com/install.sh | bash` succeeds (exit 0) even when `curl` fails with an HTTP 403, 429, or transient network error. The user sees no error message — `bash` receives an empty or partial stdin, does nothing useful, and exits 0. The install "completes" silently, leaving the system in an inconsistent state with no installed software and no indication anything went wrong.

**Why it happens:**
In a bash pipe, the exit code is from the **last** command (`bash`), not the first (`curl`). Without `set -o pipefail`, the pipeline exits 0 as long as `bash` (receiving empty stdin) exits 0. This is exactly the bug that hit the `claude-code-action` installer (issue #1136) — curl 429 rate limit → empty pipe → bash exits 0 → GitHub Action reported "Claude Code installed successfully" → subsequent `which claude` failed. Three-attempt retry logic never triggered because every attempt silently succeeded.

**How to avoid:**
1. **Never use bare `curl ... | bash`** — always prepend `set -o pipefail`:
   ```bash
   set -o pipefail
   curl -fsSL https://github.com/user/repo/releases/latest/download/install.sh | bash
   ```
2. **Even better: download-then-execute** (decouples fetch errors from execution):
   ```bash
   curl -fsSL -o /tmp/mesh-install.sh https://github.com/user/repo/releases/latest/download/install.sh
   bash /tmp/mesh-install.sh
   rm -f /tmp/mesh-install.sh
   ```
3. **Post-install verification** — always verify the binary exists:
   ```bash
   command -v mesh-status || { echo "Install failed"; exit 1; }
   ```

**Warning signs:**
- CI logs show "Installation complete" but `which mesh-status` fails in subsequent steps
- Empty `/tmp/` download artifacts when debugging
- curl exit codes masked in CI pipeline output

**Phase to address:**
Phase 1 (`deploy/install.sh`) — the curl-pipe-bash line itself must be hardened at creation. Retrofitting pipefail is trivial but easy to forget.

---

### Pitfall 2: Interactive `read` Stdin Theft in Piped Install Script

**What goes wrong:**
When `install.sh` is invoked via `curl -fsSL ... | bash`, bash reads the script incrementally from stdin. Any interactive prompt (`read -p`, `gum input`, `select`) or child process that also reads stdin **steals bytes from the script stream**. This causes:
- Truncated function names: `warn_shell_path_missing_di` instead of `warn_shell_path_missing_dir`
- "command not found" errors from corrupted function names
- Indefinite hangs where bash blocks waiting for more script input
- Silent corruption of subsequent script lines

This is not theoretical — the OpenClaw project (PR #82918) documented this exact failure. Their pipe guard attempt was rejected as too risky (it broke `bash -c` invocation), but the underlying stdin-steal bug was confirmed real.

**Why it happens:**
Bash reads piped scripts lazily from stdin, not as an atomic read. When a `read` call in the script body consumes stdin, it eats bytes intended for the shell parser. The script stream and interactive input share the same file descriptor. This only affects `curl ... | bash` — direct execution (`bash install.sh`) and process substitution (`bash <(curl ...)`) are safe because `BASH_SOURCE[0]` is set.

**How to avoid:**
1. **Delay all interactive prompts until after the script body is fully parsed.** Structure the script: define all functions first, then call a `main` function at the very bottom. Parse errors from stolen stdin hit function bodies, not definitions.
2. **If interactive prompts are unavoidable, use `/dev/tty` for input**:
   ```bash
   read -p "Enter value: " value < /dev/tty
   ```
3. **Or buffer the script first** — download to file, then execute:
   ```bash
   curl -fsSL -o /tmp/install.sh https://.../install.sh
   bash /tmp/install.sh
   ```
   This bypasses the piped-stdin problem entirely.
4. **Detect piped execution and refuse** if interactive input is needed:
   ```bash
   if [[ -p /dev/stdin && ! -t 0 ]]; then
       echo "This installer needs interactive input. Download and run directly:"
       echo "  curl -fsSL -o install.sh https://.../install.sh && bash install.sh"
       exit 1
   fi
   ```

**Warning signs:**
- Install script produces "command not found" errors for internal function names
- User is prompted but input appears corrupted or causes hangs
- Works in CI/Docker (no TTY) but fails in interactive terminal

**Phase to address:**
Phase 2 (Config bootstrapping + `start.sh`) — interactive prompts are in the config setup, and must use `/dev/tty` if stdin is piped. Phase 1 should already structure `install.sh` with the `main`-function-at-bottom pattern.

---

### Pitfall 3: Shell Script Doesn't Use `set -euo pipefail` — Silent Failures Cascade

**What goes wrong:**
Without strict mode, a failed `mkdir`, `cd`, or `cp` in the install script silently continues. The script creates a broken installation — directories exist but are empty, permissions are wrong, files are missing. The user runs `start.sh` and gets a Python import error or file-not-found. They assume the software is buggy, not that the install was incomplete.

Specific disaster scenarios with defaults:
- **`set -u` missing**: `rm -rf "$INSTALL_DIR/"` with unset `$INSTALL_DIR` → `rm -rf /` (the space after the trailing slash is stripped)
- **`set -e` missing**: `cd /non/existent && rm -rf *` — cd fails silently, `rm -rf *` runs in **current working directory**
- **`pipefail` missing**: `curl https://broken.link | tar xz` — curl fails, empty tar stream extracts successfully, script continues

**How to avoid:**
1. **Every script entrypoint gets this immediately after the shebang**:
   ```bash
   #!/usr/bin/env bash
   set -euo pipefail
   IFS=$'\n\t'
   ```
2. **But understand the caveats** (see Greg's Wiki BashFAQ/105):
   - `set -e` does NOT trigger inside `if`, `while`, `&&`, `||`, or `!`
   - `set -e` does NOT propagate from functions called in those contexts
   - For critical operations (rm, mv, critical cp), check return codes **explicitly**
   - `head` in a pipeline with `pipefail` causes false-positive SIGPIPE failures; guard with `|| true`
3. **Use `${VAR:-fallback}` for optional variables** to avoid `set -u` aborting on intentionally-unset vars
4. **Add a trap for debug output** so silent failures leave evidence:
   ```bash
   trap 'echo "ERROR at line $LINENO (exit code $?)"' ERR
   ```

**Warning signs:**
- Install "succeeds" but `start.sh` immediately fails with missing files
- Random directories created in the CWD when cd fails
- CI install step passes but subsequent verification fails

**Phase to address:**
Phase 1 (`deploy/install.sh`) and Phase 2 (`start.sh`, config setup) — every shell script entrypoint must have strict mode from the first commit.

---

### Pitfall 4: Orphaned Processes When Script Is Killed (No Signal Propagation)

**What goes wrong:**
When `start.sh` launches the Python backend and Hypercorn as background processes (`&`), a SIGTERM or SIGINT to `start.sh` kills the script but NOT the child processes. The Python processes become orphans, re-parented to init, and continue running. The user:
1. Runs `start.sh --leader` again → port 58080 is still in use → "Address already in use" error
2. Kills `start.sh` with Ctrl+C → terminal returns but process continues running on port 58080
3. Starts a new `start.sh` → finds no PID file → launches another instance → port conflict → silent failure

This is a **process group** problem, documented extensively in Unix StackExchange (#806014). The default behavior: killing a script via `kill -TERM $script_pid` kills only the script process, not its children. Only Ctrl+C in an interactive shell propagates properly because the kernel sends the signal to the process group.

**Why it happens:**
Bash does not set process group IDs for background jobs by default (`set -m` must be enabled). When the parent script dies, orphaned child processes are adopted by init. No trap or cleanup handler fires because the parent never set up signal propagation. The `entrypoint.sh` already uses `set -e` but has no process group management.

**How to avoid:**
1. **Always set a trap in `start.sh`** to propagate signals to children:
   ```bash
   #!/usr/bin/env bash
   set -euo pipefail
   
   _cleanup() {
       echo "Shutting down..."
       # Kill all children in the process group (negative PID = PGID)
       kill -- -$(ps -o pgid= -p $$ | tr -d ' ') 2>/dev/null || true
       wait
   }
   trap _cleanup EXIT SIGTERM SIGINT SIGHUP
   ```
2. **Enable job control** (`set -m`) to create proper process groups for background jobs
3. **PID file as fallback** — write the main process PID to a known location, read it on restart:
   ```bash
   PIDFILE="${MESH_STATUS_HOME:-$HOME/.mesh-status}/leader.pid"
   echo $$ > "$PIDFILE"
   # On cleanup:
   rm -f "$PIDFILE"
   ```
4. **Port-liveness pre-check** before starting to detect orphaned processes:
   ```bash
   if lsof -i :58080 >/dev/null 2>&1; then
       echo "Port 58080 is already in use. Is mesh-status already running?"
       exit 1
   fi
   ```

**Warning signs:**
- "Address already in use" when re-running `start.sh`
- `ps aux | grep hypercorn` shows multiple processes
- Port stays occupied after expected shutdown

**Phase to address:**
Phase 2 (`start.sh` runner) — signal propagation and cleanup must be designed into the startup script, not added after orphan processes cause port conflicts.

---

### Pitfall 5: Partial or Interleaved Config File Writes from Concurrent Starts

**What goes wrong:**
`start.sh --leader` runs interactive config setup that writes config to a file. Two scenarios:
1. **Concurrent launches**: User runs two `start.sh` in parallel → both write to the same config file → interleaved writes → corrupted YAML/JSON → Python parse error on startup
2. **Crash during write**: User Ctrl+C's during config write → truncated config file → on next start, `start.sh` sees existing config → skips interactive setup → Python fails to parse truncated file → user is stuck with no way to reconfigure

**Why it happens:**
Writing config files with raw `echo` or `cat > file << EOF` is not atomic. There's no write-lock mechanism. The config "exists" check (`[ -f config.json ]`) doesn't verify the file is well-formed. Once a truncated file exists, the skip-logic prevents regeneration.

**How to avoid:**
1. **Use atomic write pattern for config files**:
   ```bash
   cat > /tmp/config.tmp << EOF
   {...}
   EOF
   mv /tmp/config.tmp "$CONFIG_FILE"  # atomic on same filesystem
   ```
2. **Validate config after writing** before marking config as complete:
   ```bash
   if python3 -c "import json; json.load(open('${CONFIG_FILE}'))" 2>/dev/null; then
       echo "Config valid."
   else
       echo "Config invalid — re-running setup..."
       rm -f "$CONFIG_FILE"
       # re-run interactive setup
   fi
   ```
3. **Use a file lock for write exclusion** (`flock`) to prevent concurrent writes
4. **Interactive + non-interactive mode flag confusion guard** — if `--non-interactive` is passed, config MUST be provided via env/CLI flags. If neither env/CLI nor existing config is available, exit with clear instructions instead of silently generating partial config.

**Warning signs:**
- `start.sh` fails with JSON/YAML parse errors at startup
- Config file exists but is smaller than expected
- Two users report the same config corruption after parallel operation

**Phase to address:**
Phase 2 (Config bootstrapping in `start.sh`) — atomic writes and validation must be designed in from the start. Retrofitting after users have corrupted configs is painful.

---

### Pitfall 6: Docker CI Tests Use Cached Images, Miss Install Flow Bugs

**What goes wrong:**
The CI test for install.sh uses a pre-built Docker image that already has Python, git, and dependencies installed. The install script passes in CI because all prereqs are present. But on a fresh Ubuntu VM, the user doesn't have `uv` and the install script's `curl ... | sh` for uv silently fails (pipefail not set — see Pitfall 1). The test never caught this because the Docker base image had uv cached in a previous layer.

This exact pattern killed the worthless project's CI install tests (see GitHub Actions workflow `install-docker.yml`) — they had to force `DOCKER_BUILDKIT=1` and use `--no-cache` to get reliable install flow tests.

**Why it happens:**
Docker build layer caching is aggressive. If `apt-get`, `uv install`, or `git clone` happen in cached layers, they're not re-executed. The install script's error handling is never actually exercised. The test passes, but the install script is broken.

**How to avoid:**
1. **Use a minimal base image** for CI install tests — `scratch` or `alpine` with just `bash` and `curl`. Force every dependency to be installed via the script itself.
2. **Explicitly disable Docker layer cache** in CI install test jobs:
   ```yaml
   - name: Build test image
     run: docker build --no-cache -t mesh-install-test .
   ```
3. **Use `docker pull python:3.12-slim` fresh each time** (no local cache) as the starting image, then run the install.sh inside it
4. **Test against the actual user experience** — start from a container that matches the user's environment:
   - Ubuntu 22.04 / 24.04 (most likely target)
   - No `uv` pre-installed
   - No `git` pre-installed
   - Verify prereq-check logic actually fires
5. **Test from scratch in ephemeral containers** as separate CI jobs, not as a build step in the main image pipeline

**Warning signs:**
- Install tests pass in CI but fail when run on a fresh VM
- CI test image has dependencies that the script claims to install
- "Already installed" messages dominate CI log instead of "Installing X"

**Phase to address:**
Phase 3 (Docker CI test) — the CI test design must explicitly account for cache busting. This is the phase that validates Phases 1 and 2, so it must be rigorous.

---

### Pitfall 7: Hardcoded Version / Git SHA in Install Script Causes Version Mismatch

**What goes wrong:**
The install script clones a specific git tag or branch. Three weeks later, the same `curl ... | bash` installs a different version than the user expects. Or the install script was updated but the application code wasn't — the script references features that don't exist in the installed version.

Specific failure:
- `install.sh` installs from `main` branch → later `main` has breaking API changes → old `start.sh` doesn't work with new Python code
- Or: `install.sh` pins to tag `v0.8.0` → user installs → reads docs about features in `v0.8.1` → `start.sh` references flags that don't exist
- Or: the user already has mesh-status installed (from apt/pip) and runs `start.sh` → `start.sh` from PATH is older version → launches newer Python code from git clone → interface mismatch

**Why it happens:**
The install script and the application code have independent versioning. The script is distributed via curl URL; the code is distributed via `git clone` or pip. They can drift. The existing `pyproject.toml` declares version `0.1.0` but the actual code has evolved significantly.

**How to avoid:**
1. **Version lock-step**: The install script URL should include the version tag:
   ```
   curl -fsSL https://github.com/user/repo/releases/download/v0.8.0/install.sh | bash
   ```
   The script then checks out that same tag: `git checkout v0.8.0`
2. **Self-version check**: At the top of `install.sh`, define `INSTALLER_VERSION` and verify against the repo:
   ```bash
   SCRIPT_VERSION="0.8.0"
   REPO_VERSION=$(curl -fsSL https://api.github.com/repos/user/repo/releases/latest | ...)
   # Warn if mismatch
   ```
3. **`start.sh` checks Python package version** against its own version:
   ```bash
   INSTALLED_VER=$(python3 -c "import mesh_status; print(mesh_status.__version__)" 2>/dev/null || echo "unknown")
   EXPECTED_VER="0.8.0"
   if [ "$INSTALLED_VER" != "$EXPECTED_VER" ]; then
       echo "Warning: installed version ($INSTALLED_VER) != expected ($EXPECTED_VER)"
   fi
   ```
4. **Keep `pyproject.toml` version current** — bump on every release. Currently at `0.1.0` but code is v0.8 milestone. This discrepancy will cause confusion.

**Warning signs:**
- `start.sh --leader` throws errors about missing functions/classes
- Install script was updated but old users get stale behavior
- Docs describe flag `--foo` but `start.sh --foo` says "unrecognized argument"

**Phase to address:**
Phase 1 (install.sh) — the version pinning strategy must be designed upfront. Version drift between installer and application is a "fix it later" trap that rarely gets fixed.

---

### Pitfall 8: Prerequisite Checks Not Done First — Destructive Operations Before Validation

**What goes wrong:**
The install script starts cloning the repo or creating directories before checking that `uv` and `git` are available. The clone partially succeeds, then the script fails because `uv` isn't installed. The user is left with a half-populated directory. On retry, the script sees the directory exists and skips creation, but files are missing from the partial clone. The install is permanently broken — `git pull` in the partial directory also fails.

Specific pattern from the existing project:
- `install.sh` needs `uv` and `git`
- If `git` is not installed → `git clone` fails → script continues (no `set -e`) → creates broken directory
- If `uv` is not installed → `uv sync` fails → script errors after already modifying filesystem

**How to avoid:**
1. **Prerequisite check block at the very top of the script**, before any filesystem operations:
   ```bash
   REQS=(git curl python3 uv)
   MISSING=()
   for cmd in "${REQS[@]}"; do
       if ! command -v "$cmd" &>/dev/null; then
           MISSING+=("$cmd")
       fi
   done
   if [ ${#MISSING[@]} -gt 0 ]; then
       echo "Missing prerequisites: ${MISSING[*]}"
       echo "Install them and re-run this installer."
       exit 1
   fi
   ```
2. **Idempotent directory creation** — check `[ -d "$DIR" ] && [ -f "$DIR/sentinel.file" ]` before assuming previous install succeeded:
   ```bash
   if [ -d "$INSTALL_DIR" ]; then
       if [ ! -f "$INSTALL_DIR/.mesh-installed" ]; then
           echo "Directory exists but appears to be incomplete. Removing..."
           rm -rf "$INSTALL_DIR"
       fi
   fi
   ```
3. **Use a sentinel file** (`.mesh-installed`) written as the **last** step of install, indicating completion
4. **Never clone into an existing non-empty directory** — always start fresh or verify

**Warning signs:**
- Install fails midway but directory exists on retry
- `uv sync` fails with "missing pyproject.toml" even though directory exists
- User reports "I ran the install script twice and it works the second time"

**Phase to address:**
Phase 1 (install.sh) — prerequisite validation before destructive operations is a structural choice, not a polish detail.

---

### Pitfall 9: macOS vs Linux Shell Incompatibilities

**What goes wrong:**
The install script works perfectly on Ubuntu but fails on macOS with:
- `sed -i` requires different syntax (`sed -i ''` on BSD, `sed -i` on GNU)
- `readlink -f` doesn't exist on macOS (use `realpath` or `greadlink` from coreutils)
- `lsof` requires different flags to check port usage (`sudo lsof -i :58080` vs standard)
- `ping` has different flags (macOS uses `-c 1 -t 5`, Linux uses `-c 1 -W 5`)
- `/tmp` cleanup behavior varies (macOS clears `/tmp` on reboot, not guaranteed on Linux)
- `python3` vs `python` naming — macOS may alias python3 or require full path

The existing node.py already handles `ping` via `asyncio.create_subprocess_exec` with Linux-style args. The install/start scripts need similar care.

**Why it happens:**
Developers primarily test on one platform (Linux) and assume POSIX compatibility. BSD userland (macOS) deviates from GNU userland (Linux) in subtle but breaking ways. Shell scripts are particularly vulnerable because they invoke system utilities directly.

**How to avoid:**
1. **Use POSIX-specified utilities** where possible — avoid GNU extensions
2. **Abstract platform-specific commands into functions** at the top of the script:
   ```bash
   get_script_dir() {
       # Works on both macOS (realpath from coreutils) and Linux
       if command -v realpath &>/dev/null; then
           dirname "$(realpath "$0")"
       elif command -v greadlink &>/dev/null; then
           dirname "$(greadlink -f "$0")"
       else
           # Fallback that works for simple cases
           cd "$(dirname "$0")" && pwd
       fi
   }
   ```
3. **Use `uname -s` to branch** when needed:
   ```bash
   case "$(uname -s)" in
       Darwin*)
           PING_ARGS="-c 1 -t 5"
           ;;
       Linux*)
           PING_ARGS="-c 1 -W 5"
           ;;
       *)
           echo "Unsupported OS: $(uname -s)"
           exit 1
           ;;
   esac
   ```
4. **Test on both platforms** in CI — matrix across `ubuntu-latest` and `macos-latest`

**Warning signs:**
- Install works on dev's Ubuntu machine but fails on team member's MacBook
- "Illegal option" errors from `sed`, `readlink`, or other utilities
- CI passes but users report failures

**Phase to address:**
Phase 1 (install.sh) and Phase 2 (start.sh) — cross-platform awareness must be built in from the first line. Retrofitting platform detection is tedious.

---

### Pitfall 10: Upgrade/Downgrade Path Not Tested — Fresh Install Only

**What goes wrong:**
The `install.sh` works perfectly for a fresh install. But when a user who installed v0.7 runs the v0.8 install script:
1. The script clones over the existing directory → old config is preserved (good) or overwritten (bad) unpredictably
2. `uv sync` might downgrade packages → v0.8 requires `quart>=0.21.0` but v0.7 pinned `quart>=0.20.0` → conflict
3. Old data files in `/app/data` are incompatible with new format → leader crashes on startup
4. `start.sh` has new flags → old user's muscle memory or automation breaks

**Why it happens:**
Install scripts are almost exclusively tested on clean systems. The upgrade path is an afterthought because developers test in disposable environments. The existing project's Docker files already do clean installs every build — there's no upgrade scenario tested.

**How to avoid:**
1. **Version detection before install**:
   ```bash
   if [ -f "$INSTALL_DIR/mesh_status/__init__.py" ]; then
       OLD_VER=$(python3 -c "import sys; sys.path.insert(0,'$INSTALL_DIR'); import mesh_status; print(getattr(mesh_status, '__version__', 'unknown'))" 2>/dev/null || echo "unknown")
       echo "Existing installation detected: $OLD_VER"
       echo "Upgrading to $NEW_VER..."
   fi
   ```
2. **Backup config before upgrade**:
   ```bash
   if [ -f "$INSTALL_DIR/config.json" ]; then
       cp "$INSTALL_DIR/config.json" "$INSTALL_DIR/config.json.bak.$(date +%Y%m%d%H%M%S)"
   fi
   ```
3. **Run `uv sync` with upgrade strategy** — not just `uv sync` but `uv sync --upgrade` to respect new dependency ranges
4. **Data migration guard** — if data format changed, detect old format and either migrate or refuse:
   ```bash
   if [ -f "$DATA_DIR/checks.json" ]; then
       FIRST_LINE=$(head -1 "$DATA_DIR/checks.json")
       if echo "$FIRST_LINE" | python3 -c "import json,sys; d=json.load(sys.stdin); assert 'version' in d" 2>/dev/null; then
           : # new format, ok
       else
           echo "Old data format detected. Starting fresh..."
           mv "$DATA_DIR" "${DATA_DIR}.bak.$(date +%Y%m%d%H%M%S)"
       fi
   fi
   ```
5. **Document breaking changes** in a `RELEASE_NOTES.md` that `start.sh` can display on first run after upgrade

**Warning signs:**
- Upgrade "succeeds" but leader crashes with format errors
- Users report "it worked before upgrading"
- Only fresh-install scenarios tested in CI

**Phase to address:**
Phase 2 (start.sh) — upgrade detection logic belongs in the runner. Phase 1 (install.sh) should handle the backup. Phase 3 (Docker CI) must include an upgrade-from-previous test case.

---

### Pitfall 11: Hardcoded Paths That Break in Non-Default Environments

**What goes wrong:**
The install script hardcodes paths like `/opt/mesh-status` or `~/mesh-status` and the user has no control to change them. When:
- User doesn't have sudo access → can't write to `/opt/`
- User wants to install it in their home directory → forced to edit the script
- User runs multiple instances → path collision
- System uses a different home directory structure (NixOS, macOS)

**Why it happens:**
It's convenient to hardcode paths. The installer doesn't expose `--prefix` or `--install-dir` flags. The existing Docker build hardcodes `/app` but that's fine because Docker is a controlled environment. Non-Docker install needs flexibility.

**How to avoid:**
1. **Make install directory configurable** — `INSTALL_DIR="${1:-$HOME/.mesh-status}"`
2. **Use XDG Base Directory spec** for config and data:
   ```bash
   INSTALL_DIR="${MESH_STATUS_HOME:-$HOME/.local/share/mesh-status}"
   CONFIG_DIR="${MESH_STATUS_CONFIG:-$XDG_CONFIG_HOME/mesh-status}"
   DATA_DIR="${MESH_STATUS_DATA:-$XDG_DATA_HOME/mesh-status}"
   ```
3. **`start.sh` discovers its own location** rather than using hardcoded paths:
   ```bash
   SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
   PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
   ```
4. **Default should work without `sudo`** — install to user home by default, `--system` flag for system-wide

**Warning signs:**
- "Permission denied" on install
- Users ask "how do I change where it's installed?"
- Install script needs `sudo` for default operation

**Phase to address:**
Phase 1 (install.sh) — path configurability is a structural API decision, hard to change later.

---

### Pitfall 12: No Graceful Degradation for Missing `uv` or Corrupted Virtual Environment

**What goes wrong:**
The existing project relies on `uv` for dependency management. If `uv` is installed but the virtual environment (`/app/.venv`) is corrupted, missing, or has wrong Python version:
- `uv sync` fails with cryptic errors about "conflicting dependencies"
- `start.sh` tries to run `uv run python ...` but `.venv` doesn't exist → uv auto-creates it → but with wrong interpreter
- Or: system Python is 3.11 (not 3.12+) → `uv sync` creates env with 3.11 → some async features fail at runtime

The existing `Dockerfile.leader` already has a pattern for this (using `--no-dev`), but the non-Docker install script needs similar care.

**How to avoid:**
1. **Python version check before `uv sync`**:
   ```bash
   PYTHON_VERSION=$(python3 --version 2>&1 | grep -oP '\d+\.\d+')
   REQUIRED="3.12"
   if [ "$(echo "$PYTHON_VERSION >= $REQUIRED" | bc)" != "1" ]; then
       echo "Python $REQUIRED+ required, found $PYTHON_VERSION"
       exit 1
   fi
   ```
2. **Validate `.venv` before use** — check sentinel file created by `uv sync`:
   ```bash
   if [ -f "$INSTALL_DIR/.venv/pyvenv.cfg" ]; then
       VENV_PYTHON=$(head -1 "$INSTALL_DIR/.venv/pyvenv.cfg")
       # Verify matches expected
   fi
   ```
3. **`start.sh` should recreate `.venv` if `uv sync` fails** rather than using a broken env:
   ```bash
   cd "$PROJECT_ROOT"
   if ! uv sync --no-dev --frozen 2>/dev/null; then
       echo "Dependency sync failed. Recreating environment..."
       rm -rf .venv
       uv sync --no-dev
   fi
   ```
4. **Use `uv run` consistently** (not raw `python3`) so uv handles env activation automatically

**Warning signs:**
- `ModuleNotFoundError` on startup despite successful install
- `start.sh` runs system Python instead of venv Python
- `uv sync` succeeds but `uv run` fails with "script not found in venv"

**Phase to address:**
Phase 1 (install.sh) and Phase 2 (start.sh) — uv/venv validation must be in both install (initial setup) and start (runtime validation).

---

### Pitfall 13: Logging Configuration Collision Between `start.sh` and Python Backend

**What goes wrong:**
The current `mesh_status/config.py` reads `MESH_STATUS_LOG_LEVEL` and the Python code configures logging at startup. The `start.sh` runner also writes to stdout/stderr. When the user runs:
```bash
start.sh --leader 2>&1 | tee -a /var/log/mesh-status.log
```
- Both shell output and Python logs go to the same stream
- Shell output (INFO lines, startup messages, timestamps) and Python JSON logs mix
- If start.sh redirects stderr (e.g., `2>/dev/null`), Python errors disappear because Hypercorn inherits start.sh's stderr
- If start.sh daemonizes, all logging disappears entirely

**Why it happens:**
Shell scripts and Python processes share the same stdout/stderr by default. The `start.sh` runner is a thin wrapper that inherits the terminal's file descriptors and passes them to the child process. Without explicit log separation, mixing is inevitable.

**How to avoid:**
1. **`start.sh` does minimal logging itself** — let the Python process handle all structured logging
2. **Use `exec` to replace the shell process** with the Python process so there's no wrapper process at all:
   ```bash
   exec uv run python -m mesh_status.leader "$@"
   ```
   This way, all signals go directly to Python, there's no orphan risk, and log streams are clean.
3. **If startup logging is needed, use a dedicated log file**:
   ```bash
   exec uv run python -m mesh_status.leader "$@" >> "$LOG_FILE" 2>&1
   ```
4. **Apply consistent formatting** — if start.sh outputs startup info, match the Python log format (timestamp, level, message)
5. **Document the log destination** — users should know where to find logs without guessing

**Warning signs:**
- Mixed shell and Python output in logs
- /dev/null applied by user breaks Python logging silently
- "start.sh: line X: ..." messages mixed with asctime-format Python logs

**Phase to address:**
Phase 2 (start.sh) — the logging architecture (shell wrapper vs exec replacement) is a design decision for the runner.

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Skip `set -euo pipefail` | Faster script writing | Silent failures, rm -rf / disasters, untrusted CI | Never. Add it from line 1. |
| Hardcode install path | Simpler code, fewer flags | Users can't customize, sudo required, conflicts | First commit prototyping only; fix before tagging |
| Pin to `main` branch in install.sh | Always get latest | Breaking changes surprise users, version drift | Never for production. Use tags/releases. |
| Single-script monolithic install.sh | One file to distribute | Hard to test, review, or maintain | Acceptable for v0.8 MVP — but extract shared libs before v1.0 |
| No pidfile / process tracking | Simpler start.sh | Orphans after kill, port conflicts, can't stop | Acceptable only if `exec` is used (no wrapper process), otherwise never |
| Test install only in pre-built Docker | Fast CI, simple setup | Misses prereq failures, cached dependency bugs, real user conditions | Never for CI — test in fresh-from-scratch containers too |
| Ignore upgrade path | Ship faster, test less | Stuck users on old versions, data format incompatibility | Acceptable for v0.8 alpha only; must be addressed before v1.0 |
| No sentinel file for install completion | One fewer file to manage | Can't distinguish "never installed" from "broken install" | Acceptable short-term if `set -e` + atomic operations are used; add sentinel before v1.0 |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| `curl ... | bash` pipeline to `git clone` | Script clones into CWD, polishes installer output with no regards to where user ran the command | Always cd to a known absolute path (`INSTALL_DIR`) before git ops; never assume CWD |
| `uv sync` in install.sh | Running `uv sync` in the cloned directory without creating a `.venv` first, or running it as root | Let `uv` create `.venv` automatically; run as non-root when possible; use `--no-dev` for production installs |
| `start.sh` with `exec` vs `&` | Using `&` (background) then waiting — complex process management, signal handling fragile | Use `exec` to replace shell with Python process — simpler, reliable signal propagation, no orphans |
| `start.sh` env vars with existing `config.py` | Hardcoding env vars in start.sh that differ from the existing `MESH_STATUS_*` convention | Reuse existing `MESH_STATUS_INTERVAL`, `MESH_STATUS_LOG_LEVEL` env vars from `config.py`. Don't introduce a parallel config system. |
| Docker CI test with GitHub Actions socket | Mounting `/var/run/docker.sock` without proper group permissions, especially on Ubuntu 22.04+ | Ensure runner user is in `docker` group, check `_work` directory ownership, use `DOCKER_BUILDKIT=1` |
| Config bootstrapping with existing `mesh_status/config.py` | Creating a new config file (config.yaml) alongside the existing Python-based `config.py` that reads env vars | Don't create parallel config systems. Either use env vars (existing pattern) or generate a `.env` file that `config.py` reads. |
| `pip` vs `uv` | `start.sh` falls back to `pip install` if `uv` not found, but `uv` creates different `.venv` layouts | Have one package manager. The project chose `uv`. Don't add `pip` as a fallback — if `uv` is missing, fail with clear instructions. |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| `start.sh` uses `&` + `wait` for process management | Orphaned hypercorn processes, "port in use" on restart, leak over time | Use `exec` instead of backgrounding, or use a PID file with signal trap | First time user kills start.sh with SIGTERM (not Ctrl+C) |
| Interactive config prompt in piped install | "command not found" for function names, corrupted input, hangs | Structure script with main-at-bottom; use `/dev/tty` for prompts; or download-then-execute | First time user runs `curl ... | bash` interactively |
| `curl | bash` without post-install verification | Silent install failure, user thinks it worked, subsequent commands fail | Add `command -v mesh-status \|\| exit 1` after install | First time curl gets a 429 or network blips |
| `.venv` recreated on every `start.sh` run | 10-30 second startup delay while `uv sync` downloads packages | Cache `.venv` across runs; only re-sync if `pyproject.toml` changed; use `--frozen` for speed | Every non-cached startup |
| Config file re-read on every start.sh invocation | Slow startup if config file is large | Config is tiny; not a real perf concern for this project |
| `lsof -i :58080` port check on every start | ~100ms check; fine for this scale | N/A for this project scale | Never a real concern at <100 nodes |

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| `curl ... | sudo bash` | Full root access to remote script without verification; MITM can deliver malicious payload | Never include `sudo` in the one-liner. Install to user space by default. If system install is needed, download, review, then execute. |
| Unsafe PID file in world-writable directory | Unprivileged user writes malicious PID → root kills wrong process when stopping | Always use `$PIDFILE` in a root-owned directory when running as root, or use `exec` instead of PID files entirely |
| Insecure temporary files (`/tmp/install.sh`) | Another user on shared system can replace the script between download and execution (TOCTOU) | Download to a random temp name (`mktemp`), verify checksum, keep 0700 perms |
| Cloning repo via `git clone` over HTTP not HTTPS | Man-in-the-middle replaces repository content | Always use `https://` URLs for `git clone` |
| Script stores config with secrets in world-readable file | API keys, tokens, or credentials exposed to other users on the system | `chmod 600` on config files; set `umask 077` before creating them |
| Shell injection via user-supplied config values | User enters `$(rm -rf /)` as a config value → shell evaluates it | Validate/escape user input before using in shell context; use Python for config validation, not shell |

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Install script outputs a wall of `git clone` and `uv sync` logs | User can't tell if install succeeded or what's happening | Use `set -x` for debug only; print clear progress messages: `[1/4] Checking prerequisites... ✓`, `[2/4] Cloning repository... ✓` |
| No progress indication during long operations | User thinks the script hung | Print progress dots or "This may take a minute..." for network operations |
| Interactive prompts don't explain what they're asking for | User guesses at config values, gets it wrong | Show default values clearly: `Leader port [58080]:` — show defaults in brackets, accept enter for defaults |
| `--non-interactive` flag that still prompts | CI pipeline hangs waiting for input that never comes | `--non-interactive` must be strict: if required config is missing, exit with error listing what's needed (env vars or flags) |
| Install succeeds but PATH not updated | User runs `mesh-status` command → "command not found" immediately after install | Print post-install instructions: `Add to your PATH: export PATH="$PATH:$HOME/.mesh-status/bin"` or offer `--add-to-path` flag |
| Config error messages are Python tracebacks | User sees the `Quart` framework internals instead of a helpful message | Wrap Python execution; capture stderr; show user-friendly errors. Or don't wrap — let the Python process own its stderr output (consistent format) |
| `start.sh` fails silently if another instance is running | User runs `start.sh --leader` a second time and sees no change, assumes first one crashed | Detect port conflict, print "mesh-status is already running (PID: 12345). Use start.sh --stop or kill 12345" |

## "Looks Done But Isn't" Checklist

- [ ] **install.sh**: Has `set -euo pipefail` at the top? Or uses download-then-execute to avoid pipe issues entirely?
- [ ] **install.sh**: Checks prerequisites (`git`, `uv`, `python3.12+`) before any filesystem operations?
- [ ] **install.sh**: Uses atomic writes (temp file + `mv`) for all file creation? Never writes directly to target path.
- [ ] **install.sh**: Creates a sentinel file (`.mesh-installed`) as the absolute last step so broken installs are detectable?
- [ ] **install.sh**: Has upgrade/backup logic if install directory already exists?
- [ ] **start.sh**: Handles `SIGTERM`/`SIGINT` to kill child processes (or uses `exec` to avoid needing to)?
- [ ] **start.sh**: Has a `--stop` or `stop.sh` companion that can cleanly shut down the process?
- [ ] **start.sh**: Validates that `.venv` exists and `uv sync` ran successfully before starting Python?
- [ ] **start.sh --non-interactive**: Truly non-interactive? Will it fail with a clear error instead of hanging on a prompt?
- [ ] **Config bootstrapping**: Writes atomically? Validates format after write? Has `flock`-based concurrency guard?
- [ ] **Cross-platform**: Tested on macOS? Handles `sed`, `readlink`, `ping` flags, `python3` binary differences?
- [ ] **Docker CI test**: Starts from a fresh `python:3.12-slim` with no cached dependencies? Tests the actual install flow?
- [ ] **Docker CI test**: Tests upgrade scenario (install old version, then install new)?
- [ ] **All scripts**: Pass `shellcheck` with zero warnings?
- [ ] **Version**: `pyproject.toml` version matches the install script's expected version?
- [ ] **Failure messages**: All error messages tell the user what to do next, not just why it failed?

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Silent install failure (missing pipefail) | LOW | Rerun with `curl -fsSL -o /tmp/install.sh ... && bash /tmp/install.sh` to decouple download from execution |
| Orphaned process on port 58080 | LOW | `lsof -ti :58080 \| xargs kill` to find and kill the orphan |
| Corrupted config file | LOW | `rm ~/.config/mesh-status/config.json && start.sh --leader` to regenerate config interactively |
| Broken .venv after upgrade | MEDIUM | `rm -rf .venv && uv sync --no-dev` to recreate from scratch |
| Partial install directory | MEDIUM | `rm -rf ~/.mesh-status && re-run install.sh` — sentinel file check would detect this automatically |
| Data format incompatibility after upgrade | MEDIUM | Downgrade script: `git checkout v0.7 && uv sync --no-dev` — or restore from backup in `data.bak.*` |
| Shell injection via config value | HIGH | Purge config, revoke any leaked secrets, reinstall from trusted source |
| Compromised install script (MITM) | HIGH | Verify script checksum against published SHA-256, compare with known-good copy from GitHub releases |

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| #1 Missing pipefail | Phase 1 (install.sh curl line) | `shellcheck` on install.sh; test with mock curl 429 response |
| #2 Stdin theft in piped install | Phase 2 (interactive prompts use /dev/tty) | Run `curl .../install.sh \| bash` interactively with prompts; no corruption or hangs |
| #3 No set -euo pipefail | Phase 1 (all script entrypoints) | `shellcheck` passes with zero warnings; `grep 'set -euo pipefail' *.sh` |
| #4 Orphaned processes | Phase 2 (start.sh signal trap or exec) | Kill start.sh with SIGTERM, verify no hypercorn processes remain; `ps aux | grep -c hypercorn` |
| #5 Partial config writes | Phase 2 (atomic write + validation) | Crash test: `kill -9` during config write; on restart, config is recreated not loaded partially |
| #6 Docker CI cache masking bugs | Phase 3 (--no-cache, fresh base images) | Verify CI uses `--no-cache`; test with container that has no uv/git preinstalled |
| #7 Version drift | Phase 1 (install from tag) + Phase 2 (version check) | Verify install.sh checks out specific tag; start.sh verifies `pyproject.toml` version matches |
| #8 Prereqs checked after destructive ops | Phase 1 (prereq block first) | Ordering test: `mock` missing uv, verify script exits before creating any directories |
| #9 macOS vs Linux | Phase 1 (install.sh) + Phase 2 (start.sh) | CI matrix on ubuntu-latest + macos-latest |
| #10 Upgrade path not tested | Phase 2 (backup logic) + Phase 3 (CI upgrade test) | CI test: install v0.7, install v0.8, verify config preserved, app starts |
| #11 Hardcoded paths | Phase 1 (configurable INSTALL_DIR) | Verify `MESH_STATUS_HOME` env var overrides default; verify XDG compliance |
| #12 Missing uv/venv validation | Phase 1 (install validation) + Phase 2 (start.sh env check) | Remove `.venv`, run `start.sh`, verify it recreates env, not crashes |
| #13 Logging collision | Phase 2 (exec vs background decision) | Verify Python logs and shell logs are distinguishable; verify `exec` pattern works |

## Sources

- **actsense.dev** — GitHub Actions Security Auditor: "curl | bash is unsafe because it bypasses review and integrity checks" (Accessed 2026-04-23)
- **claude-code-action issue #1136** — Silent install failure on curl 429 due to missing pipefail (2026-04-01)
- **OpenClaw PR #82918** — Pipe guard for stdin stealing prevention in install.sh (2026-05-17)
- **Unix StackExchange #806014** — Killing bash script leaves orphan processes; set -m and process group signals (2026-05-16)
- **Greg's Wiki BashFAQ/105** — `set -e` edge cases: what it does and doesn't catch
- **Greg's Wiki ProcessManagement** — PID file risks, race conditions, and proper process management
- **Wooledge Quotes** — Quoting rules for shell scripts: "When in doubt, double-quote every expansion"
- **worthless project** — .github/workflows/install-docker.yml: Docker CI patterns for install testing with --no-cache, DOCKER_BUILDKIT=1
- **The PipePunisher attack** (SNAKE Security) — Server-side detection of curl|bash via timing; delivers different content to shell vs browser
- **start-stop-daemon(8)** — Debian manpage: PID file security, background flag, process matching
- **mesh-status codebase analysis** — entrypoint.sh (no trap, no signal propagation), Dockerfile.leader/node (uv install pattern, user/gid configuration), config.py (MESH_STATUS_* env var pattern), pyproject.toml (version 0.1.0 vs actual code maturity)
- **"Why My One-Line Installer Worked Everywhere Except WSL"** (Vineeth N K, 2026-05-15) — CRLF stripping, curl.exe vs curl on Windows, .gitattributes for line endings
- **Bash Strict Mode Guide** (linuxize.com, 2026-04-20) — `set -euo pipefail` + IFS explained with examples
- **"set -euo pipefail Is Not Enough"** (unixy.io, 2024-06-05) — The 40% of failure cases that strict mode misses; ERR trap for debug output

---
*Pitfalls research for: mesh-status v0.8 install.sh, start.sh, and Docker CI testing*
*Researched: 2026-06-20*
