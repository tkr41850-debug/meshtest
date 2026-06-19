export interface CheckResult {
  node_ip: string;
  target_ip: string;
  ping_status: string;
  http_status: string;
  ping_latency_ms: number | null;
  http_latency_ms: number | null;
  timestamp: number;
}

export interface StatusEntry {
  node_ip: string;
  target_ip: string;
  ping_status: string;
  http_status: string;
}

export interface Data30mResponse {
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
}

export interface DayData {
  date: string;
  connections: DayConnection[];
}

export interface Data30dResponse {
  days: DayData[];
  window: string;
}

export interface NodeListResponse {
  nodes: Array<{ ip: string; port: number } | string>;
}
