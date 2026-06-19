# Phase 11: Uptime History Visualization - Context

**Gathered:** 2026-06-19
**Status:** Ready for planning

<domain>
## Phase Boundary

Add UptimeRobot-style history visualization per node pair using the 30-day data. Show daily uptime bars with ping/http split colors and an inline SVG sparkline for trend. Integrate with Phase 9's scrollTo anchors.

</domain>

<decisions>
## Implementation Decisions

### Visualization Type
- **CSS bar + inline sparkline grid** — horizontal row of 30 colored bars (one per day), each split diagonally for ping/http, followed by an inline SVG line chart showing trend
- **No charting library** — pure CSS/HTML/SVG

### Layout
- **Per-pair horizontal bars** — 30 bars in a row, each with `background: linear-gradient(...)` split per protocol
- **Sparkline below bars** — small SVG polyline showing uptime % trend over 30 days
- **Scroll-to anchors** from Phase 9 `data-node-pair` attributes — clicking 30-day split circle scrolls to the matching history section

### Interaction
- **30-day API** (`/data?window=30d`) — already fetched by main.ts, reuse same data
- **Per-pair `<details>` expanders** — nested under source node expanders
- **`title` attribute per bar** — shows date, ping %, http % on hover

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `frontend/src/views/day30.ts` — already renders 30-day data, has `data-node-pair` / `id` attributes for scrollTo
- `frontend/src/main.ts` — already fetches 30d data, passes to renderers
- `frontend/src/types.ts` — DayData, DayConnection interfaces

### Established Patterns
- Function-per-view renderer (same as matrix.ts, cards.ts, day30.ts)
- Tailwind theme tokens for colors
- `<details>` expander pattern
- innerHTML rendering

### Integration Points
- `main.ts` — add history container and render call
- Phase 9 day30.ts cells have `id="uptime-cell-{pairKey}"` for scrollTo

</code_context>

<specifics>
## Specific Ideas

- Match UptimeRobot style: horizontal bars colored by uptime %, green → amber → red
- Each bar = one day, split between ping (upper-left) and HTTP (lower-right)
- Sparkline = simple SVG polyline over 30 points
- ScrollTo: `document.getElementById(hash).scrollIntoView({ behavior: 'smooth' })` when 30-day cell is clicked
- Add `scroll-margin-top` to history sections for header offset

</specifics>

<deferred>
## Deferred Ideas

None

</deferred>
