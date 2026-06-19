---
phase: 04-dashboard
reviewed: 2026-06-18T16:00:00Z
depth: standard
files_reviewed: 3
files_reviewed_list:
  - mesh_status/dashboard.py
  - pyproject.toml
  - README.md
findings:
  critical: 1
  warning: 6
  info: 3
  total: 10
status: issues_found
---

# Phase 4: Code Review Report — Streamlit Dashboard

**Reviewed:** 2026-06-18T16:00:00Z
**Depth:** standard
**Files Reviewed:** 3
**Status:** issues_found

## Summary

Reviewed the Streamlit dashboard implementation (253 lines), dependency changes in `pyproject.toml`, and deployment documentation in `README.md`. The code is structurally sound with a clear fragment-based auto-refresh architecture, but has a security-relevant XSS vector through unescaped IP addresses rendered with `unsafe_allow_html=True`, several Streamlit anti-patterns that degrade UX, and error-handling gaps that hamper debuggability.

---

## Critical Issues

### CR-01: XSS via `unsafe_allow_html=True` with unescaped IP addresses

**File:** `mesh_status/dashboard.py:72,90,166-170`
**Issue:** Node IP addresses from the leader's `/node-list` endpoint are interpolated directly into HTML and rendered with `unsafe_allow_html=True` in `st.markdown()`. The `/register` endpoint (in `leader.py`) does not validate `node_ip` format — any string is accepted. An attacker who can reach the leader's `/register` endpoint can register a node with a malicious `node_ip` containing HTML/JavaScript (e.g., `10.0.0.1<script>alert('xss')</script>`). When a dashboard viewer loads the page, the script executes in their browser context.

**Affected code paths:**

Line 72 (connectivity matrix — source node cell):
```python
f'<td style="padding: 4px 8px; font-family: monospace; color: #374151; '
f'border: 1px solid #e5e7eb; white-space: nowrap;">{src_ip}</td>'
```

Line 90 (renders the assembled HTML):
```python
st.markdown("".join(html_parts), unsafe_allow_html=True)
```

Lines 166-170 (expander detail rows):
```python
cols[0].markdown(f'<span style="font-family:monospace; font-size:14px;">{tgt_ip}</span>', unsafe_allow_html=True)
```

**Fix:** Escape IP addresses before inserting into HTML, or use Streamlit's native components (e.g., `st.write()`, `st.dataframe()`) instead of raw HTML. The simplest fix is to HTML-escape IPs:

```python
import html
# ...
f'<td ...>{html.escape(src_ip)}</td>'
```

Or better, avoid `unsafe_allow_html=True` entirely by using `st.dataframe()` for the matrix and `st.write()` for IP labels in expanders. Also validate `node_ip` format in `leader.py`'s `/register` handler (reject non-IP strings).

---

## Warnings

### WR-01: Silent error swallowing with no logging

**File:** `mesh_status/dashboard.py:18-19, 28-29, 38-39`
**Issue:** All three catch blocks (`fetch_data_30m`, `fetch_data_30d`, `fetch_node_list`) silently return `None`/`[]` on `requests.RequestException`. There is no `logging` output, no `st.error()`, and no `print()` to stderr. When the leader is unreachable or returns errors, the dashboard silently shows stale/empty data with no indication of why. Operators have no way to diagnose connectivity issues without inspecting Streamlit's internal logs.

```python
except requests.RequestException:
    return None          # ← silently swallowed
```

**Fix:** At minimum, log the exception. Consider also surfacing the error to the user via `st.warning()` or `st.error()`:

```python
import logging
logger = logging.getLogger(__name__)

# ...
except requests.RequestException as e:
    logger.warning("Failed to fetch 30m data from leader: %s", e)
    return None
```

For the node list fetch, log a warning but return `[]` so the dashboard can degrade gracefully.

---

### WR-02: `st.tabs()` inside `@st.fragment` causes tab content flicker and expander state loss

**File:** `mesh_status/dashboard.py:232-250`
**Issue:** Both `st.tabs()` and the expander widgets (`st.expander`) are created inside the `@st.fragment`-decorated `render_dashboard()` function. Every 30 seconds the fragment reruns from the top, destroying and recreating all tab containers and expanders. While Streamlit preserves the active tab index, the tab content (including expander open/close state, scroll position, and any transient UI state) is fully reconstructed. This means:

1. Any expander a user has opened will collapse on the next 30s refresh
2. Scroll position inside tabs is lost on each refresh
3. The entire tab content area flickers/redraws every 30 seconds

This makes the per-source expander details (the primary drill-down mechanism) effectively unusable for monitoring — operators cannot keep a specific source's details open while watching it refresh.

**Fix:** Two approaches:

**Option A (recommended):** Move `st.tabs()` outside the fragment. Keep the fragment scope to just the data + content INSIDE each tab:

```python
tab1, tab2 = st.tabs(["30-Minute View", "30-Day View"])

with tab1:
    _render_30m_view(data_30m, nodes)  # placeholder — will be filled by fragment

with tab2:
    _render_30d_view(data_30d, nodes)  # placeholder
```

This is not trivial with the current architecture since tab content is rendered by the fragment. An alternative is to use `st.empty()` placeholders inside tabs and have the fragment update them.

**Option B:** Accept the trade-off but document it explicitly. Increase the refresh interval to 60s to reduce disruption frequency.

---

### WR-03: Inconsistent data access — direct key access risks KeyError

**File:** `mesh_status/dashboard.py:104-107, 117, 183, 195-197, 208`
**Issue:** The code inconsistently uses direct key access (`s["node_ip"]`) and safe access via `.get()` (`c.get("timestamp", 0)`). If the leader API returns a status or connection entry missing expected fields, the dashboard crashes with `KeyError` instead of degrading gracefully.

