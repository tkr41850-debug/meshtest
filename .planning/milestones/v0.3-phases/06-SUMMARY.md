# Phase 6: Frontend — Dashboard Bug Fix + UI Enhancement

## Summary
Fixed the Streamlit fragment rerun error and replaced the flat table rows with UptimeRobot-style status cards.

## Requirements Delivered
- **DASHF-01**: Removed `scope="fragment"` from `st.rerun()` — the `scope` parameter was removed in Streamlit 1.38+. Now uses plain `st.rerun()` (full script rerun).
- **DASHU-01**: Replaced per-target table rows inside expanders with styled detail cards. Each card shows:
  - Color-coded left border (green/amber/gray by status)
  - Status badge (pill-shaped, colored background)
  - Target IP (monospace, bold)
  - Ping + HTTP latency
  - Last check timestamp
  - Uptime % from 30d data (color-coded: green ≥99%, amber ≥95%, red <95%)

## Files Modified
- `mesh_status/dashboard.py` — `st.rerun()` fix, new `_render_detail_card` and `_build_uptime_map` helpers, `_render_30m_view` accepts `data_30d` param

## Notes
- 51 tests pass
- Existing connectivity matrix and 30-day view unchanged
