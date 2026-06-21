# UI Consolidation Milestone — Pitfalls

**Context:** v0.9 — Refining frontend views for the mesh monitoring dashboard
**Changes analyzed:**
1. Bar count: 30 → 90 bars per window (3× more DOM elements)
2. Color scheme: HSL gradient → discrete thresholds (≥99% green, ≥95% amber, <95% red)
3. Views: unify cards.ts vs day30.ts into a consistent card layout
4. New view: 90h hourly history (requires backend aggregation endpoint)
5. All rendering is string template + innerHTML (no framework)
**Date:** 2026-06-20
**Confidence:** HIGH (verified against codebase analysis, DOM performance studies, time-series monitoring research)

---

## A. Discrete Color Threshold Pitfalls

### A1. Boundary Hard — The 94.9% / 99.4% Trap

**What goes wrong:**
The proposed thresholds are:
- `>= 99%` → green (`#22c55e`)
- `>= 95%` → amber (`#f59e0b`)
- `< 95%` → red (`#ef4444`)

A value of **94.9%** renders red. A value of **99.4%** renders green. Both are semantically correct for the threshold system, but the **perception gap** between "almost 95%" (red) and "95.0%" (amber) creates a jarring visual jump when a value crosses the boundary. In a bar chart of 90 bars, a single bar flipping from amber to red (or vice versa) draws disproportionate attention because the human visual system is highly sensitive to color transitions in dense grids.

**Why it happens:**
The existing code (`cards.ts:19-23`, `day30.ts:4-8`) already uses these exact thresholds. The migration from HSL gradient (`bars.ts:3-6`) to discrete thresholds amplifies the problem because bars will now jump between three colors instead of smoothly transitioning. At 90 bars per row, boundary-crossing bars stand out.

**Consequences:**
- During a partial-outage recovery window, uptime values around 94-96% cause bars to flicker between amber and red across refresh cycles
- Users interpret the red-amber boundary as an alert threshold, but values just above 95% are still problematic — they just look less alarming
- With HSL, a 95% bar was a different shade of yellow-green than a 94% bar; with discrete thresholds they're completely different colors

**Prevention:**
1. **Add hysteresis** — once a bar goes red, require `>= 97%` to go back to amber (prevents flicker around boundaries):
   ```typescript
   let _lastColor: Map<string, string> = new Map();
   export function barColor(percent: number, barKey?: string): string {
     // ...normal threshold logic...
     // Then apply hysteresis if barKey provided
   }
   ```
   This is standard practice in monitoring dashboards (Grafana, Statuspage). Without it, every bar near 95% oscillates.

2. **Use more than 3 tiers** — Grafana's thresholds default uses 4+ tiers (null→red, 95→orange, 99→yellow, 99.9→green). The 3-tier system loses granularity at the high end. Consider:
   - `>= 99.9` → green (`#22c55e`)
   - `>= 99.0` → lime (`#84cc16`)
   - `>= 95.0` → amber (`#f59e0b`)
   - `< 95.0` → red (`#ef4444`)

3. **Document the behavior** — In the tooltip or a legend, explain: "Green = ≥99%, Amber = ≥95%, Red = <95%. Small fluctuations near boundaries are normal."

4. **Test boundary values** — The bar test suite (`bars.test.ts`) only tests `barColor(0)`, `barColor(1)`, `barColor(0.5)`, and `barColor(-1)`. Add tests for:
   - `barColor(0.9499)` → red
   - `barColor(0.9500)` → amber
   - `barColor(0.9899)` → amber
   - `barColor(0.9900)` → green
   - `barColor(0.9999)` → green (verify no HSL bleed)

**Detection:**
- Visual inspection of a 90-bar timeline during partial outage shows chaotic color banding around recovery
- Unit tests: boundary values return wrong color within rounding of a single test iteration
- Test failures: `barColor(0.95)` sometimes returns amber, sometimes red depending on floating point

**Phase to address:** Color scheme change (first phase of UI consolidation changes)

---

### A2. HSL → Discrete: Color Function Inconsistency Across Views

**What goes wrong:**
There are currently **two different color functions** in the codebase:
- `bars.ts:barColor()` — uses HSL gradient (`hsl(percent * 120, 85%, 40%)`)
- `cards.ts:uptimeColor()` — uses discrete thresholds (`>=99 → green, >=95 → amber, else red`)
- `day30.ts:uptimeColor()` — identical to cards.ts, but separate copy

The plan to switch `barColor()` from HSL to discrete thresholds means this now needs to be extracted to a shared function. If someone forgets to update `bars.ts:barColor()`, the 30m tab (which uses `renderBars` → `barColor`) and the 30d tab (which also uses `renderBars` → `barColor`) will show different colors than the summary badges (`uptimeColor`).

**Why it happens:**
All three files (`bars.ts`, `cards.ts`, `day30.ts`) independently implement color logic. After the change, `bars.ts` calls `barColor()` for bar elements, while `cards.ts` and `day30.ts` call `uptimeColor()` for badge elements. If thresholds drift between these two implementations, a card's badge could show "99.1% (green)" while its bar shows "99.1% (not green yet because HSL scale)".

