---
phase: 9
name: Dashboard Views
requirements: [DASH-01, DASH-02, DASH-03, DASH-04, DASH-05, DASH-06]
files_modified:
  - frontend/src/main.ts
  - frontend/src/types.ts
  - frontend/src/api.ts
  - frontend/src/views/matrix.ts
  - frontend/src/views/cards.ts
  - frontend/src/views/day30.ts
  - frontend/index.html
  - frontend/src/mesh.test.ts
autonomous: true
---

## Wave 1: Data Layer & Types

### Task 1.1: Define TypeScript interfaces

<read_first>
- frontend/src/vite-env.d.ts
- mesh_status/leader.py (data API response shapes)
- mesh_status/dashboard.py (consumption patterns)
</read_first>

<action>
Create `frontend/src/types.ts` with the following interfaces:

```typescript
export interface CheckResult {
  node_ip: string;
  target_ip: string;
  ping_status: string;
  http_status: string;
  ping_latency_ms: number | null;
  http_latency_ms: number | null;
  timestamp: number;
}

export interface StatusEntry {
  node_ip: string;
  target_ip: string;
  ping_status: string;
  http_status: string;
}

export interface Data30mResponse {
  checks: CheckResult[];
  statuses: StatusEntry[];
  timestamp: number;
  window: string;
}

export interface DayConnection {
  node_ip: string;
  target_ip: string;
  ping_uptime_pct: number;
  http_uptime_pct: number;
  total_checks: number;
}

export interface DayData {
  date: string;
  connections: DayConnection[];
}

export interface Data30dResponse {
  days: DayData[];
  window: string;
}

export interface NodeListResponse {
  nodes: Array<{ ip: string; port: number } | string>;
}
```
</action>

<acceptance_criteria>
- `frontend/src/types.ts` exists
- All 6 interfaces defined with exact field names from API responses
- File compiles: `npm run typecheck` exits 0
</acceptance_criteria>

### Task 1.2: Create API client module

<read_first>
- frontend/src/types.ts (created in task 1.1)
- frontend/vite.config.ts (dev proxy config)
- mesh_status/leader.py (API endpoints)
</read_first>

<action>
Create `frontend/src/api.ts` with:

```typescript
import type { Data30mResponse, Data30dResponse, NodeListResponse } from "./types";

const FETCH_TIMEOUT = 5_000;

async function fetchWithTimeout<T>(url: string): Promise<T | null> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), FETCH_TIMEOUT);
  try {
    const resp = await fetch(url, { signal: controller.signal });
    if (!resp.ok) return null;
    return (await resp.json()) as T;
  } catch {
    return null;
  } finally {
    clearTimeout(timer);
  }
}

export function fetchData30m(): Promise<Data30mResponse | null> {
  return fetchWithTimeout<Data30mResponse>("/data?window=30m");
}

export function fetchData30d(): Promise<Data30dResponse | null> {
  return fetchWithTimeout<Data30dResponse>("/data?window=30d");
}

export function fetchNodeList(): Promise<NodeListResponse | null> {
  return fetchWithTimeout<NodeListResponse>("/node-list");
}
```
</action>

<acceptance_criteria>
- `frontend/src/api.ts` exists
- Contains `fetchData30m`, `fetchData30d`, `fetchNodeList` functions
- Each function returns the typed response or null
- Uses AbortController with 5s timeout
- `npm run typecheck` exits 0
</acceptance_criteria>

---

## Wave 2: View Renderers

### Task 2.1: Connectivity matrix renderer

<read_first>
- frontend/src/types.ts
- frontend/src/api.ts
- mesh_status/dashboard.py (lines 59-99 — _render_connectivity_matrix)
- frontend/src/style.css (Tailwind theme tokens)
</read_first>

<action>
Create `frontend/src/views/matrix.ts` with a `renderMatrix` function:

