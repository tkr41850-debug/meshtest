# Technology Stack — v0.9 UI Consolidation

**Project:** mesh-status
**Milestone:** v0.9 — 90-bar UI consolidation (subsequent milestone, already in Phase 1)
**Researched:** 2026-06-20
**Verdict:** **No stack changes needed.** Current stack handles 90 bars × 2 types × N node-pairs without issue.

---

## Current Stack (Verified — All Versions Current)

| Technology | Version in package.json | Latest Available | Status |
|------------|------------------------|------------------|--------|
| TypeScript | `~6.0.2` | 6.0.3 | ✅ Locked to 6.0.x, latest is 6.0.3 |
| Vite | `^8.0.12` | 8.0.16 | ✅ ^ resolves to latest 8.0.x |
| Tailwind CSS | `^4.3.1` | 4.3.1 | ✅ Latest |
| @tailwindcss/vite | `^4.3.1` | 4.3.1 | ✅ Matches Tailwind version |
| Vitest | `^4.1.9` | 4.1.9 | ✅ Latest |
| happy-dom | `^20.10.6` | 20.10.2* | ⚠️ See note below |

**\*happy-dom note:** npm registry shows latest as 20.10.2 (Jun 6, 2026). The `^20.10.6` range in package.json may resolve to a newer patch. Not a blocker — happy-dom is only used for test DOM environment, not runtime.

---

## Performance Analysis: 90 Bars × 2 Types × N Node-Pairs

### DOM Element Count Estimate

| Node count (N) | Node-pairs (N×(N-1)) | Bar elements (pairs × 2 × 90) | Total elements incl. cards |
|----------------|----------------------|-------------------------------|---------------------------|
| 5 | 20 | 3,600 | ~4,500 |
| 10 | 90 | 16,200 | ~18,000 |
| 15 | 210 | 37,800 | ~42,000 |
| 20 | 380 | 68,400 | ~76,000 |

### Why innerHTML Is Fine at This Scale

