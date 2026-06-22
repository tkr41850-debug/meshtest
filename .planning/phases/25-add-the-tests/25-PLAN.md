---
phase: 25
name: Add the tests
wave: 1
plan: 1
plan_name: Restart/data-reload integration + unit tests
depends_on: []
files_modified:
  - mesh_status/persistence.py
  - mesh_status/leader.py
  - tests/test_persistence.py
  - tests/test_leader_integration.py
  - tests/conftest.py
autonomous: true
requirements: []
---

# Plan 1: Restart/data-reload tests

## Goal

Add integration and unit tests for leader restart/data-reload behavior, plus fix implementation gaps G1-G6 identified during the scan.

## Tasks

### Task 1: Extract aggregation helper (fix G3/G4)

<read_first>
- mesh_status/persistence.py
- mesh_status/leader.py
</read_first>

<action>
Extract a shared `_move_old_to_aggregates(results, day_aggregates, cutoff)` function in `persistence.py` that takes `results` (dict of node_ip → list of check dicts), `day_aggregates` (dict for output), and a `cutoff` timestamp. The function iterates `results`, moves entries with `timestamp < cutoff` into `day_aggregates` (keyed by `(node_ip, target_ip)` with `total`/`ping_ok`/`http_ok` counters), and returns a new dict containing only entries with `timestamp >= cutoff`.

Then:
1. Refactor `load_into_memory()` to use `_move_old_to_aggregates()` 
2. Refactor `flush_loop()` to use `_move_old_to_aggregates()` instead of inline aggregation

This makes both testable without importing from `leader` module.
</action>

<acceptance_criteria>
- `persistence.py` has a `_move_old_to_aggregates(results, day_aggregates, cutoff)` function
- `load_into_memory()` calls `_move_old_to_aggregates()`
- `flush_loop()` calls `_move_old_to_aggregates()`
- All existing tests still pass
</acceptance_criteria>

---

### Task 2: Fix node_ip inference ordering (fix G1)

<read_first>
- mesh_status/persistence.py (load_into_memory function)
</read_first>

<action>
In `load_into_memory()`, change the record processing order from ascending timestamp to DESCENDING timestamp. Records sorted descending ensures that records WITH `node_ip` populated appear before records WITHOUT `node_ip`, so the `target_to_source` mapping is built before it's needed for inference.

Change:
```python
raw = _read_results(start, end)
# raw is sorted ascending by timestamp
```
To process descending, either reverse the list or sort descending.
</action>

<acceptance_criteria>
- `load_into_memory()` processes records in descending timestamp order
- Records missing `node_ip` but with matching `target_ip` in an earlier (more recent) record get correctly inferred
</acceptance_criteria>

---

### Task 3: Handle malformed JSON lines (fix G2)

<read_first>
- mesh_status/persistence.py (_read_results function)
</read_first>

<action>
In `_read_results()`, wrap the `json.loads(line)` call in a try/except for `json.JSONDecodeError`. On error, log a warning with the date path and line preview, then `continue` to the next line instead of crashing.

```python
try:
    results.append(json.loads(line))
except json.JSONDecodeError:
    logger.warning("Skipping malformed JSON in %s: %s", path, line[:80])
    continue
```
</action>

<acceptance_criteria>
- `_read_results()` skips malformed JSON lines instead of crashing
- Warning is logged with file path and line preview
- Valid lines are still loaded correctly
</acceptance_criteria>

---

### Task 4: Fix per-key day skip in 90d handler (fix G6)

<read_first>
- mesh_status/leader.py (get_data 90d handler)
</read_first>

<action>
In the 90d handler, change the `if day in _day_aggregates: continue` check (line ~228) from per-day to per-key. Instead of skipping ALL recent results for a day if the day exists in `_day_aggregates`, skip only if the specific `(node_ip, target_ip)` key exists in `_day_aggregates[day]`.

Before:
```python
if day in _day_aggregates:
    continue
```

After:
```python
if day in _day_aggregates and key in _day_aggregates[day]:
    continue
```
</action>

<acceptance_criteria>
- Recent `_results` data for a day that already has some entries in `_day_aggregates` is not skipped for pairs NOT yet in `_day_aggregates[day]`
- All existing tests still pass
</acceptance_criteria>

---

### Task 5: Unit tests for load_into_memory()

