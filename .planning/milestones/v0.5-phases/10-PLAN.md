---
phase: 10
name: Streamlit Cleanup
requirements: [CLEAN-01, CLEAN-02, CLEAN-03, CLEAN-04, TEST-01, TEST-02]
files_modified:
  - mesh_status/dashboard.py (delete)
  - tests/test_dashboard.py (delete)
  - pyproject.toml
  - Dockerfile.node
  - frontend/src/mesh.test.ts
autonomous: true
---

## Wave 1: Cleanup

### Task 1.1: Delete Streamlit dashboard and tests

<read_first>
- mesh_status/dashboard.py (confirm file exists)
- tests/test_dashboard.py (confirm file exists)
- pyproject.toml (check streamlit/requests entries)
- Dockerfile.node (check EXPOSE 58581)
</read_first>

<action>
1. Delete `mesh_status/dashboard.py`
2. Delete `tests/test_dashboard.py`
3. In `pyproject.toml`: remove `streamlit` and `requests` from the `[project.dependencies]` list
4. In `Dockerfile.node`: remove the `EXPOSE 58581` line
</action>

<acceptance_criteria>
- `mesh_status/dashboard.py` does not exist
- `tests/test_dashboard.py` does not exist
- `pyproject.toml` does not contain `streamlit` or `requests` in dependencies
- `Dockerfile.node` does not contain `EXPOSE 58581`
</acceptance_criteria>

### Task 1.2: Add frontend view tests

<read_first>
- frontend/src/mesh.test.ts (existing tests)
- frontend/src/views/matrix.ts
- frontend/src/views/cards.ts
- frontend/src/views/day30.ts
</read_first>

<action>
Add additional Vitest tests to `frontend/src/mesh.test.ts`:

1. Matrix tests:
   - Renders correct status dot colors (green for OK, amber for NotAvailable)
   - Renders `Need at least 2 nodes` for single node
   - Short label computed correctly

2. Cards tests:
   - Renders detail card content for a target with OK status
   - Uptime colors: green for >=99, amber for >=95, red for <95

3. 30-day view tests:
   - Renders no-data message for empty days array
   - Split circle gradient has correct colors
</action>

<acceptance_criteria>
- `npm test` passes with all existing + new tests
- At least 15 total tests in mesh.test.ts
</acceptance_criteria>

---

## Verification

### must_haves
- [ ] `mesh_status/dashboard.py` deleted
- [ ] `tests/test_dashboard.py` deleted
- [ ] `streamlit` and `requests` removed from pyproject.toml
- [ ] `EXPOSE 58581` removed from Dockerfile.node
- [ ] `python3 -m pytest tests/ -q` passes (51 tests)
- [ ] `npm test` passes (15+ tests)
- [ ] `npm run build` succeeds
- [ ] `npm run typecheck` succeeds