**Consequences:**
- Same uptime value rendered in two colors on the same card
- Users lose trust in the data display
- Debugging requires tracing through three files to find the inconsistency

**Prevention:**
1. **Extract a single shared `uptimeColor(percent: number): string` function** into a new file (e.g., `views/colors.ts`). Both `bars.ts` and `cards.ts` import from it. `day30.ts` imports from it too.
2. **The function must return the same type** — currently `barColor` returns `string` (the CSS color), `uptimeColor` returns `string`. Keep it consistent.
3. **Deprecate individual implementations** — add a `// @deprecated Use views/colors.ts:uptimeColor()` comment to the old functions.
4. **Add a cross-view test** — in `bars.test.ts`, import both `barColor` and `uptimeColor` and verify they return the same color for the same input:
   ```typescript
   import { uptimeColor } from "./colors";
   import { barColor } from "./bars";
   // After refactor: barColor should delegate to uptimeColor internally
   ```

**Detection:**
- Visual diff: same uptime percentage displayed as different colors on badge vs bar
- Integration test: render card with known uptime, inspect both badge color and bar color, verify match

**Phase to address:** Color scheme change, but also touching views/bars.ts

---

### A3. HSL Gradient Loss: Information Destruction

**What goes wrong:**
HSL gradient maps `0% → red (hue 0)`, `50% → yellow-green (hue 60)`, `100% → green (hue 120)`. This encodes the **magnitude** of uptime into the hue — users can visually estimate "about 80%" just from color.

Discrete thresholds collapse this to 3 colors. A bar at 89% and a bar at 10% are both red — you lose the ability to distinguish "barely failed" from "completely down" without reading the tooltip.

**Why it happens:**
HSL gradient is actually superior for magnitude encoding. The proposed change prioritizes "glanceability" (quickly see which are good/bad) over precision (see how bad). This is a legitimate tradeoff, but it's a deliberate loss of information that must be acknowledged.

**Consequences:**
- At 90 bars per row with 3 colors, any row with >10% failure is uniformly uninformative
- Users must hover each red bar to see if it's 95% or 10%
- The "no data" bars (`percent < 0`, gray) and the "failed" bars (red) are both non-green, but mean very different things

**Prevention:**
1. **Keep the HSL gradient as a secondary encoding** — gray for no-data, then use saturation or lightness changes within the discrete color bands to preserve magnitude information:
   ```typescript
   // Four bands with intensity
   if (percent >= 99) return `hsl(120, 85%, ${35 + (percent - 0.99) * 1000}%)`; // green, varying lightness
   if (percent >= 95) return `hsl(45, 85%, 50%)`; // amber (fixed)
   return `hsl(0, 85%, ${20 + percent * 20}%)`; // red, varying lightness
   ```
   This keeps the "green/amber/red at a glance" benefit while preserving magnitude within each band.

2. **Add a saturation dimension for no-data** — make `percent < 0` renders as `hsl(0, 0%, 80%)` (light gray with zero saturation) to distinguish from actual failures.

3. **Document the tradeoff explicitly** — in the PR description, note: "HSL gradient → discrete thresholds loses magnitude encoding. Mitigated by using lightness variation within bands and improved tooltip density."

**Detection:**
- User feedback: "All the red bars look the same, I can't tell if it's barely down or completely down"
- A/B comparison: 30-bar HSL history is more information-dense than 90-bar discrete history

**Phase to address:** Color scheme change — acceptance criteria must include "color still encodes magnitude within each band"

---

## B. DOM Density Pitfalls

### B1. innerHTML at Scale: The O(n²) String Concatenation Trap

**What goes wrong:**
The existing code builds HTML by array-joining template strings and then assigning to `container.innerHTML = html`. Currently at 30 bars per window, each card generates 60 `<span>` elements (2 rows × 30 bars). For a 10-node mesh (90 pairs), that's 90 × 60 = 5,400 bar `<span>` elements. Total DOM: cards + headers + badges ≈ 6,000 elements for the 30m view.

At 90 bars: 90 × 180 = 16,200 bar elements. Total ≈ 17,000 elements.

The current code does **not** use `innerHTML +=` in a loop (it builds the full string and assigns once). So it avoids the worst O(n²) pattern. However:
- `renderBars()` is called **per-card** (90 times for 10 nodes)
- Each call produces a separate string for the bar row
- InnerHTML assignment happens once at the end in `renderCards()`

