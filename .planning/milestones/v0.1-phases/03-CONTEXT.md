# Phase 3: Persistence & Data API - Context

**Gathered:** 2026-06-18
**Status:** Ready for planning

<domain>
## Phase Boundary

Hourly JSON Lines persistence of check results to date-partitioned files (`data/YYYY/MM/DD.json`), a background asyncio flush task, and `GET /data?window=30m` and `GET /data?window=30d` query endpoints with dynamic node status calculation (OK/Pending/NotAvailable) per check type.

This phase adds persistence and querying on top of the existing leader from Phase 1. The data flowing in via POST /submit is now persisted and queryable.
</domain>

<decisions>
## Implementation Decisions

### JSON Lines Format
- File naming: `data/YYYY/MM/DD.json` — one file per day
- Append strategy: Append-only JSON Lines — each result is one JSON line
- Atomic writes: Write to temp file, `os.rename()` to final path
- File rotation: No rotation needed (one file per day, hourly flush appends)

### Hourly Flush Strategy
- Flush trigger: `asyncio` background task with `while True: sleep(3600); flush()`
- What gets flushed: All `_results` entries since last flush (incremental)
- After flush: Keep last 10 minutes in memory for 30m API queries
- Flush failure: Log warning, retry next cycle, data safe in memory

### Data API Design
- Endpoint format: `GET /data?window=30m` and `GET /data?window=30d`
- 30m response: Raw check results from last 30 minutes (in-memory + recent file data)
- 30d response: Daily aggregated uptime % per node-pair
- Pagination: No pagination for prototype

### Status Calculation
- Per-check-type status: ping_ok and http_ok tracked independently
- Pending: Until first result arrives from this node
- NotAvailable: Data is missing (node exists in registry but no recent submission)
- Calculated at query time

### OpenCode's Discretion
- Exact JSON Lines line format
- 30-day aggregation format
- Number of status levels in addition to OK/Pending/NotAvailable
</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `mesh_status/leader.py` — has `_results` dict, `_registry`, app routes, async patterns
- `mesh_status/config.py` — existing config module
- `mesh_status/models.py` — CheckResult model

### Established Patterns
- Quart route handlers with JSON responses
- asyncio background tasks via `@app.before_serving`
- httpx.AsyncClient for HTTP calls
- Logging to stderr at INFO level

### Integration Points
- Phase 4 (Dashboard) will consume `GET /data` endpoints
- Phase 1 (Leader) provides the data via `_results`
</code_context>

<specifics>
## Specific Ideas

- Per-check-type status (ping_ok and http_ok are independent signals)
- Pending until first result arrives
- NotAvailable means data missing, not node down
</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.
</deferred>