```typescript
import type { StatusEntry } from "../types";

function computeStatus(s: StatusEntry): "OK" | "NotAvailable" | "Pending" {
  if (s.ping_status === "OK" && s.http_status === "OK") return "OK";
  if (s.ping_status === "NotAvailable" || s.http_status === "NotAvailable") return "NotAvailable";
  return "Pending";
}

function shortLabel(ip: string): string {
  const firstDot = ip.indexOf(".");
  const beforeDot = ip.slice(0, firstDot);
  const lastDash = beforeDot.lastIndexOf("-");
  return lastDash !== -1 ? beforeDot.slice(lastDash + 1) : beforeDot;
}

const STATUS_DOT: Record<string, string> = {
  OK: "●",
  NotAvailable: "●",
  Pending: "●",
};

const STATUS_COLOR: Record<string, string> = {
  OK: "text-mesh-green",
  NotAvailable: "text-mesh-amber",
  Pending: "text-mesh-gray",
};

export function renderMatrix(container: HTMLElement, nodes: string[], statuses: StatusEntry[]): void {
  if (nodes.length < 2) {
    container.innerHTML = '<p class="text-mesh-muted text-sm">Need at least 2 nodes for a matrix</p>';
    return;
  }

  const combined = new Map<string, string>();
  for (const s of statuses) {
    combined.set(`${s.node_ip}|${s.target_ip}`, computeStatus(s));
  }

  let html = '<div class="overflow-x-auto"><table class="w-full text-sm border-collapse">';
  html += "<tr><th></th>";
  for (const tgt of nodes) {
    html += `<th class="px-2 py-1 text-center font-semibold text-mesh-dark bg-mesh-bg border border-mesh-border font-mono" title="${tgt}">${shortLabel(tgt)}</th>`;
  }
  html += "</tr>";

  for (const src of nodes) {
    html += `<tr><td class="px-2 py-1 font-mono text-mesh-dark border border-mesh-border whitespace-nowrap">${src}</td>`;
    for (const tgt of nodes) {
      const key = `${src}|${tgt}`;
      if (src === tgt) {
        html += '<td class="px-2 py-1 text-center text-mesh-gray border border-mesh-border">—</td>';
      } else {
        const st = combined.get(key) ?? "Pending";
        html += `<td class="px-2 py-1 text-center border border-mesh-border"><span class="${STATUS_COLOR[st]} text-lg">${STATUS_DOT[st]}</span></td>`;
      }
    }
    html += "</tr>";
  }
  html += "</table></div>";

  container.innerHTML = html;
}
```
</action>

<acceptance_criteria>
- `frontend/src/views/matrix.ts` exists
- `npm run typecheck` exits 0
- renders N×N table with colored dots
- diagonal cells show gray em-dash
- column headers use short labels with full IP in title attribute
</acceptance_criteria>

### Task 2.2: Detail cards renderer

<read_first>
- frontend/src/types.ts
- mesh_status/dashboard.py (lines 101-228 — _render_detail_card, _render_30m_view)
- frontend/src/style.css
</read_first>

<action>
Create `frontend/src/views/cards.ts` with a `renderCards` function:

