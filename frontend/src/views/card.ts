import type { BarEntry } from "../types";
import { renderBars } from "./bars";
import { uptimeColor } from "./colors";

export const BADGE_MAP: Record<string, { color: string; label: string }> = {
  OK: { color: "#22c55e", label: "OK" },
  NotAvailable: { color: "#f59e0b", label: "Not Available" },
  Pending: { color: "#9ca3af", label: "Pending" },
};

export function splitCircle(pingPct: number, httpPct: number): string {
  const pingColor = uptimeColor(pingPct / 100);
  const httpColor = uptimeColor(httpPct / 100);
  return `<span style="display:inline-block;width:24px;height:24px;border-radius:50%;background:linear-gradient(135deg,${pingColor} 50%,${httpColor} 50%);vertical-align:middle;"></span>`;
}

function uptimeSpan(pct: number | null): string {
  if (pct === null) return "";
  const c = uptimeColor(pct / 100);
  return `<span style="color:${c};font-weight:600;">(${pct.toFixed(1)}%)</span>`;
}

export function cardHtml(
  tgtIp: string,
  status: string,
  pingLabel: string,
  httpLabel: string,
  lastSeen: string,
  pingUp: number | null,
  httpUp: number | null,
  totalChecks: number,
  pingBars: BarEntry[],
  httpBars: BarEntry[],
  pairKey?: string,
): string {
  const badge = BADGE_MAP[status] ?? BADGE_MAP.Pending;
  const pingBarHtml = renderBars(pingBars);
  const httpBarHtml = renderBars(httpBars);
  const circle = pingUp !== null && httpUp !== null
    ? splitCircle(pingUp, httpUp)
    : "";
  const pairAttr = pairKey ? ` data-node-pair="${pairKey}"` : "";
  return [
    `<div${pairAttr} class="border border-mesh-border border-l-4 rounded-lg p-3 mb-2 bg-white" style="border-left-color:${badge.color}">`,
    `<div class="flex items-center gap-2 mb-1">`,
    `<span class="inline-block px-2.5 py-0.5 rounded-full text-xs font-semibold tracking-wide text-white" style="background:${badge.color}">${badge.label}</span>`,
    `<span class="font-mono text-sm font-semibold text-mesh-dark">${tgtIp}</span>`,
    `<span class="ml-auto flex items-center gap-1">${circle}</span>`,
    `</div>`,
    `<div class="text-xs text-mesh-muted flex gap-4 flex-wrap">`,
    `<span>Ping: <strong class="text-mesh-dark">${pingLabel}</strong> ${pingUp !== null ? uptimeSpan(pingUp) : ""}</span>`,
    `<span>HTTP: <strong class="text-mesh-dark">${httpLabel}</strong> ${httpUp !== null ? uptimeSpan(httpUp) : ""}</span>`,
    `<span>Last: <strong class="text-mesh-dark">${lastSeen}</strong></span>`,
    `<span>Checks: <strong class="text-mesh-dark">${totalChecks}</strong></span>`,
    `</div>`,
    `<div class="mesh-tooltip-group"><div class="mesh-tooltip">ICMP</div><div class="flex items-end gap-0.5 mt-1.5">${pingBarHtml}</div></div>`,
    `<div class="mesh-tooltip-group"><div class="mesh-tooltip">HTTP</div><div class="flex items-end gap-0.5 mt-0.5">${httpBarHtml}</div></div>`,
    `</div>`,
  ].join("");
}
