# Phase 26: Persistence & Leader Core - Context

**Gathered:** 2026-06-21
**Status:** Ready for planning
**Mode:** Auto-generated (infrastructure phase — all decisions previously discussed)

<domain>
## Phase Boundary

Fix data integrity, leader API robustness, and remove dead code in the persistence layer and leader API. All decisions were made during code review discussion on 2026-06-21.

Key decisions already made:
1. `_append_results`: Use direct append mode (`open(path, "a")`), discard invalid lines on read with warning log
2. Add `asyncio.Lock` for `_results` and `_day_aggregates` synchronization
3. `/updateConfig`: Validate input types and bounds, return 400 for invalid input
4. Uptime division: Guard with zero-check, return 0.0% for total=0
5. 90d dedup: Merge `recent_by_day` data into existing day entries instead of appending duplicates
6. Remove `_peers_by_node`, `_ensure_data_dir`, consolidate push functions, remove unused registry param, modernize Optional syntax

</domain>

<decisions>
## Implementation Decisions

### Append-to-File Mode
- Use direct `open(path, "a")` for appending new results — simpler, no data loss
- On read, discard invalid JSON lines with a warning log (not silent)

### Dead Code Removal
- Remove `_peers_by_node` from leader.py (line 34)
- Remove `_ensure_data_dir` from persistence.py
- Consolidate `_push_peer_list_to_all` and `_push_config_to_all` into single function
- Remove unused `registry` param from `calculate_status`
- Replace `Optional[str]` with `str | None` (Python 3.12+)

### OpenCode's Discretion
- Sort order for 90d merged days
- Exact lock granularity (single lock vs per-store locks)
- Test structure for new TDD tests
</decisions>

<code_context>
## Existing Code Insights

### Key Files
- `mesh_status/persistence.py` — `_append_results`, `_read_results`, `_ensure_data_dir`, `load_into_memory`, `flush_loop`
- `mesh_status/leader.py` — `/data` endpoint, `/updateConfig`, `_day_aggregates`, `_results`, `_peers_by_node`, push functions
- `mesh_status/status.py` — `calculate_status`
- `mesh_status/models.py` — `Optional[str]` usage

### Established Patterns
- TDD: Write test first, verify fails, fix code, verify passes
- Tests in `tests/test_persistence.py`, `tests/test_data_api.py`, `tests/test_leader_integration.py`
- `asyncio.Lock` already used in `_registry` access (leader.py)

### Integration Points
- `_results` and `_day_aggregates` accessed by: `/submit`, `/data`, `flush_loop`, `load_into_memory`
- Consolidating push functions requires updating callers in `register` and `updateConfig` handlers
</code_context>

<specifics>
## Specific Ideas

No specific requirements beyond the code review findings. All fixes have clear expected behavior.

</specifics>

<deferred>
## Deferred Ideas

None — all code review findings for this area are in scope.

</deferred>
