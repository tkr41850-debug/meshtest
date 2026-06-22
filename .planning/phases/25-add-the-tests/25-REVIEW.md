---
phase: 25-add-the-tests
reviewed: 2026-06-21T21:30:00Z
depth: standard
files_reviewed: 9
files_reviewed_list:
  - frontend/src/mesh.test.ts
  - frontend/src/types.ts
  - frontend/src/views/day30.ts
  - frontend/src/views/hourly.ts
  - mesh_status/leader.py
  - mesh_status/persistence.py
  - tests/test_data_api.py
  - tests/test_leader_integration.py
  - tests/test_persistence.py
findings:
  critical: 0
  warning: 5
  info: 3
  total: 8
status: issues_found
---

# Phase 25: Code Review Report

**Reviewed:** 2026-06-21T21:30:00Z
**Depth:** standard
**Files Reviewed:** 9
**Status:** issues_found

## Summary

Reviewed 9 source files covering frontend rendering (mesh.test.ts, types.ts, day30.ts, hourly.ts), backend leader API (leader.py, persistence.py), and test suites (test_data_api.py, test_leader_integration.py, test_persistence.py). Found 8 issues: 0 critical, 5 warnings, 3 info.

The most significant finding is a data integrity bug in the `/data?window=90d` API endpoint that produces duplicate day entries when data for a given calendar date is split across the `_day_aggregates` and `_results` in-memory stores. Two test isolation gaps in the test suite could cause flaky cross-test pollution.

## Warnings

### WR-01: Duplicate day entries in `/data?window=90d` response

**File:** `mesh_status/leader.py:199-260`
**Issue:** When a calendar date has data in both `_day_aggregates` (pre-flush aggregated pairs) and `_results` (recent unflushed pairs), the endpoint returns **two separate entries** for the same date in the `days` array.

The root cause is the two-pass construction of `days_list`:
1. **Pass 1 (line 204-221):** Iterates `_day_aggregates` and appends a day entry for each date present.
2. **Pass 2 (line 243-257):** Iterates `recent_by_day` (built from `_results`) and appends another day entry for each date present.

The deduplication logic at line 231 (`if day in _day_aggregates and key in _day_aggregates[day]: continue`) only skips individual **(node_ip, target_ip) pairs** that are already aggregated, but the day-level entry itself is still added again at line 257 if ANY pair in `recent_by_day` fell through. This means a single date like `"2026-06-01"` can appear twice — once with aggregated pairs, once with recent-only pairs.

**Example scenario:**
- Day `2026-06-01`: pair `(A, B)` is in `_day_aggregates` (from a prior flush cycle), pair `(A, C)` is still in `_results` (new pair, not yet aggregated)
- Response: `days: [{date: "2026-06-01", connections: [{A, B}]}, {date: "2026-06-01", connections: [{A, C}]}]`
- Frontend renders the same date header twice with partial connection lists

**Fix:** Merge `recent_by_day` data into the existing day entries instead of appending new ones. Replace the second loop (lines 243-257) with logic that updates the already-built day entries:

```python
# After building days_list from _day_aggregates, create a date-indexed lookup:
days_by_date = {d["date"]: d for d in days_list}

for day_str in sorted(recent_by_day.keys()):
    connections = []
    for (src, dst), stats in recent_by_day[day_str].items():
        connections.append({
            "node_ip": src,
            "target_ip": dst,
            "total_checks": stats["total"],
            "ping_ok": stats["ping_ok"],
            "http_ok": stats["http_ok"],
            "ping_uptime_pct": round(stats["ping_ok"] / stats["total"] * 100, 1),
            "http_uptime_pct": round(stats["http_ok"] / stats["total"] * 100, 1),
        })
    if day_str in days_by_date:
        # Merge into existing entry
        days_by_date[day_str]["connections"].extend(connections)
    else:
        days_list.append({"date": day_str, "connections": connections})
```

### WR-02: `_day_aggregates` state leaks across tests in `TestDataAPI`

**File:** `tests/conftest.py:7-17` and `tests/test_data_api.py`
**Issue:** The `reset_leader_state` autouse fixture clears `_registry`, `_results`, and `_peers_by_node` before each test, but **does not clear `_day_aggregates`**. Since `_day_aggregates` is a module-level global in `leader.py`, data written by one test persists into the next.

**Contamination chain:**
1. `test_data_90d_includes_raw_counts` (line 32) sets `_day_aggregates["2026-06-01"]` but never cleans up
2. `test_data_90m_endpoint`, `test_data_90d_endpoint`, `test_data_90h_endpoint` all run subsequently with `_day_aggregates` still containing the previous test's data
3. While these tests only assert structural properties (e.g., `data["window"] == "90d"`), any future test that asserts emptiness of `data["days"]` after this test would fail nondeterministically

**Fix:** Add `_day_aggregates.clear()` to the `reset_leader_state` fixture:

```python
@pytest.fixture(autouse=True)
def reset_leader_state():
    from mesh_status.leader import _registry, _results, _peers_by_node, _day_aggregates

    _registry.clear()
    _results.clear()
    _peers_by_node.clear()
    _day_aggregates.clear()
    data_dir = os.path.join(os.path.dirname(__file__), "..", "data")
    if os.path.isdir(data_dir):
        shutil.rmtree(data_dir)
```

