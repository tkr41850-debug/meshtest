import type { BarEntry, HourData } from "../types";
import { cardHtml } from "./card";

function hourlyBarsForPair(
  hours: HourData[],
  src: string,
  tgt: string,
): { pingBars: BarEntry[]; httpBars: BarEntry[] } {
  const recentHours = hours.slice(-90);
  const pingBars: BarEntry[] = [];
  const httpBars: BarEntry[] = [];
  for (let i = 0; i < 90; i++) {
    const hourIndex = recentHours.length - 90 + i;
    if (hourIndex >= 0 && hourIndex < recentHours.length) {
      const hour = recentHours[hourIndex];
      const conn = hour.connections.find(
        (c) => c.node_ip === src && c.target_ip === tgt,
      );
      if (conn) {
        pingBars.push({
          percent: conn.ping_uptime_pct / 100,
          tooltip: `${hour.date} — ${conn.ping_uptime_pct.toFixed(1)}% ICMP`,
        });
        httpBars.push({
          percent: conn.http_uptime_pct / 100,
          tooltip: `${hour.date} — ${conn.http_uptime_pct.toFixed(1)}% HTTP`,
        });
        continue;
      }
    }
    pingBars.push({ percent: -1, tooltip: "" });
    httpBars.push({ percent: -1, tooltip: "" });
  }
  return { pingBars, httpBars };
}

function aggregateHourlyPct(
  hours: HourData[],
  src: string,
  tgt: string,
): { pingPct: number; httpPct: number; totalChecks: number } {
  let totalOk = 0;
  let totalHttpOk = 0;
  let totalChecks = 0;
  for (const hour of hours) {
    const conn = hour.connections.find(
      (c) => c.node_ip === src && c.target_ip === tgt,
    );
    if (conn) {
      totalOk += conn.ping_ok;
      totalHttpOk += conn.http_ok;
      totalChecks += conn.total_checks;
    }
  }
  return {
    pingPct: totalChecks > 0 ? +(totalOk / totalChecks * 100).toFixed(1) : 0,
    httpPct: totalChecks > 0 ? +(totalHttpOk / totalChecks * 100).toFixed(1) : 0,
    totalChecks,
  };
}

function computeStatus(
  pingUp: number,
  httpUp: number,
): string {
  if (pingUp >= 99.9 && httpUp >= 99.9) return "OK";
  if (pingUp >= 99.9 || httpUp >= 99.9) return "Degraded";
  return "Pending";
}

export function renderHourly(
  container: HTMLElement,
  nodes: string[],
  hours: HourData[] | undefined,
): void {
  if (!hours || hours.length === 0) {
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
      for (const hour of hours) {
        for (const conn of hour.connections) {
          if (conn.node_ip !== src) continue;
          const pairKey = `${src}--${conn.target_ip}`;
          if (seenPairs.has(pairKey)) continue;
          seenPairs.add(pairKey);
          hasData = true;
          const { pingBars, httpBars } = hourlyBarsForPair(hours, src, conn.target_ip);
          const agg = aggregateHourlyPct(hours, src, conn.target_ip);
          const st = computeStatus(agg.pingPct, agg.httpPct);
          const lastSeen = hour.date;
          html += cardHtml(
            conn.target_ip,
            st,
            `${agg.pingPct.toFixed(1)}%`,
            `${agg.httpPct.toFixed(1)}%`,
            lastSeen,
            agg.pingPct,
            agg.httpPct,
            agg.totalChecks,
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
