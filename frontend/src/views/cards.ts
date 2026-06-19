import type { CheckResult, StatusEntry } from "../types";

function summaryLabel(
  src: string,
  nodes: string[],
  combined: Map<string, string>,
): string {
  const targets = nodes.filter((n) => n !== src);
  if (targets.length === 0) return "No targets";
  const ok = targets.filter(
    (t) => combined.get(`${src}|${t}`) === "OK",
  ).length;
  if (ok === targets.length) return "All OK";
  if (ok === 0) return "Pending";
  return `${targets.length - ok} of ${targets.length} down`;
}

function uptimeColor(pct: number): string {
  if (pct >= 99) return "#22c55e";
  if (pct >= 95) return "#f59e0b";
  return "#ef4444";
}

function uptimeSpan(pct: number | null): string {
  if (pct === null) return "";
  const c = uptimeColor(pct);
  return `<span style="color:${c};font-weight:600;">(${pct.toFixed(1)}%)</span>`;
}

const BADGE_MAP: Record<string, { color: string; label: string }> = {
  OK: { color: "#22c55e", label: "OK" },
  NotAvailable: { color: "#f59e0b", label: "Not Available" },
  Pending: { color: "#9ca3af", label: "Pending" },
};

function cardHtml(
  tgtIp: string,
  status: string,
  pingLat: string,
  httpLat: string,
  lastSeen: string,
  pingUp: number | null,
  httpUp: number | null,
): string {
  const badge = BADGE_MAP[status] ?? BADGE_MAP.Pending;
  return [
    `<div class="border border-mesh-border border-l-4 rounded-lg p-3 mb-2 bg-white" style="border-left-color:${badge.color}">`,
    `<div class="flex items-center gap-2 mb-1">`,
    `<span class="inline-block px-2.5 py-0.5 rounded-full text-xs font-semibold tracking-wide text-white" style="background:${badge.color}">${badge.label}</span>`,
    `<span class="font-mono text-sm font-semibold text-mesh-dark">${tgtIp}</span>`,
    `</div>`,
    `<div class="text-xs text-mesh-muted flex gap-4 flex-wrap">`,
    `<span>Ping: <strong class="text-mesh-dark">${pingLat}</strong> ${uptimeSpan(pingUp)}</span>`,
    `<span>HTTP: <strong class="text-mesh-dark">${httpLat}</strong> ${uptimeSpan(httpUp)}</span>`,
    `<span>Last: <strong class="text-mesh-dark">${lastSeen}</strong></span>`,
    `</div></div>`,
  ].join("");
}

export function renderCards(
  container: HTMLElement,
  nodes: string[],
  statuses: StatusEntry[],
  checks: CheckResult[],
  uptimeMap: Map<string, [number | null, number | null]>,
): void {
  if (nodes.length === 0) {
    container.innerHTML =
      '<p class="text-mesh-muted text-sm">No nodes registered</p>';
    return;
  }

  const combined = new Map<string, string>();
  for (const s of statuses) {
    const ping = s.ping_status === "OK";
    const http = s.http_status === "OK";
    let st: string;
    if (ping && http) st = "OK";
    else if (
      s.ping_status === "NotAvailable" ||
      s.http_status === "NotAvailable"
    )
      st = "NotAvailable";
    else st = "Pending";
    combined.set(`${s.node_ip}|${s.target_ip}`, st);
  }

  const latestCheck = new Map<string, CheckResult>();
  for (const c of checks) {
    const key = `${c.node_ip}|${c.target_ip}`;
    const existing = latestCheck.get(key);
    if (!existing || c.timestamp > existing.timestamp) {
      latestCheck.set(key, c);
    }
  }

  const sorted = [...nodes].sort();
  let html = "";
  for (const src of sorted) {
    const summary = summaryLabel(src, sorted, combined);
    html += `<details class="mb-3"><summary class="cursor-pointer font-mono text-sm text-mesh-dark font-semibold">${src}  [${summary}]  — ${sorted.filter((n) => n !== src).length} targets</summary><div class="pl-4 mt-2">`;
    for (const tgt of sorted) {
      if (src === tgt) continue;
      const st = combined.get(`${src}|${tgt}`) ?? "Pending";
      const ck = latestCheck.get(`${src}|${tgt}`) ?? ({} as CheckResult);
      const pingLat =
        ck.ping_latency_ms != null
          ? `${ck.ping_latency_ms.toFixed(1)}ms`
          : "—";
      const httpLat =
        ck.http_latency_ms != null
          ? `${ck.http_latency_ms.toFixed(1)}ms`
          : "—";
      const lastSeen = ck.timestamp
        ? new Date(ck.timestamp * 1000).toLocaleTimeString()
        : "—";
      const uptime = uptimeMap.get(`${src}|${tgt}`) ?? [null, null];
      html += cardHtml(
        tgt,
        st,
        pingLat,
        httpLat,
        lastSeen,
        uptime[0],
        uptime[1],
      );
    }
    html += "</div></details>";
  }

  container.innerHTML = html;
}
