---
phase: 02
plan: 1
type: execute
wave: 1
depends_on: []
files_modified:
  - Dockerfile.node
autonomous: true
requirements:
  - DOCK-02
  - DOCK-04
must_haves:
  truths:
    - "`docker build -t mesh-node -f Dockerfile.node .` succeeds"
    - "`docker run mesh-node` starts the node agent and registers with leader"
    - "`iputils-ping` is installed — ping binary available at `/bin/ping`"
    - "UV is installed and used for dependency installation (not pip)"
    - "Container runs as non-root user `meshstatus` (uid 1001)"
    - "Build works for both `linux/amd64` and `linux/arm64` via docker buildx"
    - "ENV vars LEADER_URL, NODE_IP, CHECK_INTERVAL, MESH_STATUS_PORT exist with sensible defaults"
  artifacts:
    - path: "Dockerfile.node"
      provides: "Multi-arch Dockerfile for node agent container"
      min_lines: 20
      contains: "python:3.12-slim"
    - path: "/bin/ping"
      provides: "System ping binary for ICMP checks (inside container)"
      contains: "ping"
    - path: "/usr/local/bin/uv"
      provides: "UV package manager (inside container)"
      contains: "uv"
  key_links:
    - from: "Dockerfile.node"
      to: "pyproject.toml"
      via: "uv sync installs dependencies"
      pattern: "uv sync"
    - from: "Dockerfile.node"
      to: "node.py"
      via: "CMD invokes uv run python node.py"
      pattern: "node.py"
    - from: "Dockerfile.node"
      to: "mesh_status/config.py"
      via: "Copy mesh_status/ package for import"
      pattern: "mesh_status/"
    - from: "Dockerfile.node"
      to: "iputils-ping"
      via: "apt-get install for system ping binary"
      pattern: "iputils-ping"
---

<objective>
Create `Dockerfile.node` — a Dockerfile for the standalone node agent container based on `python:3.12-slim` with `iputils-ping`, UV package manager, and multi-arch support.

Purpose: Containerize the node agent so it can run as a standalone container on any VM in the mesh VPN WAN without manual Python setup.
Output: `Dockerfile.node` at repo root.
</objective>

<execution_context>
@$HOME/.config/opencode/get-shit-done/workflows/execute-plan.md
@$HOME/.config/opencode/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/STATE.md
@.planning/phases/02-CONTEXT.md
@.planning/milestones/v0.2-REQUIREMENTS.md
@.planning/milestones/v0.2-ROADMAP.md

<interfaces>
<!-- Key contracts and patterns the executor needs. Extracted from codebase. -->

**From Dockerfile.leader** (established patterns to follow):
```dockerfile
# Layer ordering pattern:
FROM python:3.12-slim AS base
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*
RUN curl -LsSf https://astral.sh/uv/install.sh | UV_INSTALL_DIR=/usr/local/bin sh
WORKDIR /app
COPY pyproject.toml /app/
RUN --mount=type=cache,target=/root/.cache/uv uv sync --no-dev --no-install-project
COPY <source> /app/.../
RUN --mount=type=cache,target=/root/.cache/uv uv sync --no-dev

# Non-root user pattern:
RUN addgroup --system --gid 1001 meshstatus && \
    adduser --system --uid 1001 --ingroup meshstatus --no-create-home meshstatus && \
    chown -R meshstatus:meshstatus /app
USER meshstatus

# ENV before EXPOSE
ENV KEY=value
EXPOSE <port>
```

**From node.py** (runtime behavior):
```python
# node.py reads these from argparse:
# --leader-ip / -l  : Leader server IP address
# --node-ip / -n    : This node's IP address
# --port / -p       : Leader port (default: config.LEADER_PORT = 58080)

# node.py reads from env via mesh_status/config.py:
# MESH_STATUS_PORT (default: 58080) — controls LEADER_PORT in config
# CHECK_INTERVAL via MESH_STATUS_INTERVAL (default: 10)

# node.py uses:
# - asyncio.create_subprocess_exec("ping", ...) — needs /bin/ping
# - mesh_status package imports — requires mesh_status/ in PYTHONPATH or installed
```

**From mesh_status/config.py:**
```python
LEADER_PORT = int(os.environ.get("MESH_STATUS_PORT", "58080"))
CHECK_INTERVAL = int(os.environ.get("MESH_STATUS_INTERVAL", "10"))
```

