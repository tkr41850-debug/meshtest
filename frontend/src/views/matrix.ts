import type { StatusEntry } from "../types";

function computeStatus(
  s: StatusEntry,
): "OK" | "Degraded" | "NotAvailable" | "Pending" {
  if (s.ping_status === "OK" && s.http_status === "OK") return "OK";
  if (s.ping_status === "Pending" && s.http_status === "Pending") return "Pending";
  if (s.ping_status === "NotAvailable" && s.http_status === "NotAvailable") return "NotAvailable";
  return "Degraded";
}

function shortLabel(ip: string): string {
  const firstDot = ip.indexOf(".");
  const beforeDot = ip.slice(0, firstDot);
  const lastDash = beforeDot.lastIndexOf("-");
  return lastDash !== -1
    ? beforeDot.slice(lastDash + 1)
    : beforeDot;
}

const STATUS_DOT: Record<string, string> = {
  OK: "●",
  Degraded: "●",
  NotAvailable: "●",
  Pending: "●",
};

const STATUS_COLOR: Record<string, string> = {
  OK: "text-mesh-green",
  Degraded: "text-mesh-amber",
  NotAvailable: "text-mesh-red",
  Pending: "text-mesh-gray",
};

export function renderMatrix(
  container: HTMLElement,
  nodes: string[],
  statuses: StatusEntry[],
): void {
  if (nodes.length < 2) {
    container.innerHTML =
      '<p class="text-mesh-muted text-sm">Need at least 2 nodes for a matrix</p>';
    return;
  }

  const combined = new Map<string, string>();
  for (const s of statuses) {
    combined.set(`${s.node_ip}|${s.target_ip}`, computeStatus(s));
  }

  let html =
    '<div class="overflow-x-auto"><table class="w-full text-sm border-collapse">';
  html += "<tr><th></th>";
  for (const tgt of nodes) {
    html += `<th class="px-2 py-1 text-center font-semibold text-mesh-dark bg-mesh-bg border border-mesh-border font-mono"><div class="mesh-tooltip-group"><span>${shortLabel(tgt)}</span><div class="mesh-tooltip">${tgt}</div></div></th>`;
  }
  html += "</tr>";

  for (const src of nodes) {
    html += `<tr><td class="px-2 py-1 font-mono text-mesh-dark border border-mesh-border whitespace-nowrap">${src}</td>`;
    for (const tgt of nodes) {
      const key = `${src}|${tgt}`;
      if (src === tgt) {
        html += '<td class="px-2 py-1 text-center text-mesh-gray border border-mesh-border">—</td>';
      } else {
        const st = combined.get(key) ?? "Pending";
        html += `<td class="px-2 py-1 text-center border border-mesh-border"><span class="${STATUS_COLOR[st]} text-lg">${STATUS_DOT[st]}</span></td>`;
      }
    }
    html += "</tr>";
  }
  html += "</table></div>";

  container.innerHTML = html;
}