```typescript
import type { CheckResult, StatusEntry } from "../types";

function summaryLabel(src: string, nodes: string[], combined: Map<string, string>): string {
  const targets = nodes.filter((n) => n !== src);
  if (targets.length === 0) return "No targets";
  const ok = targets.filter((t) => combined.get(`${src}|${t}`) === "OK").length;
  if (ok === targets.length) return "All OK";
  if (ok === 0) return "Pending";
  return `${targets.length - ok} of ${targets.length} down`;
}

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

const BADGE_MAP: Record<string, { color: string; label: string }> = {
  OK: { color: "#22c55e", label: "OK" },
  NotAvailable: { color: "#f59e0b", label: "Not Available" },
  Pending: { color: "#9ca3af", label: "Pending" },
};

function cardHtml(
  tgtIp: string,
  status: string,
  pingLat: string,
  httpLat: string,
  lastSeen: string,
  pingUp: number | null,
  httpUp: number | null,
): string {
  const badge = BADGE_MAP[status] ?? BADGE_MAP.Pending;
  return [
    `<div class="border border-mesh-border border-l-4 rounded-lg p-3 mb-2 bg-white" style="border-left-color:${badge.color}">`,
    `<div class="flex items-center gap-2 mb-1">`,
    `<span class="inline-block px-2.5 py-0.5 rounded-full text-xs font-semibold tracking-wide text-white" style="background:${badge.color}">${badge.label}</span>`,
    `<span class="font-mono text-sm font-semibold text-mesh-dark">${tgtIp}</span>`,
    `</div>`,
    `<div class="text-xs text-mesh-muted flex gap-4 flex-wrap">`,
    `<span>Ping: <strong class="text-mesh-dark">${pingLat}</strong> ${uptimeSpan(pingUp)}</span>`,
    `<span>HTTP: <strong class="text-mesh-dark">${httpLat}</strong> ${uptimeSpan(httpUp)}</span>`,
    `<span>Last: <strong class="text-mesh-dark">${lastSeen}</strong></span>`,
    `</div></div>`,
  ].join("");
}

export function renderCards(
  container: HTMLElement,
  nodes: string[],
  statuses: StatusEntry[],
  checks: CheckResult[],
  uptimeMap: Map<string, [number | null, number | null]>,
): void {
  if (nodes.length === 0) {
    container.innerHTML = '<p class="text-mesh-muted text-sm">No nodes registered</p>';
    return;
  }

  const combined = new Map<string, string>();
  for (const s of statuses) {
    const ping = s.ping_status === "OK";
    const http = s.http_status === "OK";
    let st: string;
    if (ping && http) st = "OK";
    else if (s.ping_status === "NotAvailable" || s.http_status === "NotAvailable") st = "NotAvailable";
    else st = "Pending";
    combined.set(`${s.node_ip}|${s.target_ip}`, st);
  }

  const latestCheck = new Map<string, CheckResult>();
  for (const c of checks) {
    const key = `${c.node_ip}|${c.target_ip}`;
    const existing = latestCheck.get(key);
    if (!existing || c.timestamp > existing.timestamp) {
      latestCheck.set(key, c);
    }
  }

  const sorted = [...nodes].sort();
  let html = "";
  for (const src of sorted) {
    const summary = summaryLabel(src, sorted, combined);
    html += `<details class="mb-3"><summary class="cursor-pointer font-mono text-sm text-mesh-dark font-semibold">${src}  [${summary}]  — ${sorted.filter((n) => n !== src).length} targets</summary><div class="pl-4 mt-2">`;
    for (const tgt of sorted) {
      if (src === tgt) continue;
      const st = combined.get(`${src}|${tgt}`) ?? "Pending";
      const ck = latestCheck.get(`${src}|${tgt}`) ?? ({} as CheckResult);
      const pingLat = ck.ping_latency_ms != null ? `${ck.ping_latency_ms.toFixed(1)}ms` : "—";
      const httpLat = ck.http_latency_ms != null ? `${ck.http_latency_ms.toFixed(1)}ms` : "—";
      const lastSeen = ck.timestamp ? new Date(ck.timestamp * 1000).toLocaleTimeString() : "—";
      const uptime = uptimeMap.get(`${src}|${tgt}`) ?? [null, null];
      html += cardHtml(tgt, st, pingLat, httpLat, lastSeen, uptime[0], uptime[1]);
    }
    html += "</div></details>";
  }

  container.innerHTML = html;
}
```
</action>

<acceptance_criteria>
- `frontend/src/views/cards.ts` exists
- `npm run typecheck` exits 0
- renders `<details>` expanders per source node
- each target rendered as card with border-left, status badge, IP, latencies, uptime %
</acceptance_criteria>

### Task 2.3: 30-day view renderer

