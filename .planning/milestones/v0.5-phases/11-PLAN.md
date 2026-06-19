---
phase: 11
name: Uptime History Visualization
requirements: [DASH-07, DASH-08, DASH-09]
files_modified:
  - frontend/src/views/history.ts
  - frontend/src/main.ts
  - frontend/src/mesh.test.ts
autonomous: true
---

## Wave 1: History Renderer

### Task 1.1: Create history view

<read_first>
- frontend/src/views/day30.ts (existing day rendering)
- frontend/src/types.ts (DayData interface)
- frontend/src/style.css (theme colors)
</read_first>

<action>
Create `frontend/src/views/history.ts`:

```typescript
import type { DayData } from "../types";

function uptimeColor(pct: number): string {
  if (pct >= 99) return "#22c55e";
  if (pct >= 95) return "#f59e0b";
  return "#ef4444";
}

function barHtml(pingPct: number, httpPct: number, date: string): string {
  const pingColor = uptimeColor(pingPct);
  const httpColor = uptimeColor(httpPct);
  return `<span style="display:inline-block;width:12px;height:40px;border-radius:2px;background:linear-gradient(135deg,${pingColor} 50%,${httpColor} 50%);border:1px solid #d1d5db;vertical-align:bottom;" title="${date} | Ping: ${pingPct.toFixed(1)}% | HTTP: ${httpPct.toFixed(1)}%"></span>`;
}

function emptyBar(): string {
  return '<span style="display:inline-block;width:12px;height:40px;border-radius:2px;background:#e5e7eb;border:1px solid #d1d5db;vertical-align:bottom;" title="No data"></span>';
}

function sparklineHtml(values: number[]): string {
  if (values.length === 0) return "";
  const w = 180;
  const h = 30;
  const max = Math.max(...values, 1);
  const points = values
    .map((v, i) => {
      const x = (i / (values.length - 1)) * w;
      const y = h - (v / max) * h;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
  const lastY = h - (values[values.length - 1] / max) * h;
  return [
    `<svg width="${w}" height="${h}" class="inline-block align-middle ml-2">`,
    `<polyline points="${points}" fill="none" stroke="#6b7280" stroke-width="2"/>`,
    `<polygon points="0,${h} ${points} ${w},${h}" fill="rgba(107,114,128,0.1)"/>`,
    `<circle cx="${w}" cy="${lastY.toFixed(1)}" r="2.5" fill="#6b7280"/>`,
    "</svg>",
  ].join("");
}

export function renderHistory(container: HTMLElement, nodes: string[], days: DayData[] | undefined): void {
  if (!days || days.length === 0) {
    container.innerHTML = '<p class="text-mesh-muted text-sm">No history data available for this time window</p>';
    return;
  }

  const sorted = [...nodes].sort();
  let html = "";
  for (const src of sorted) {
    html += `<details class="mb-3"><summary class="cursor-pointer font-mono text-sm text-mesh-dark font-semibold">${src}</summary><div class="pl-4 mt-2">`;
    let hasAnyData = false;
    for (const tgt of sorted) {
      if (src === tgt) continue;
      const pairKey = `${src}--${tgt}`;
      const conns: Array<{ ping: number; http: number; date: string }> = [];
      for (const day of days) {
        const c = day.connections.find((c) => c.node_ip === src && c.target_ip === tgt);
        if (c) {
          conns.push({ ping: c.ping_uptime_pct, http: c.http_uptime_pct, date: day.date });
        }
      }
      if (conns.length === 0) continue;
      hasAnyData = true;
      const bests = conns.map((c) => Math.max(c.ping, c.http));
      html += `<details class="mb-2" id="history-${pairKey}" style="scroll-margin-top:20px;"><summary class="cursor-pointer font-mono text-xs text-mesh-dark">${tgt}</summary><div class="pl-2 mt-1 flex items-end gap-0.5 flex-wrap">`;
      // Build up to 30 bars, filling gaps with empty bars
      for (let i = 0; i < 30; i++) {
        const idx = days.length - 30 + i;
        if (idx >= 0 && idx < conns.length) {
          const c = conns[idx];
          html += barHtml(c.ping, c.http, c.date);
        } else {
          html += emptyBar();
        }
      }
      html += sparklineHtml(bests);
      html += "</div></details>";
    }
    if (!hasAnyData) html += '<p class="text-xs text-mesh-muted">No history data for this node</p>';
    html += "</div></details>";
  }
  container.innerHTML = html;
}
```

Key implementation details:
- 30 bars horizontally, one per day, matched to the most recent 30 days
- Each bar is split diagonally by gradient: ping (upper-left), HTTP (lower-right)
- Sparkline SVG uses best-of ping+http values
- History sections have `id="history-{pairKey}"` for scrollTo
- `scroll-margin-top: 20px` for visual offset
- Missing days shown as gray empty bars
</action>

