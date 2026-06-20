import type { BarEntry } from "../types";

export function barColor(percent: number): string {
  if (percent < 0) return "#e5e7eb";
  const hue = percent * 120;
  return `hsl(${hue.toFixed(0)}, 85%, 40%)`;
}

export function renderBars(bars: BarEntry[]): string {
  return bars
    .map((b) => {
      if (b.percent < 0) {
        return `<span data-history-bar style="display:inline-block;width:8px;height:20px;border-radius:1px;background:#e5e7eb;border:1px solid #d1d5db;" title="No data"></span>`;
      }
      return `<span data-history-bar style="display:inline-block;width:8px;height:20px;border-radius:1px;background:${barColor(b.percent)};border:1px solid #d1d5db;" title="${b.tooltip}"></span>`;
    })
    .join("");
}
