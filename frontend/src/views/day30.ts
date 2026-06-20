import type { BarEntry, DayData } from "../types";
import { renderBars } from "./bars";

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

function dailyBarsForPair(
  days: DayData[],
  src: string,
  tgt: string,
): { pingBars: BarEntry[]; httpBars: BarEntry[] } {
  const allDays = days
    .filter((d) =>
      d.connections.some(
        (c) => c.node_ip === src && c.target_ip === tgt,
      ),
    )
    .sort((a, b) => a.date.localeCompare(b.date));
  const recentDays = allDays.slice(-30);
  const pingBars: BarEntry[] = [];
  const httpBars: BarEntry[] = [];
  for (let i = 0; i < 30; i++) {
    const dayIndex = recentDays.length - 30 + i;
    if (dayIndex >= 0 && dayIndex < recentDays.length) {
      const day = recentDays[dayIndex];
      const conn = day.connections.find(
        (c) => c.node_ip === src && c.target_ip === tgt,
      );
      if (conn) {
        pingBars.push({
          percent: conn.ping_uptime_pct / 100,
          tooltip: `${day.date} — ${conn.ping_uptime_pct.toFixed(1)}% ICMP`,
        });
        httpBars.push({
          percent: conn.http_uptime_pct / 100,
          tooltip: `${day.date} — ${conn.http_uptime_pct.toFixed(1)}% HTTP`,
        });
        continue;
      }
    }
    pingBars.push({ percent: -1, tooltip: "" });
    httpBars.push({ percent: -1, tooltip: "" });
  }
  return { pingBars, httpBars };
}

export function renderDay30(
  container: HTMLElement,
  nodes: string[],
  days: DayData[] | undefined,
): void {
  if (!days || days.length === 0) {
    container.innerHTML =
      '<p class="text-mesh-muted text-sm">No data available for this time window</p>';
    return;
  }

  const sorted = [...nodes].sort();
  let html = "";
  for (const src of sorted) {
    html += `<div data-source-group class="mb-6">`;
    html += `<div data-source-header class="sticky top-0 bg-mesh-bg z-10 font-mono text-sm font-semibold text-mesh-dark py-2 border-b border-mesh-border">${src}</div>`;
    html += `<div class="pl-4 mt-2">`;

    let hasData = false;
    for (const day of days) {
      const conns = day.connections.filter((c) => c.node_ip === src);
      if (conns.length === 0) {
        html += `<div class="text-xs text-mesh-muted py-1">${day.date} → —</div>`;
        continue;
      }
      hasData = true;
      for (const conn of conns) {
        const best = Math.max(
          conn.ping_uptime_pct,
          conn.http_uptime_pct,
        );
        const pairKey = `${src}--${conn.target_ip}`;
        const { pingBars, httpBars } = dailyBarsForPair(days, src, conn.target_ip);
        html += [
          `<div class="py-1 text-xs border-b border-mesh-border last:border-0">`,
          `<div class="flex items-center gap-3">`,
          `<span class="w-32 font-mono text-mesh-muted">${day.date} → ${conn.target_ip}</span>`,
          `<span data-node-pair="${pairKey}" id="uptime-cell-${pairKey}">${splitCircle(conn.ping_uptime_pct, conn.http_uptime_pct)}</span>`,
          `<span>${badgeHtml(best)}</span>`,
          `<span class="font-mono text-mesh-dark w-16 text-right">${conn.ping_uptime_pct.toFixed(1)}%</span>`,
          `<span class="font-mono text-mesh-dark w-16 text-right">${conn.http_uptime_pct.toFixed(1)}%</span>`,
          `<span class="font-mono text-mesh-muted w-10 text-right">${conn.total_checks}</span>`,
          `</div>`,
          `<div class="flex items-end gap-0.5 mt-1 pl-32">${renderBars(pingBars)}</div>`,
          `<div class="flex items-end gap-0.5 mt-0.5 pl-32">${renderBars(httpBars)}</div>`,
          `</div>`,
        ].join("");
      }
    }
    if (!hasData) {
      html +=
        '<p class="text-xs text-mesh-muted">No data for this node</p>';
    }
    html += "</div></div>";
  }
  container.innerHTML = html;
}
