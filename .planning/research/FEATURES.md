# Feature Landscape: UI Consolidation (v0.9)

**Domain:** Mesh connectivity monitoring dashboard — per-pair card views across multiple time windows
**Researched:** 2026-06-20
**Mode:** Ecosystem investigation for refinement of existing views (90m/90h/90d)
**Overall confidence:** HIGH — patterns verified against Grafana dashboard best practices, shadcn/ui monitoring blocks, and uptime monitoring industry conventions

## Context

This research targets a **subsequent milestone** refining existing frontend views. Current state has two views with different layouts and coloring strategies. Target is to unify display language, switch to discrete threshold coloring, and extend to three time windows with consistent 90-bar history rows.

### Current Codebase State (Baseline)

| View | Current Window | Layout | Bar Coloring | Split Circle | Check Count |
|------|---------------|--------|-------------|-------------|-------------|
| cards.ts | 30 × 1-min | Per-pair cards, left-border color | HSL gradient (red→green) | No | No |
| day30.ts | 30 × 1-day | Per-day rows grouped by node | HSL gradient (red→green) | Yes (per-day) | Yes (per-day) |

### Target State

| View | Window | Bars | Layout | Bar Coloring | Split Circle | Check Count |
|------|--------|------|--------|-------------|-------------|-------------|
| 90m | 90 × 1-min | 90 bars | Unified cards | Discrete threshold | Yes (per-window) | Yes (per-window) |
| 90h | 90 × 1-hour | 90 bars | Unified cards | Discrete threshold | Yes (per-window) | Yes (per-window) |
| 90d | 90 × 1-day | 90 bars | Dense cards | Discrete threshold | Yes (per-window) | Yes (per-window) |

---

## Table Stakes

Features users expect from a monitoring dashboard. Missing these = product feels incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Multiple time windows** | Monitoring requires both recent signal (minutes) and trend (days) | LOW | Already exists (30m/30d). Adding 90h is incremental |
| **Per-pair card layout** | User needs to see connectivity between specific node pairs | LOW | Already exists in cards.ts. Standard for mesh/network monitoring |
| **Status at a glance** | Green/amber/red for healthy/degraded/down — color is the primary signal | LOW | Already exists with different strategies in each view. Need unified thresholds |
| **History bar rows** | The universal "uptime timeline" pattern — small colored bars showing availability over time | LOW | Already exists in bars.ts. Need threshold recoloring |
| **Uptime percentage** | Numeric certainty alongside visual signal | LOW | Already exists in both views |
| **Auto-refresh** | Short-window views must stay current without manual reload | LOW | Already exists (10s interval in main.ts). 90h/90d may use longer intervals |
| **Node identity** | IP or hostname for each pair | LOW | Already displayed |
| **Source-group grouping** | Cards grouped by source node with sticky header | LOW | Already exists in cards.ts. Works well |
| **No-data handling** | Gaps in data shown as gray bars, not missing rows | LOW | Already exists (percent: -1 → gray bar) |
| **Responsive bar wrapping** | Bars wrap gracefully when viewport is narrow | MEDIUM | Currently inline spans wrap naturally. 90 bars is wider — may need overflow-x on long windows |

### Table Stakes Derived from Industry Monitoring Dashboards

| Feature | Why Expected | Source |
|---------|-------------|--------|
| **Threshold-based colors** not gradients | Discrete boundaries (green/amber/red) give actionable signal vs pretty gradients | Grafana best practices, every major uptime tool |
| **Consistent layout across time windows** | Switching windows shouldn't reorient the user — same visual hierarchy | Grafana "consistency by design" principle |
| **Same information hierarchy per window** | Split circle, badge, uptime %, check count, bar row — in that order, every time | shadcn/ui uptime blocks, IsDown, Uptime Kuma |
| **Clickable to drill down** | 90d → 90h → 90m drill-down path for incident investigation | Standard observability UX (Grafana, Datadog) |

---

## Differentiators

