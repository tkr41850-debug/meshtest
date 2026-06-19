# Phase 7a: Display & Refresh Tuning

## Summary
Reduced auto-refresh from 30s to 10s, added per-check-type uptime percentage inline with latency values, and fixed matrix column headers to show meaningful short labels with hostname tooltips.

## Items Delivered

### Item 2: Auto-refresh 30s → 10s
- `REFRESH_INTERVAL = 30` → `10`
- All three cache TTLs `25` → `8`
- Indicator text: `"every 30s"` → `"every 10s"`

### Item 3: Per-check-type uptime in card display
- `_build_uptime_map()` now stores `(ping_uptime_pct, http_uptime_pct)` tuple instead of single max
- Card shows `Ping: 49.5ms (99.8%)` and `HTTP: 621.0ms (95.2%)` with color-coded percentages
- Separated uptime line removed from card
- Helper functions `_uptime_color()` and `_inline_uptime_html()` added for reuse

### Item 4: Matrix short labels with hover tooltip
- Short name extracted as: `tgt_ip.split(".")[0].rsplit("-", 1)[-1]`
- `title` attribute on `<th>` elements shows full hostname on hover

## Files Modified
- `mesh_status/dashboard.py`

## Verification
- All 53 tests pass (no regressions)
