# Phase 1: Dockerfile — Leader+Dashboard - Context

**Gathered:** 2026-06-18
**Status:** Ready for planning
**Mode:** Smart discuss (autonomous)

<domain>
## Phase Boundary

Create a Dockerfile that runs both Quart (58080) and Streamlit (58581) in a single container based on `python:3.12-slim` with multi-arch support (`linux/amd64`, `linux/arm64`).

</domain>

<decisions>
## Implementation Decisions

### Accepted Grey Area Decisions
| Area | Decision | Rationale |
|------|----------|-----------|
| Base image | `python:3.12-slim` | Minimal, multi-arch support, matches requires-python |
| Package manager | UV via `COPY --from=ghcr.io/astral-sh/uv:latest` | Fast install, matches project convention |
| Entrypoint | Shell script launching Hypercorn + Streamlit as bg processes | Simplest way to run 2 processes in 1 container |
| Port mapping | 58080 (API), 58581 (dashboard) | Matches existing conventions |
| Working directory | `/app` | Standard Python layout |
| Build stages | Single stage | No compile step needed |

</decisions>

<code_context>
## Existing Code Insights

- Leader is at `mesh_status/leader.py` — requires Hypercorn to serve
- Dashboard is at `mesh_status/dashboard.py` — requires `streamlit run`
- Dependencies in `pyproject.toml` managed via UV
- ENV `LEADER_URL` for dashboard to connect to leader
- ENV vars: `LEADER_HOST`, `LEADER_PORT`, `LEADER_URL`

</code_context>

<specifics>
## Specific Ideas

1. `Dockerfile.leader` at repo root
2. `entrypoint.sh` that starts Hypercorn in background, then Streamlit in foreground
3. UV install via COPY from official UV image
4. HEALTHCHECK for container orchestration

</specifics>

<deferred>
## Deferred Ideas

- Multi-stage build — not needed for pure Python deps
</deferred>
