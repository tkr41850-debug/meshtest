# Phase 7a: Display & Refresh Tuning - Context

**Gathered:** 2026-06-18
**Status:** Ready for planning

<domain>
## Phase Boundary

Tune dashboard display and refresh behavior: reduce auto-refresh from 30s to 10s, add per-check-type uptime percentage inline with latency values, and fix matrix column headers to show meaningful short labels with hostname tooltips.

</domain>

<decisions>
## Implementation Decisions

### Auto-Refresh Tuning
- Refresh interval reduced from 30s to 10s (`REFRESH_INTERVAL = 10`)
- Cache TTL reduced from 25s to 8s (slightly less than refresh interval)
- Indicator text updated: "every 30s" → "every 10s"

### Per-Check-Type Uptime Display
- `_build_uptime_map` returns both `ping_uptime_pct` and `http_uptime_pct` as a tuple
- Card display format: `Ping: 49.5ms (99.8%)` and `HTTP: 621.0ms (95.2%)`
- Separate uptime line removed from card
- If no 30d data available, show latencies without uptime % (backward compatible)

### Matrix Short Labels
- Short name extracted as: `tgt_ip.split(".")[0].rsplit("-", 1)[-1]`
  - e.g., `buldak-server-1.datawall.ai` → `1`
- `title` attribute on `<th>` elements shows full hostname on hover

### OpenCode's Discretion
- Color coding for uptime percentages inside card (reuse existing green/amber/red palette)
- HTML structure adjustments for inline layout

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `_build_uptime_map()` in dashboard.py:130-143 — currently returns single max uptime
- `_render_detail_card()` in dashboard.py:145-199 — currently shows uptime on separate line
- `_render_connectivity_matrix()` in dashboard.py:59-99 — currently uses `rsplit(".", 1)[-1]` for short names
- `REFRESH_INTERVAL` constant at dashboard.py:14

### Established Patterns
- All cache TTLs set to `REFRESH_INTERVAL - 5` (25s for 30s, 8s for 10s)
- HTML rendered via `st.markdown(..., unsafe_allow_html=True)`
- Color scheme: green `#22c55e` (≥99%), amber `#f59e0b` (≥95%), red `#ef4444` (<95%)

### Integration Points
- All changes isolated to `mesh_status/dashboard.py`
- No leader, node, or API changes needed

</code_context>

<specifics>
## Specific Ideas

- Matrix labels should be compact but informative — numeric suffix with hover title
- Uptime % should appear immediately after the relevant latency value, not on a separate line
- Per-check-type percentages allow ping vs http reliability comparison at a glance

</specifics>

<deferred>
## Deferred Ideas

- None — discussion stayed within phase scope

</deferred>
