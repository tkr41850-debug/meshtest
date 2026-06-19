import type { Data30mResponse, Data30dResponse, NodeListResponse } from "./types";

const FETCH_TIMEOUT = 5_000;

async function fetchWithTimeout<T>(url: string): Promise<T | null> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), FETCH_TIMEOUT);
  try {
    const resp = await fetch(url, { signal: controller.signal });
    if (!resp.ok) return null;
    return (await resp.json()) as T;
  } catch {
    return null;
  } finally {
    clearTimeout(timer);
  }
}

export function fetchData30m(): Promise<Data30mResponse | null> {
  return fetchWithTimeout<Data30mResponse>("/data?window=30m");
}

export function fetchData30d(): Promise<Data30dResponse | null> {
  return fetchWithTimeout<Data30dResponse>("/data?window=30d");
}

export function fetchNodeList(): Promise<NodeListResponse | null> {
  return fetchWithTimeout<NodeListResponse>("/node-list");
}
