---
wave: 1
id: 19-plan-01-start-sh
objective: Create start.sh runner and fix persistence.py DATA_DIR
depends_on: []
files_modified:
  - start.sh
  - mesh_status/persistence.py
requirements_addressed:
  - START-01
  - START-02
  - START-03
  - START-04
  - START-05
  - START-06
  - START-07
  - START-08
  - CONF-02
  - CONF-04
  - FIX-05
autonomous: true
must_haves:
  truths:
    - "start.sh --leader starts the leader on port 58080 with PID tracking and logs"
    - "start.sh --node starts the node agent with PID tracking and logs"
    - "SIGTERM/SIGINT gracefully shuts down the process"
    - "Config wizard prompts interactively when no CLI flags are given"
    - "CLI flags skip the wizard (implied non-interactive mode)"
    - "start.sh --uninstall removes the install directory"
    - "persistence.py respects DATA_DIR env var"
  artifacts:
    - path: "start.sh"
      provides: "Unified runner for leader and node"
    - path: "mesh_status/persistence.py"
      provides: "Data persistence with configurable DATA_DIR"
  key_links:
    - from: "start.sh (.env loading)"
      to: "mesh_status/persistence.py"
      via: "DATA_DIR env var (loaded from .env with set -a, read by os.environ.get)"
---
# Plan 19-01: Start Script & Config

## Tasks

### Task 1: Create start.sh

<read_first>
- deploy/install.sh (uses $INSTALL_DIR, .mesh-status.install sentinel)
- entrypoint.sh (existing exec hypercorn pattern)
- node.py (CLI args: --leader-url, --node-ip)
- .planning/phases/19-start-script-config/19-CONTEXT.md (decisions)
</read_first>

<files>
start.sh
</files>

<action>
Create `start.sh` at repo root with `#!/usr/bin/env bash` and:

**Self-location:**
```bash
INSTALL_DIR="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
```
Follows symlinks so works from `~/.local/bin/start.sh -> ~/.local/meshtest/start.sh`

**Role dispatch:**
- `--leader` → `uv run hypercorn mesh_status.leader:app --bind 0.0.0.0:58080`
- `--node` → `uv run python node.py`

**Config wizard** (runs only when no CLI flags are passed):
```
Wizard prompts:
1. Node role: (choose leader/node, skip if --leader/--node given)
2. Leader URL [http://0.0.0.0:58080]:
3. Leader host [0.0.0.0]:
4. DATA_DIR [$INSTALL_DIR/data]:
```
Read input from `/dev/tty` when available (for pipe mode fallback).
Skip wizard if ANY of `--leader-url`, `--node-ip`, `--leader-ip` flags are present.

**CLI flags** (skip wizard when present):
- `--leader` / `--node` — role selection
- `--leader-url <url>` — leader URL override
- `--node-ip <ip>` — node IP override
- `--leader-ip <ip>` — leader IP for node registration
- `--help` — print usage
- `--version` — read and print from `.mesh-status.install`

**Logging:**
```
mkdir -p "$INSTALL_DIR/var"
LOG_FILE="$INSTALL_DIR/var/${ROLE}.log"
exec >"$LOG_FILE" 2>&1
```

**PID management:**
```
PID_FILE="$INSTALL_DIR/var/${ROLE}.pid"
mkdir -p "$(dirname "$PID_FILE")"
if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
    echo "Error: $ROLE is already running (PID $(cat "$PID_FILE"))"
    exit 1
fi
rm -f "$PID_FILE"
echo $$ > "$PID_FILE"
trap 'rm -f "$PID_FILE"; kill $CHILD_PID 2>/dev/null; wait $CHILD_PID; exit' SIGTERM SIGINT
```

**Foreground exec:**
```bash
exec uv run python -m mesh_status.node --leader-url "$LEADER_URL" --node-ip "$NODE_IP"
```
or for leader:
```bash
exec uv run hypercorn mesh_status.leader:app --bind "${LEADER_HOST}:${LEADER_PORT}"
```

**Uninstall** (`--uninstall`):
```
rm -rf "$INSTALL_DIR"
echo "Removed $INSTALL_DIR"
echo "To clean up PATH, remove $INSTALL_DIR from your shell rc file."
```

**Load .env if exists:**
```bash
if [ -f "$INSTALL_DIR/.env" ]; then
    set -a
    . "$INSTALL_DIR/.env"
    set +a
fi
```
</action>

<acceptance_criteria>
- `head -1 start.sh` contains `#!/usr/bin/env bash`
- `grep -q 'hypercorn' start.sh` — leader mode
- `grep -q 'node.py' start.sh` — node mode
- `grep -q 'PID_FILE\|\.pid' start.sh` — PID management
- `grep -q 'SIGTERM\|trap' start.sh` — signal handling
- `grep -q '--leader' start.sh` — leader flag
- `grep -q '--node' start.sh` — node flag
- `grep -q '--help' start.sh` — help flag
- `grep -q '--version' start.sh` — version flag
- `grep -q '--uninstall' start.sh` — uninstall flag
- `grep -q 'read.*/dev/tty\|wizard\|prompt' start.sh` — config wizard
- `grep -q '\.env' start.sh` — .env loading
- File is executable
</acceptance_criteria>

<verify>
bash -n start.sh 2>&1 || echo "syntax check failed"
</verify>

### Task 2: Fix persistence.py DATA_DIR

<read_first>
- mesh_status/persistence.py (current hardcoded Path("data"))
- entrypoint.sh (sets DATA_DIR env var)
</read_first>

<files>
mesh_status/persistence.py
</files>

<action>
Change line at top of `persistence.py` that defines `DATA_ROOT`:

**Before:**
```python
DATA_ROOT = Path("data")
```

**After:**
```python
DATA_ROOT = Path(os.environ.get("DATA_DIR", "data"))
```

Make sure `os` is already imported at the top of persistence.py.
</action>

<acceptance_criteria>
- `grep -q 'os.environ.get.*DATA_DIR' mesh_status/persistence.py` — env var support
- `grep 'DATA_ROOT' mesh_status/persistence.py | grep -v 'os.environ'` should return nothing (no hardcoded Path("data") for DATA_ROOT)
- `python3 -c "from mesh_status import persistence; print(persistence.DATA_ROOT)"` runs without error
- `DATA_DIR=/tmp/test-data python3 -c "from mesh_status import persistence; print(persistence.DATA_ROOT)"` prints `/tmp/test-data`
</acceptance_criteria>

<verify>
python3 -X dev -c "
import os, sys
sys.path.insert(0, '.')
from mesh_status import persistence
# Test default
assert str(persistence.DATA_ROOT) == 'data', f'default should be data, got {persistence.DATA_ROOT}'
# Test env var override
os.environ['DATA_DIR'] = '/tmp/test-mesh-data'
import importlib; importlib.reload(persistence)
assert str(persistence.DATA_ROOT) == '/tmp/test-mesh-data', f'override should work, got {persistence.DATA_ROOT}'
print('DATA_DIR fix verified OK')
"
</verify>
