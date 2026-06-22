import type { BarEntry, CheckResult, StatusEntry } from "../types";
import { cardHtml } from "./card";

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

function aggregateByMinute(
  checks: CheckResult[],
  src: string,
  tgt: string,
): { pingBars: BarEntry[]; httpBars: BarEntry[] } {
  const pairChecks = checks.filter(
    (c) => c.node_ip === src && c.target_ip === tgt,
  );
  const now = pairChecks.length > 0
    ? Math.max(...pairChecks.map((c) => c.timestamp))
    : Date.now() / 1000;
  const currentMinute = Math.floor(now / 60) * 60;
  const buckets = new Map<
    number,
    { total: number; pingOk: number; httpOk: number }
  >();
  for (const c of pairChecks) {
    const minute = Math.floor(c.timestamp / 60) * 60;
    if (!buckets.has(minute)) {
      buckets.set(minute, { total: 0, pingOk: 0, httpOk: 0 });
    }
    const b = buckets.get(minute)!;
    b.total++;
    if (c.ping_ok) b.pingOk++;
    if (c.http_ok) b.httpOk++;
  }
  const pingBars: BarEntry[] = [];
  const httpBars: BarEntry[] = [];
  for (let i = 89; i >= 0; i--) {
    const minute = currentMinute - i * 60;
    const b = buckets.get(minute);
    if (b && b.total > 0) {
      const label = new Date(minute * 1000).toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
      });
      const pingPct = b.pingOk / b.total;
      const httpPct = b.httpOk / b.total;
      pingBars.push({
        percent: pingPct,
        tooltip: `${label} — ${(pingPct * 100).toFixed(1)}% ICMP`,
      });
      httpBars.push({
        percent: httpPct,
        tooltip: `${label} — ${(httpPct * 100).toFixed(1)}% HTTP`,
      });
    } else {
      pingBars.push({ percent: -1, tooltip: "" });
      httpBars.push({ percent: -1, tooltip: "" });
    }
  }
  return { pingBars, httpBars };
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
    else if (s.ping_status === "Pending" && s.http_status === "Pending") st = "Pending";
    else if (!ping && !http) st = "NotAvailable";
    else st = "Degraded";
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
    const targets = sorted.filter((n) => n !== src);
    html += `<div data-source-group class="mb-6">`;
    html += `<div data-source-header class="sticky top-0 bg-mesh-bg z-10 font-mono text-sm font-semibold text-mesh-dark py-2 border-b border-mesh-border">${src}  [${summary}]  — ${targets.length} targets</div>`;
    html += `<div class="pl-4 mt-2">`;
    for (const tgt of targets) {
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
      const { pingBars, httpBars } = aggregateByMinute(checks, src, tgt);
      const totalChecks = checks.filter(
        (c) => c.node_ip === src && c.target_ip === tgt,
      ).length;
      html += cardHtml(
        tgt,
        st,
        pingLat,
        httpLat,
        lastSeen,
        uptime[0],
        uptime[1],
        totalChecks,
        pingBars,
        httpBars,
      );
    }
    html += "</div></div>";
  }

  container.innerHTML = html;
}
