# Phase 9: Dashboard Views — UI Design Contract

## Overview

Port the Streamlit dashboard views (30-minute connectivity matrix, per-pair detail cards, 30-day aggregated uptime) to the Vite + TypeScript + Tailwind CSS frontend. All data from same-origin API, auto-refresh every 10s.

---

## Visual Design

### Color Palette

| Token | Value | Usage |
|-------|-------|-------|
| `mesh-green` | `#22c55e` | OK status, >=99% uptime |
| `mesh-amber` | `#f59e0b` | NotAvailable, >=95% uptime |
| `mesh-red` | `#ef4444` | <95% uptime |
| `mesh-gray` | `#9ca3af` | Pending, dividers, muted text |
| `mesh-dark` | `#1f2937` | Headings, primary text |
| `mesh-muted` | `#6b7280` | Secondary text, labels |
| `mesh-border` | `#e5e7eb` | Table borders, card borders |
| `mesh-bg` | `#f3f4f6` | Table header backgrounds |

Already defined in `style.css`.

### Typography

- **Body**: system-ui/-apple-system stack (default Tailwind)
- **IPs/status text**: `font-mono` (ui-monospace stack)
- **Matrix headers**: `font-semibold`
- **Card details**: 12-14px range

### Spacing

- **Layout**: `max-w-6xl mx-auto p-6`
- **Matrix cells**: `px-2 py-1` (tight)
- **Cards**: `p-3 mb-2` with `rounded-lg` and `border-l-4`

---

## Component Architecture

### File Structure

```
frontend/src/
├── main.ts         # Entry: setInterval, tab switching, initial render
├── style.css       # Tailwind theme (already exists)
├── types.ts        # TS interfaces for API responses
├── api.ts          # fetchData30m(), fetchData30d(), fetchNodeList()
└── views/
    ├── matrix.ts   # Connectivity matrix renderer
    ├── cards.ts    # Per-pair detail cards renderer
    └── day30.ts    # 30-day aggregated uptime renderer
```

### Data Flow

```
main.ts (setInterval 10s)
  → api.ts (fetch /data?window=30m, /data?window=30d, /node-list)
  → types.ts (interfaces for response shapes)
  → views/matrix.ts (render into #matrix-container)
  → views/cards.ts (render into #cards-container)
  → views/day30.ts (render into #day30-container)
```

---

## View Specifications

### 30-Minute View (Tab 1)

**Connectivity Matrix** (`#matrix-container`)

| Aspect | Spec |
|--------|------|
| Structure | N×N HTML table, `<table>` with `<th>` headers, `<td>` cells |
| Diagonal cells | Gray em-dash `—` (self-references) |
| Status dots | `●` colored circle character |
| OK (both ping+http OK) | `text-mesh-green` |
| NotAvailable (either) | `text-mesh-amber` |
| Pending (default) | `text-mesh-gray` |
| Row headers | Source IP in monospace, left-aligned |
| Column headers | Short label (last segment before first `.` or after last `-`), monospace, centered, full IP on `title` hover |
| Overflow | `overflow-x-auto` wrapper |

**Detail Cards** (`#cards-container`)

| Aspect | Spec |
|--------|------|
| Structure | `<details>` expander per source node |
| Expander label | `▶ {src_ip}  [{summary}]  —  {N} targets` |
| Summary logic | All OK → "All OK"; none OK → "Pending"; else "{N} of {N} down" |
| Card per target | `<div>` with left border, rounded corners, white bg |
| Status badge | `<span>` pill: green bg + "OK", amber bg + "Not Available", gray bg + "Pending" |
| IP | Monospace, bold, dark text |
| Metrics row | Ping latency, HTTP latency, last check time |
| Inline uptime % | Colored span after each latency: `(XX.X%)` in green/amber/red |
| Latency format | `X.Xms` or em-dash if missing |
| Timestamp format | `HH:MM:SS` |

### 30-Day View (Tab 2)

**Aggregated Uptime** (`#day30-container`)

| Aspect | Spec |
|--------|------|
| Structure | `<details>` expander per source node |
| Rows | One row per target per day |
| Date column | `YYYY-MM-DD → target_ip` |
| Uptime cell | Diagonally split circle (`background: linear-gradient(...)`): left/upper half = ping uptime color, right/lower half = http uptime color |
| Best uptime badge | Colored pill: >=99% green, >=95% amber, <95% red (best of ping+http) |
| Ping % column | `XX.X%` |
| HTTP % column | `XX.X%` |
| Total checks column | Integer count |
| Click action | Each circle gets `data-node-pair="{src_ip}--{tgt_ip}"` and `id="uptime-cell-{src_ip}--{tgt_ip}"` for Phase 11 scrollTo |
| Empty state | "No data for this node" or gray em-dashes |

---

## Interaction Behavior

| Behavior | Spec |
|----------|------|
| Auto-refresh | `setInterval(10000)` in main.ts — fetches all 3 endpoints, re-renders all containers |
| Initial load | Show "Loading mesh data..." text, replace on first successful fetch |
| Refresh behavior | Stale-while-revalidate: keep old HTML visible, silently replace on response |
| Error state | Inline error message per view if fetch fails, data stays visible from last successful fetch |
| Tab switching | Two tabs: "30-Minute View" and "30-Day View", show/hide containers |
| Abort | 5s timeout per API call via AbortController |

---

## States

| State | Matrix | Cards | 30-Day |
|-------|--------|-------|--------|
| Loading | "Loading..." | "Loading..." | "Loading..." |
| No data | "No data available" (no nodes or null response) | "No data available" | "No data available" |
| Error | Error message | Error message | Error message |
| Normal | Table + cards rendered | Cards rendered | Table rendered |
| <2 nodes | No matrix shown (only cards) | Cards with self-only skip | Table with self-only skip |

---

## Responsive & Accessibility

- Desktop-first (primary use case)
- Matrix uses `overflow-x-auto` for horizontal scroll on small windows
- Cards wrap metrics via `flex-wrap`
- Color is not the only indicator — status badge text communicates state
- Tab keyboard navigable
