# Phase 2: Dockerfile — Node Agent - Context

**Gathered:** 2026-06-18
**Status:** Ready for planning
**Mode:** Smart discuss (autonomous)

<domain>
## Phase Boundary

Create a Dockerfile for the standalone node agent based on `python:3.12-slim` that installs `iputils-ping`, UV, and runs `node.py` with multi-arch support (`linux/amd64`, `linux/arm64`).

</domain>

<decisions>
## Implementation Decisions

### Accepted Grey Area Decisions
| Area | Decision | Rationale |
|------|----------|-----------|
| Base image | `python:3.12-slim` | Same as leader, multi-arch native |
| UV install | `curl -LsSf https://astral.sh/uv/install.sh | UV_INSTALL_DIR=/usr/local/bin sh` | Auto-detects arch for multi-arch builds |
| Ping binary | `iputils-ping` from apt | Provides `/bin/ping` for ICMP checks |
| Extra packages | `curl` | Consistent with leader, health checks |
| Entrypoint | `CMD ["uv", "run", "python", "node.py"]` | Simple, no shell script needed |
| Port | Expose node HTTP port (58081 default) | Configurable via env |
| Working directory | `/app` | Consistent with leader |
| Non-root user | `meshstatus` (uid 1001) | Consistent with leader |
| Build stage | Single stage | No compile step needed |

</decisions>

<code_context>
## Existing Code Insights

- Node agent at `node.py` (repo root) — standalone script
- Uses `asyncio.create_subprocess_exec("ping", ...)` — needs system ping binary
- Has aiohttp HTTP server (POST /update-peers, POST /updateConfig) on configurable port
- Reads env: `LEADER_URL` (default http://localhost:58080)
- Reads env: `NODE_IP` (required)
- Reads env: `CHECK_INTERVAL` (from leader config push)
- Phase 1 established Dockerfile patterns to follow

</code_context>

<specifics>
## Specific Ideas

1. `Dockerfile.node` at repo root
2. File structure matches Phase 1 patterns
3. `CMD` not `ENTRYPOINT` (no entrypoint script needed — node.py is self-contained)

</specifics>

<deferred>
## Deferred Ideas

- None
</deferred>