<read_first>
- frontend/src/types.ts
- mesh_status/dashboard.py (lines 230-273 — _render_30d_view)
- frontend/src/style.css
</read_first>

<action>
Create `frontend/src/views/day30.ts` with a `renderDay30` function.

Render a nested expander layout: per source node, show a table with rows for each (date → target_ip). Each row has:
- Date + target IP label column
- Diagonally split circle (`background: linear-gradient(...)`) where left/upper half = ping uptime color, right/lower half = http uptime color
- Best uptime badge (colored pill)
- Ping % column
- HTTP % column
- Total checks column

Each circle gets `data-node-pair="{src_ip}--{tgt_ip}"` and `id="uptime-cell-{src_ip}--{tgt_ip}"` for Phase 11 scrollTo integration.

```typescript
import type { DayData } from "../types";

function uptimeColor(pct: number): string {
  if (pct >= 99) return "#22c55e";
  if (pct >= 95) return "#f59e0b";
  return "#ef4444";
}

function splitCircle(pingPct: number, httpPct: number): string {
  const pingColor = uptimeColor(pingPct);
  const httpColor = uptimeColor(httpPct);
  return `<span style="display:inline-block;width:24px;height:24px;border-radius:50%;background:linear-gradient(135deg,${pingColor} 50%,${httpColor} 50%);vertical-align:middle;"></span>`;
}

function badgeHtml(pct: number): string {
  const c = uptimeColor(pct);
  return `<span class="inline-block px-2 py-0.5 rounded text-xs font-semibold text-white" style="background:${c}">${pct.toFixed(1)}%</span>`;
}

export function renderDay30(container: HTMLElement, nodes: string[], days: DayData[] | undefined): void {
  if (!days || days.length === 0) {
    container.innerHTML = '<p class="text-mesh-muted text-sm">No data available for this time window</p>';
    return;
  }

  const sorted = [...nodes].sort();
  let html = "";
  for (const src of sorted) {
    html += `<details class="mb-3"><summary class="cursor-pointer font-mono text-sm text-mesh-dark font-semibold">${src}</summary><div class="pl-4 mt-2">`;

    let hasData = false;
    for (const day of days) {
      const conns = day.connections.filter((c) => c.node_ip === src);
      if (conns.length === 0) {
        html += `<div class="text-xs text-mesh-muted py-1">${day.date} → —</div>`;
        continue;
      }
      hasData = true;
      for (const conn of conns) {
        const best = Math.max(conn.ping_uptime_pct, conn.http_uptime_pct);
        const pairKey = `${src}--${conn.target_ip}`;
        html += [
          `<div class="flex items-center gap-3 py-1 text-xs border-b border-mesh-border last:border-0">`,
          `<span class="w-32 font-mono text-mesh-muted">${day.date} → ${conn.target_ip}</span>`,
          `<span data-node-pair="${pairKey}" id="uptime-cell-${pairKey}">${splitCircle(conn.ping_uptime_pct, conn.http_uptime_pct)}</span>`,
          `<span>${badgeHtml(best)}</span>`,
          `<span class="font-mono text-mesh-dark w-16 text-right">${conn.ping_uptime_pct.toFixed(1)}%</span>`,
          `<span class="font-mono text-mesh-dark w-16 text-right">${conn.http_uptime_pct.toFixed(1)}%</span>`,
          `<span class="font-mono text-mesh-muted w-10 text-right">${conn.total_checks}</span>`,
          `</div>`,
        ].join("");
      }
    }
    if (!hasData) {
      html += '<p class="text-xs text-mesh-muted">No data for this node</p>';
    }
    html += "</div></details>";
  }
  container.innerHTML = html;
}
```
</action>

<acceptance_criteria>
- `frontend/src/views/day30.ts` exists
- `npm run typecheck` exits 0
- renders nested expanders with date rows
- diagonal split circles with `data-node-pair` and `id` attributes
- colored uptime badges
</acceptance_criteria>

---

