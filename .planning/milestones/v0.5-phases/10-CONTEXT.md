# Phase 10: Streamlit Cleanup - Context

**Gathered:** 2026-06-19
**Status:** Ready for planning
**Mode:** Auto-generated (infrastructure phase)

<domain>
## Phase Boundary

Remove Streamlit dashboard (`dashboard.py`), its dependencies (`streamlit`, `requests`) from `pyproject.toml`, and clean up EXPOSE and port references. Add frontend Vitest tests for the Phase 9 views.

</domain>

<decisions>
## Implementation Decisions

### OpenCode's Discretion
All implementation choices are at OpenCode's discretion — pure cleanup phase.

</decisions>

<code_context>
## Existing Code Insights

- `mesh_status/dashboard.py` — 321 lines, to be deleted
- `pyproject.toml` — dependencies to clean: `streamlit`, `requests`
- `tests/test_dashboard.py` — 2 tests that import from `dashboard.py`, to be deleted with the file
- `Dockerfile.leader` — no longer has EXPOSE 58581 (already removed in Phase 8)
- `Dockerfile.node` — still may have EXPOSE 58581
- `frontend/src/mesh.test.ts` — 10 tests already exist, add view coverage

</code_context>

<specifics>
## Specific Ideas

- Delete `mesh_status/dashboard.py` and `tests/test_dashboard.py` together
- Remove `streamlit` and `requests` from `pyproject.toml` dependencies
- Verify all 53 Python tests still pass (down from 55 due to test deletion)
- Verify `npm test` still passes
- Verify `npm run build` and `npm run typecheck` still pass

</specifics>

<deferred>
## Deferred Ideas

None

</deferred>