### WR-03: `/updateConfig` endpoint crashes on non-integer input

**File:** `mesh_status/leader.py:165-168`
**Issue:** The `updateConfig` handler passes raw JSON values directly to `int()` without type checking or validation. If a client sends a non-integer value (e.g., `"abc"`, `[1,2]`, `3.14`), `int()` raises `ValueError` and the handler returns a 500 error.

```python
if "check_interval" in data:
    config.CHECK_INTERVAL = int(data["check_interval"])
if "buffer_size" in data:
    config.BUFFER_SIZE = int(data["buffer_size"])
```

Additionally, there are no bounds checks: setting `check_interval` to 0 or -1 would cause issues in the status calculation threshold (`max(config.GRACE_PERIOD, 3 * config.CHECK_INTERVAL)`).

**Fix:** Add type validation and bounds checking:

```python
if "check_interval" in data:
    if not isinstance(data["check_interval"], int) or data["check_interval"] < 1:
        return {"error": "check_interval must be a positive integer", "status": 400}, 400
    config.CHECK_INTERVAL = data["check_interval"]
if "buffer_size" in data:
    if not isinstance(data["buffer_size"], int) or data["buffer_size"] < 1:
        return {"error": "buffer_size must be a positive integer", "status": 400}, 400
    config.BUFFER_SIZE = data["buffer_size"]
```

### WR-04: `test_config_change_updates_state` leaves global config dirty on failure

**File:** `tests/test_leader_integration.py:124-128`
**Issue:** The test saves `config.CHECK_INTERVAL`, mutates it, and relies on a `try-finally`-equivalent pattern to restore it — but there's no `finally` block. If the `assert` fails, `config.CHECK_INTERVAL` stays at `99` and leaks to subsequent tests.

```python
async def test_config_change_updates_state(self, client, mock_httpx):
    old_interval = config.CHECK_INTERVAL
    await client.post("/updateConfig", json={"check_interval": 99})
    assert config.CHECK_INTERVAL == 99
    config.CHECK_INTERVAL = old_interval  # never reached if assert fails
```

Since `reset_leader_state` doesn't reset config module globals, the contamination persists for the rest of the session.

**Fix:** Use `try`/`finally` or, better, avoid mutating global config in tests:

```python
async def test_config_change_updates_state(self, client, mock_httpx):
    old_interval = config.CHECK_INTERVAL
    try:
        await client.post("/updateConfig", json={"check_interval": 99})
        assert config.CHECK_INTERVAL == 99
    finally:
        config.CHECK_INTERVAL = old_interval
```

### WR-05: Potential `ZeroDivisionError` from aggregate stats

**File:** `mesh_status/leader.py:217, 253, 298`
**Issue:** The uptime percentage calculation `round(stats["ping_ok"] / stats["total"] * 100, 1)` divides by `stats["total"]` without a zero check. While in normal operation `total >= 1` for all entries (because entries are created with `total: 0` then incremented), data corruption, manual editing, or a race condition in aggregate construction could produce entries with `total: 0`, causing a crash.

**Fix:** Guard the division with a zero check:

```python
"ping_uptime_pct": round(stats["ping_ok"] / stats["total"] * 100, 1) if stats["total"] > 0 else 0.0,
"http_uptime_pct": round(stats["http_ok"] / stats["total"] * 100, 1) if stats["total"] > 0 else 0.0,
```

(This pattern is used 3 times in the file — at lines 217, 253, and 298.)

## Info

### IN-01: Duplicate code between `_push_peer_list_to_all` and `_push_config_to_all`

**File:** `mesh_status/leader.py:343-358`
**Issue:** Both functions are identical (iterate all registered nodes, call `_notify_node` with the same payload, `asyncio.gather`). This violates DRY. If the notification logic ever needs to change (e.g., adding headers, error handling), both functions must be updated in lockstep.

**Fix:** Consolidate into a single `_notify_all(peers: list[dict])` that both callers invoke. The payload difference (config vs. peer-list-only) could be merged since `_notify_node` already sends both `peers` and `config` fields in every notification.

### IN-02: Unused `registry` parameter in `calculate_status`

**File:** `mesh_status/status.py:6-8`
**Issue:** The `registry: dict` parameter is accepted but never referenced in the function body. The caller `leader.py:195` passes `_registry` unnecessarily, creating a misleading API surface.

**Fix:** Remove the `registry` parameter from `calculate_status` and its call site:

```python
def calculate_status(
    node_ip: str, target_ip: str, results: dict[str, list[dict]], now: float = None
) -> dict:
```

### IN-03: `test_data_90h_raw_counts_no_data` only clears `_results` but not `_day_aggregates`

**File:** `tests/test_data_api.py:22-30`
**Issue:** This test clears `_results` but does not account for possible `_day_aggregates` pollution from a previous test. The `90h` endpoint rebuilds entirely from `_results`, so it would not be directly affected by `_day_aggregates`. However, the pattern is inconsistent with other tests in the same class and could be confusing. Consider explicitly clearing both stores or relying on a fixed `reset_leader_state` (see WR-02).

---

_Reviewed: 2026-06-21T21:30:00Z_
_Reviewer: OpenCode (gsd-code-reviewer)_
_Depth: standard_
