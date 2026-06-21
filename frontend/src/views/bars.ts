import type { BarEntry } from "../types";
import { uptimeColor } from "./colors";

export { uptimeColor as barColor };

export function renderBars(bars: BarEntry[]): string {
  return bars
    .map((b) => {
      const title = b.percent < 0 ? "No data" : b.tooltip;
      return `<span data-history-bar style="display:inline-block;width:8px;height:20px;border-radius:1px;background:${uptimeColor(b.percent)};border:1px solid #d1d5db;" data-tooltip="${title}"></span>`;
    })
    .join("");
}
