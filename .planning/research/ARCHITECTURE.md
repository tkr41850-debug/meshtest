# Architecture Research: v0.9 UI Consolidation — Three Time Windows

**Domain:** Frontend data flow + backend endpoint changes for 90m/90h/90d windows
**Researched:** 2026-06-20
**Overall confidence:** HIGH (verified against existing codebase)

## Current Architecture (v0.8)

### Data Flow — Two Windows

```
main.ts (refresh every 10s)
├── fetchData30m() → GET /data?window=30m
│   └── Response: { window:"30m", checks:CheckResult[], statuses:StatusEntry[] }
│       │ checks: in-memory only (_results dict), cutoff = now - 1800s
│       │ statuses: derived from _registry + _results
│       └── Consumed by: renderCards(), renderMatrix()
│
├── fetchData30d() → GET /data?window=30d
│   └── Response: { window:"30d", days:DayData[] }
│       │ days: disk (_read_results) + in-memory fallback, aggregated per-day
│       └── Consumed by: buildUptimeMap() → renderCards() (uptime %), renderDay30()
│
└── fetchNodeList() → GET /node-list
    └── Consumed by: all three renderers (node list)
```

### Endpoint Monolith

The `/data` endpoint in `leader.py` is a single `if/elif/else` chain:

```
get_data()
  ├── window == "30m" → in-memory checks + derived statuses
  ├── window == "30d" → disk read + in-memory, aggregate by day
  └── else → 400 error
```

### Rendering Duplication

| View | Layout | Bars | Bar Count | Color Source |
|------|--------|------|-----------|--------------|
| `cards.ts` | Card per target, grouped by source | 30 one-minute bars per ICMP/HTTP | 30 | `bars.ts` HSL gradient |
| `day30.ts` | Row per day, grouped by source | 30 daily bars per ICMP/HTTP | 30 | `bars.ts` HSL gradient + local `uptimeColor()` |
| `matrix.ts` | Heatmap table | None | N/A | N/A |

Both `cards.ts` and `day30.ts` have their own `uptimeColor()` function (identical logic, duplicated), and both call `bars.ts` for the actual bar rendering.

### Bar Color (current)

`bars.ts` uses an HSL gradient from red→green:
```typescript
const hue = percent * 120;  // 0=red, 120=green
return `hsl(${hue.toFixed(0)}, 85%, 40%)`;
```

This means every bar has a slightly different color depending on its exact percentage — makes it hard to visually group bars into severity bands at a glance.

### In-Memory Retention

`persistence.py` flush_loop keeps `time.time() - 1800` (30 min) in memory after each flush (runs every 3600s). The 30m endpoint uses the same 1800s cutoff. Result: ~30 minutes of per-second check data is available for bar rendering.

## Target Architecture — Three Windows (90m, 90h, 90d)

### Data Flow

```
main.ts (refresh every 10s)
├── fetchData90m() → GET /data?window=90m
│   └── Response: { window:"90m", checks:CheckResult[], statuses:StatusEntry[] }
│       │ checks: in-memory, cutoff = now - 5400s (90 min)
│       └── Consumed by: renderCards() [90-min view]
│
├── fetchData90h() → GET /data?window=90h          ← NEW
│   └── Response: { window:"90h", hours:HourData[] }
│       │ hours: disk + in-memory, aggregated per-hour over 90 hours
│       └── Consumed by: renderHourly() [new: 90-hour view]
│
├── fetchData90d() → GET /data?window=90d
│   └── Response: { window:"90d", days:DayData[] }
│       │ days: disk + in-memory, aggregated per-day over 90 days
│       └── Consumed by: renderDay30() [90-day view]
│
└── fetchNodeList() → GET /node-list
    └── Consumed by: all renderers (node list)
```

### Shared Card Component

All three time-window views use the same card layout:

```
┌──────────────────────────────────────────────────┐
│ [OK]  10.0.0.2                                   │
│ Ping: 5.2ms  HTTP: 12.1ms  Last: 14:32:01        │
│ ██████████████████████████████████████████████████ │  (90 bars — ICMP)
│ ██████████████████████████████████████████████████ │  (90 bars — HTTP)
└──────────────────────────────────────────────────┘
```