1. **Benchmarks confirm innerHTML is fastest for static bulk markup:**
   - `.map().join("")` + `innerHTML` for 1,000 list items: **~1.5ms** (fastest tested approach)
   - `createElement` + `appendChild`: ~1.7ms
   - `forEach` + per-iteration innerHTML: ~920ms (the only truly slow approach)
   - Source: [Go Make Things — DOM injection performance tests](https://gomakethings.com/testing-dom-injection-performance-with-vanilla-js/)

2. **Extrapolation to 90 bars:**
   - A single `renderBars(90)` call generates ~7,650 chars of HTML (90 × ~85 chars per `<span>`)
   - Two bar rows per pair = ~15,300 chars
   - For 90 pairs (10 nodes): ~1.38M chars total
   - Expected innerHTML cost for full rebuild: **15–30ms** (linear with element count, browser HTML parser is native code)
   - This is the total render time for a full dashboard refresh — well within acceptable range for a monitoring tool with multi-second poll intervals

3. **Why the full-rebuild model works here:**
   - Views are rebuilt entirely on each data refresh (no incremental updates)
   - There are no single-bar mutations that would benefit from VDOM diffing
   - The innerHTML approach avoids framework overhead entirely
   - No event listeners exist on individual bar elements (event delegation on parent containers)

### What Would Be Slow (And We Don't Do)

The only approach that benchmarks show as catastrophically slow at scale is **per-element DOM appending in a loop** (the "Inject on each loop" pattern at ~920ms for 1,000 elements). The current code correctly builds a single HTML string with `.map().join("")` and assigns to `innerHTML` once — the fast pattern.

---

## CSS-Only Performance Optimizations (Recommended, Zero Library Cost)

These are the only additions needed — native CSS properties that the browser provides at no cost.

### 1. `content-visibility: auto` on card containers

```css
[data-source-group] {
  content-visibility: auto;
  contain-intrinsic-size: 120px; /* approximate card height */
}
```

**Effect:** Browser skips layout/paint for cards that are off-screen until they scroll close to the viewport.
**Benefit:** Google web.dev case study reports **7× rendering speedup** on initial load for long pages.
**Support:** Chrome 85+, Firefox 125+, Safari 18+ — all current evergreen browsers.
**Source:** [MDN — content-visibility](https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/Properties/content-visibility)

**Mandatory pairing:** Always pair with `contain-intrinsic-size` to prevent 0px height collapse on off-screen elements.

**Where to apply:**
- `[data-source-group]` — each source node's group of target cards
- Not on `[data-source-header]` (sticky headers must remain visible)

### 2. `contain: layout style paint` on individual cards

```css
[data-history-bar] {
  contain: layout style paint;
}
```

**Effect:** Isolates each bar span's layout from the rest of the page. Style changes inside don't propagate up.
**Support:** Chrome 52+, Safari 15.4+, Firefox 118+ — universally supported in modern browsers.
**Source:** [MDN — CSS containment](https://developer.mozilla.org/en-US/docs/Web/CSS/Guides/Containment/Using)

---

## What NOT to Add

| Technology | Why Not |
|------------|---------|
| **React / Vue / Svelte** | Would require full rewrite from string-concat to JSX/templates. No incremental updates needed — full rebuilds per data refresh. Framework overhead (40-100KB) with zero benefit for this use case. |
| **virtual-scroll / react-window** | Cards grouped hierarchically per source node with sticky headers. Fixed-list virtualization breaks this grouping. Not needed at practical node counts (10-20 nodes). |
| **D3 / chart.js / any chart lib** | Bars are styled `<span>` elements with `background-color`. A chart library adds 40-200KB+ for what 10 lines of CSS + template can do. |
| **lit-html / htmx** | These bring incremental DOM diffing for per-element updates. We do full-rebuild — no diff needed. Adds complexity without benefit. |
| **CSS-in-JS (emotion, styled-components)** | Tailwind handles all styling. CSS-in-JS adds runtime cost and bundle size. |
| **Web Components** | Over-engineered for styling `<span>` elements. Current approach of `data-` attributes + CSS is simpler. |
| **Canvas / WebGL** | Monumental overkill for bar charts. Each bar is 8×20px with a border-radius. GPU acceleration is wasted here. |
| **Streaming DOM (generative-dom)** | Designed for token-stream rendering (e.g., LLM output). Data is fully available at render time — no streaming benefit. |

---

## What Actually Changes (Code-Level Only)

These are changes to existing files, not new dependencies:

```
frontend/src/views/bars.ts      # barColor(): HSL gradient → discrete thresholds
frontend/src/views/cards.ts     # aggregateByMinute(): 30→90 bars, parameterize count
frontend/src/views/day30.ts     # dailyBarsForPair(): 30→90 days, rename for clarity
frontend/src/views/new-90h.ts   # NEW: hourly bar view (similar to cards.ts with hourly buckets)
frontend/src/styles/**          # content-visibility / contain CSS additions
```

No `npm install` needed. No new `devDependencies`. No build config changes.

---

## Integration Points

| Integration | Current | After v0.9 |
|-------------|---------|------------|
| Build tool | Vite 8 via `@tailwindcss/vite` plugin | Same — no config change |
| Testing | Vitest + happy-dom | Same — CSS additions don't affect tests |
| TypeScript | strict mode, bundler module resolution | Same |
| CSS pipeline | Tailwind 4 with JIT (class scanning) | Same — new CSS uses standard Tailwind classes + custom CSS |
| Bar rendering | `renderBars()` in `bars.ts` | Same function signature, changed color logic |
| View structure | String concatenation → innerHTML | Same pattern |

---

## Sources

- [Vite 8 Changelog](https://github.com/vitejs/vite/blob/main/packages/vite/CHANGELOG.md) — v8.0.16 latest (Jun 2026)
- [Tailwind CSS 4.3.1 Release](https://github.com/tailwindlabs/tailwindcss/releases/tag/v4.3.1) — Latest (Jun 12, 2026)
- [TypeScript 6.0.3 Release](https://github.com/microsoft/TypeScript/releases/tag/v6.0.3) — Latest (Apr 2026)
- [Vitest 4.1.9 Release](https://github.com/vitest-dev/vitest/releases/tag/v4.1.9) — Latest (Jun 2026)
- [MDN — content-visibility](https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/Properties/content-visibility) — Render deferral for off-screen elements
- [MDN — CSS Containment](https://developer.mozilla.org/en-US/docs/Web/CSS/Guides/Containment/Using) — Layout/style/paint isolation
- [Go Make Things — DOM injection performance](https://gomakethings.com/testing-dom-injection-performance-with-vanilla-js/) — innerHTML vs DOM creation benchmarks
- [TheLinuxCode — innerHTML in 2026](https://thelinuxcode.com/html-dom-innerhtml-property-in-2026-practical-patterns-pitfalls-and-safer-alternatives/) — Modern innerHTML patterns and performance
