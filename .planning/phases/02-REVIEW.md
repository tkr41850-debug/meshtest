---
phase: 02
reviewed: 2026-06-18T18:00:00Z
depth: standard
files_reviewed: 1
files_reviewed_list:
  - Dockerfile.node
findings:
  critical: 0
  warning: 4
  info: 2
  total: 6
status: issues_found
---

# Phase 2: Code Review Report — Dockerfile.node

**Reviewed:** 2026-06-18T18:00:00Z
**Depth:** standard
**Files Reviewed:** 1
**Status:** issues_found

## Summary

Reviewed `Dockerfile.node` at standard depth with cross-file analysis against `node.py`, `mesh_status/config.py`, `pyproject.toml`, and `Dockerfile.leader`. The Dockerfile is structurally sound with good patterns (layer caching, non-root user, apt cleanup, separate dependency COPY) but contains three environment variable naming inconsistencies that create misleading or dead configuration, plus a shell-form CMD that impacts signal delivery. No blockers were found — all issues are correctable warnings.

---

## Warnings

### WR-01: Env var `CHECK_INTERVAL` never read by the application — application expects `MESH_STATUS_INTERVAL`

**File:** `Dockerfile.node:29`
**Issue:** Line 29 declares `ENV CHECK_INTERVAL=10` with the intent to configure the check interval, but `mesh_status/config.py:4` reads `MESH_STATUS_INTERVAL` from the environment:

```python
CHECK_INTERVAL = int(os.environ.get("MESH_STATUS_INTERVAL", "10"))
```

This means:
- `CHECK_INTERVAL` as an env var is completely ignored at runtime — the application never reads it.
- The `MESH_STATUS_INTERVAL` env var (which the app actually reads) is never declared in the Dockerfile.
- Works correctly only by coincidence: both default to `10`. If a user overrides via `docker run -e CHECK_INTERVAL=5`, the change is silently ignored and the interval stays at 10.

**Fix:** Rename the ENV declaration to match what config.py actually reads:

```dockerfile
ENV MESH_STATUS_INTERVAL=10
```

For consistency, also verify the naming convention in `Dockerfile.leader` — it uses `LEADER_PORT` rather than `MESH_STATUS_PORT` for the same config value, suggesting the ENV naming convention across the two Dockerfiles should be reconciled.

### WR-02: Env var `LEADER_URL` is set but never consumed by the node agent — CMD uses `LEADER_IP` instead

**File:** `Dockerfile.node:27`
**Issue:** Line 27 declares `ENV LEADER_URL=http://leader:58080`, but no code running in the node container reads `LEADER_URL`:
- `node.py` constructs leader URLs directly from `--leader-ip` and `--port` arguments (lines 107, 185, 200) — it never reads `LEADER_URL`.
- The CMD on line 33 references `${LEADER_IP:-leader}`, which is a completely different variable.
- `LEADER_URL` is consumed by `mesh_status/dashboard.py:12` — which runs in the **leader** container (`Dockerfile.leader` also sets `ENV LEADER_URL=http://localhost:58080` on its line 31).

This creates confusion: a user might set `LEADER_URL` at runtime expecting it to affect node behavior, but it has no effect. Meanwhile, the variable that actually matters (`LEADER_IP`) has no ENV declaration (see IN-02).

**Fix one of the following:**
- Option A: Remove `LEADER_URL` from `Dockerfile.node` entirely (it belongs in `Dockerfile.leader` only).
- Option B: If the intent was to document connection targets, rename to `LEADER_IP`:

```dockerfile
ENV LEADER_IP=leader
```

### WR-03: Shell-form CMD prevents clean signal handling

**File:** `Dockerfile.node:33`
**Issue:** The CMD uses shell form:

```dockerfile
CMD uv run python node.py --leader-ip ${LEADER_IP:-leader} --node-ip ${NODE_IP}
```

