# Phase 11: Uptime History Visualization — UI Design Contract

## History Section Layout

```
Source Node ▼
├── target1-ip ▼
│   ┌─────────────────────────────────────────────────────┐
│   │ [bar][bar][bar][bar][bar]...[bar]   ╱‾‾‾╲          │
│   │                                       ╲__╱‾\       │
│   │                                       Sparkline    │
│   │ Day1  Day2  Day3 ... Day30             Trend       │
│   └─────────────────────────────────────────────────────┘
├── target2-ip ▼
│   ...
```

## Bar Specification

| Aspect | Spec |
|--------|------|
| Count | 30 bars per row (one per day) |
| Width | 12px each, 4px gap |
| Height | 40px |
| Color | Diagonally split: `background: linear-gradient(135deg, pingColor 50%, httpColor 50%)` |
| Color logic | >=99% green `#22c55e`, >=95% amber `#f59e0b`, <95% red `#ef4444`, no data gray `#e5e7eb` |
| Border | 1px solid `#d1d5db`, rounded `2px` |
| Tooltip | `title="YYYY-MM-DD | Ping: X.X% | HTTP: X.X%"` |

## Sparkline Specification

| Aspect | Spec |
|--------|------|
| Type | Inline SVG `<svg>` with `<polyline>` |
| Dimensions | 180×30px |
| Points | 30 data points (one per day), best of ping+http uptime % |
| Line color | `#6b7280` (mesh-muted), 2px stroke |
| Fill | Light gray gradient `fill: rgba(107,114,128,0.1)` |
| Y-axis | Mapped so 100% = top, 0% = bottom |

## Interaction

| Behavior | Spec |
|----------|------|
| Expand/collapse | Per-pair `<details>` under per-source `<details>` (nested accordion) |
| ScrollTo from Phase 9 | Click on 30-day split circle → scroll to `#history-{pairKey}` with `scrollIntoView({ behavior: 'smooth' })` |
| scroll-margin-top | 20px on history sections for header visibility |

## Empty State

- No data: "No history data available for this time window"
- Per-pair with no data: "No data" gray text