The card HTML generation moves from being private inside `cards.ts` to a shared export in a new `card.ts` module. The interface:

```typescript
// views/card.ts — shared card rendering
export interface CardConfig {
  badgeColor: string;
  badgeLabel: string;
  targetIp: string;
  statsLines: Array<{ label: string; value: string; color?: string }>;
  pingBars: BarEntry[];
  httpBars: BarEntry[];
}

export function renderCardHtml(config: CardConfig): string;
```

Each view module:
1. Computes its own bars (different aggregation logic per window)
2. Gathers status/latency stats (different sources per window)
3. Calls `renderCardHtml()` for each pair
4. Wraps cards in source-group HTML

### Component Boundaries (After)

| Module | Responsibility | Depends On |
|--------|---------------|------------|
| `api.ts` | Fetch functions for all 4 endpoints (90m, 90h, 90d, node-list) | `types.ts` |
| `types.ts` | Type definitions for all three response shapes, BarEntry, etc. | Nothing |
| `views/bars.ts` | `barColor()` + `renderBars()` — shared bar rendering | `types.ts` |
| `views/card.ts` | `renderCardHtml()` — shared card layout template | `types.ts`, `views/bars.ts` |
| `views/cards.ts` | 90-minute view: per-minute bar aggregation + live status | `views/card.ts`, `types.ts` |
| `views/hourly.ts` | 90-hour view: per-hour bar aggregation (NEW) | `views/card.ts`, `types.ts` |
| `views/day30.ts` | 90-day view: per-day bar aggregation (refactored to use cards) | `views/card.ts`, `types.ts` |
| `views/matrix.ts` | Connectivity table (unchanged) | `types.ts` |
| `main.ts` | Tab management, data fetching, wiring | All of the above |

### Data Model Per Window

| Window | Raw Source | Aggregation | Bar Unit | Bars |
|--------|-----------|-------------|----------|------|
| 90m | `_results` in-memory | 1-minute buckets from raw check timestamps | 1 minute | 90 |
| 90h | Disk + in-memory, read 4 days | Per-hour from raw check timestamps (hour bucket) | 1 hour | 90 |
| 90d | Disk + in-memory, read 90 days | Per-day (already aggregated in `DayConnection`) | 1 day | 90 |

## Backend Changes

### 1. Extend In-Memory Retention (for 90m)

**File:** `mesh_status/persistence.py` line 80

```python
# Before
cutoff = time.time() - 1800   # 30 min

# After
cutoff = time.time() - 5400   # 90 min
```

This ensures enough raw check data stays in `_results` to render 90 one-minute bars.

### 2. Extend 30m → 90m and 30d → 90d Endpoints

**File:** `mesh_status/leader.py` in `get_data()`

The URL params change to match the actual window sizes:
- `window=30m` → `window=90m` (cutoff: 1800 → 5400)
- `window=30d` → `window=90d` (timedelta: 30 → 90)

```python
@app.route("/data", methods=["GET"])
async def get_data():
    window = request.args.get("window", "")
    if window == "90m":
        cutoff = time.time() - 5400
        # ... same logic as current 30m with new cutoff
    elif window == "90h":
        # NEW: hourly aggregation for 90 hours
    elif window == "90d":
        start = (datetime.now() - timedelta(days=90)).date()
        # ... same logic as current 30d with new day count
    else:
        return {"error": "... Use ?window=90m, ?window=90h, or ?window=90d"}, 400
```

The old `30m` and `30d` window values can be kept for backward compatibility (aliases), but the frontend switches to the new names.

### 3. New `90h` Endpoint

**File:** `mesh_status/leader.py` — new `elif window == "90h"` branch

Data flow for 90h:
```
1. Read disk: persistence._read_results(start=4 days ago, end=today)
2. Append in-memory _results (not yet flushed)
3. Filter to last 90 hours (time.time() - 324000)
4. Group by hour (datetime.fromtimestamp(ts).strftime("%Y-%m-%dT%H:00:00"))
5. For each hour, for each (node_ip, target_ip) pair:
     total = count of checks
     ping_uptime_pct = ping_ok / total * 100
     http_uptime_pct = http_ok / total * 100
6. Return: { window: "90h", hours: HourData[], timestamp: now }
```