Specifically:
- Lines 104-107: `s["node_ip"]`, `s["target_ip"]`, `s["ping_status"]`, `s["http_status"]` — direct access on status entries
- Line 117: `c["node_ip"]`, `c["target_ip"]` — direct access on check entries
- Line 183: `c["node_ip"]` — direct access on connection entries in the 30d view
- Lines 195-197: `conn["ping_uptime_pct"]`, `conn["http_uptime_pct"]`, `conn["total_checks"]` — direct access
- Line 208: `conn["target_ip"]` — direct access

Compare with lines 118, 160-163 which safely use `.get()` with defaults.

**Fix:** Use `.get()` consistently, or validate the structure early with a helper:

```python
src = s.get("node_ip")
tgt = s.get("target_ip")
ping = s.get("ping_status")
http = s.get("http_status")
if not all([src, tgt, ping, http]):
    continue  # skip malformed entry
```

---

### WR-04: No loading indicator during initial data fetch

**File:** `mesh_status/dashboard.py:232-253`
**Issue:** On initial page load, `render_dashboard()` calls `fetch_all_data()` which fires up to 3 sequential HTTP requests (with 5s timeout each). During this time, the page shows a blank white screen with no loading indicator. The UI spec (in `04-UI-SPEC.md` line 289) calls for `st.spinner("Loading mesh data...")` during initial load, but it is not implemented.

**Fix:** Wrap the initial render in a spinner:

```python
with st.spinner("Loading mesh data..."):
    render_dashboard()
```

Or, restructure so the initial data fetch has a loading state outside the fragment:

```python
if not st.session_state.get("data_loaded"):
    with st.spinner("Loading mesh data..."):
        data_30m, data_30d, nodes, leader_ok = fetch_all_data()
        st.session_state.data_loaded = True
        st.session_state.data_30m = data_30m
        st.session_state.data_30d = data_30d
        st.session_state.nodes = nodes
        st.session_state.leader_ok = leader_ok
```

---

### WR-05: `@st.cache_data(ttl=30)` TTL matches fragment sleep interval exactly — no tolerance for fetch latency

**File:** `mesh_status/dashboard.py:12, 22, 32, 249`
**Issue:** Both the cache TTL and the fragment sleep interval are set to 30 seconds. Combined with the data fetch taking some time (e.g., 500ms–3s), the actual refresh cycle is `fetch_time + render_time + 30s`. If fetch time is 2s, the cache TTL (30s) expires slightly before the next fragment run starts (at ~32s), so every cycle fetches fresh data. This works but is fragile: if the fetch consistently takes longer than the render+sleep gap, or if there's clock drift, the cache might not be expired when the fragment reruns, causing stale data display for a cycle.

**Fix:** Use a slightly shorter TTL (e.g., 25s) to guarantee cache expiry before the next fragment run. Add a comment explaining the relationship:

```python
@st.cache_data(ttl=25)  # slightly less than fragment sleep (30s) to ensure fresh fetch
```

---

### WR-06: README.md Python version mismatch with pyproject.toml

**File:** `README.md:10`
**Issue:** README.md says "Python 3.11+" but `pyproject.toml` specifies `requires-python = ">=3.12"`. This discrepancy will cause users with Python 3.11 to encounter install failures.

**Fix:** Align README.md with pyproject.toml:

```markdown
**Prerequisites:**
- Python 3.12+
```

---

## Info

### IN-01: Default argument `"\u2014"` in `.get()` is unreachable

**File:** `mesh_status/dashboard.py:161-162`
**Issue:** The default argument in both `.get()` calls is dead code:

```python
ping_lat = f'{check.get("ping_latency_ms", "\u2014"):.1f}ms' if check.get("ping_latency_ms") is not None else "\u2014"
```

The format expression `check.get("ping_latency_ms", "\u2014")` is only evaluated when `check.get("ping_latency_ms") is not None` (the ternary condition). In that case, `.get()` returns the actual value, never the default `"\u2014"`. The default argument is never used and can be removed.

**Fix:**

```python
ping_lat = f'{check["ping_latency_ms"]:.1f}ms' if check.get("ping_latency_ms") is not None else "\u2014"
```

Or more cleanly:

```python
ping_val = check.get("ping_latency_ms")
ping_lat = f"{ping_val:.1f}ms" if ping_val is not None else "\u2014"
```

---

### IN-02: `datetime` class imported as module-level name collision

**File:** `mesh_status/dashboard.py:3`
**Issue:** `from datetime import datetime` shadows the `datetime` module with the `datetime` class, preventing use of other `datetime` members (e.g., `datetime.timedelta`). This is a conventional but fragile pattern. The module is used as `datetime.now()` (class method) and `datetime.fromtimestamp()` (class method), so it works, but it forces a collision that may confuse future editors.

**Fix:** Import more explicitly:

```python
from datetime import datetime as dt
```
Then use `dt.now()` and `dt.fromtimestamp()`.

---

### IN-03: Magic sleep interval hardcoded instead of named constant

**File:** `mesh_status/dashboard.py:249`
**Issue:** `time.sleep(30)` uses a magic number. While its purpose is obvious in context (it pairs with `st.rerun()`), extracting to a named constant improves maintainability and documents the relationship with the cache TTL.

**Fix:**

```python
REFRESH_INTERVAL = 30
# ...
time.sleep(REFRESH_INTERVAL)
```

---

_Reviewed: 2026-06-18T16:00:00Z_
_Reviewer: OpenCode (gsd-code-reviewer)_
_Depth: standard_