This runs as `/bin/sh -c "uv run python node.py ..."`, making the shell PID 1 inside the container. Signals such as `SIGTERM` (sent by `docker stop`) are delivered to the shell process, which does **not** forward them to the `uv`/`python` child process. Consequences:
- `python node.py` never receives `SIGTERM`, so it cannot perform graceful shutdown (e.g., the `finally` block on line 225–229 that calls `http_runner.cleanup()` will not execute on `docker stop`).
- The container will be killed after the 10-second grace period rather than shutting down cooperatively.
- `uv run` adds an extra indirection layer between the shell and Python, compounding the signal delivery problem.

**Fix:** Use exec-form with an entrypoint wrapper that sources env vars, or use a dedicated entrypoint script (matching the pattern in `Dockerfile.leader` which uses `ENTRYPOINT ["/app/entrypoint.sh"]`):

Option A — Use a shell entrypoint script that `exec`s the Python process:

```dockerfile
# Create entrypoint script inline
RUN echo '#!/bin/sh\nexec uv run python node.py --leader-ip "${LEADER_IP:-leader}" --node-ip "${NODE_IP}"' > /app/entrypoint-node.sh && \
    chmod +x /app/entrypoint-node.sh && \
    chown meshstatus:meshstatus /app/entrypoint-node.sh
ENTRYPOINT ["/app/entrypoint-node.sh"]
```

Option B — If env var expansion is not needed at runtime, use exec-form CMD directly (requires defining `LEADER_IP` as a Docker ENV):

```dockerfile
ENV LEADER_IP=leader
CMD ["uv", "run", "python", "node.py", "--leader-ip", "leader", "--node-ip", ""]
```

### WR-04: Piped curl-to-sh installation with no integrity verification

**File:** `Dockerfile.node:6`
**Issue:** The uv installer is fetched and executed without validation:

```dockerfile
RUN curl -LsSf https://astral.sh/uv/install.sh | UV_INSTALL_DIR=/usr/local/bin sh
```

This pattern downloads a shell script from the internet and pipes it directly into `sh` with no:
- Checksum or signature verification of the downloaded script.
- Fallback if the download source is compromised.
- Pin to a specific installer version.

While this is the officially documented uv install method, it violates supply-chain security best practices. If `astral.sh` were compromised, the attacker gains arbitrary code execution during the Docker build.

**Fix:** Download the script first, verify a checksum, then execute:

```dockerfile
RUN curl -LsSf -o /tmp/uv-install.sh https://astral.sh/uv/install.sh && \
    echo "<expected-sha256>  /tmp/uv-install.sh" | sha256sum -c - && \
    UV_INSTALL_DIR=/usr/local/bin sh /tmp/uv-install.sh && \
    rm /tmp/uv-install.sh
```

Alternatively, download the uv binary directly from the GitHub release page with checksum verification, bypassing the shell script entirely.

---

## Info

### IN-01: Base image uses mutable tag with no digest pinning

**File:** `Dockerfile.node:1`
**Issue:** `FROM python:3.12-slim` uses a mutable tag. The `python:3.12-slim` manifest can be updated with new patches or security fixes, producing a different image on rebuild without notice. While this is the common pattern, it introduces non-reproducible builds.

**Fix:** Pin to a specific digest for reproducible builds:

```dockerfile
FROM python:3.12-slim@sha256:<specific-digest>
```

The `Dockerfile.leader` has the same pattern — both should be updated together if addressed.

### IN-02: `LEADER_IP` referenced in CMD but not declared as an ENV

**File:** `Dockerfile.node:33` (CMD line)
**Issue:** The CMD uses `${LEADER_IP:-leader}` and `${NODE_IP}` for configuration. `NODE_IP` is declared as `ENV NODE_IP=` on line 28, but `LEADER_IP` has no corresponding ENV declaration — it relies entirely on the shell default `leader`. This makes it an undocumented configuration surface: users must know (or reverse-engineer) that `LEADER_IP` is the correct variable to set, not the documented `LEADER_URL`.

**Fix:** Declare `LEADER_IP` as an ENV (especially if `WR-02` is fixed by removing `LEADER_URL`):

```dockerfile
ENV LEADER_IP=leader
ENV NODE_IP=
```

---

_Reviewed: 2026-06-18T18:00:00Z_
_Reviewer: OpenCode (gsd-code-reviewer)_
_Depth: standard_
