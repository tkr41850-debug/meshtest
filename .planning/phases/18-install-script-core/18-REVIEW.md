---
phase: 18-install-script-core
reviewed: 2026-06-21T12:00:00Z
depth: standard
files_reviewed: 1
files_reviewed_list:
  - deploy/install.sh
findings:
  critical: 0
  warning: 3
  info: 2
  total: 5
status: issues_found
---

# Phase 18: Code Review Report — Install Script Core

**Reviewed:** 2026-06-21T12:00:00Z
**Depth:** standard
**Files Reviewed:** 1
**Status:** issues_found

## Summary

Reviewed `deploy/install.sh` (123 lines, POSIX sh) — the curl-pipe-bash installer for mesh-status. The script correctly implements core features: prerequisite checks for uv/git/curl with actionable error messages, version-pinned git clone, uv sync for Python deps, npm-based frontend build, .env generation, sentinel-based idempotent reinstall, and a success banner. Overall structure is sound and properly follows POSIX sh conventions with `set -e`.

Three warnings found: a missing prerequisite check (npm — the function even has instructions for it but the check was never wired up), a relative-path resolution bug in the frontend build `cd` steps, and an incorrect install URL in the usage text. Two info items: leftover temp file and missing `-h` short flag.

---

## Warnings

### WR-01: Missing prerequisite check for `npm`

**File:** `deploy/install.sh:53-55`
**Issue:** The script builds the frontend via `npm ci && npm run build` (lines 95–96), so `npm` is a hard requirement. However, only `uv`, `git`, and `curl` are checked with `command -v` on lines 53–55. There is no `command -v npm` check. The `missing_prereq` function (line 39) already has a case block for `npm` with install instructions (line 47), but the check was never wired up.

If `npm` is missing, the user sees a cryptic shell error at line 95 (`npm: not found` or similar) after a long install sequence, instead of an early, actionable error message.

**Fix:** Add a `command -v npm` check alongside the other three on lines 53–55:

```sh
command -v npm >/dev/null 2>&1 || missing_prereq npm
```

---

### WR-02: Relative `$MESH_STATUS_HOME` causes incorrect path resolution in frontend build steps

**File:** `deploy/install.sh:94,97`
**Issue:** After the install/clone step, the script changes directory to `$MESH_STATUS_HOME` (line 82, 87, or 67). On lines 94 and 97, it then uses `cd "$MESH_STATUS_HOME/frontend"` and `cd "$MESH_STATUS_HOME"` again. If `$MESH_STATUS_HOME` is a relative path (e.g., `./my-meshtest`), these paths resolve relative to the *new* working directory (which is already `$MESH_STATUS_HOME`), not the original working directory.

For example, if `MESH_STATUS_HOME=./my-meshtest` and the user starts from `~`:
1. Line 85: `mkdir -p "$(dirname "./my-meshtest")"` → creates `~` (no-op)
2. Line 86: `git clone ... "./my-meshtest"` → clones to `~/my-meshtest`
3. Line 87: `cd "./my-meshtest"` → now in `~/my-meshtest`
4. Line 94: `cd "$MESH_STATUS_HOME/frontend"` resolves `./my-meshtest/frontend` from `~/my-meshtest`, becoming `~/my-meshtest/my-meshtest/frontend` — **wrong directory**

The default (`$HOME/.local/meshtest`) is an absolute path and works correctly, but any user who overrides with a relative path will hit this bug.

**Fix:** After the first `cd` into `MESH_STATUS_HOME`, use relative paths directly instead of re-resolving the env var:

```sh
# After cd into MESH_STATUS_HOME (line 82 or 87):
cd "$MESH_STATUS_HOME"  # first cd only
# ... uv sync ...
cd frontend || { echo "Error: frontend directory not found"; exit 1; }
npm ci
npm run build
cd ..
```

Alternatively, resolve `MESH_STATUS_HOME` to an absolute path at the start:

```sh
MESH_STATUS_HOME="$(cd "$MESH_STATUS_HOME" && pwd)" 2>/dev/null || { echo "Invalid MESH_STATUS_HOME"; exit 1; }
```

---

### WR-03: Incorrect install URL in usage text

**File:** `deploy/install.sh:16`
**Issue:** The usage text says:
```
Usage: curl -fsSL https://github.com/opencode-ai/mesh-status | sh [options]
```

This URL (`https://github.com/opencode-ai/mesh-status`) returns an HTML page (the GitHub repo page), not the raw `install.sh` script. Piping HTML to `sh` would produce confusing syntax errors. The correct URL should point to the raw file:

`https://raw.githubusercontent.com/opencode-ai/mesh-status/main/deploy/install.sh`

This is not just a documentation nicety — it breaks the primary install workflow for any user who follows the documented command.

**Fix:**
```sh
Usage: curl -fsSL https://raw.githubusercontent.com/opencode-ai/mesh-status/main/deploy/install.sh | sh [options]
```

---

## Info

### IN-01: Temp file `/tmp/_mesh_env_backup` not cleaned up

**File:** `deploy/install.sh:74,78-80`
**Issue:** The local-source install path backs up `.env` to `/tmp/_mesh_env_backup` before removing the install directory, then restores it. However, if the restore succeeds, the temp file is left behind in `/tmp`. While not a correctness problem, it leaks a temp file that persists after a successful install.

**Fix:** Remove the backup after a successful restore:

```sh
if [ -f /tmp/_mesh_env_backup ]; then
    mv /tmp/_mesh_env_backup "$MESH_STATUS_HOME/.env"
    echo "Existing .env preserved"
fi
```
→
```sh
if [ -f /tmp/_mesh_env_backup ]; then
    mv /tmp/_mesh_env_backup "$MESH_STATUS_HOME/.env"
    echo "Existing .env preserved"
    rm -f /tmp/_mesh_env_backup 2>/dev/null || true
fi
```

---

### IN-02: Missing `-h` short flag for help

**File:** `deploy/install.sh:33`
**Issue:** The flag parser only handles `--help` but not the conventional `-h` short flag. Users reaching for `./install.sh -h` will silently get no help.

**Fix:** Add `-h` to the help case:

```sh
-h|--help) usage ;;
```

---

_Reviewed: 2026-06-21T12:00:00Z_
_Reviewer: OpenCode (gsd-code-reviewer)_
_Depth: standard_
