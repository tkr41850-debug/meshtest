import type { BarEntry, DayData } from "../types";
import { cardHtml } from "./card";

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
  const recentDays = allDays.slice(-90);
  const pingBars: BarEntry[] = [];
  const httpBars: BarEntry[] = [];
  for (let i = 0; i < 90; i++) {
    const dayIndex = recentDays.length - 90 + i;
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

function sumDailyChecks(
  days: DayData[],
  src: string,
  tgt: string,
): number {
  let total = 0;
  for (const day of days) {
    const conn = day.connections.find(
      (c) => c.node_ip === src && c.target_ip === tgt,
    );
    if (conn) total += conn.total_checks;
  }
  return total;
}

function computeStatus(
  pingUp: number,
  httpUp: number,
): string {
  if (pingUp >= 99.9 && httpUp >= 99.9) return "OK";
  if (pingUp < 99.9 && httpUp < 99.9) return "Pending";
  return "NotAvailable";
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
    const seenPairs = new Set<string>();
    for (const day of days) {
      for (const conn of day.connections) {
        if (conn.node_ip !== src) continue;
        const pairKey = `${src}--${conn.target_ip}`;
        if (seenPairs.has(pairKey)) continue;
        seenPairs.add(pairKey);
        hasData = true;
        const { pingBars, httpBars } = dailyBarsForPair(days, src, conn.target_ip);
        const st = computeStatus(conn.ping_uptime_pct, conn.http_uptime_pct);
        const lastSeen = day.date;
        const totalChecks = sumDailyChecks(days, src, conn.target_ip);
        html += cardHtml(
          conn.target_ip,
          st,
          `${conn.ping_uptime_pct.toFixed(1)}%`,
          `${conn.http_uptime_pct.toFixed(1)}%`,
          lastSeen,
          conn.ping_uptime_pct,
          conn.http_uptime_pct,
          totalChecks,
          pingBars,
          httpBars,
          pairKey,
        );
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