**Locked decisions (per CONTEXT.md, DOCK-04):**
| Decision | Value |
|----------|-------|
| Base image | `python:3.12-slim` |
| UV install | `curl -LsSf https://astral.sh/uv/install.sh | UV_INSTALL_DIR=/usr/local/bin sh` |
| Ping binary | `iputils-ping` from apt |
| Extra pkgs | `curl` (consistent with leader) |
| CMD | `uv run python node.py` (shell-form for env var injection, no entrypoint script) |
| WORKDIR | `/app` |
| Non-root user | `meshstatus` (uid 1001) |
| Build stage | Single stage |
| EXPOSE | Node HTTP server port |
| ENV vars | `LEADER_URL`, `NODE_IP`, `CHECK_INTERVAL` with sensible defaults |

**Layer ordering rationale** (same as Phase 1, proven working):
1. Base image + apt packages (cached unless apt changes)
2. UV install (cached unless install script URL changes)
3. pyproject.toml → `uv sync --no-dev --no-install-project` (caches ALL dependency downloads)
4. Copy source code → `uv sync --no-dev` (only re-runs if source changes, deps already cached)
5. Non-root user setup
6. ENV / EXPOSE / CMD
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>task 1: Create Dockerfile.node — multi-arch Dockerfile for node agent</name>
  <files>Dockerfile.node</files>
  <action>
    Create `Dockerfile.node` at repo root with the following structure and requirements. Follow the same patterns and layer ordering as `Dockerfile.leader` (Phase 1, proven in review).

    ```dockerfile
    # syntax=docker/dockerfile:1
    FROM python:3.12-slim

    # Layer 1: Install system packages
    # - curl: needed for UV install script + health checks
    # - iputils-ping: provides /bin/ping for ICMP connectivity checks (per NODE-02)
    RUN apt-get update && apt-get install -y --no-install-recommends curl iputils-ping && \
        rm -rf /var/lib/apt/lists/*

    # Layer 2: Install UV (multi-arch compatible — install script auto-detects arch)
    # Per locked decision: curl install script (same as Dockerfile.leader, works for amd64/arm64)
    RUN curl -LsSf https://astral.sh/uv/install.sh | UV_INSTALL_DIR=/usr/local/bin sh

    WORKDIR /app

    # Layer 3: Install dependencies (cached unless pyproject.toml changes)
    COPY pyproject.toml /app/
    RUN --mount=type=cache,target=/root/.cache/uv \
        uv sync --no-dev --no-install-project

    # Layer 4: Copy project source
    # node.py is at repo root — it imports from mesh_status.config and aiohttp
    # mesh_status/ package is needed for the import to resolve
    COPY node.py /app/
    COPY mesh_status/ /app/mesh_status/

    # Layer 5: Install project (installs mesh-status package so imports resolve)
    RUN --mount=type=cache,target=/root/.cache/uv \
        uv sync --no-dev

    # Layer 6: Set up non-root user (same uid/gid as Dockerfile.leader)
    # No /app/data directory needed for node (no persistence in node agent)
    RUN addgroup --system --gid 1001 meshstatus && \
        adduser --system --uid 1001 --ingroup meshstatus --no-create-home meshstatus && \
        chown -R meshstatus:meshstatus /app

    USER meshstatus

    # Env vars (per DOCK-04 and locked decisions)
    # MESH_STATUS_PORT: controls the node HTTP server port (via config.LEADER_PORT)
    # Default 58080 matches pyproject.toml default — node's HTTP server listens here
    # In docker-compose (Phase 3), this gets remapped to a non-conflicting host port
    ENV MESH_STATUS_PORT=58080

    # LEADER_URL: URL to reach the leader API (for dashboard/node reference)
    # In docker-compose, this would be http://leader:58080
    ENV LEADER_URL=http://leader:58080

    # NODE_IP: IP the node advertises to the leader. Empty = auto-detect via socket.
    ENV NODE_IP=

    # CHECK_INTERVAL: seconds between check cycles (consumed by node.py at runtime
    # from leader's config push — kept here for documentation/docker-compose override)
    ENV CHECK_INTERVAL=10

    # EXPOSE the node's HTTP server port (configurable via MESH_STATUS_PORT)
    # This documents the port for container networking (does NOT publish on host)
    EXPOSE 58080

    # CMD: run node.py via uv
    # Shell-form CMD used for env var substitution of --leader-ip and --node-ip.
    # No entrypoint.sh needed — node.py is self-contained.
    #
    # Env var mapping:
    #   LEADER_IP   → --leader-ip  (default: "leader" — resolves in compose DNS)
    #   NODE_IP     → --node-ip    (default: empty → node.py auto-detects via socket)
    #
    # Users can override any arg at runtime:
    #   docker run mesh-node uv run python node.py --leader-ip 10.0.0.1 --node-ip 10.0.0.2
    #
    # --port is NOT passed here — relies on MESH_STATUS_PORT env var read by config.py
    CMD uv run python node.py --leader-ip ${LEADER_IP:-leader} --node-ip ${NODE_IP}
    ```

    **Critical details:**

    1. **No entrypoint script** — Per user decision, no `entrypoint.sh` needed. The `CMD` handles everything inline. Shell-form CMD is used for env var substitution (the `CMD ["uv", "run", "python", "node.py"]` exec form cannot substitute env vars; shell-form achieves the same intent without a separate script file).

    2. **`--port` NOT passed in CMD** — The node's HTTP server port is controlled by the `MESH_STATUS_PORT` env var (read by `config.py` → `LEADER_PORT`). Not passing `--port` means the arg defaults to `config.LEADER_PORT` which reads from env. This keeps the port configurable via `-e MESH_STATUS_PORT=58081` at `docker run` without touching the CMD.

    3. **No HEALTHCHECK** — Unlike the leader (which has /livez), the node agent does not expose a liveness endpoint by default. HEALTHCHECK is not required for Phase 2.

    4. **Layer caching** — Use `--mount=type=cache,target=/root/.cache/uv` for `uv sync` commands. This caches downloaded wheels across builds, dramatically speeding up rebuilds when only source changed.

    5. **COPY ordering** — `pyproject.toml` first (for dep caching), then `node.py` + `mesh_status/` together (both are source code changes). This means changing either source file re-runs only Layer 5, not Layer 3.

    6. **uv.lock generation** — `uv sync` generates `uv.lock` inside the container. This is fine — the lock file stays in the container only and is not committed to the repo.

    7. **`.dockerignore` reuse** — The existing `.dockerignore` from Phase 1 already excludes `__pycache__/`, `.venv/`, `tests/`, etc. No changes needed.

    8. **Non-root user** — Same `meshstatus` (uid 1001) pattern as leader. No `/app/data` directory needed (node agent does not persist data locally — results are submitted to leader each cycle, buffered in memory only).

    9. **Why env defaults differ from node.py code:**
       - `LEADER_URL=http://leader:58080` — The hostname `leader` resolves in Docker Compose networks (Phase 3). For standalone `docker run`, users override via `-e LEADER_URL=http://<actual-ip>:58080` and pass `--leader-ip <ip>` as CMD override.
       - `NODE_IP` default is empty — triggers `get_own_ip()` auto-detection in node.py.
       - `MESH_STATUS_PORT=58080` matches the code default in config.py.
  </action>
  <verify>
    <automated>test -f Dockerfile.node && grep -q "python:3.12-slim" Dockerfile.node && grep -q "iputils-ping" Dockerfile.node && grep -q "uv/install.sh" Dockerfile.node && grep -q "uv sync" Dockerfile.node && grep -q "addgroup.*meshstatus" Dockerfile.node && grep -q "USER meshstatus" Dockerfile.node && grep -q "EXPOSE" Dockerfile.node && grep -q "CMD uv run python node.py" Dockerfile.node && grep -q "MESH_STATUS_PORT" Dockerfile.node && grep -q "LEADER_URL" Dockerfile.node && grep -q "NODE_IP" Dockerfile.node</automated>
  </verify>
  <done>
    Dockerfile.node exists at repo root, builds successfully with `docker build -t mesh-node -f Dockerfile.node .` (exit 0), contains `iputils-ping` + UV install + non-root user + env vars + EXPOSE + CMD, and passes all grep validation checks.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Container→Host | Container accesses host networking for ICMP ping (via `iputils-ping`) and HTTP connections to leader/mesh peers |