<acceptance_criteria>
- `frontend/src/views/history.ts` exists
- `npm run typecheck` exits 0
- Renders 30 horizontal bars per pair
- Each bar has `title` with date + ping% + http%
- Sparkline SVG rendered after bars
- History sections have `id` attribute
</acceptance_criteria>

---

## Wave 2: Integration

### Task 2.1: Wire history into main.ts with scrollTo

<read_first>
- frontend/src/main.ts
- frontend/src/views/history.ts
- frontend/src/views/day30.ts
</read_first>

<action>
Update `frontend/src/main.ts`:

1. Add import for `renderHistory` from `./views/history`
2. Add a new container `#history-container` after the existing containers
3. Add a third tab "History" in the tab bar
4. Call `renderHistory(historyContainer, nodes, data30d?.days)` in the `refresh()` function
5. Add `switchTab` logic for the "History" tab
6. Implement scroll-to from 30-day cells:

```typescript
// Add event listener for scroll-to clicks on 30-day split circles
day30Container.addEventListener("click", (e) => {
  const target = e.target as HTMLElement;
  const cell = target.closest("[data-node-pair]");
  if (cell) {
    const pairKey = cell.getAttribute("data-node-pair");
    if (pairKey) {
      const historyEl = document.getElementById(`history-${pairKey}`);
      if (historyEl) {
        switchTab("history");
        historyEl.scrollIntoView({ behavior: "smooth" });
        historyEl.open = true; // open the expander
        // Also open parent expander
        const parent = historyEl.closest("details");
        if (parent) parent.open = true;
      }
    }
  }
});
```

Add `#history-container` to the app innerHTML after day30-container:
```html
<div id="history-container" class="hidden"></div>
```
</action>

<acceptance_criteria>
- `npm run typecheck` exits 0
- History tab present in tab bar
- History container renders history data
- Clicking a 30-day split circle switches to History tab and scrolls to the matching section
</acceptance_criteria>

---

## Wave 3: Tests

### Task 3.1: Add history view tests

<read_first>
- frontend/src/views/history.ts
- frontend/src/mesh.test.ts
</read_first>

<action>
Add tests to `frontend/src/mesh.test.ts`:

```typescript
import { renderHistory } from "./views/history";

describe("renderHistory", () => {
  it("renders expanders per source node", () => {
    const container = document.createElement("div");
    renderHistory(container, ["10.0.0.1", "10.0.0.2"], [
      {
        date: "2026-06-01",
        connections: [
          {
            node_ip: "10.0.0.1",
            target_ip: "10.0.0.2",
            ping_uptime_pct: 100,
            http_uptime_pct: 99.5,
            total_checks: 8640,
          },
        ],
      },
    ]);
    expect(container.querySelectorAll("details").length).toBeGreaterThan(0);
  });

  it("shows no-data message for undefined days", () => {
    const container = document.createElement("div");
    renderHistory(container, ["10.0.0.1"], undefined);
    expect(container.innerHTML).toContain("No history data");
  });

  it("renders bars for connection data", () => {
    const container = document.createElement("div");
    renderHistory(container, ["10.0.0.1", "10.0.0.2"], [
      {
        date: "2026-06-01",
        connections: [
          {
            node_ip: "10.0.0.1",
            target_ip: "10.0.0.2",
            ping_uptime_pct: 100,
            http_uptime_pct: 99.5,
            total_checks: 8640,
          },
        ],
      },
    ]);
    expect(container.innerHTML).toContain("background:linear-gradient");
    expect(container.innerHTML).toContain("svg");
  });

  it("sets history section id for scrollTo", () => {
    const container = document.createElement("div");
    renderHistory(container, ["10.0.0.1", "10.0.0.2"], [
      {
        date: "2026-06-01",
        connections: [
          {
            node_ip: "10.0.0.1",
            target_ip: "10.0.0.2",
            ping_uptime_pct: 100,
            http_uptime_pct: 99.5,
            total_checks: 8640,
          },
        ],
      },
    ]);
    expect(container.innerHTML).toContain('id="history-10.0.0.1--10.0.0.2"');
  });
});
```
</action>

<acceptance_criteria>
- `npm test` passes with 21+ total tests
- Tests cover rendering, empty state, bar HTML, scrollTo id
</acceptance_criteria>

---

## Verification

### must_haves
- [ ] `npm run build` succeeds
- [ ] `npm test` passes (21+ tests)
- [ ] `npm run typecheck` exits 0
- [ ] `npm run lint` passes
- [ ] History tab shows per-pair uptime bars with ping/http split colors (DASH-07)
- [ ] Ping and HTTP displayed as separate metrics (DASH-08)
- [ ] 30-bar trend visualization with sparkline (DASH-09)
- [ ] Clicking 30-day split circle scrolls to history section
- [ ] Empty state handled
