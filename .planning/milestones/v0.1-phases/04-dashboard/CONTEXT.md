# Phase 4: Streamlit Dashboard - Context

**Gathered:** 2026-06-18
**Status:** Ready for planning
**Mode:** Smart discuss (autonomous)

<domain>
## Phase Boundary

Build a Streamlit dashboard that visualizes mesh connectivity in real-time (30-minute window) and historically (30-day window) by consuming the leader's data API. Support two views (30-minute raw checks + per-pair statuses, 30-day daily aggregated uptime), auto-refresh with fragment-based partial reruns, cached data loading, and clear visual status distinction (OK/Pending/NotAvailable).

</domain>

<decisions>
## Implementation Decisions

### Serving Mode
- Streamlit served standalone via `streamlit run` (not spawned from leader)
- Port 58581
- Leader URL configured via `LEADER_URL` environment variable
- Deployment documented in README with `streamlit run` command and `LEADER_URL` setup

### Layout & Navigation
- Tabs: `st.tabs(["30-Minute View", "30-Day View"])`
- Connectivity matrix: table (row=source, col=target, cell=colored status indicator)
- Status colors: Green=OK, Yellow=NotAvailable, Gray=Pending
- Per-peer detail: expandable rows (`st.expander`) showing latency + last check time

### Data Loading & Refresh
- Auto-refresh interval: 30 seconds
- `@st.cache_data(ttl=30)` for 30-minute view
- Single `@st.fragment` wrapping both tab contents
- Loading state: "Loading mesh data..." skeleton text

### Error Handling & UX
- Leader unreachable: banner "⚠ Leader unreachable — showing cached data", keep stale data visible
- No data available: "No data available for this time window" message
- Diagonal cells (self-to-self): Gray "—"

### OpenCode's Discretion
- Specific column widths, font sizes, padding within cells
- Exact color hex values for status indicators
- Streamlit theme configuration (config.toml or inline)

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `GET /data?window=30m` endpoint — returns raw checks + per-pair statuses
- `GET /data?window=30d` endpoint — returns daily aggregated per-pair uptime
- `mesh_status/status.py` — status calculation logic (OK/Pending/NotAvailable)
- `mesh_status/config.py` — LEADER_PORT, CHECK_INTERVAL

### Established Patterns
- Quart with CORS enabled (data API already supports cross-origin)
- httpx for async HTTP (not used by dashboard — Streamlit uses `requests` or `httpx` sync)
- Env-based configuration pattern from register.py (LEADER_URL)

### Integration Points
- `http://<leader-ip>:58080/data?window=30m` — 30-minute data
- `http://<leader-ip>:58080/data?window=30d` — 30-day data
- `http://<leader-ip>:58080/node-list` — node list for matrix axes

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard Streamlit dashboard approaches.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>