Features that set mesh-status apart. Not universally expected, but valued by users of a mesh connectivity monitoring tool.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Split circle (ping | HTTP)** | Instant visual of both protocol health in one glyph. Unique to this tool — most monitors show single protocol | LOW | Already exists in day30.ts. Reuse pattern, move to per-pair-card level (not per-day) |
| **Discrete threshold bar coloring** | More actionable than gradient. Every bar is green (≥99%), amber (≥95%), or red (<95%). At 30ft you can count red vs green | LOW | Requires changing ~4 lines in bars.ts. High value for low cost |
| **90-bar consistency across windows** | Same bar count for 90m, 90h, 90d creates muscle memory. User learns "90 bars = one full window" | LOW | Just math — same aggregate logic, different bucket sizes |
| **Ping + HTTP dual metrics per card** | Two protocol views in one card (ping bars row, HTTP bars row). Richer signal than single-protocol monitors | LOW | Already exists. Just needs layout consistency |
| **Check count in card header** | Total checks in window gives confidence signal — "100% from 1 check" vs "100% from 500 checks" are different signals | LOW | Already in day30.ts per-day. Move to per-pair-card level |
| **Status badge with discrete color** | "OK" / "Degraded" / "Down" label with matching color in a pill badge | LOW | Already in cards.ts. Ensure consistent threshold logic across all views |
| **Source-group headers sticky** | Scroll through many pairs, always know which source node you're looking at | LOW | Already works in both views |

### Additional Differentiators to Consider

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Summary row per source group** | At top of each source-group, show aggregate: "3 of 5 pairs degraded" or "All OK" | LOW | Currently per-source summary shows text only. Could make it a clickable pivot |
| **Card left-border color matches status** | Strong left-edge color stripe that matches the badge. Fast scan signal for OK/NotAvailable/Pending | LOW | Already in cards.ts, will need to carry forward |
| **Empty state differentiation** | "No data yet" vs "No nodes registered" vs "Window has no data" | LOW | Already partially exists. Standardize across all views |
| **Window label in card** | Subtle "90m" / "90h" / "90d" label so user knows what window they're viewing | LOW | Helpful when screenshotting or sharing |

---

## Anti-Features

Features to explicitly NOT build for this milestone.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| **HSL gradient bars** | Pretty but less actionable than thresholds. A bar at 97% (amber threshold) may look nearly green in gradient (hue ~116°) | Discrete threshold coloring — every user sees the same color for the same data value |
| **Animated bar transitions** | Added visual load with zero information gain. Monitoring is quiet scanning, not a screensaver | Static colors, instant render. No fade-in, no pulse |
| **Custom chart library (Chart.js, D3)** | 90 history bars are colored `<span>` elements. Adding a chart library for this is massive overkill | Current approach (pure DOM + CSS) handles this perfectly. No dependencies needed |
| **Per-second granularity** | 90 bars at sub-minute granularity is too dense for human perception. Bars must represent meaningful intervals | 1-min (90m), 1-hour (90h), 1-day (90d) buckets — each bar is a clearly understandable unit |
| **3D or gauge visualizations** | Gauges look impressive in demos but tell on-call engineers nothing actionable about mesh connectivity per-pair | Bar rows + percentage text. Simple, honest, actionable |
| **Dark mode** (for this milestone) | Scope creep. Requires theming all cards, badges, bars, headers. Zero behavioral change | Defer to dedicated UI polish milestone. Current light theme is consistent |
| **Sorting/filtering/pagination** (for this milestone) | Would need per-pair state management, sort controls, search. Substantial scope increase. | Defer. Current alphabetical ordering is predictable. Can add later without layout redesign |
| **Interactive bar hover tooltips** | Nice to have but 90 tooltips per bar row creates cognitive density. User can estimate from bar color | Keep current hover tooltip style (shows exact time + percentage) |
| **Clickable bars to zoom** | Full drill-down (90d → 90h → 90m → raw data) requires backend time-series queries that don't exist yet | Defer to future milestone when backend supports window-scoped data endpoints |

---

## Feature Definitions: The Three Views

### 90m View (Short Window — "What's happening right now?")

**Purpose:** Near-real-time mesh connectivity status. Answers "Is the mesh healthy right now?"

**Refresh interval:** 10s (same as current)

**Data source:** `GET /data?window=90m` — returns per-minute aggregate of raw checks