| Container→External Network | Container makes outbound HTTP connections to leader API and peer /healthz endpoints |
| Build→Supply Chain | Docker build pulls base image from Docker Hub, UV from astral.sh, apt packages from debian.org |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-02-01 | T (Tampering) | `python:3.12-slim` base image | accept | Official Docker image, signed by Docker. Tag pin acceptable for prototype. |
| T-02-02 | T (Tampering) | `curl ... astral.sh/uv/install.sh` | accept | Supply chain risk accepted for prototype. Pinned install URL, checksum verification in production. |
| T-02-03 | T (Tampering) | `apt-get install iputils-ping` | accept | Official Debian package. Verified by Debian package signing. |
| T-02-04 | E (Elevation) | Container runs as non-root `meshstatus` | mitigate | `USER meshstatus` ensures the node agent and ping subprocess run without root privileges. ping SUID binary is owned by root but accessible to non-root. |
| T-02-05 | D (DoS) | Ping subprocess resource exhaustion | accept | Semaphore (10 concurrent) in node.py limits parallel pings. Docker cgroup limits protect host. |
| T-02-06 | S (Spoofing) | Container identity (NODE_IP) | accept | NODE_IP is self-declared; in VPN WAN, the mesh is trusted. For production, add mTLS or signed registration. |
</threat_model>

