---
phase: 04-dashboard
fixed_at: 2026-06-19T00:00:27Z
review_path: .planning/phases/04-dashboard/REVIEW.md
iteration: 1
findings_in_scope: 10
fixed: 10
skipped: 0
status: all_fixed
---

# Phase 4: Code Review Fix Report

**Fixed at:** 2026-06-19T00:00:27Z
**Source review:** .planning/phases/04-dashboard/REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 10 (1 critical, 6 warnings, 3 info)
- Fixed: 10
- Skipped: 0

## Fixed Issues

### CR-01: XSS via `unsafe_allow_html=True` with unescaped IP addresses

**Files modified:** `mesh_status/dashboard.py`
**Commit:** dacf13a
**Applied fix:** Added `import html` at top of file. All IP address interpolations inside `unsafe_allow_html=True` contexts are now wrapped with `html.escape()`: `html.escape(short)` in matrix column headers (line 72), `html.escape(src_ip)` in matrix source cells (line 79), and `html.escape(tgt_ip)` in expander detail rows (line 176). Three `html.escape()` call sites total, covering all user-data interpolation paths through HTML renderers.

### WR-01: Silent error swallowing with no logging

**Files modified:** `mesh_status/dashboard.py`
**Commit:** dacf13a
**Applied fix:** Added `import logging` and `logger = logging.getLogger(__name__)`. Each `except requests.RequestException` block now catches the exception as `e` and calls `logger.warning(...)` with a descriptive message and the exception details. Three catch blocks updated: `fetch_data_30m` (line 24), `fetch_data_30d` (line 35), and `fetch_node_list` (line 46).

### WR-02: `st.tabs()` inside `@st.fragment` causes tab content flicker and expander state loss

**Files modified:** `mesh_status/dashboard.py`
**Commit:** dacf13a
**Applied fix:** Restructured the bottom of the file so `st.tabs()` is created **outside** the `@st.fragment`-decorated `render_dashboard()` function. `st.empty()` placeholders (`tab1_placeholder`, `tab2_placeholder`, `refresh_indicator_placeholder`) are created inside the tab context blocks. The fragment now updates these placeholders via `.container()` context managers instead of creating new tabs/expanders on every rerun. This preserves expander open/close state, scroll position, and eliminates UI flicker across 30-second refresh cycles.

### WR-03: Inconsistent data access — direct key access risks KeyError

**Files modified:** `mesh_status/dashboard.py`
**Commit:** dacf13a
**Applied fix:** Replaced all direct key access with `.get()` calls:
- Lines 112-115: `s["node_ip"]` → `s.get("node_ip")`, `s["target_ip"]` → `s.get("target_ip")`, etc.
- Line 117: Added validation guard `if not all([src, tgt, ping, http]): continue` to skip malformed entries
- Line 127: `c["node_ip"]` → `c.get("node_ip")`, `c["target_ip"]` → `c.get("target_ip")`
- Line 193: `c["node_ip"]` → `c.get("node_ip")`
- Lines 205-207: `conn["ping_uptime_pct"]` → `conn.get("ping_uptime_pct", 0)`, etc.
- Line 218: `conn["target_ip"]` → `conn.get("target_ip", "\u2014")`

### WR-04: No loading indicator during initial data fetch

**Files modified:** `mesh_status/dashboard.py`
**Commit:** dacf13a
**Applied fix:** Wrapped `render_dashboard()` call with `st.spinner("Loading mesh data...")` on line 273. The spinner shows during the initial data fetch and disappears once the first fragment render completes. Subsequent fragment reruns (inside the `@st.fragment` scope) do not show the spinner, as intended.

### WR-05: `@st.cache_data(ttl=30)` TTL matches fragment sleep interval exactly — no tolerance for fetch latency

**Files modified:** `mesh_status/dashboard.py`
**Commit:** dacf13a
**Applied fix:** Changed all three `@st.cache_data(ttl=30)` decorators to `@st.cache_data(ttl=25)` with a comment explaining the relationship: "slightly less than fragment sleep (30s) to ensure fresh fetch". This guarantees cache expiry before the next fragment rerun, even when fetch latency consumes part of the 30-second window.

### WR-06: README.md Python version mismatch with pyproject.toml

**Files modified:** `README.md`
**Commit:** dacf13a
**Applied fix:** Changed "Python 3.11+" to "Python 3.12+" in `README.md` line 10, matching the `requires-python = ">=3.12"` constraint in `pyproject.toml`.

### IN-01: Default argument `"\u2014"` in `.get()` is unreachable

**Files modified:** `mesh_status/dashboard.py`
**Commit:** dacf13a
**Applied fix:** Removed the unreachable default `"\u2014"` from two `.get()` calls. Changed `check.get("ping_latency_ms", "\u2014")` to `check["ping_latency_ms"]` (line 171) and `check.get("http_latency_ms", "\u2014")` to `check["http_latency_ms"]` (line 172). The ternary guard (`is not None`) ensures the value exists before the format expression is evaluated, so the `.get()` default was dead code.

### IN-02: `datetime` class imported as module-level name collision

**Files modified:** `mesh_status/dashboard.py`
**Commit:** dacf13a
**Applied fix:** Changed import from `from datetime import datetime` to `from datetime import datetime as dt`. Updated all usage sites: `dt.now()` (line 229) and `dt.fromtimestamp()` (line 173).

### IN-03: Magic sleep interval hardcoded instead of named constant

**Files modified:** `mesh_status/dashboard.py`
**Commit:** dacf13a
**Applied fix:** Extracted `time.sleep(30)` to a module-level constant `REFRESH_INTERVAL = 30` (line 14). Updated the sleep call to `time.sleep(REFRESH_INTERVAL)` (line 269). The constant name documents the relationship with the cache TTL (25s) and scheduled refresh cycle.

---

## Skipped Issues

None — all 10 findings were successfully fixed.

---

_Fixed: 2026-06-19T00:00:27Z_
_Fixer: OpenCode (gsd-code-fixer)_
_Iteration: 1_