Response shape:
```json
{
  "window": "90h",
  "hours": [
    {
      "hour": "2026-06-19T14:00:00",
      "connections": [
        {
          "node_ip": "10.0.0.1",
          "target_ip": "10.0.0.2",
          "total_checks": 360,
          "ping_uptime_pct": 99.7,
          "http_uptime_pct": 98.2
        }
      ]
    }
  ],
  "timestamp": 1770550000
}
```

The `HourConnection` type is structurally identical to `DayConnection` — same fields. The type alias exists for semantic clarity.

### 4. Disk Read for 90m Fallback (Optional Optimization)

The current 30m endpoint reads ONLY from in-memory `_results`. With the extended retention (5400s), memory should always have 90 min of data (flush_loop runs every 3600s, retains 5400s). No disk read needed for 90m.

However, at startup or after a leader restart, _results starts empty. For robustness, the 90m endpoint could optionally read from disk for the first cycle:

```python
if window == "90m":
    # Primary: in-memory
    # Fallback: disk for recent data if memory is empty
    if not _results:
        raw = persistence._read_results(today, today)
        recent = [r for r in raw if r.get("timestamp", 0) >= time.time() - 5400]
        # ... use recent as checks
```

**Recommendation:** Defer this — the 10-second refresh cycle means memory fills within one cycle.

## Frontend Changes

### Types (`types.ts`)

```typescript
// Renamed for clarity (keep old names as aliases for transition)
export type Data90mResponse = Data30mResponse;  // same shape, different window

export interface HourConnection {
  node_ip: string;
  target_ip: string;
  ping_uptime_pct: number;
  http_uptime_pct: number;
  total_checks: number;
}

export interface HourData {
  hour: string;  // ISO format: "2026-06-20T14:00:00"
  connections: HourConnection[];
}

export interface Data90hResponse {
  hours: HourData[];
  window: string;
}

export type Data90dResponse = Data30dResponse;  // same shape, different window
```

### API (`api.ts`)

```typescript
export function fetchData90m(): Promise<Data90mResponse | null> {
  return fetchWithTimeout<Data90mResponse>("/data?window=90m");
}

export function fetchData90h(): Promise<Data90hResponse | null> {
  return fetchWithTimeout<Data90hResponse>("/data?window=90h");
}

export function fetchData90d(): Promise<Data90dResponse | null> {
  return fetchWithTimeout<Data90dResponse>("/data?window=90d");
}
```

Old `fetchData30m()` and `fetchData30d()` can be removed or kept as aliases.

### Shared Card (`views/card.ts`) — NEW

Extracted from `views/cards.ts` `cardHtml()` function:

```typescript
import type { BarEntry } from "../types";
import { renderBars } from "./bars";

const BADGE_MAP: Record<string, { color: string; label: string }> = {
  OK: { color: "#22c55e", label: "OK" },
  NotAvailable: { color: "#f59e0b", label: "Not Available" },
  Pending: { color: "#9ca3af", label: "Pending" },
};

function uptimeColor(pct: number): string {
  if (pct >= 99) return "#22c55e";
  if (pct >= 95) return "#f59e0b";
  return "#ef4444";
}

function uptimeSpan(pct: number | null): string {
  if (pct === null) return "";
  const c = uptimeColor(pct);
  return `<span style="color:${c};font-weight:600;">(${pct.toFixed(1)}%)</span>`;
}

export function renderCardHtml(
  tgtIp: string,
  status: string,
  pingLat: string,
  httpLat: string,
  lastSeen: string,
  pingUp: number | null,
  httpUp: number | null,
  pingBars: BarEntry[],
  httpBars: BarEntry[],
): string {
  // Same implementation as current cards.ts cardHtml()
  // but exported for use by all views
}
```

### Bars (`views/bars.ts`) — Color Change

Replace HSL gradient with discrete severity thresholds:

```typescript
export function barColor(percent: number): string {
  if (percent < 0) return "#e5e7eb";      // gray — no data
  if (percent >= 0.99) return "#22c55e";  // green — ≥99%
  if (percent >= 0.95) return "#f59e0b";  // amber — 95-98.9%
  return "#ef4444";                        // red — <95%
}
```

This matches the existing `uptimeColor()` function in cards.ts and day30.ts, creating visual consistency between bar colors and uptime text colors.