<verification>

### Per-Task Verification

| # | Check | Command |
|---|-------|---------|
| 1 | Dockerfile exists with correct structure | `test -f Dockerfile.node && grep -q "python:3.12-slim" Dockerfile.node && grep -q "iputils-ping" Dockerfile.node` |
| 2 | UV install present | `grep -q "uv/install.sh" Dockerfile.node` |
| 3 | Non-root user setup | `grep -q "addgroup.*meshstatus" Dockerfile.node && grep -q "USER meshstatus" Dockerfile.node` |
| 4 | CMD presence | `grep -q "CMD uv run python node.py" Dockerfile.node` |
| 5 | Env vars defined | `grep -q "MESH_STATUS_PORT" Dockerfile.node && grep -q "LEADER_URL" Dockerfile.node && grep -q "NODE_IP" Dockerfile.node && grep -q "CHECK_INTERVAL" Dockerfile.node` |
| 6 | EXPOSE directive | `grep -q "EXPOSE" Dockerfile.node` |
| 7 | Layer caching flags | `grep -q "mount=type=cache.*uv" Dockerfile.node` |

### Docker Build Verification (requires Docker socket)

```bash
# Single-arch build (primary test)
docker build -t mesh-node -f Dockerfile.node .

# Verify container structure (if build succeeds)
docker run --rm mesh-node which ping       # Should return /bin/ping
docker run --rm mesh-node which uv         # Should return /usr/local/bin/uv
docker run --rm mesh-node id -un           # Should return meshstatus
```

### Multi-Arch Build Verification (if buildx available)

```bash
docker buildx build --platform linux/amd64,linux/arm64 -t mesh-node -f Dockerfile.node --load .
```

Note: `--load` only saves the current architecture locally. Use `--push` for multi-arch pushes to a registry.

### Container Runtime Verification

```bash
# Start a leader container first (Phase 1)
docker build -t mesh-leader -f Dockerfile.leader .
docker run -d --name mesh-leader -p 58080:58080 mesh-leader

# Wait for leader to be ready
sleep 5
curl -f http://localhost:58080/livez

# Start a node container (needs --leader-ip pointing to leader container)
# Use --network host for simplicity, or create a Docker network
docker run --rm --network host mesh-node uv run python node.py --leader-ip 127.0.0.1
```

### Cleanup
```bash
docker stop mesh-leader && docker rm mesh-leader 2>/dev/null; true
```

</verification>

<success_criteria>

- [ ] `Dockerfile.node` exists at repo root with correct FROM/COPY/RUN/USER/ENV/EXPOSE/CMD
- [ ] `docker build -t mesh-node -f Dockerfile.node .` completes successfully (exit 0)
- [ ] `iputils-ping` is installed: `which ping` inside container returns `/bin/ping`
- [ ] UV is installed: `which uv` inside container returns `/usr/local/bin/uv`
- [ ] Container runs as `meshstatus` (uid 1001): `id -un` returns `meshstatus`
- [ ] `MESH_STATUS_PORT`, `LEADER_URL`, `NODE_IP`, `CHECK_INTERVAL` env vars present with defaults
- [ ] EXPOSE directive present for node HTTP server port
- [ ] Layer caching with `--mount=type=cache,target=/root/.cache/uv` for uv sync
- [ ] Buildx multi-arch check: `docker buildx build --platform linux/amd64,linux/arm64 -t mesh-node -f Dockerfile.node --load .` succeeds (parses for both archs)
- [ ] Node agent starts: `docker run --network host mesh-node uv run python node.py --leader-ip 127.0.0.1` runs without import errors

</success_criteria>

<output>
After completion, create `.planning/phases/02-SUMMARY.md` capturing:
- File created (`Dockerfile.node`)
- Any deviations from plan
- Build test results (single-arch)
- Multi-arch verification results (or note if buildx not available)
- Container structure verification (ping, uv, meshstatus user)
</output>