<read_first>
- tests/test_persistence.py
- mesh_status/persistence.py
</read_first>

<action>
Add these test functions to `tests/test_persistence.py`:

1. `test_load_empty_data_dir` — Ensure empty/missing `data/` dir → `results_store == {}`, `day_aggregates == {}`

2. `test_load_all_recent_data` — Write 10 results with timestamps within last 90h → all in `results_store`, `day_aggregates` empty

3. `test_load_all_old_data` — Write results with timestamps >90h ago across multiple days → `results_store` empty, `day_aggregates` has correct per-day per-pair aggregation

4. `test_load_mixed_data` — Write 5 recent + 5 old results → correct split between stores

5. `test_load_aggregation_math` — Write 10 old records: 6 ping_ok, 7 http_ok → verify `day_aggregates[key] == {"total": 10, "ping_ok": 6, "http_ok": 7}`

6. `test_load_missing_node_ip` — Write a record WITH node_ip=10.0.0.1 target_ip=10.0.0.2, then a record WITHOUT node_ip but with target_ip=10.0.0.2. The older record (without node_ip) should get inferred node_ip from the newer one (descending sort).

7. `test_load_data_beyond_90_days` — Data 100 days old should not be loaded at all

Use the pattern from existing tests: write JSONL files to `data/YYYY/MM/DD.json`, then call `load_into_memory(store, agg)`.
</action>

<acceptance_criteria>
- 7 new test functions in `tests/test_persistence.py`
- Each test creates disk data, calls `load_into_memory()`, and asserts on store contents
- All 7 pass when running `make test-backend`
</acceptance_criteria>

---

### Task 6: Integration tests for API after reload

<read_first>
- tests/test_leader_integration.py
- tests/test_data_api.py
- tests/conftest.py
- mesh_status/persistence.py
- mesh_status/leader.py
</read_first>

<action>
Add integration tests to `tests/test_leader_integration.py`:

1. `test_90h_after_load_returns_from_memory` — Write recent data to disk, call `persistence.load_into_memory(_results, _day_aggregates)`, query `GET /data?window=90h`, verify hours contain expected data

2. `test_90d_after_load_returns_from_both_sources` — Write recent + old data to disk, load, query `GET /data?window=90d`, verify days contains entries from both stores

3. `test_90d_aggregate_merging` — Set `_day_aggregates` with some pairs for a day, `_results` with different pairs for same day, verify both appear in 90d response (tests G6 fix)

Use the `app.test_client()` pattern from existing tests. The setup needs to mock/replace the startup call since `before_serving` handlers don't fire automatically in test client.
</action>

<acceptance_criteria>
- 3 new test functions in `tests/test_leader_integration.py`
- Each directly calls `persistence.load_into_memory()` and queries API endpoints
- All pass when running `make test-backend`
</acceptance_criteria>

---

### Task 7: Unit tests for flush_loop aggregation

<read_first>
- tests/test_persistence.py
- mesh_status/persistence.py
</read_first>

<action>
Add tests for the `_move_old_to_aggregates()` helper extracted in Task 1:

1. `test_move_old_to_aggregates_mixed` — Results dict has 2 recent + 3 old entries for node A. After call, recent entries remain in results, old entries are in day_aggregates.

2. `test_move_old_to_aggregates_all_old` — All entries old → results empty, key removed

3. `test_move_old_to_aggregates_all_recent` — All entries recent → results unchanged, day_aggregates empty

4. `test_move_old_to_aggregates_empty` — Empty results → no-op

Call `_move_old_to_aggregates()` directly with test dicts.
</action>

<acceptance_criteria>
- 4 new test functions in `tests/test_persistence.py`
- Each directly calls `_move_old_to_aggregates()` with controlled inputs
- All pass when running `make test-backend`
</acceptance_criteria>

---

## must_haves

- [ ] Fix G1-G4, G6 implementation gaps
- [ ] 7 unit tests for `load_into_memory()` covering empty/recent/old/mixed/missing-node/aggregation-math/90d-boundary
- [ ] 4 unit tests for `_move_old_to_aggregates()` covering mixed/all-old/all-recent/empty
- [ ] 3 integration tests for 90h/90d/merge behavior after load
- [ ] All existing tests still pass (no regressions)
- [ ] `make ci` passes (lint, format, tests, build)
