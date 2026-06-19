---
phase: 01-leader-core-registration
reviewed: 2026-06-18T18:00:00Z
depth: standard
files_reviewed: 3
files_reviewed_list:
  - Dockerfile.leader
  - entrypoint.sh
  - .dockerignore
findings:
  critical: 1
  warning: 5
  info: 3
  total: 9
status: issues_found
---

# Phase 01: Code Review Report

**Reviewed:** 2026-06-18T18:00:00Z
**Depth:** standard
**Files Reviewed:** 3
**Status:** issues_found

## Summary

Reviewed the Docker/container packaging layer for the mesh-status leader component: `Dockerfile.leader`, `entrypoint.sh`, and `.dockerignore`. Three files, three severity classes across 9 findings.

The most critical issue is a signal-handling defect in `entrypoint.sh` — the `exec` of Streamlit orphans the Hypercorn background process and prevents the cleanup trap from ever firing, causing Hypercorn to receive no graceful shutdown. Additional warnings include a fragile 1-second startup race, non-reproducible `latest` tag pinning, root execution, and missing `.dockerignore` entries for standard Python build artifacts.

## Critical Issues

### CR-01: `exec` on Streamlit orphans Hypercorn and disables signal cleanup

**File:** `entrypoint.sh:32`
**Issue:** Line 32 runs `exec streamlit run ...`, which replaces the shell process with Streamlit. This has two consequences:
1. The background `$HC_PID` (Hypercorn) is orphaned — since its parent shell is replaced, Hypercorn becomes reparented to PID 1 but never receives a graceful shutdown signal from the cleanup trap.
2. The `trap cleanup TERM INT` on line 29 is registered on the shell, not on Streamlit. Once `exec` replaces the shell, the trap is gone. When Docker sends SIGTERM, Streamlit receives it and shuts down, but Hypercorn keeps running. Docker eventually sends SIGKILL, giving Hypercorn no chance to shut down cleanly (losing in-flight requests, corrupting state).

**Fix:** Remove `exec` and use a background-wait pattern so both processes receive cleanup. Replace lines 32-36 with:

```sh
echo "Starting Streamlit on port 58581..."
streamlit run mesh_status/dashboard.py \
    --server.port 58581 \
    --server.address 0.0.0.0 \
    --server.headless true \
    --server.runOnSave false &
ST_PID=$!

# Wait for either process to exit
while true; do
    if ! kill -0 "$HC_PID" 2>/dev/null && ! kill -0 "$ST_PID" 2>/dev/null; then
        break
    fi
    wait 2>/dev/null
done

cleanup
```

Or, more simply, keep both in the foreground with `wait -n` (bash-specific):

```sh
streamlit run ... &
ST_PID=$!

trap cleanup TERM INT

wait -n  # exits when either process dies
kill "$HC_PID" "$ST_PID" 2>/dev/null
wait
```

## Warnings

### WR-01: UV image pinned to `latest` — non-reproducible builds

**File:** `Dockerfile.leader:6`
**Issue:** `COPY --from=ghcr.io/astral-sh/uv:latest /uv /uv` uses the `latest` tag. If the UV maintainers release a breaking change to the binary interface, or if the `latest` tag shifts between Docker builds, the final image is not reproducible. This also breaks Docker layer caching — when `latest` moves, the entire layer invalidates.

**Fix:** Use the official UV install script which auto-detects platform:

```dockerfile
RUN curl -LsSf https://astral.sh/uv/install.sh | UV_INSTALL_DIR=/usr/local/bin sh
```

This handles multi-arch correctly (downloads the right binary per platform at build time).

### WR-02: `sleep 1` race condition for Hypercorn start check

**File:** `entrypoint.sh:18-21`
**Issue:** After backgrounding Hypercorn, the script sleeps only 1 second (`sleep 1`) before checking with `kill -0`. On a cold start or under load, Hypercorn may take longer than 1 second to initialize, especially if it needs to import modules, bind the socket, or connect to dependencies. This would produce a false positive "Warning: Hypercorn failed to start" message and the container would continue without Hypercorn, even though it was about to start successfully.

**Fix:** Use a retry loop with a longer timeout or check the port directly:

```sh
# Check if Hypercorn actually bound the port (more reliable than PID check)
for i in $(seq 1 10); do
    if nc -z "$LEADER_HOST" "$LEADER_PORT" 2>/dev/null; then
        break
    fi
    sleep 1
done
if ! nc -z "$LEADER_HOST" "$LEADER_PORT" 2>/dev/null; then
    echo "Warning: Hypercorn failed to start — continuing with Streamlit only"
fi
```