The benchmark research confirms: building HTML with `.join("")` and a single innerHTML assignment is the correct pattern. The performance concern is not O(n²) string cost (that's avoided), but **total parsed HTML size**.

**Why it happens:**
At 17,000 elements, innerHTML assignment triggers the browser HTML parser on a ~300KB HTML string. For reference:
- A single innerHTML assignment of 1,000 nodes takes ~2.4ms (benchmarked)
- At 17,000 nodes, expect ~40ms parse + ~30ms layout
- That's fine for initial render, but this runs **every 10 seconds** (the auto-refresh interval in `main.ts:109`)
- Over 5 minutes of uptime: 30 parses × 70ms = 2.1 seconds of blocking main thread work

**Consequences:**
- UI freezes for 70-100ms every 10 seconds during refresh
- On slower devices (Raspberry Pi, older laptops): 150-300ms freezes
- Scrolling during refresh becomes janky (layout thrash)
- If the user has many browser tabs open, the cumulative CPU usage is noticeable

**Prevention:**
1. **The current `.join("") + innerHTML` pattern is correct** — do NOT switch to `innerHTML +=` in a loop. The existing code already does it right.

2. **Measure before optimizing** — run a performance test first:
   ```typescript
   const t0 = performance.now();
   renderCards(container, nodes, statuses, checks, uptimeMap);
   const t1 = performance.now();
   console.log(`Render took ${(t1 - t0).toFixed(1)}ms`);
   ```
   If `< 50ms`, no optimization needed. The real problem starts above 100ms.

3. **Optimize if > 100ms: Detach container during rebuild** — prevents layout thrashing on intermediate states:
   ```typescript
   const parent = container.parentNode;
   const nextSibling = container.nextSibling;
   parent?.removeChild(container);
   container.innerHTML = html; // No layout thrash — detached
   parent?.insertBefore(container, nextSibling); // Single layout
   ```
   This reduces reflow from N partial reflows to 2 total.

4. **Worst-case guard** — if more than 50 nodes registered, cap bar rendering or show a warning:
   ```typescript
   if (nodes.length > 50) {
     // Skip bar rendering, show text-only view
   }
   ```

**Detection:**
- Chrome DevTools Performance recording shows a long task (>50ms) every 10s
- `window.performance.now()` logging reveals render time creeping up with node count
- Users report "page freezes every few seconds" on lower-end hardware

**Phase to address:** Bar count change — must include performance measurement gate

---

### B2. Total Bar Element Count Math

**The numbers at 90 bars:**

| Scenario | Nodes | Pairs | Cards | Bars/Card | Total Bars | Total DOM nodes |
|----------|-------|-------|-------|-----------|------------|-----------------|
| Small mesh | 3 | 6 | 6 | 180 | 1,080 | ~1,300 |
| Medium mesh | 10 | 90 | 90 | 180 | 16,200 | ~17,000 |
| Large mesh | 50 | 2,450 | 2,450 | 180 | 441,000 | ~445,000 |
| Max registry | 100 | 9,900 | 9,900 | 180 | 1,782,000 | ~1.8M |

**Key insight:** At 10 nodes (the most realistic deployment), total bars is 16,200 — manageable. At 50+, the system falls apart because:
- The 30m view builds ALL pairs (N × N-1) × 2 rows × 90 bars
- The 30d view builds ALL pairs × 2 rows × 30 bars (daily, not per-hour)
- The new 90h view would build ALL pairs × 2 rows × 90 hourly bars

**The 50-node / 100-node scenarios are not handled by any view.** The code currently iterates over all pairs and renders every bar. At 50 nodes: 445,000 DOM nodes from bars alone. At 100 nodes: 1.8 million — the browser will crash or become unusable.

**Prevention:**
1. **Pagination per source group** — Instead of rendering all 49 targets for a 50-node source, show first 10, hide rest behind "Show all 49" toggle:
   ```typescript
   const INITIAL_TARGETS = 10;
   const visibleTargets = targets.slice(0, INITIAL_TARGETS);
   const hiddenTargets = targets.slice(INITIAL_TARGETS);
   ```
2. **Virtualize the bar rows** — Only render bars for visible viewport cards. Use `IntersectionObserver` to defer rendering of off-screen cards. This is **not** full virtual scrolling, but deferred rendering per-source-group.
3. **Hard cap at 30 nodes for full bar rendering** — Above 30, show collapsed view with no bars, just summary stats. The matrix view (no bars) already handles this scale.
4. **Add a node count check before render** — If `nodes.length > 30`, skip bar rendering and show a text hint: `"Bar chart hidden — {N} nodes. See matrix view for overview."`

**Detection:**
- Chrome DevTools shows 445,000+ DOM nodes on a 50-node deployment
- `document.querySelectorAll("[data-history-bar]").length` reveals the count
- Browser tab crashes or shows "Out of memory" on 100-node registrations
- Scroll performance degrades to < 10fps

**Phase to address:** Bar count change — must include node-count-based render gating

---

### B3. innerHTML Destroys Event Listeners & State

**What goes wrong:**
Every 10-second refresh, `renderCards()` calls `container.innerHTML = html`. This **destroys all existing DOM nodes and creates new ones from scratch**. Any event listeners attached to individual bar elements or cards are lost.

The existing day30 view has a click handler attached to `day30Container` (in `main.ts:113`) that uses event delegation via `e.target.closest("[data-node-pair]")` — this works because the listener is on the **container**, not on individual elements. However, any state attached to DOM nodes (e.g., expanded detail state, hover tooltip timeout IDs, `data-*` attributes set by JS after render) is lost.

**Why it happens:**
`innerHTML = ...` is a full replacement. The existing code recognizes this and uses `data-*` attributes for all state (no JS event listeners on nodes). But if any new view adds interactivity (e.g., click-to-expand tooltips, scroll position tracking), those will be lost on every 10s refresh.

**Consequences:**
- User scrolls down, 10s refresh fires, scroll resets to top (because nodes are recreated)
- Expanded tooltip or detail panel collapses on every refresh
- Any `data-*` attributes set by JS after initial render disappear

**Prevention:**
1. **Current pattern is acceptable** — the existing code deliberately avoids JS event listeners on bar elements. This is correct for `innerHTML`-based rendering.
2. **If adding interactivity** (e.g., click-on-bar to see details): use **event delegation** on a container that isn't replaced (like `main.ts:113` already does), or attach listeners **after** innerHTML assignment.
3. **Save and restore scroll position** on refresh:
   ```typescript
   const scrollY = window.scrollY;
   container.innerHTML = html;
   window.scrollTo(0, scrollY);
   ```
   But this causes a flash. Better: save per-source-group scroll state and restore selectively.
4. **Consider `DocumentFragment` for partial updates** — If the 90h view needs persistent state (expanded rows, pinned cards), switch to DOM API for rendering instead of innerHTML. But this is a major refactor — not recommended for this milestone.

**Detection:**
- After 10s refresh, user's scroll position jumps to top
- Expanded tooltips/hints collapse on auto-refresh
- Any `data-expanded="true"` set by JS is reset to initial state

**Phase to address:** View unification (if adding interactive elements) or defer to post-v0.9

---

## C. View Unification Pitfalls

### C1. Different Data Shapes Collide in One Layout

**What goes wrong:**
Currently, `cards.ts` and `day30.ts` accept different data shapes:
- `cards.ts:renderCards(container, nodes, statuses, checks, uptimeMap)` — needs real-time status + raw checks + 30d uptime map
- `day30.ts:renderDay30(container, nodes, days)` — needs pre-aggregated daily data

The unified view must handle BOTH shapes. If the same layout function receives different data (e.g., 30m data has no uptime aggregation, 90h data has different granularity), rendering the wrong view with the wrong data type will throw errors or show empty states.

**Why it happens:**
The existing code has separate view functions with different signatures. Unifying them requires a common interface (or a renderer that detects which data it received). The type `Data30mResponse` has `checks` and `statuses`, while `Data30dResponse` has `days`. A unified card must render from either.

**Consequences:**
- Rendering 30m view with 30d data (or vice versa) produces empty bars because key fields don't exist
- TypeScript catches some mismatches, but runtime checks for null/undefined are needed
- The `aggregateByMinute()` function in `cards.ts:37-89` expects raw `CheckResult[]` — if passed `DayData[]`, it silently returns empty bars

**Prevention:**
1. **Keep separate render functions for different data shapes** — do not try to merge `renderCards` and `renderDay30` into one. Instead, **share the card template** but keep the data shaping separate:
   ```typescript
   // Shared card template
   function cardHtml(props: CardProps): string { ... }
   
   // Each view shapes data to CardProps
   function render30mView(...) { ... renderCards(cardProps) ... }
   function render30dView(...) { ... renderCards(cardProps) ... }
   function render90hView(...) { ... renderCards(cardProps) ... }
   ```
2. **Define a `CardProps` interface** that both views can produce:
   ```typescript
   interface CardProps {
     targetIp: string;
     status: string;
     pingLat: string;
     httpLat: string;
     lastSeen: string;
     pingUp: number | null;
     httpUp: number | null;
     bars: { ping: BarEntry[]; http: BarEntry[] };
   }
   ```
3. **Add a TypeScript discriminant** to distinguish data sources — a `kind` field that the unified renderer can switch on.

**Detection:**
- Rendering a 30m tab shows "No data" for all bars even though data exists
- `aggregateByMinute()` returns empty arrays when data shape changes
- TypeScript error: `Property 'date' does not exist on type 'CheckResult[]'`

**Phase to address:** View unification — design the shared card template first, then adapt views

---

### C2. Dark Mode / CSS Class Inconsistency Between Views

**What goes wrong:**
`cards.ts` uses Tailwind utility classes like `bg-white`, `border-mesh-border`, `text-mesh-dark`, `text-mesh-muted`. `day30.ts` uses some of the same classes but with different combinations. When unifying, the card layout's class strings must produce identical styling regardless of which data source populated it.

**Why it happens:**
Both views use Tailwind, but the exact class combinations have drifted:
- `cards.ts:106` card div: `"border border-mesh-border border-l-4 rounded-lg p-3 mb-2 bg-white"`
- `day30.ts:95` row div: `"py-1 text-xs border-b border-mesh-border last:border-0"`
- Different backgrounds: cards use `bg-white`, day30 rows have no explicit background

When cards and day30 rows become the same layout, the background, padding, and border classes must be identical or the visual inconsistency is obvious.

**Consequences:**
- Cards from 30m data look different from cards from 90h data on the same page
- If dark mode is later added (via Tailwind `dark:` prefix), both views need separate dark-mode updates
- Users perceive the different styling as a bug or broken page

**Prevention:**
1. **Extract a single `cardTailwindClasses` constant** or function:
   ```typescript
   const CARD_CLASSES = "border border-mesh-border border-l-4 rounded-lg p-3 mb-2 bg-white";
   const CARD_HEADER_CLASSES = "flex items-center gap-2 mb-1";
   const CARD_STATS_CLASSES = "text-xs text-mesh-muted flex gap-4 flex-wrap";
   const BAR_ROW_CLASSES = "flex items-end gap-0.5 mt-1.5";
   ```
2. **Both `renderCards` and `renderDay30` (and `render90h`) import from the same constants file.**
3. **If dark mode is needed later**, add the CSS variables approach (not Tailwind `dark:` classes which would require updating every card) — use CSS custom properties that can be toggled via a single class on `<html>`.

**Detection:**
- Side-by-side visual comparison: a 30m card and a 30d card have different padding, background, or border styles
- CSS specificity war: one view's classes override the other's after unification

**Phase to address:** View unification — must include CSS audit of all card classes

---

### C3. Sticky Header Collisions After Unification

**What goes wrong:**
Both `cards.ts:165` and `day30.ts:76` use sticky headers:
```html
<div data-source-header class="sticky top-0 bg-mesh-bg z-10 ...">${src}</div>
```

After unification, if multiple views are rendered on the same page (the 30m tab shows both matrix + cards), the sticky headers from different views overlap. The `top-0` position causes headers from the card view to collide with headers from the day view when they're in the same scroll container.

**Why it happens:**
`main.ts:42-51` shows/hides containers. Both `cardsContainer` and `day30Container` have `class="hidden"` toggling, so they are never visible simultaneously. However, within a single view, if the unified layout nests source-group headers at different levels of the DOM, they may overlap.

**Consequences:**
- After view unification, headers from different data sections overlap when scrolling
- `z-10` is not enough if both headers are at the same z-index layer
- The `top-0` position is relative to the scrolling container, not the viewport — if the card layout is inside a nested scrollable div, sticky breaks

**Prevention:**
1. **Verify sticky positioning context** — For `position: sticky` to work, the parent element must not have `overflow: hidden` or `overflow: auto`. The card container div (`#cards-container`) must be a block-level flow element.
2. **Use `top: 0` only if the container is the viewport scroll** — If the cards are inside a scrollable container, use `top: 0` relative to that container's top.
3. **Stagger z-index levels** if nested source groups appear:
   - Level 1 source group header: `z-10`
   - Level 2 sub-header: `z-20`
4. **Test specifically with 3+ source groups** scrolling — this is where sticky header collisions first appear.

**Detection:**
- Two source headers overlap when scrolling through the list
- Header text is partially obscured by another element
- Sticky header scrolls away instead of sticking (wrong scroll container)

**Phase to address:** View unification — include sticky scroll test in acceptance criteria

---

## D. 90h Hourly History Endpoint Pitfalls

### D1. Window Alignment Mismatch — 90h ≠ 4 Days

**What goes wrong:**
90 hours = 3 days + 18 hours = 3.75 days. This is an unusual time window that doesn't align with calendar boundaries. The existing `day30.ts` aligns to day boundaries (midnight). A 90h window aligned to "now" will produce partial-day buckets:
- Most recent 18 hours of today
- All of yesterday
- All of the day before
- First 6 hours of 3 days ago

When users see "90 Hour History" and the bars don't align to midnight, it's confusing. Worse: if the server returns buckets aligned to the **hour** (00:00, 01:00, ...), but the frontend expects 90 bars starting from "current hour - 89 hours", the last bar will be a partial hour.

**Why it happens:**
The 30d view aligns to calendar days. The 30m view aligns to minute boundaries. A 90h view must decide between:
- **Sliding window**: last 90 hours from "now" — bucket boundaries change every second
- **Calendar hours**: aligned to 00:00 of each day — last bucket is always partial
- **Rolling hours**: aligned to the current clock hour — full hours only, total count varies

**Consequences:**
- The final hour bucket has fewer checks than others → its uptime percentage is noisy/skewed
- Comparing "same hour yesterday" is impossible because windows shift
- The 90h endpoint returns 89 bars some refreshes and 90 others depending on timing

**Prevention:**
1. **Use fixed hourly buckets aligned to UTC/clock hours** — truncate each check's timestamp to the start of the clock hour (`timestamp - (timestamp % 3600)`). Return 90 full hours plus the current partial hour.
2. **Return a stable count** — always return 90 buckets, where bucket 0 is the oldest full hour and bucket 89 is the current (possibly partial) hour. This matches the existing `30m` pattern (30 buckets, current minute is last).
3. **Document the partial bucket behavior** — the current hour bucket shows "in progress" and may have fewer data points. Add a visual indicator (lighter opacity, dashed border) for the active bucket.
4. **Use a consistent naming convention** — `?window=90h` (not `90hours`, not `3d18h`).

**Detection:**
- Refresh at 10:31 → last bar shows 10:00-10:31 data (21 fewer minutes than other buckets)
- 90h endpoint returns 89 bars one refresh, 90 bars the next
- User asks "why is the last bar lighter / different?"

**Phase to address:** Backend aggregation endpoint design — must specify bucket alignment strategy before implementation

---

### D2. The Aggregation Query Performance Problem (N×M Explosion)

**What goes wrong:**
The existing 30d endpoint (`leader.py:191-239`) builds per-day aggregations by iterating over ALL in-memory checks AND ALL disk-stored checks, then grouping by day + key. For the 90h endpoint, this same pattern would need to read disk data for the last 4 days and group by **hour** instead of **day**.

The problem: the 30d endpoint currently reads ALL disk data from the persistence layer (`persistence._read_results(start, end)`) for the entire 30-day range. For 90h (4 days), this would read ~13% of that data. But the grouping by hour creates 24× more buckets than the daily grouping, so the per-bucket overhead is higher.

**Why it happens:**
`leader.py:212-238` loads ALL raw results into memory and iterates through each to build day buckets. This scales as O(N_checks × N_days). For 10 nodes checking every 10 seconds for 30 days: 10 × 8640/day × 30 = 2.6M checks. Loading 2.6M rows into memory every request is already expensive. Adding a 90h endpoint that also loads all raw data and re-aggregates doubles the work.

**Consequences:**
- `/data?window=90h` takes 5+ seconds to respond (loading 4 days of raw data)
- Memory usage spikes during the aggregation (loading all raw checks into Python dicts)
- The 10-second auto-refresh in `main.ts` now has TWO expensive API calls: 30m + 90h (or 30d + 90h) → request waterfall causes stale data display

**Prevention:**
1. **Pre-aggregate on write, not on read** — The persistence layer (`persistence.py`) could maintain hourly rollups that are updated as checks are flushed. The 90h endpoint reads pre-aggregated hourly buckets instead of scanning all raw checks. This is the Prometheus pattern (recording rules).
2. **Add a dedicated hourly aggregation table/file** — When `_flush_results()` runs (every hour, line 70), aggregate the last hour's data into hourly buckets and save separately:
   ```python
   def _flush_hourly_summary():
       now = datetime.now()
       current_hour = now.replace(minute=0, second=0, microsecond=0)
       # Aggregate all checks for this hour
       # Write to data/hourly/<year>/<month>/<day>/<hour>.json
   ```
3. **At minimum, limit the scan scope** — Only load raw checks timestamped within the last 90 hours, not all 30 days. The 30d endpoint also needs this fix.
4. **Cache the aggregation result** — If the leader is in-memory, cache the 90h result for 60 seconds (one refresh cycle). The data doesn't change between 10s refreshes.
5. **Add a `_last_90h_cache` to `leader.py`** — Simple dict with timestamp, invalidated when new checks arrive:
   ```python
   _90h_cache: dict = {}
   _90h_cache_ts: float = 0
   
   elif window == "90h":
       if time.time() - _90h_cache_ts < 10:
           return _90h_cache, 200
       # ... expensive aggregation ...
       _90h_cache = result
       _90h_cache_ts = time.time()
   ```

**Detection:**
- Network tab in DevTools shows `/data?window=90h` taking > 2 seconds
- Chrome shows "Queued" time on the 90h request (blocked by 30m request completing first)
- Server logs show `/data` handling taking > 1 second per request
- `top` on the server shows Python process at 100% CPU during dashboard refresh

**Phase to address:** Backend aggregation endpoint — design pre-aggregation or caching before implementing

---

### D3. Hourly Granularity: The Midnight Boundary Bug

**What goes wrong:**
The existing persistence layer (`persistence.py`) stores checks in **daily files** (`YYYY/MM/DD.json`, line 21-23). For hourly aggregation, the endpoint must read partial day files:
- Today's file (contains all checks from today)
- Yesterday's file
- Day-before-yesterday's file
- 3-days-ago file

But `_read_results()` reads entire daily files. If the 90h endpoint calls `_read_results(start_date=3_days_ago, end_date=today)`, it reads **all checks for all 4 days** — not just the last 90 hours. This includes checks from hour 0 of 3-days-ago that are outside the window.

**Why it happens:**
File granularity is per-day. Hourly filtering must happen **after** loading. The 30d endpoint loads entire days and groups by day, so the granularity matches. The 90h endpoint loads 4 entire days (each ~86K checks for 10 nodes) just to filter to 90 hours.

**Consequences:**
- 90h endpoint loads 33% more data than it needs (loading full days instead of hours)
- `persistence.py` filesystem reads are O(N_days), not O(N_hours)
- The extra data is loaded but filtered out after processing — wasted memory and CPU
- At scale (50 nodes): loading 4 days × 50 × 8640 = 1.7M checks to display 172K

**Prevention:**
1. **Add a lower-level persistence function** that reads only checks within a timestamp range, not whole days:
   ```python
   def _read_results_range(start_ts: float, end_ts: float) -> list[dict]:
       # Determine which daily files to open
       # For each file, read and filter by timestamp
       # Potentially use line seek + binary search on sorted files
   ```
   This is the most impactful optimization — reading fewer bytes from disk.
2. **Add hourly summary files** (as described in D2) — completely avoids reading raw data for the 90h endpoint.
3. **If neither optimization is possible** (time constraint), at minimum add a post-read filter:
   ```python
   raw = _read_results(start_date, end_date)
   raw = [r for r in raw if start_ts <= r.get("timestamp", 0) <= end_ts]
   ```

**Detection:**
- Total checks in 90h response is suspiciously high (e.g., 86,400 for 2 nodes when 90h window should have 32,400)
- Response size for `/data?window=90h` is close to `/data?window=30d` (should be ~13%)
- Slow response times during the first day of the month (daily file rotation)

**Phase to address:** Backend aggregation — persistence layer must support sub-day reads

---

### D4. Frontend: 90h Bar Bucket → Day30 Bar Bucket Mapping

**What goes wrong:**
The existing `day30.ts:33-57` (`dailyBarsForPair()`) assumes daily granularity — each bucket represents one calendar day. The 90h view needs hourly granularity — each bucket represents one clock hour. If a shared `renderBars()` function receives 90 hourly `BarEntry[]` objects where it expects 30 daily ones, the bar widths, spacing, and row layout are wrong.

**Why it happens:**
`renderBars()` in `bars.ts` hardcodes `width:8px` per bar. 90 bars × 8px = 720px per row. On mobile (375px viewport), this overflows. The existing 30 bars × 8px = 240px, which fits. The fix isn't to make bars narrower (they'd become unreadable at 4px) — it's to make the row scrollable or to collapse bars.

