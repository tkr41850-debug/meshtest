# Phase 7a: Display & Refresh Tuning - Plan

## Tasks

### Task 1: Reduce auto-refresh from 30s to 10s
- Change `REFRESH_INTERVAL = 30` → `10` (line 14)
- Change cache TTL `25` → `8` (lines 17, 28, 39, comment updates)
- Update indicator text `"every 30s"` → `"every 10s"` (line 287)

### Task 2: Per-check-type uptime in card display
- Change `_build_uptime_map` to return `(ping_pct, http_pct)` tuple instead of single max
- Update `_render_detail_card` signature to accept both ping and http uptime pcts
- Change card HTML: `Ping: 49.5ms (99.8%)` and `HTTP: 621.0ms (95.2%)` with inline color
- Remove separate `{uptime_html}` line from card
- Update `_render_30m_view` callers to pass both pcts

### Task 3: Fix matrix short labels with hover tooltip
- Replace `rsplit(".", 1)[-1]` with `split(".")[0].rsplit("-", 1)[-1]`
- Add `title="{full_hostname}"` attribute to `<th>` elements

## Files Modified
- `mesh_status/dashboard.py`

## Verification
- Run existing tests: `python -m pytest tests/ -v`
- Verify no test regressions (all tests still pass)