## Wave 3: App Entry Point

### Task 3.1: Wire main.ts with tab switching and auto-refresh

<read_first>
- frontend/src/main.ts (current stub)
- frontend/src/api.ts
- frontend/src/views/matrix.ts
- frontend/src/views/cards.ts
- frontend/src/views/day30.ts
- frontend/index.html
</read_first>

<action>
Rewrite `frontend/src/main.ts` to:

1. Replace `index.html` content with two-tab layout:
   - Tab bar with "30-Minute View" and "30-Day View" buttons
   - Three containers: `#matrix-container`, `#cards-container`, `#day30-container`
   - Auto-refresh indicator at bottom: "🔄 Auto-refreshing every 10s | Last update: HH:MM:SS"

2. Implement tab switching (show/hide containers)

3. Implement `refresh()` that:
   - Fetches all 3 endpoints in parallel via `Promise.all`
   - Re-renders all containers
   - Updates last-update timestamp
   - On error: inline message, keep stale data visible

4. Start `setInterval(refresh, 10000)`, call `refresh()` immediately on load

5. Build uptime map from 30d data and pass to `renderCards`

```typescript
import "./style.css";
import { fetchData30m, fetchData30d, fetchNodeList } from "./api";
import { renderMatrix } from "./views/matrix";
import { renderCards } from "./views/cards";
import { renderDay30 } from "./views/day30";

const app = document.querySelector<HTMLDivElement>("#app")!;
app.innerHTML = `
  <div class="max-w-6xl mx-auto p-6">
    <h1 class="text-2xl font-bold text-mesh-dark mb-4">mesh-status</h1>
    <div class="flex gap-2 mb-4 border-b border-mesh-border">
      <button id="tab-30m" class="tab-btn px-4 py-2 text-sm font-semibold text-mesh-dark border-b-2 border-mesh-green">30-Minute View</button>
      <button id="tab-30d" class="tab-btn px-4 py-2 text-sm font-semibold text-mesh-muted border-b-2 border-transparent">30-Day View</button>
    </div>
    <div id="matrix-container"></div>
    <div id="cards-container"></div>
    <div id="day30-container" class="hidden"></div>
    <p id="refresh-indicator" class="text-center text-xs text-mesh-muted mt-6">Loading mesh data...</p>
  </div>
`;

const matrixContainer = document.querySelector<HTMLDivElement>("#matrix-container")!;
const cardsContainer = document.querySelector<HTMLDivElement>("#cards-container")!;
const day30Container = document.querySelector<HTMLDivElement>("#day30-container")!;
const indicator = document.querySelector<HTMLParagraphElement>("#refresh-indicator")!;
const tab30m = document.querySelector<HTMLButtonElement>("#tab-30m")!;
const tab30d = document.querySelector<HTMLButtonElement>("#tab-30d")!;

function switchTab(tab: "30m" | "30d"): void {
  const is30m = tab === "30m";
  matrixContainer.classList.toggle("hidden", !is30m);
  cardsContainer.classList.toggle("hidden", !is30m);
  day30Container.classList.toggle("hidden", is30m);
  tab30m.className = is30m
    ? "tab-btn px-4 py-2 text-sm font-semibold text-mesh-dark border-b-2 border-mesh-green"
    : "tab-btn px-4 py-2 text-sm font-semibold text-mesh-muted border-b-2 border-transparent";
  tab30d.className = is30m
    ? "tab-btn px-4 py-2 text-sm font-semibold text-mesh-muted border-b-2 border-transparent"
    : "tab-btn px-4 py-2 text-sm font-semibold text-mesh-dark border-b-2 border-mesh-green";
}

tab30m.addEventListener("click", () => switchTab("30m"));
tab30d.addEventListener("click", () => switchTab("30d"));

function buildUptimeMap(data30d: Awaited<ReturnType<typeof fetchData30d>>): Map<string, [number | null, number | null]> {
  const map = new Map<string, [number | null, number | null]>();
  if (!data30d?.days) return map;
  for (const day of data30d.days) {
    for (const conn of day.connections) {
      map.set(`${conn.node_ip}|${conn.target_ip}`, [conn.ping_uptime_pct, conn.http_uptime_pct]);
    }
  }
  return map;
}

async function refresh(): Promise<void> {
  const [data30m, data30d, nodeList] = await Promise.all([
    fetchData30m(),
    fetchData30d(),
    fetchNodeList(),
  ]);

  const nodes = nodeList?.nodes?.map((n) => (typeof n === "string" ? n : n.ip)) ?? [];

  if (!data30m) {
    indicator.textContent = "⚠ Leader unreachable — showing cached data";
  } else {
    indicator.textContent = `🔄 Auto-refreshing every 10s | Last update: ${new Date().toLocaleTimeString()}`;
  }

  const statuses = data30m?.statuses ?? [];
  const checks = data30m?.checks ?? [];
  const uptimeMap = buildUptimeMap(data30d);

  if (nodes.length === 0) {
    matrixContainer.innerHTML = '<p class="text-mesh-muted text-sm">No nodes registered</p>';
    cardsContainer.innerHTML = '<p class="text-mesh-muted text-sm">No nodes registered</p>';
  } else {
    renderMatrix(matrixContainer, nodes, statuses);
    renderCards(cardsContainer, nodes, statuses, checks, uptimeMap);
  }

  renderDay30(day30Container, nodes, data30d?.days);
}

refresh();
setInterval(refresh, 10_000);
```
</action>

