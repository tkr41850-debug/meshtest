---
phase: 01
plan: 1
type: execute
wave: 1
depends_on: []
files_modified:
  - Dockerfile.leader
  - entrypoint.sh
autonomous: true
requirements:
  - DOCK-01
  - DOCK-04
must_haves:
  truths:
    - "docker build -t mesh-leader -f Dockerfile.leader . succeeds"
    - "docker run mesh-leader starts Hypercorn on 58080 and Streamlit on 58581"
    - "curl localhost:58080/livez inside container returns 200"
    - "UV is installed in the image and used for dependency installation"
    - "LEADER_HOST, LEADER_PORT, LEADER_URL, DATA_DIR env vars exist with correct defaults"
    - "Build works for both linux/amd64 and linux/arm64 via docker buildx"
  artifacts:
    - path: "Dockerfile.leader"
      provides: "Multi-arch Dockerfile for leader+dashboard container"
      min_lines: 25
      contains: "python:3.12-slim"
    - path: "entrypoint.sh"
      provides: "Shell entrypoint launching Hypercorn (bg) and Streamlit (fg)"
      min_lines: 25
      is_executable: true
  key_links:
    - from: "Dockerfile.leader"
      to: "entrypoint.sh"
      via: "COPY in Dockerfile"
      pattern: "COPY.*entrypoint.sh"
    - from: "entrypoint.sh"
      to: "mesh_status/leader.py"
      via: "hypercorn command"
      pattern: "hypercorn"
    - from: "entrypoint.sh"
      to: "mesh_status/dashboard.py"
      via: "streamlit run command"
      pattern: "streamlit"
    - from: "Dockerfile.leader"
      to: "pyproject.toml"
      via: "uv sync installs dependencies"
      pattern: "uv sync"
---

<objective>
Create Dockerfile for leader+dashboard container — single container running Quart API (Hypercorn on 58080) and Streamlit (58581), based on `python:3.12-slim` with multi-arch support.

Purpose: Containerize the leader+dashboard so it can be deployed across multi-VM VPN WAN without manual Python setup.
Output: `Dockerfile.leader` and `entrypoint.sh` at repo root.
</objective>

<execution_context>
@$HOME/.config/opencode/get-shit-done/workflows/execute-plan.md
@$HOME/.config/opencode/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/STATE.md
@.planning/phases/01-CONTEXT.md
@.planning/milestones/v0.2-REQUIREMENTS.md
@.planning/milestones/v0.2-ROADMAP.md

<interfaces>
<!-- Key contracts and patterns the executor needs. Extracted from codebase. -->

From pyproject.toml:
```toml
dependencies = [
    "quart>=0.20.0",
    "hypercorn>=0.18.0",
    "quart-cors>=0.8.0",
    "aiofiles>=24.1.0",
    "httpx>=0.28.0",
    "aiohttp>=3.9.0",
    "streamlit>=1.38.0",
    "requests>=2.32.0",
]
```

From mesh_status/config.py:
```python
LEADER_PORT = int(os.environ.get("MESH_STATUS_PORT", "58080"))
```

From mesh_status/leader.py (line 217):
```python
def main():
    hypercorn_config = Config()
    hypercorn_config.bind = [f"0.0.0.0:{config.LEADER_PORT}"]
    asyncio.run(serve(app, hypercorn_config))
```

From mesh_status/dashboard.py (line 12):
```python
LEADER_URL = os.environ.get("LEADER_URL", "http://localhost:58080")
```

