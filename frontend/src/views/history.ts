import type { DayData } from "../types";

function uptimeColor(pct: number): string {
  if (pct >= 99) return "#22c55e";
  if (pct >= 95) return "#f59e0b";
  return "#ef4444";
}

function barHtml(
  pingPct: number,
  httpPct: number,
  date: string,
): string {
  const pingColor = uptimeColor(pingPct);
  const httpColor = uptimeColor(httpPct);
  return [
    '<span style="display:inline-block;width:12px;height:40px;border-radius:2px;',
    `background:linear-gradient(135deg,${pingColor} 50%,${httpColor} 50%);`,
    'border:1px solid #d1d5db;vertical-align:bottom;"',
    ` title="${date} | Ping: ${pingPct.toFixed(1)}% | HTTP: ${httpPct.toFixed(1)}%"`,
    "></span>",
  ].join("");
}

function emptyBar(): string {
  return [
    '<span style="display:inline-block;width:12px;height:40px;border-radius:2px;',
    'background:#e5e7eb;border:1px solid #d1d5db;vertical-align:bottom;"',
    ' title="No data"></span>',
  ].join("");
}

function sparklineHtml(values: number[]): string {
  if (values.length === 0) return "";
  const w = 180;
  const h = 30;
  const max = Math.max(...values, 1);
  const points = values
    .map((v, i) => {
      const x = (i / (values.length - 1)) * w;
      const y = h - (v / max) * h;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
  const lastY = h - (values[values.length - 1] / max) * h;
  return [
    `<svg width="${w}" height="${h}" class="inline-block align-middle ml-2">`,
    `<polyline points="${points}" fill="none" stroke="#6b7280" stroke-width="2"/>`,
    `<polygon points="0,${h} ${points} ${w},${h}" fill="rgba(107,114,128,0.1)"/>`,
    `<circle cx="${w}" cy="${lastY.toFixed(1)}" r="2.5" fill="#6b7280"/>`,
    "</svg>",
  ].join("");
}

export function renderHistory(
  container: HTMLElement,
  nodes: string[],
  days: DayData[] | undefined,
): void {
  if (!days || days.length === 0) {
    container.innerHTML =
      '<p class="text-mesh-muted text-sm">No history data available for this time window</p>';
    return;
  }

  const sorted = [...nodes].sort();
  let html = "";
  for (const src of sorted) {
    html +=
      '<details class="mb-3"><summary class="cursor-pointer font-mono text-sm text-mesh-dark font-semibold">' +
      src +
      "</summary><div class=\"pl-4 mt-2\">";
    let hasAnyData = false;
    for (const tgt of sorted) {
      if (src === tgt) continue;
      const pairKey = `${src}--${tgt}`;
      const conns: Array<{
        ping: number;
        http: number;
        date: string;
      }> = [];
      for (const day of days) {
        const c = day.connections.find(
          (conn) =>
            conn.node_ip === src && conn.target_ip === tgt,
        );
        if (c) {
          conns.push({
            ping: c.ping_uptime_pct,
            http: c.http_uptime_pct,
            date: day.date,
          });
        }
      }
      if (conns.length === 0) continue;
      hasAnyData = true;
      const bests = conns.map((c) => Math.max(c.ping, c.http));
      html +=
        '<details class="mb-2" id="history-' +
        pairKey +
        '" style="scroll-margin-top:20px;"><summary class="cursor-pointer font-mono text-xs text-mesh-dark">' +
        tgt +
        "</summary><div class=\"pl-2 mt-1 flex items-end gap-0.5 flex-wrap\">";
      for (let i = 0; i < 30; i++) {
        const idx = conns.length - 30 + i;
        if (idx >= 0 && idx < conns.length) {
          const c = conns[idx];
          html += barHtml(c.ping, c.http, c.date);
        } else {
          html += emptyBar();
        }
      }
      html += sparklineHtml(bests);
      html += "</div></details>";
    }
    if (!hasAnyData)
      html +=
        '<p class="text-xs text-mesh-muted">No history data for this node</p>';
    html += "</div></details>";
  }
  container.innerHTML = html;
}