Note: `nc` may need to be installed in the Docker image, or use `/dev/tcp` if using bash.

### WR-03: No `USER` directive — container runs as root

**File:** `Dockerfile.leader:33`
**Issue:** No `USER` directive is set, so the container runs as root. If any process in the container is compromised (Hypercorn via a deserialization bug, Streamlit via a server-side vulnerability, etc.), the attacker has full root access within the container. The pod/container security context in orchestration may override this, but the image should not default to root.

**Fix:** Add a non-root user and switch to it before HEALTHCHECK/ENTRYPOINT:

```dockerfile
RUN addgroup --system --gid 1001 meshstatus && \
    adduser --system --uid 1001 --ingroup meshstatus --no-create-home meshstatus && \
    chown meshstatus:meshstatus /app/data

USER meshstatus
```

### WR-04: Cleanup function always exits with code 0, masking failures

**File:** `entrypoint.sh:23-28`
**Issue:** The cleanup function calls `exit 0` unconditionally. If Hypercorn was killed by a signal (e.g., SIGSEGV), the exit code from `wait "$HC_PID"` would carry the failure signal, but it is discarded. The container would report exit code 0 regardless of how Hypercorn died, making it impossible for orchestration systems to detect abnormal termination.

**Fix:** Capture and propagate the exit code:

```sh
cleanup() {
    echo "Shutting down Hypercorn (pid $HC_PID)..."
    kill "$HC_PID" 2>/dev/null
    wait "$HC_PID" 2>/dev/null
    EXIT_CODE=$?
    # If Hypercorn exited on its own (abnormal), preserve its exit code
    exit ${EXIT_CODE}
}
```

### WR-05: `.dockerignore` missing standard Python build/test exclusions

**File:** `.dockerignore`
**Issue:** Several standard directories and files that should never ship in a production image are not excluded from the Docker build context. While `COPY` instructions in the Dockerfile are selective and won't pull these in, the `.dockerignore` prevents them from being sent to the Docker daemon at all, reducing build context size and avoiding accidental inclusion if `COPY .` is ever used.

**Fix:** Add the following entries:

```
tests/
.pytest_cache/
dist/
build/
*.egg-info/
*.egg
.mypy_cache/
.ruff_cache/
.coverage
htmlcov/
.venv/
```

## Info

### IN-01: Redundant `|| exit 1` in HEALTHCHECK

**File:** `Dockerfile.leader:31`
**Issue:** `curl -f` already returns a non-zero exit code when the request fails (HTTP error or connection failure). The `|| exit 1` at the end is redundant — if `curl -f` fails, the shell exits with code 1 regardless, because the RUN command has `set -e`. The behavior is identical with or without `|| exit 1`. Not a bug, but unnecessary ceremony.

**Fix:** Simplify to:

```dockerfile
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:58080/livez
```

### IN-02: Default ENV values duplicated between Dockerfile and entrypoint.sh

**File:** `Dockerfile.leader:22-26` and `entrypoint.sh:5-8`
**Issue:** The same default values for `LEADER_HOST`, `LEADER_PORT`, `LEADER_URL`, and `DATA_DIR` are defined in both the Dockerfile (as `ENV`) and entrypoint.sh (as `${VAR:-default}` shell fallbacks). If one is updated but not the other, behavior diverges. The Dockerfile `ENV` directives ensure the variables are set at container runtime, so the shell defaults in the entrypoint serve no purpose inside Docker — they only matter if the script is run directly (which is not the intended use case).

**Fix:** Remove the shell fallback defaults from `entrypoint.sh` since Dockerfile `ENV` ensures they are always set:

```sh
LEADER_HOST="${LEADER_HOST}"
LEADER_PORT="${LEADER_PORT}"
LEADER_URL="${LEADER_URL}"
DATA_DIR="${DATA_DIR}"
```

Or simply use the variables directly without defaults and document that they come from container environment.

### IN-03: `COPY` + `RUN chmod` creates extra layer

**File:** `Dockerfile.leader:19-20`
**Issue:** A separate `RUN chmod +x /app/entrypoint.sh` line creates an additional image layer. Docker's `COPY` supports a `--chmod` flag that can set the executable bit in a single layer.

**Fix:** Combine into a single layer:

```dockerfile
COPY --chmod=+x entrypoint.sh /app/entrypoint.sh
```

---

_Reviewed: 2026-06-18T18:00:00Z_
_Reviewer: OpenCode (gsd-code-reviewer)_
_Depth: standard_