<acceptance_criteria>
- `npm run typecheck` exits 0
- `npm run build` succeeds
- Tabs switch between 30m and 30d views
- Auto-refresh fires every 10s
- Error states show inline message, stale data remains visible
- Refresh indicator updates timestamp
</acceptance_criteria>

---

## Wave 4: Tests

### Task 4.1: Add frontend tests for view renderers

<read_first>
- frontend/src/main.test.ts (existing stub)
- frontend/src/types.ts
- frontend/src/views/matrix.ts
- frontend/src/views/cards.ts
- frontend/src/views/day30.ts
</read_first>

<action>
Create `frontend/src/mesh.test.ts` with Vitest tests:

```typescript
import { describe, it, expect } from "vitest";
import { renderMatrix } from "./views/matrix";
import { renderCards } from "./views/cards";
import { renderDay30 } from "./views/day30";

// Matrix tests
describe("renderMatrix", () => {
  it("renders table with correct number of rows/cols", () => {
    const container = document.createElement("div");
    renderMatrix(container, ["10.0.0.1", "10.0.0.2"], [
      { node_ip: "10.0.0.1", target_ip: "10.0.0.2", ping_status: "OK", http_status: "OK" },
    ]);
    expect(container.querySelectorAll("tr").length).toBe(3); // header + 2 rows
  });

  it("shows gray dots for pending status", () => {
    const container = document.createElement("div");
    renderMatrix(container, ["10.0.0.1", "10.0.0.2"], []);
    expect(container.innerHTML).toContain("●");
  });

  it("shows message for fewer than 2 nodes", () => {
    const container = document.createElement("div");
    renderMatrix(container, ["10.0.0.1"], []);
    expect(container.innerHTML).toContain("Need at least 2 nodes");
  });

  it("shows em-dash on diagonal", () => {
    const container = document.createElement("div");
    renderMatrix(container, ["10.0.0.1", "10.0.0.2"], []);
    const cells = container.querySelectorAll("td");
    expect(cells[0].textContent).toBe("—");
  });
});

// Cards tests
describe("renderCards", () => {
  it("renders expanders per source node", () => {
    const container = document.createElement("div");
    renderCards(container, ["10.0.0.1", "10.0.0.2"], [], [], new Map());
    expect(container.querySelectorAll("details").length).toBe(2);
  });

  it("shows no-nodes message for empty list", () => {
    const container = document.createElement("div");
    renderCards(container, [], [], [], new Map());
    expect(container.innerHTML).toContain("No nodes registered");
  });

  it("skips self-pair in cards", () => {
    const container = document.createElement("div");
    renderCards(container, ["10.0.0.1"], [], [], new Map());
    expect(container.innerHTML).not.toContain("10.0.0.1");
  });
});

// 30-day view tests
describe("renderDay30", () => {
  it("renders expanders per source node", () => {
    const container = document.createElement("div");
    renderDay30(container, ["10.0.0.1", "10.0.0.2"], [
      { date: "2026-06-01", connections: [{ node_ip: "10.0.0.1", target_ip: "10.0.0.2", ping_uptime_pct: 100, http_uptime_pct: 99.5, total_checks: 8640 }] },
    ]);
    expect(container.querySelectorAll("details").length).toBe(2);
  });

  it("shows no-data message for null days", () => {
    const container = document.createElement("div");
    renderDay30(container, ["10.0.0.1"], undefined);
    expect(container.innerHTML).toContain("No data available");
  });

  it("sets data-node-pair attribute on circles", () => {
    const container = document.createElement("div");
    renderDay30(container, ["10.0.0.1", "10.0.0.2"], [
      { date: "2026-06-01", connections: [{ node_ip: "10.0.0.1", target_ip: "10.0.0.2", ping_uptime_pct: 100, http_uptime_pct: 99.5, total_checks: 8640 }] },
    ]);
    const circle = container.querySelector("[data-node-pair]");
    expect(circle?.getAttribute("data-node-pair")).toBe("10.0.0.1--10.0.0.2");
  });
});
```

