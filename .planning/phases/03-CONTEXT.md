# Phase 3: Docker Compose + Deployment Docs - Context

**Gathered:** 2026-06-18
**Status:** Ready for planning
**Mode:** Smart discuss (autonomous)

<domain>
## Phase Boundary

Create compose.yml for local dev/test with leader+dashboard and node agent services, plus update README.md with Docker-based deployment instructions.

</domain>

<decisions>
## Implementation Decisions

### Accepted Grey Area Decisions
| Area | Decision | Rationale |
|------|----------|-----------|
| Compose file | `compose.yml` at repo root | Modern Docker Compose default |
| Network | `mesh-net` bridge network | DNS hostnames `leader`/`node1` for inter-container resolution |
| Leader service | Build: Dockerfile.leader, ports: 58080:58080, 58581:58581, volume: ./data:/app/data | Standard pattern |
| Node service | Build: Dockerfile.node, depends_on: leader, env: LEADER_IP=leader, NODE_IP=node1, MESH_STATUS_PORT=58081 | No port collision — leader uses 58080, node uses 58081 |
| Readme | Update README.md at repo root | Keep docs centralized |

</decisions>

<code_context>
## Existing Code Insights

- `Dockerfile.leader` — Mult-arch Dockerfile, entrypoint.sh, HEALTHCHECK
- `Dockerfile.node` — Multi-arch Dockerfile, requires iputils-ping
- Both use non-root `meshstatus` user
- Leader needs port 58080 (API) and 58581 (dashboard)
- Node needs port 58081 (HTTP server) — 58080 would conflict with leader on same host
- Data directory: mounted at /app/data for persistence
- README.md exists with project overview

</code_context>

<specifics>
## Specific Ideas

1. `compose.yml` with bridge network, two services, data volume
2. README sections: Prerequisites, Quick Start, Configuration, Build, Multi-Arch

</specifics>

<deferred>
## Deferred Ideas

- Multiple nodes in compose (just one node for now — user scales with `--scale`)
- Production-grade compose (restart policies, healthcheck dependencies)
</deferred>