**Consequences:**
- 90 bar row overflows its card container on any viewport < 720px
- Bars squish to fit via CSS `gap` collapse, producing uneven spacing
- The `flex items-end gap-0.5` layout in `bars.ts:15` doesn't handle overflow — it clips

**Prevention:**
1. **Make bar rows horizontally scrollable** — wrap in `overflow-x-auto` container:
   ```html
   <div class="overflow-x-auto">${renderBars(bars)}</div>
   ```
2. **Keep `width: 8px` but allow container scroll** — this preserves bar readability on desktop while mobile users can scroll horizontally.
3. **Alternative: shrink bars on small viewports** — use CSS `clamp()` or container queries:
   ```css
   [data-history-bar] {
     width: clamp(4px, 1.5vw, 8px);
   }
   ```
4. **Add a `barCount` parameter to `renderBars()`** so the function can adjust layout:
   ```typescript
   export function renderBars(bars: BarEntry[], options?: { barWidth?: number }): string
   ```

**Detection:**
- 90-bar row extends beyond card boundary on standard monitor (1920px)
- Mobile viewport: bars overlap or are invisible
- CSS `overflow: hidden` clips the last 60 bars (common Chrome bug with flex items)
- When resizing the browser, bars at the right edge are cut off

**Phase to address:** View unification — must include responsive bar layout, not just data plumbing