Also update `frontend/src/main.test.ts`:
```typescript
import { describe, it, expect } from "vitest";

describe("app", () => {
  it("stub test passes", () => {
    expect(1 + 1).toBe(2);
  });
});
```
</action>

<acceptance_criteria>
- `npm test` passes (all tests)
- Tests cover matrix rendering, cards rendering, 30-day rendering
- Tests verify data-node-pair attribute presence
- Tests verify empty/error states
</acceptance_criteria>

---

## Verification

### must_haves
- [ ] `npm run build` succeeds
- [ ] `npm test` passes
- [ ] `npm run typecheck` exits 0
- [ ] `npm run lint` passes
- [ ] Connectivity matrix renders as N×N table with colored dots (DASH-01)
- [ ] Detail cards show status badge, latencies, inline uptime % (DASH-02)
- [ ] 30-day view shows daily aggregated uptime per pair (DASH-03)
- [ ] Auto-refresh fires every 10s via `setInterval` (DASH-04)
- [ ] Matrix column headers use short labels with full IP on hover (DASH-05)
- [ ] Cards match v0.4 visual design (color-coded border, status pill, monospace IP) (DASH-06)
- [ ] Tab switching between 30m and 30d views works
- [ ] Error states handled (inline message, stale data preservation)
- [ ] Loading state displayed on initial fetch
</acceptance_criteria>

## Verification

### must_haves
- [ ] `npm run build` succeeds
- [ ] `npm test` passes
- [ ] `npm run typecheck` exits 0
- [ ] `npm run lint` passes
- [ ] Connectivity matrix renders as N×N table with colored dots (DASH-01)
- [ ] Detail cards show status badge, latencies, inline uptime % (DASH-02)
- [ ] 30-day view shows daily aggregated uptime per pair (DASH-03)
- [ ] Auto-refresh fires every 10s via `setInterval` (DASH-04)
- [ ] Matrix column headers use short labels with full IP on hover (DASH-05)
- [ ] Cards match v0.4 visual design (color-coded border, status pill, monospace IP) (DASH-06)
- [ ] Tab switching between 30m and 30d views works
- [ ] Error states handled (inline message, stale data preservation)
- [ ] Loading state displayed on initial fetch
</acceptance_criteria>