### Cards View (`views/cards.ts`) — Modified In Place

Changes:
1. Import `renderCardHtml` from `views/card.ts` instead of local `cardHtml()`
2. Change `for (let i = 29; i >= 0; i--)` → `for (let i = 89; i >= 0; i--)` in `aggregateByMinute()`
3. Remove local `cardHtml()`, `uptimeColor()`, `uptimeSpan()`, `BADGE_MAP`

```typescript
export function renderCards(
  container: HTMLElement,
  nodes: string[],
  statuses: StatusEntry[],
  checks: CheckResult[],
  uptimeMap: Map<string, [number | null, number | null]>,
): void {
  // Same structure, but uses shared renderCardHtml
}
```

### Hourly View (`views/hourly.ts`) — NEW

New module for the 90-hour window:

```typescript
import type { BarEntry, HourData, Data90hResponse } from "../types";
import { renderCardHtml } from "./card";

function hourlyBarsForPair(
  hours: HourData[],
  src: string,
  tgt: string,
): { pingBars: BarEntry[]; httpBars: BarEntry[] } {
  // Similar to dailyBarsForPair() in day30.ts
  // Slide over the last 90 hours, collect ping_uptime_pct / http_uptime_pct
  const sorted = hours.sort((a, b) => a.hour.localeCompare(b.hour));
  const recentHours = sorted.slice(-90);
  // ... map to BarEntry[90] for ping and http
}

export function renderHourly(
  container: HTMLElement,
  nodes: string[],
  hours: HourData[] | undefined,
): void {
  if (!hours || hours.length === 0) {
    container.innerHTML = '<p class="text-mesh-muted text-sm">No data available</p>';
    return;
  }
  // Build status by looking at recent hourly aggregates
  // ... similar source-group + cards layout as cards.ts
}
```

### Day View (`views/day30.ts`) — Refactored

Changes:
1. Import `renderCardHtml` from `views/card.ts`
2. Remove local `uptimeColor()`, `splitCircle()`, `badgeHtml()`
3. Change `for (let i = 0; i < 30; i++)` → `for (let i = 0; i < 90; i++)` in `dailyBarsForPair()`
4. Rework layout from per-day rows to cards (consistent with 90m/90h views)

The current layout:
```
10.0.0.1 (source header)
  2026-06-01 → 10.0.0.2  [●] [100.0%] 100.0%  100.0%  8640
  ████████████████████████████████  (30 bars)
  ████████████████████████████████  (30 bars)
```

Target layout (using shared card):
```
10.0.0.1 (source header)
  ┌──────────────────────────────────────────────────┐
  │ [OK]  10.0.0.2                                   │
  │ Ping: 5.2ms  HTTP: 12.1ms  Last: 90d aggregate   │
  │ ██████████████████████████████████████████████████ │  (90 bars)
  │ ██████████████████████████████████████████████████ │  (90 bars)
  └──────────────────────────────────────────────────┘
```

