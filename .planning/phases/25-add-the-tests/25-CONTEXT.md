# Phase 25: Add the tests - Context

**Gathered:** 2026-06-21
**Status:** Ready for planning
**Mode:** Infrastructure phase — smart discuss skipped

<domain>
## Phase Boundary

Add integration and unit tests for the leader restart/data-reload behavior:
- `persistence.load_into_memory()` — reads up to 90 days of disk data on startup (recent → raw `_results`, old → `_day_aggregates`)
- `persistence.flush_loop()` — moves data older than 90h to daily aggregates
- `/data?window=90d` — combines `_day_aggregates` + `_results` (no disk reads)
- `/data?window=90h` — uses only `_results` (no disk reads)
- Fix G1: node_ip inference ordering (descending sort)
- Fix G2: malformed JSON error handling (skip+log)
- Fix G3/G4: extract aggregation helper for testability
- Fix G6: per-key day_aggregates skip (not per-day)

</domain>

<decisions>
## Implementation Decisions

### OpenCode's Discretion
All implementation choices are at OpenCode's discretion — pure test/infrastructure phase. Use patterns from existing test files (`tests/conftest.py`, `tests/test_persistence.py`, `tests/test_leader_integration.py`).

Priority order from the scan:
1. Fix G3/G4 first — extract `_move_old_to_aggregates` helper
2. Fix G1 — descending sort for node_ip inference
3. Fix G2 — try/except for malformed JSON lines
4. Add P0 tests (load_into_memory correctness: empty, all-recent, all-old, mixed, missing node_ip)
5. Add P0 integration tests (API returns correct data after load)
6. Add flush loop P0 tests
7. Fix G6 — per-key day_aggregates skip
8. Add P1/P2 tests (edge cases, aggregation math, 90d boundary)
</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `tests/conftest.py`: `reset_leader_state` autouse fixture (clears `_registry`, `_results`, `_peers_by_node`, removes `data/` dir); `app` fixture (Quart app); `client` fixture (Quart test client)
- `tests/test_persistence.py`: Direct calls to `_append_results`, `_read_results`, `_flush_results` with real filesystem
- `tests/test_data_api.py`: Direct `app.test_client()` with module-level state manipulation
- `tests/test_leader_integration.py`: Quart test client with `POST /submit` + `GET /data`

### Established Patterns
- Unit tests call persistence functions directly, manipulate module-level state
- Integration tests use `client` fixture for API calls
- Disk data written via `_append_results()` to date-partitioned JSONL files
- Autouse fixture cleans state between each test
- No mocking of filesystem — real I/O to `data/` (which gets cleaned)

### Integration Points
- `persistence.load_into_memory(results_store, day_aggregates)` — takes two empty dicts, mutates them
- `persistence.flush_loop()` — hard-imports `_results`, `_day_aggregates` from leader module (G3)
- `leader.get_data()` 90d handler — reads from both `_day_aggregates` and `_results`
- `leader.get_data()` 90h handler — reads from `_results` only
</code_context>

<specifics>
## Specific Ideas

No specific requirements — infrastructure/testing phase. Refer to subagent scan results and implementation gaps G1-G6.

Key test scenarios to cover:
- Empty data dir → empty in-memory stores
- All data <90h old → all in `_results`, nothing in `_day_aggregates`
- All data >90h old → all aggregated in `_day_aggregates`
- Mixed data → correct split between stores
- Missing `node_ip` inference from `target_to_source` mapping
- Flush loop moves old data, keeps recent data
- 90d endpoint returns combined data from both stores
- 90h endpoint returns data from `_results` only (no disk)
</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.
</deferred>
