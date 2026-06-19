# Phase 9: Dashboard Views - Context

**Gathered:** 2026-06-19
**Status:** Ready for planning

<domain>
## Phase Boundary

Port all three Streamlit views (connectivity matrix, per-node-pair detail cards, 30-day daily aggregated uptime) from `mesh_status/dashboard.py` to the Vite + TypeScript + Tailwind CSS frontend in `frontend/`. The frontend fetches data from the existing same-origin API endpoints and renders interactive views with 10s auto-refresh.

</domain>

<decisions>
## Implementation Decisions

### Code Architecture
- **Modular file organization** — separate files for API client, types, views (matrix, cards, 30-day), and app entry
- **Dedicated `api.ts`** — typed fetch functions with error handling for `/data?window=30m`, `/data?window=30d`, `/node-list`
- **`types.ts`** — TypeScript interfaces for API response shapes (CheckResult, StatusEntry, DayAggregate, etc.)

### DOM Rendering
- **`innerHTML` with typed template functions** — each view renders via string templates assigned to container `.innerHTML`
- **Function-per-view architecture** — pure functions taking (data, containerElement) and rendering HTML

### Auto-refresh & State
- **Single `setInterval` in main.ts** — fetches all data, re-renders both views in one cycle
- **Stale-while-revalidate** — show loading text initially, keep old data visible during refresh, inline error on failure

### 30-Day View Layout
- **Nested expanders** — source node accordion, then per-target row with date columns (compact)
- **Color-coded badge showing best uptime %** — green/amber/red per v0.4
- **Diagonally split circle per protocol** — each cell shows a circle split diagonally, one half colored by ping uptime, the other by HTTP uptime
- **Click on circle scrolls to Phase 11 history** — add `id`/`data-*` anchor attributes for scrollTo integration with future uptime history visualization

### OpenCode's Discretion
- Exact file naming within `frontend/src/` directory
- CSS class naming conventions
- Error message copy

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `mesh_status/dashboard.py` — source of truth for view logic, data structure, color scheme, status logic
- `frontend/src/main.ts` — app entry point (currently stub)
- `frontend/src/style.css` — Tailwind theme with mesh-status colors (`mesh-green`, `mesh-amber`, `mesh-red`, etc.)

### Established Patterns
- Color scheme: green `#22c55e`, amber `#f59e0b`, red `#ef4444`, gray `#9ca3af`
- Status combination: both OK→green, either NotAvailable→amber, else gray/Pending
- Uptime thresholds: >=99% green, >=95% amber, <95% red
- API endpoints: `/data?window=30m`, `/data?window=30d`, `/node-list`, `/livez`
- Relative API URLs (same-origin, no CORS needed)
- Vite dev proxy configured for `/data`, `/node-list`, `/livez` → localhost:58080

### Integration Points
- `main.ts` — entry point where setInterval + initial render will live
- API responses from leader — same contract as consumed by dashboard.py
- Phase 11 will need `id`/`data-*` anchor attributes on 30-day cells for scrollTo integration

</code_context>

<specifics>
## Specific Ideas

- 30-day view cells use a diagonally split circle: left/upper half colored by ping uptime %, right/lower half by HTTP uptime %
- Each circle cell gets a `data-node-pair` and `id` attribute for Phase 11 scrollTo integration
- Keep the same status/uptime logic from dashboard.py (OK threshold = 3× check interval, combined status, etc.)
- Use `fetch()` with AbortController for timeout handling (5s per request)
- Tab switching between 30m and 30d views (matching v0.4 Streamlit tabs)

</specifics>

<deferred>
## Deferred Ideas

- Scroll-to-anchor integration from 30-day view cells to Phase 11 history visualization — implement `data-*` attributes now, wire scrollTo in Phase 11
- Mini sparkline in 30-day view — belongs in Phase 11

</deferred>