**Card layout (per pair):**

```
┌───────────────────────────────────────────────────────────────┐
│ [○]  OK  192.168.1.10                                   90m  │
│ Ping: 12.3ms  100%   HTTP: 45.6ms  99.2%   Checks: 540      │
│ Last: 14:32:01                                              │
│ ████████████████████████████████████████████████████████████  │  ← 90 bars, ping
│ ████████████████████████████████████████████████████████████  │  ← 90 bars, http
└───────────────────────────────────────────────────────────────┘
```

**Card elements (left to right, top to bottom):**

| Element | Position | Description |
|---------|----------|-------------|
| **Split circle** | Far left, first visual | Diagonal split (135° gradient): ping on top-left, HTTP on bottom-right. Each half colored by window uptime threshold |
| **Status badge** | Right of split circle | "OK" / "Not Available" / "Pending" pill with discrete color. Derived from latest live check |
| **Target IP** | Right of badge | Monospace, the remote node IP |
| **Window label** | Far right of top row | "90m" in subtle muted text — context for the bar count |
| **Latency line** | Row 2 | Ping latency + uptime %, HTTP latency + uptime %, total check count |
| **Last seen** | Row 2, right side | `HH:MM:SS` or "—" if never seen |
| **Ping bar row** | Row 3 | 90 × 1-minute bars, threshold colored, wrapped |
| **HTTP bar row** | Row 4 | 90 × 1-minute bars, threshold colored, wrapped |

**Behavior:**
- Latency is meaningful here (recent data within seconds)
- Status badge reflects live check (could differ from window uptime)
- Scroll within source-group for many pairs
- Card left-border color matches status badge

### 90h View (Medium Window — "How's the mesh been today?")

**Purpose:** Intra-day trend visibility. Answers "Has the mesh been stable through this shift?"

