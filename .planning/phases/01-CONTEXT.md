# Phase 1: Leader Core & Registration - Context

**Gathered:** 2026-06-18
**Status:** Ready for planning

<domain>
## Phase Boundary

A running Quart HTTP server on port 58080 that accepts node registrations (`POST /register`), maintains an in-memory node registry, pushes updated peer IP lists to all registered nodes when new nodes join, accepts check result submissions (`POST /submit`), and exposes health endpoints (`GET /livez`, `GET /readyz`). Also includes `register.py` — a CLI registration script that can take node-ip and leader-ip via argv or stdin.

What this phase does NOT include: periodic checking logic (Phase 2), data persistence (Phase 3), dashboard (Phase 4). This phase only builds the leader server foundation and registration workflow.
</domain>

<decisions>
## Implementation Decisions

### Project Structure
- Project layout: Single Python package (`mesh_status/` with `leader.py`, `models.py`, `config.py`)
- Dependency management: `pyproject.toml` with standard metadata + UV for package management
- ASGI server config: Hypercorn config inline in `leader.py` `__main__` block
- Entry point: `python -m mesh_status.leader` as package run

### Quart Server Configuration
- Async startup pattern: `@app.before_serving` for background tasks
- CORS handling: `quart-cors` with `allow_origin="*"` (trusted VPN)
- Error response format: JSON `{"error": "...", "status": NNN}`
- Request logging: Standard `logging` module at INFO level to stderr

### Registration Protocol
- Registration payload: JSON `{"node_ip": "..."}` with optional `{"hostname": "..."}`
- Registration response: JSON `{"status": "registered", "peers": [...]}` with full peer list
- Peer list push: Leader maintains registry; on new registration, POSTs full peer list to each node's `/update-peers` endpoint on the same port (58080)
- Node identification: By IP address (string key in registry)

### Health & Error Handling
- `/livez`: Returns `200 OK {"status": "alive"}` — always responds if process is running
- `/readyz`: Returns `200 OK` when leader is accepting registrations + submissions
- `/submit` validation: Validates JSON body has `node_ip`, `checks` array, `timestamp`; returns 400 on bad data
- `/submit` response: `202 Accepted {"status": "accepted", "count": N}`

### OpenCode's Discretion
- Exact retry/cleanup timing for peer notification failures
- Specific logging format and levels for each endpoint
- Error detail verbosity level in error responses
</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
No existing code — greenfield project.

### Established Patterns
No existing patterns — greenfield project.

### Integration Points
- Phase 2 (Node Agent) will consume `GET /node-list` and `POST /submit`
- Phase 3 (Persistence) will read from in-memory state and write to disk
- Phase 4 (Dashboard) will consume `GET /data` (added in Phase 3)

</code_context>

<specifics>
## Specific Ideas

- Peer notification endpoint should be on the same port as the leader (58080)
- UV for package management for portability
- `register.py` as a standalone CLI script (not part of the Python package)
</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.
</deferred>
