export interface CheckResult {
  node_ip: string;
  target_ip: string;
  ping_ok: boolean;
  http_ok: boolean;
  ping_latency_ms: number | null;
  http_latency_ms: number | null;
  timestamp: number;
  is_extra?: boolean;
}

export interface BarEntry {
  percent: number;
  tooltip: string;
}

export interface StatusEntry {
  node_ip: string;
  target_ip: string;
  ping_status: string;
  http_status: string;
}

export interface Data90mResponse {
  checks: CheckResult[];
  statuses: StatusEntry[];
  timestamp: number;
  window: string;
}

export interface DayConnection {
  node_ip: string;
  target_ip: string;
  ping_uptime_pct: number;
  http_uptime_pct: number;
  total_checks: number;
  ping_ok: number;
  http_ok: number;
}

export interface DayData {
  date: string;
  connections: DayConnection[];
}

export interface HourData {
  date: string;
  connections: DayConnection[];
}

export interface Data90hResponse {
  hours: HourData[];
  window: string;
}

export interface Data90dResponse {
  days: DayData[];
  window: string;
}

export interface NodeListResponse {
  nodes: Array<{ ip: string; port: number } | string>;
}