**Refresh interval:** 60s (hourly aggregation doesn't change quickly)

**Data source:** `GET /data?window=90h` — returns per-hour aggregate

**Card layout (per pair):**

```
┌───────────────────────────────────────────────────────────────┐
│ [○]  Degraded  192.168.1.10                             90h  │
│ Ping: 97.2%   HTTP: 94.8%   Checks: 3,240                 │
│ ████████████████████████████████████████████████████████████  │
│ ████████████████████████████████████████████████████████████  │
└───────────────────────────────────────────────────────────────┘
```

**Card elements:**

| Element | Position | Description |
|---------|----------|-------------|
| **Split circle** | Far left | Aggregate ping+HTTP uptime for the 90h window |
| **Status badge** | Right of circle | Window-level status: "OK" if both ≥99%, "Degraded" if either <99%, "Down" if either <95% |
| **Target IP** | Right of badge | Same format |
| **Window label** | Far right | "90h" |
| **Uptime line** | Row 2 | Ping uptime %, HTTP uptime %, total check count. No latency (too aggregated to be meaningful) |
| **Ping bar row** | Row 3 | 90 × 1-hour bars |
| **HTTP bar row** | Row 4 | 90 × 1-hour bars |

**Behavior:**
- No latency shown — hourly aggregates blur latency into averages, which is misleading
- Status badge reflects WINDOW status, not live status (unlike 90m)
- Bars represent 1-hour windows — a red bar means that hour had <95% uptime

### 90d View (Long Window — "Is the mesh trending down?")

**Purpose:** Long-term trend and SLA monitoring. Answers "Is reliability improving or degrading?"

**Refresh interval:** 300s (5 min) — daily data changes infrequently

**Data source:** `GET /data?window=90d` — returns per-day aggregate

**Card layout (per pair) — compact variant:**

```
┌─────────────────────────────────────────────────────────┐
│ [○]  99.2%  192.168.1.10  Checks: 25,920  90d         │
│ ████████████████████████████████████████████████████████ │  ← 90 bars, 6px width
│ ████████████████████████████████████████████████████████ │
└─────────────────────────────────────────────────────────┘
```

**Card elements:**

| Element | Position | Description |
|---------|----------|-------------|
| **Split circle** | Far left | Overall 90d ping+HTTP uptime |
| **Badge (uptime %)** | Right of circle | Numeric badge showing the WORST of ping/http uptime, threshold colored (e.g., "99.2%" in green) |
| **Target IP** | Right of badge | Same format |
| **Check count + window** | Right of IP | "Checks: 25,920" + "90d" |
| **Ping bar row** | Row 2 | 90 × 1-day bars, **6px width** for compactness |
| **HTTP bar row** | Row 3 | 90 × 1-day bars, **6px width** |

**Behavior:**
- More compact card (single header row, no secondary metrics row)
- **6px bars** instead of 8px to fit 90 bars in the card width (90 × 8px = 720px vs 90 × 6px = 540px)
- Bar border reduced or removed for compact bars
- No latency (meaningless at daily granularity)
- The badge is the window uptime percentage (numeric), not the live status label
- Split circle + badge gives "instant read + exact number" pairing

### Layout Comparison: Cards vs Rows

| Criterion | Cards (90m/90h) | Dense Cards (90d) | Rows (current 30d approach) |
|-----------|-----------------|-------------------|------------------------------|
| Visual separation per pair | ✅ Strong — border + whitespace isolates each pair | ✅ Strong — border isolates each pair | ❌ Weaker — rows run together |
| Per-pair identity | ✅ Header makes pair identity clear | ✅ Header makes pair identity clear | ❌ Target IP is a column value, easy to misalign |
| Dense long-window display | ❌ 90 × 2 bars + padding = tall cards | ✅ Tighter = fits more pairs on screen | ✅ Most compact (day rows grouped by date) |
| Cross-pair comparison | ❌ Pairs are stacked, harder to compare | ❌ Same limitation | ✅ Same row structure makes date-aligned comparison easy |
| Scanning for anomalies | ✅ Each card has left-border color as scan signal | ✅ Same | ❌ Must scan multiple rows |
| Familiar mental model | ✅ Users know "one card = one pair" | ✅ Same | ❌ Row model requires visual tracking |

**Recommendation: Use cards for all three views.** The "dense cards" variant for 90d adjusts bar width and removes the redundant secondary metric line, but maintains the same card-based layout. This satisfies the "unify display" requirement while being practical for long-window density.

---

## Feature Dependencies

### Component Dependency Graph

```
shared/barColor()
    └── required by: all views (bars.ts → threshold coloring)
    └── replaces: current HSL gradient

shared/uptimeColor()  -- already exists in cards.ts and day30.ts
    └── used by: splitCircle(), badgeHtml(), uptimeSpan()
    └── needs: single source of truth (extract to shared)

views/splitCircle()  -- exists in day30.ts
    └── needs: extract from day30.ts to shared utility
    └── used by: all three views

views/bars.ts  -- shared component
    └── needs: barColor() → discrete threshold (replacing HSL)
    └── needs: accept bar-width option (8px default, 6px for 90d)
    └── used by: all three views with barEntry[] data

View 90m (replaces cards.ts / 30m tab)
    ├── data: GET /data?window=90m  (backend must serve 90m window)
    ├── layout: card per pair
    ├── requires: aggregateByMinute() → aggregateByInterval(window=90m, 60 buckets)
    ├── shows: split circle, badge (live), IP, latencies, uptime %, check count, bar rows
    └── uses: bars.ts (8px width), splitCircle()

View 90h (new)
    ├── data: GET /data?window=90h  (backend must serve 90h window)
    ├── layout: card per pair
    ├── shows: split circle, badge (window), IP, uptime %, check count, bar rows (no latency)
    ├── uses: bars.ts (8px width), splitCircle()
    └── needs: aggregateByInterval(window=90h, 3600 buckets → hourly groups)

View 90d (replaces day30.ts / 30d tab)
    ├── data: GET /data?window=90d  (backend must serve 90d window)
    ├── layout: card per pair (compact variant)
    ├── shows: split circle, badge (window %), IP, check count, bar rows (no latency)
    ├── uses: bars.ts (6px width), splitCircle()
    └── needs: aggregateByInterval(window=90d, 86400 buckets → daily groups)
```

### Data Dependency Notes

| Dependency | Current State | Needed Change | Impact |
|-----------|---------------|---------------|--------|
| `/data?window=90m` | Returns checks array | Must return 90-min window of checks | Backend change (likely just parameter) |
| `/data?window=90h` | Does not exist | New endpoint or new parameter | Backend change |
| `/data?window=90d` | Returns per-day DayData[] | Must return 90 days | Possibly already correct if query is dynamic |
| `aggregateByMinute()` | Hardcoded to 30 buckets | Make generic: `aggregateByInterval(checks, src, tgt, bucketSize, count)` | Refactor |
| `dailyBarsForPair()` | Hardcoded to 30 days | Change to 90 days | Trivial |
| `BarEntry` type | Works | No change needed | — |

### UI Tab / Navigation Dependencies

```
Tab bar layout (main.ts)
    ├── 90m tab (was 30m tab)
    │   ├── matrix container (unchanged)
    │   └── cards-90m container (was cards-container)
    │
    ├── 90h tab (new)
    │   └── cards-90h container (new, same layout as 90m)
    │
    └── 90d tab (was 30d tab)
        └── cards-90d container (was day30-container, now cards layout)

main.ts refresh():
    ├── fetches all three windows
    ├── renders matrix (from latest view's data)
    └── renders cards for active tab

BuildUptimeMap():
    ├── currently uses 30d data for cards.ts uptime numbers
    └── 90m view should use 90m window data (not cross-window data)
        → uptime % in 90m card should reflect THE 90m WINDOW, not 30d data
```

**❗ Critical dependency:** Currently `cards.ts` uses 30d uptime data for its uptime percentages. This is a cross-window bleed. For the unified approach, **each view's uptime % must be computed from its own window's data**, not borrowed from another window. This means:
- 90m uptime % = computed from 90m checks
- 90h uptime % = computed from 90h aggregates
- 90d uptime % = computed from 90d aggregates

The current `buildUptimeMap()` in main.ts pulls 30d data for display in the 30m cards view. This must change.

---

## Shared Components to Extract

Several utilities exist in duplicate or view-specific locations. For the unified approach, extract to shared:

### 1. `shared/color.ts` (or `views/_shared.ts`)

```typescript
// Discrete threshold colors — single source of truth
const GREEN = "#22c55e";   // mesh-green
const AMBER = "#f59e0b";   // mesh-amber
const RED   = "#ef4444";   // mesh-red
const GRAY  = "#9ca3af";   // mesh-gray (no data/pending)
const TINT  = "#e5e7eb";   // mesh-border (no-data bar background)

export function uptimeColor(pct: number): string {
  if (pct >= 99) return GREEN;
  if (pct >= 95) return AMBER;
  return RED;
}

export function barColor(percent: number): string {
  if (percent < 0) return TINT;
  const pct = percent * 100;
  if (pct >= 99) return GREEN;
  if (pct >= 95) return AMBER;
  return RED;
}
```

**Change from current:** `bars.ts` currently uses HSL gradient. Replace with discrete threshold call. This is the **single most impactful change** for the milestone — it swaps gradient for threshold-coloring everywhere.

### 2. `shared/splitCircle.ts`

```typescript
// Diagonal split circle: ping (top-left) / http (bottom-right)
export function splitCircle(pingPct: number, httpPct: number): string {
  const pingColor = uptimeColor(pingPct);
  const httpColor = uptimeColor(httpPct);
  // 135deg gradient = diagonal split
  return `<span style="display:inline-block;width:24px;height:24px;
    border-radius:50%;background:linear-gradient(135deg,${pingColor} 50%,${httpColor} 50%);
    vertical-align:middle;" title="Ping: ${pingPct.toFixed(1)}% | HTTP: ${httpPct.toFixed(1)}%"></span>`;
}
```

### 3. `views/cardLayout.ts` — shared card wrapper

```typescript
// Common card structure used by all 3 views
export function cardFrame(
  leftBorderColor: string,
  innerHtml: string,
  compact?: boolean,
): string {
  const p = compact ? 'p-2' : 'p-3';
  return `<div class="border border-mesh-border border-l-4 rounded-lg ${p} mb-2 bg-white"
    style="border-left-color:${leftBorderColor}">${innerHtml}</div>`;
}
```

---

## State Evolution: Before vs After

### Before (Current)

| Aspect | 30m (cards.ts) | 30d (day30.ts) |
|--------|---------------|----------------|
| Layout | Cards | Rows per-day |
| Bars | 30 × 1-min, HSL gradient | 30 × 1-day, HSL gradient |
| Split circle | ❌ | ✅ per-day |
| Check count | ❌ | ✅ per-day |
| Latency | ✅ (ping/HTTP ms) | ❌ |
| Coloring | Discrete (badge/uptime text) | Discrete (split circle, badge) |
| Bar width | 8px | 8px |
| Data source | 90m checks + uptime borrowed from 30d | DayData[] |
| Scrollable bars | Wraps naturally | Wraps naturally |

### After (Target)

| Aspect | 90m | 90h | 90d |
|--------|-----|-----|-----|
| Layout | Cards | Cards | Dense cards |
| Bars | 90 × 1-min, threshold | 90 × 1-hour, threshold | 90 × 1-day, threshold |
| Split circle | ✅ per-pair | ✅ per-pair | ✅ per-pair |
| Check count | ✅ per-pair (total in window) | ✅ per-pair | ✅ per-pair |
| Latency | ✅ (ping/HTTP ms) | ❌ | ❌ |
| Status badge | Live status | Window status (aggregate) | Window uptime % |
| Coloring | Discrete (ALL elements) | Discrete (ALL elements) | Discrete (ALL elements) |
| Bar width | 8px | 8px | 8px → 6px recommended |
| Data source | 90m checks (self-contained) | 90h aggregates (new) | 90d aggregates (new) |

---

## Signal Density Analysis

The composition of split circle + bar row + check count produces specific signal per element:

| Signal Element | What It Communicates | Time to Read | Decision It Enables |
|---------------|---------------------|--------------|---------------------|
| **Split circle** | Is ping and HTTP both healthy? | <0.5s | "Everything OK" vs "Look closer" |
| **Status badge** | What's the current or aggregate status? | <0.5s | "Need to investigate this pair" |
| **Bar row (overall color distribution)** | Is there a recent pattern of failures? | 1s | "Is this a blip or a trend?" |
| **Uptime %** | Exactly how reliable is this link? | 0.5s | "Is this within SLO?" |
| **Check count** | How much confidence do we have in the uptime %? | 0.5s | "99% from 10 checks vs 99% from 10K checks" |
| **Individual bars (hover)** | When exactly did failures happen? | 2-3s per bar | "Drill into timeline for incident correlation" |

### Why 90 Bars Works

The 90-bar count is not arbitrary — it aligns with dashboard best practices:
- **90 minutes** = standard "last hour and a half" for near-real-time (Grafana default often "last 1 hour")
- **90 hours** ≈ 3.75 days — covers a long weekend
- **90 days** = standard SLA reporting quarter
- **Same bar count** across windows creates predictable visual density. User develops muscle memory for "90 bars = one full window"

### Bar Width Decision

| Width | 90 bars total width | Best for | Tradeoff |
|-------|--------------------|----------|----------|
| 8px (current) | 720px + gaps ≈ 765px | 90m, 90h (detail views) | May overflow on <768px viewport |
| 6px (compact) | 540px + gaps ≈ 585px | 90d (dense view) | Fits most tablets, still readable |
| 5px (very compact) | 450px + gaps ≈ 495px | Mobile | Bar details hard to distinguish |
| 4px (minimum) | 360px + gaps ≈ 405px | Not recommended | Color signal lost at small size |

**Recommendation: 8px for 90m/90h, 6px for 90d.** This matches the use case — short windows are detail-oriented (need readable bars), long windows are overview-oriented (need compactness).

---

## MVP Recommendation

### Build First (Core of the Milestone)

1. **`shared/color.ts`** — single `uptimeColor()` and `barColor()` with discrete thresholds. **This is the foundation.**
2. **`shared/splitCircle.ts`** — extract from day30.ts for reuse in all views
3. **`bars.ts` refactor** — replace HSL gradient with discrete threshold from shared color module
4. **`cards.ts` → `view90m.ts`** — update to 90 bars, add split circle + check count. Remove dependency on cross-window uptime data
5. **`day30.ts` → `view90d.ts`** — rewrite to cards layout (dense variant), 90 bars, same component hierarchy as 90m
6. **`view90h.ts`** — new view, cards layout, 90 × 1-hour bars, no latency
7. **`main.ts` update** — three tabs (90m/90h/90d), three data fetches, consistent rendering pipeline

### Defer (Post-MVP Polish)

| Feature | Reason to Defer |
|---------|----------------|
| Horizontal scroll containers for bar overflow | May not be needed if bars wrap naturally. Test first |
| 90d 6px bar variant | Can add after core 90m/90h/90d cards work. Start all at 8px |
| Cross-view click-to-drill-down (e.g., click 90d → 90h → 90m) | Requires data-stack coordination between views. Complex |
| Source-group summary bar (aggregate health per source) | Pure addition — no rework needed. Can layer on later |
| Responsive layout for mobile | Scope for a separate UI polish pass |

---

## Sources

### Industry Dashboard Design (HIGH confidence)
- [Grafana Dashboard Best Practices](https://grafana.com/docs/grafana/latest/visualizations/dashboards/build-dashboards/best-practices/) — "Consistency by design," threshold-based coloring, reduce cognitive load (verified — official docs)
- [Grafana Dashboard Design: Patterns That Don't Suck](https://devopsil.com/articles/2026-03-29-grafana-dashboard-design-patterns) — Three-layer model (overview → triage → debug), panel type selection (MEDIUM confidence — blog post, aligns with Grafana docs)
- [Designing Grafana Dashboards That SREs Actually Use](https://devopsil.com/articles/2026-03-21-grafana-dashboard-design-principles) — "Every panel should answer a question," anti-patterns (MEDIUM confidence — blog post, aligns with SRE book)

### Uptime Monitoring UI Patterns (HIGH confidence)
- [shadcn/ui — Uptime Status Block](https://www.shadcn.io/blocks/monitoring-uptime-status) — Multi-region status bars, historical uptime tracking, "barbell" visualization (verified — live component source)
- [shadcn/ui — Status Matrix Grid](https://www.shadcn.io/blocks/stats-status-matrix-grid) — Column/row status grid, threshold cell colors, uptime % summaries (verified — live component source)
- [shadcn/ui — Dashboard Status Page](https://www.shadcn.io/blocks/dashboard-status-page) — Service cards with 30-day history bars, colored dot indicators (verified — live component source)
- [shadcn/ui — Timeline Server Uptime](https://www.shadcn.io/blocks/timeline-server-uptime) — Color-coded timeline segments, duration labels (verified — live component source)
- [shadcn/ui — Live Connectivity Status Banner](https://www.shadcn.io/blocks/banner-live-connectivity) — Pulsing status dot pattern (verified — live component source)

### Uptime Monitoring Tools (MEDIUM confidence)
- [IsDown — What to Include in a Monitoring Dashboard](https://isdown.app/blog/third-party-monitoring-dashboard) — Rolling 30/90-day uptime, consistent color coding, vendor grouping (MEDIUM — blog post, aligns with observed patterns)
- [codewizdevs/uptime](https://github.com/codewizdevs/uptime) — Open source uptime monitor with 90-day daily bars, compact monitor cards, status stripes (MEDIUM — GitHub README, open source tool design)
- [Xandeum LATTICE Dashboard](https://xandeum-lattice.vercel.app/doc) — Node monitoring with 3-column layout, uptime thresholds, green/amber/red status cards (MEDIUM — documentation, specific to blockchain node monitoring)

### Color and Accessibility (HIGH confidence)
- [Aceternity UI — Uptime Status Illustration](https://ui.aceternity.com/blocks/illustrations/uptime-status-illustration) — 45 vertical bars with green/amber/orange/red coloring pattern (verified — live component)
- WCAG 2.1 contrast ratios — Current threshold colors (#22c55e green, #f59e0b amber, #ef4444 red) all pass AA on white backgrounds

---

*Feature research for: mesh-status v0.9 UI consolidation (three-view unified cards with threshold coloring)*
*Researched: 2026-06-20*