Env vars (Docker-specific, per DOCK-04 and user decisions):
- LEADER_HOST (default: 0.0.0.0) — Hypercorn bind host
- LEADER_PORT (default: 58080) — Hypercorn bind port
- LEADER_URL (default: http://localhost:58080) — Dashboard's URL to reach leader API
- DATA_DIR (default: /app/data) — Persistence data directory
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>task 1: Create entrypoint.sh — shell script launching Hypercorn + Streamlit</name>
  <files>entrypoint.sh</files>
  <action>
    Create `/app/entrypoint.sh` with the following requirements:

    1. **Shebang:** `#!/bin/sh` (not bash — keep it portable, slim image has sh)
    2. **Env var defaults:**
       - `LEADER_HOST` default: `0.0.0.0`
       - `LEADER_PORT` default: `58080`
       - `LEADER_URL` default: `http://localhost:58080`
       - `DATA_DIR` default: `/app/data`
    3. **Set up data directory:** `mkdir -p "$DATA_DIR"` — ensure it exists before services start
    4. **Export LEADER_URL** for dashboard.py consumption (dashboard.py reads from os.environ)
    5. **Start Hypercorn in background:**
       ```
       hypercorn mesh_status.leader:app --bind ${LEADER_HOST}:${LEADER_PORT} &
       HC_PID=$!
       ```
       - Use `--worker-class uvloop` if available (faster on Linux), but do NOT require uvloop (not in deps)
       - Log "Starting Hypercorn on ${LEADER_HOST}:${LEADER_PORT}" to stdout
    6. **Start Streamlit in foreground** (the main process container tracks):
       ```
       exec streamlit run mesh_status/dashboard.py \
         --server.port 58581 \
         --server.address 0.0.0.0 \
         --server.headless true \
         --server.runOnSave false
       ```
       - Use `exec` so Streamlit replaces the shell process (handles SIGTERM properly)
       - `--server.headless true` suppresses the browser-open attempt (container has no browser)
    7. **PID management:** Save `HC_PID` so that if Streamlit exits, the script kills Hypercorn before exiting
    8. **Trap SIGTERM/SIGINT:** On signal, kill Hypercorn bg process, then exit
    9. **Wait loop:** After launching, wait on Streamlit pid. When Streamlit exits, kill Hypercorn and exit with Streamlit's exit code.

    **Full signal flow:**
    ```
    cleanup() {
      echo "Shutting down Hypercorn (pid $HC_PID)..."
      kill "$HC_PID" 2>/dev/null
      wait "$HC_PID" 2>/dev/null
      exit 0
    }
    trap cleanup TERM INT
    ```

    **Edge cases:**
    - If Hypercorn fails to start (returns immediately), still continue — Streamlit may still be useful. Log a warning.
    - If Streamlit fails to start, Hypercorn should still be killed.

    Make the file executable: `chmod +x entrypoint.sh` in the Dockerfile (not in the plan).
  </action>
  <verify>
    <automated>test -f entrypoint.sh && head -1 entrypoint.sh | grep -q "#!/bin/sh" && grep -q "hypercorn" entrypoint.sh && grep -q "streamlit" entrypoint.sh && grep -q "exec streamlit" entrypoint.sh</automated>
  </verify>
  <done>
    entrypoint.sh exists at repo root, executable, with correct shebang, env var handling, background Hypercorn launch, foreground Streamlit exec, and signal trap.
  </done>
</task>

<task type="auto">
  <name>task 2: Create Dockerfile.leader — multi-arch Dockerfile for leader+dashboard</name>
  <files>Dockerfile.leader</files>
  <action>
    Create `Dockerfile.leader` at repo root with the following structure:

    ```dockerfile
    # syntax=docker/dockerfile:1
    FROM python:3.12-slim AS base

    # Install UV — copy binary from official multi-arch image (ghcr.io/astral-sh/uv supports amd64 and arm64)
    COPY --from=ghcr.io/astral-sh/uv:latest /uv /uv

    WORKDIR /app

    # Layer 1: Install dependencies (cached unless pyproject.toml changes)
    COPY pyproject.toml /app/
    # uv sync with --no-dev (dev deps not needed in production image)
    # Use --no-install-project to install dependencies without the project itself (better layering)
    # Actually simpler: just `uv sync --no-dev` — this installs both deps and the project.
    # For layer caching, do it in two steps:
    RUN --mount=type=cache,target=/root/.cache/uv \
        uv sync --no-dev --no-install-project

    # Layer 2: Copy project source
    COPY mesh_status/ /app/mesh_status/

    # Layer 3: Copy and install project in editable mode (or just uv sync again)
    RUN --mount=type=cache,target=/root/.cache/uv \
        uv sync --no-dev

    # Layer 4: Copy entrypoint
    COPY entrypoint.sh /app/entrypoint.sh
    RUN chmod +x /app/entrypoint.sh

    # Add .venv/bin to PATH so hypercorn/streamlit are directly available
    ENV PATH="/app/.venv/bin:$PATH"

    # Default env vars (per DOCK-04, user decisions)
    ENV LEADER_HOST=0.0.0.0
    ENV LEADER_PORT=58080
    ENV LEADER_URL=http://localhost:58080
    ENV DATA_DIR=/app/data

    EXPOSE 58080 58581

    HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
        CMD curl -f http://localhost:58080/livez || exit 1

    ENTRYPOINT ["/app/entrypoint.sh"]
    ```

    **Important details:**

    1. **UV layer caching:** Use `--mount=type=cache,target=/root/.cache/uv` for the `uv sync` RUN commands. This caches downloaded packages across builds. If the Docker version/buildx doesn't support --mount, fall back to a plain `RUN uv sync --no-dev` without mount flags and add a note about it.

    2. **Layer ordering for caching:**
       - pyproject.toml → uv sync (no-install-project) — caches ALL dependency downloads
       - Copy source code → uv sync (installs project only) — fast second step
       - Copy entrypoint.sh → chmod

    3. **curl for HEALTHCHECK:** python:3.12-slim does NOT have curl. Install it in the Dockerfile before HEALTHCHECK:
       ```
       RUN apt-get update && apt-get install -y --no-install-recommends curl && \
           rm -rf /var/lib/apt/lists/*
       ```
       Place this early in the Dockerfile (before uv sync) so it's cached.

    4. **.dockerignore consideration:** The Dockerfile should work standalone. However, since `.dockerignore` doesn't exist yet, note in a comment that `COPY mesh_status/` will copy the whole directory (fine for this project). If a `.dockerignore` is created later, it should exclude `__pycache__/`, `.venv/`, etc.

    5. **UV sync without uv.lock:** There's no `uv.lock` in the repo. `uv sync` will generate one. That's fine. The lock file stays inside the container only.

    6. **Deferred architecture (per user decision):** Single build stage. No multi-stage needed for Python-only dependencies.
  </action>
  <verify>
    <automated>test -f Dockerfile.leader && grep -q "python:3.12-slim" Dockerfile.leader && grep -q "ghcr.io/astral-sh/uv" Dockerfile.leader && grep -q "EXPOSE 58080 58581" Dockerfile.leader && grep -q "HEALTHCHECK" Dockerfile.leader && grep -q "entrypoint.sh" Dockerfile.leader && grep -q "uv sync" Dockerfile.leader</automated>
  </verify>
  <done>
    Dockerfile.leader exists at repo root, builds successfully with `docker build -t mesh-leader -f Dockerfile.leader .`, runs both services, and passes health check.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Container→Host | Containerized services access host networking and filesystem via bind mounts |
| Build→Supply Chain | Docker build pulls base images and UV binary from external registries |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-01-01 | T (Tampering) | `ghcr.io/astral-sh/uv` image | accept | Pinned `:latest` tag; supply-chain risk accepted for prototype. Use digest pinning in production. |
| T-01-02 | T (Tampering) | `python:3.12-slim` base image | accept | Official Docker image, signed by Docker. Tag pin acceptable for prototype. |
| T-01-03 | D (DoS) | HEALTHCHECK curl | mitigate | HEALTHCHECK interval prevents fork-bomb curl loops. curl is single-shot per check. |
| T-01-04 | E (Elevation) | entrypoint.sh PID handling | mitigate | Trap + kill pattern prevents orphaned Hypercorn processes on Streamlit crash. |
</threat_model>

<verification>

### Per-Task Verification

| # | Check | Command |
|---|-------|---------|
| 1 | entrypoint.sh exists with correct structure | `test -f entrypoint.sh && head -1 entrypoint.sh | grep -q "#!/bin/sh" && grep -q "hypercorn" entrypoint.sh && grep -q "streamlit" entrypoint.sh` |
| 2 | Dockerfile exists with correct structure | `test -f Dockerfile.leader && grep -q "python:3.12-slim" Dockerfile.leader && grep -q "EXPOSE 58080" Dockerfile.leader && grep -q "HEALTHCHECK" Dockerfile.leader` |
| 3 | Docker build succeeds | `docker build -t mesh-leader -f Dockerfile.leader . 2>&1` |
| 4 | Container starts and serves | `docker run -d --name mesh-test -p 58080:58080 -p 58581:58581 mesh-leader && sleep 5 && curl -f http://localhost:58080/livez` |
| 5 | Dashboard accessible | `curl -s -o /dev/null -w "%{http_code}" http://localhost:58581` (expects 200) |

### Cleanup (after verification)
```bash
docker stop mesh-test && docker rm mesh-test
```

</verification>

<success_criteria>

- [ ] `Dockerfile.leader` exists at repo root with correct FROM/COPY/EXPOSE/HEALTHCHECK/ENTRYPOINT
- [ ] `entrypoint.sh` exists at repo root, executable, with correct env var handling and process management
- [ ] `docker build -t mesh-leader -f Dockerfile.leader .` completes successfully (exit 0)
- [ ] Container starts: Hypercorn binds to LEADER_HOST:LEADER_PORT, Streamlit binds to 58581
- [ ] `docker run` passes: `curl -f http://localhost:58080/livez` returns `{"status":"alive"}`
- [ ] `ENV PATH="/app/.venv/bin:$PATH"` makes hypercorn/streamlit available without `uv run`
- [ ] Buildx multi-arch check: `docker buildx build --platform linux/amd64,linux/arm64 -t mesh-leader -f Dockerfile.leader --load .` (note: --load only saves current arch; use `docker buildx build --platform linux/amd64,linux/arm64 -t mesh-leader -f Dockerfile.leader . --push` for actual multi-arch registry push; local --load test validates the Dockerfile parses correctly for both archs)

</success_criteria>

<output>
After completion, create `.planning/phases/01-SUMMARY.md` capturing:
- Files created (`Dockerfile.leader`, `entrypoint.sh`)
- Any deviations from plan (env var names, layer ordering changes, curl installation)
- Build and run test results
- Multi-arch verification results
</output>
