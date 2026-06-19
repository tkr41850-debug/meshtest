# Phase 4.1: Fix cross-phase integration gaps - Context

**Gathered:** 2026-06-18
**Status:** Ready for planning
**Mode:** Milestone audit gap fix

<domain>
## Phase Boundary

Fix the 3 critical cross-phase integration gaps discovered during the v0.1 milestone audit that break runtime behavior: add an HTTP server to node.py for peer push and config push reception, add /healthz endpoint to leader, and ensure the 30-minute data window retains enough data after hourly flush.

</domain>

<decisions>
## Implementation Decisions

### Gap 1: Node has no HTTP server
- Leader pushes peer list to `POST /update-peers` on node:58080 and config to `POST /updateConfig` on node:58080, but `node.py` has no HTTP server
- **Fix:** Add a lightweight async HTTP server to `node.py` (using `aiohttp` or just the Quart/uvicorn pattern) that handles `POST /update-peers` and `POST /updateConfig` on port 58080
- The node agent should continue its check loop independently; the HTTP server runs as a background task

### Gap 2: No /healthz endpoint on leader
- Node checks `GET /healthz` on peers, but leader only has `/livez` and `/readyz`
- **Fix:** Add `GET /healthz` to `leader.py` that returns the same as `/livez`

### Gap 3: 30m endpoint retains only 10 min of in-memory data after flush
- After hourly flush, only 10 min of data stays in memory for 30m queries
- **Fix:** Increase in-memory retention to 30 minutes, or change the 30m endpoint to read from disk when in-memory data is insufficient

### OpenCode's Discretion
- HTTP server library choice for node.py (aiohttp vs streaming via existing asyncio)
- Error handling for the node HTTP server (graceful degradation if server fails to start)

</decisions>

<code_context>
## Existing Code Insights

### Integration Points
- `node.py` — async check loop, currently no HTTP server (just a client)
- `leader.py` — Quart server with `/update-peers` endpoint (pushes to nodes), `/livez`, `/readyz`
- `leader.py` — `_notify_node()` sends POST to `node_ip:58080/update-peers`
- `leader.py` — `_push_config_to_all()` sends POST to `node_ip:58080/updateConfig`
- `mesh_status/persistence.py` — `flush_loop` clears in-memory after hourly flush, keeps 10 min

</code_context>

<specifics>
## Specific Issues to Fix

1. node.py needs: async HTTP server with `POST /update-peers` and `POST /updateConfig`
2. leader.py needs: `GET /healthz` endpoint (simple alias of `/livez`)
3. persistence or leader.py needs: ensure 30-minute endpoint has enough data after flush

</specifics>

<deferred>
## Deferred Ideas

None

</deferred>