Since `DayConnection` only has aggregated percentages (not per-request latency), the 90d view shows:
- **Badge:** Based on best of ping/http uptime for the period
- **Latency:** Use `—` or "N/A" (daily aggregates don't include per-request latency)
- **Bars:** 90 daily bars from `DayConnection.ping_uptime_pct` / `http_uptime_pct`
- **Uptime:** Show the latest/max uptime % in parentheses

### Main (`main.ts`) — Modified

Changes:
1. Import `fetchData90m`, `fetchData90h`, `fetchData90d` instead of old fetches
2. Import `renderHourly` from new view
3. Three tabs: "90-Minute", "90-Hour", "90-Day"
4. `switchTab("90m" | "90h" | "90d")` — three-way instead of two-way
5. `refresh()` fetches all three + node-list in parallel
6. New container for hourly view in HTML template

```typescript
const app = document.querySelector<HTMLDivElement>("#app")!;
app.innerHTML = `
  <div class="max-w-6xl mx-auto p-6">
    <h1 class="text-2xl font-bold text-mesh-dark mb-4">mesh-status</h1>
    <div class="flex gap-2 mb-4 border-b border-mesh-border">
      <button id="tab-90m" class="tab-btn ...">90-Minute View</button>
      <button id="tab-90h" class="tab-btn ...">90-Hour View</button>
      <button id="tab-90d" class="tab-btn ...">90-Day View</button>
    </div>
    <div id="matrix-container" class="mb-6"></div>
    <div id="cards-container"></div>
    <div id="hourly-container" class="hidden"></div>
    <div id="day30-container" class="hidden"></div>
    <p id="refresh-indicator">Loading...</p>
  </div>
`;
```

## Key Integration Points

| Integration | What Connects | Risk | Mitigation |
|-------------|---------------|------|------------|
| Backend 90h → frontend hourly view | Response shape: `{hours: HourData[]}` | Shape mismatch breaks rendering | Define types first, implement backend + frontend from same contract |
| Backend flush retention → 90m data | `flush_loop()` cutoff = 5400 | OOM if many nodes × many checks | 5400s × ~1 check/sec × 10 nodes = ~54K entries, ~few MB. Acceptable. |
| Cards → all three views | `renderCardHtml()` signature | Changing signature breaks all callers | Freeze signature early. Add overloads if needed. |
| Tab switching state | `switchTab()` + container hide/show | Missing container breaks UI | Three containers, three tabs, one active at a time |
| Uptime map → 90m cards | `buildUptimeMap()` from 90d data | 90d data not loaded yet → null bars | `refresh()` fetches all in parallel; map is populated by the time cards render |

## Build Order (Dependency-Aware)

```
Step 1: Backend — Extend retention in persistence.py (5400s)
  ↓ No frontend dependency
Step 2: Backend — Rename 30m→90m, add 90h, rename 30d→90d in leader.py
  ↓ Backend must respond to /data?window=90h
Step 3: Backend — Add tests for 90h endpoint in test_data_api.py
  ↓
  ──── Backend complete. Frontend can start. ────
  ↓
Step 4: Frontend — bars.ts: barColor() discrete thresholds
  ↓ No deps on other frontend changes
Step 5: Frontend — types.ts: add Data90hResponse, HourConnection, HourData
  ↓ Deps: bars.ts (no circular)
Step 6: Frontend — api.ts: add fetchData90h(), rename fetch functions
  ↓ Deps: types.ts
Step 7: Frontend — bars.ts: change 30→90 bar count
  ↓ Deps: bars.ts (self-contained)
Step 8: Frontend — card.ts: extract renderCardHtml from cards.ts
  ↓ Deps: bars.ts, types.ts
Step 9: Frontend — cards.ts: refactor to use shared card.ts
  ↓ Deps: card.ts
Step 10: Frontend — hourly.ts: new view module
  ↓ Deps: card.ts, types.ts
Step 11: Frontend — day30.ts: refactor to use shared card + 90 bars
  ↓ Deps: card.ts
Step 12: Frontend — main.ts: wire up third tab + new fetches
  ↓ Deps: all views, api.ts
Step 13: Frontend — Update tests: bars.test.ts, mesh.test.ts
  ↓ Deps: all changes (do last)
```

## Scaling Notes

| Concern | At 10 nodes × 90m | At 50 nodes × 90m | Mitigation |
|---------|-------------------|-------------------|------------|
| In-memory check data | ~54K entries (~5 MB) | ~270K entries (~27 MB) | Acceptable for typical VPS. If memory is tight: reduce retention to 30m, show 30 bars. |
| 90h aggregation CPU | ~100K records grouped into 90h × N² pairs | ~2.5M records | Aggregation runs per-request. For large meshes, consider caching the 90h result in leader memory. |
| Bar rendering DOM | 90 bars × 2 rows × (N²-N) cards | 90 bars × 2 rows × 2450 cards | DOM with ~450K spans will lag. Virtualize or paginate for >20 nodes. |

## Sources

- **Existing codebase**: Verified against `leader.py`, `persistence.py`, `cards.ts`, `day30.ts`, `bars.ts`, `main.ts`, `types.ts`, `api.ts`, `test_data_api.py`, `bars.test.ts`, `mesh.test.ts`
- **Requirement analysis**: Derived from milestone prompt — "three time windows (90m, 90h, 90d)", "bar count 30→90", "consistent card layout", "discrete threshold colors"

---

*Architecture research for: mesh-status v0.9 UI consolidation*
*Researched: 2026-06-20*