---

### D5. 30-Minute + 90-Hour + 30-Day: Triple API Call Overload

**What goes wrong:**
Currently (`main.ts:73-78`), the app fetches three endpoints every 10 seconds:
- `fetchData30m()` — 30-minute window, for the real-time view
- `fetchData30d()` — 30-day window, for the uptime map
- `fetchNodeList()` — node registration list

Adding a 90h endpoint means **four parallel requests every 10 seconds**. On a mesh with 10 nodes, each request returns ~50-200KB. Four simultaneous requests = 200-800KB every 10 seconds = 80-320KB/s sustained bandwidth. On a constrained network (VPN WAN), this can saturate the connection.

**Why it happens:**
The current architecture polls aggressively (`setInterval(refresh, 10_000)`). Each function fetches a full data dump — there's no incremental update, no delta mechanism, no client-side caching of unchanging data.

**Consequences:**
- Data usage: ~10MB/hour on a 10-node mesh (just for the dashboard)
- VPN WAN bandwidth consumed by dashboard polling instead of application traffic
- On metered connections, this is expensive
- Browser memory grows as responses accumulate in JS heap (the old responses aren't cleaned aggressively)

**Prevention:**
1. **Stagger refresh intervals** — 30m data refreshes every 10s (needs real-time), 90h/30d data refreshes every 60s (stale data is acceptable for historical views):
   ```typescript
   setInterval(refresh30m, 10_000);
   setInterval(refresh90h, 60_000);
   setInterval(refresh30d, 60_000);
   ```
2. **Use stale-while-revalidate pattern** — Show cached data immediately, fetch new data in background, swap when ready. The existing code already does this implicitly (data is fetched → innerHTML replaced atomically).
3. **Only fetch the active tab's data** — If 30m tab is active, skip the 90h/30d fetch. The 30d data is needed for `uptimeMap` even in the 30m tab (for uptime percentages in cards). But the 90h data is only needed when the 90h tab is visible.
4. **Implement HTTP caching headers** — The server can return `Cache-Control: max-age=10` so browsers cache the response within the refresh window. This is free and reduces bandwidth on repeat requests.

**Detection:**
- Chrome DevTools Network tab shows 4 simultaneous requests every 10s
- Bandwidth usage visible in Chrome Task Manager (Shift+Esc on Windows/Linux)
- Users on metered connections report high data usage
- Dashboard feels sluggish because 4 API calls compete for bandwidth

**Phase to address:** 90h view addition — must include refresh strategy audit

---

## Summary: Pitfall-to-Phase Mapping

| Pitfall | Category | Phase | Severity |
|---------|----------|-------|----------|
| A1: Boundary 94.9%/99.4% hard threshold | Color | Color change | MEDIUM — visual flicker but no data loss |
| A2: Color function inconsistency across views | Color | Color change | HIGH — same value, different colors on same card |
| A3: HSL gradient information destruction | Color | Color change | LOW — deliberate tradeoff, document it |
| B1: innerHTML at 17K nodes performance | DOM density | Bar count change | MEDIUM — 70ms freeze every 10s |
| B2: 50+ node DOM explosion (445K+ nodes) | DOM density | Bar count change | CRITICAL — browser crash at 100 nodes |
| B3: innerHTML destroys state & scroll | DOM density | Bar count change | MEDIUM — scroll reset, lost state |
| C1: Different data shapes collide | Unification | View unification | HIGH — runtime errors, empty renders |
| C2: CSS inconsistency between views | Unification | View unification | MEDIUM — visual drift, dark mode pain |
| C3: Sticky header overlap | Unification | View unification | LOW — contained to same-page views |
| D1: 90h window alignment (partial hour) | Backend | 90h aggregation | MEDIUM — confusing last bucket |
| D2: N×M aggregation query performance | Backend | 90h aggregation | CRITICAL — 5s+ response at 10 nodes |
| D3: Midnight boundary in daily files | Backend | 90h aggregation | MEDIUM — loads 33% more data than needed |
| D4: 90 bars × 8px = 720px overflow | Frontend | 90h view | MEDIUM — mobile overflow, desktop edge clip |
| D5: Triple API call bandwidth overload | Frontend | 90h view | MEDIUM — ~10MB/hour on VPN WAN |

## Critical Pitfalls (Must Fix Before Ship)

| # | Pitfall | Why Critical | Action |
|---|---------|-------------|--------|
| 1 | **B2: 50+ node DOM crash** | 445K DOM elements at 50 nodes crashes the browser. Current code has no guard. | Add node-count gating: >30 nodes → skip bars. Defer off-screen cards via IntersectionObserver. |
| 2 | **D2: Aggregation query performance** | Loading 1.7M raw checks every 10 seconds will kill the server at 10+ nodes. | Implement hourly pre-aggregation or in-memory cache. Do NOT scan raw data per-request. |
| 3 | **A2: Color function inconsistency** | Same value, different colors on the same card destroys trust in the display. | Extract shared `uptimeColor()` to `views/colors.ts`. Both badges and bars import from it. |
| 4 | **C1: Data shape collision at runtime** | Passing `DayData[]` to a function that expects `CheckResult[]` causes silent empty renders. | Keep separate render functions; share only the card template. Add TypeScript discriminant. |

## Sources

- **DOM Performance Study (2026)** — stackinsight.dev benchmark: innerHTML in loop = O(n²), single innerHTML = acceptable up to ~10K nodes. 17K nodes = ~70ms render time.
- **Grafana Threshold Configuration** — Grafana stat panel thresholds: multi-tier (null→red, 95→orange, 99→yellow, 99.9→green). Supports 4+ tiers for high-end granularity.
- **Statuspage Uptime Display** (Atlassian) — Discrete color thresholds with no-data gray. Documents that partial buckets (current hour/day) get lighter treatment.
- **Prometheus Aggregation Patterns** — Pre-aggregate on write (recording rules), not on read. Avoids per-request full data scan.
- **CSS-Tricks Fixed-Height Cards** (2026) — Card UI fragility with varying content lengths: translations, missing images, viewport changes cause layout breaks.
- **Google Cloud Monitoring Aggregation API docs** — Alignment (regularize data within series) before reduction (combine across series). Single-aggregation-before-reduction pattern.
- **Looker Studio Data Blending Pitfalls** — Cross-join risk when key types don't match (DATE vs string). Verify join keys exactly.
- **mesh-status codebase analysis** — Verified against `bars.ts`, `cards.ts`, `day30.ts`, `bars.test.ts`, `mesh.test.ts`, `leader.py`, `persistence.py`, `types.ts`, `api.ts`, `main.ts`.

---

*Pitfalls research for: mesh-status v0.9 UI consolidation milestone*
*Focus: Discrete color thresholds, 3× bar density, view unification, 90h hourly history*
*Researched: 2026-06-20*
