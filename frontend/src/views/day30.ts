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
        const best = Math.max(
          conn.ping_uptime_pct,
          conn.http_uptime_pct,
        );
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
      html +=
        '<p class="text-xs text-mesh-muted">No data for this node</p>';
    }
    html += "</div></details>";
  }
  container.innerHTML = html;
}
