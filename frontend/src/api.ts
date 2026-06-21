import type { Data90mResponse, Data90hResponse, Data90dResponse, NodeListResponse } from "./types";

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

export function fetchData90m(): Promise<Data90mResponse | null> {
  return fetchWithTimeout<Data90mResponse>("/data?window=90m");
}

export function fetchData90h(): Promise<Data90hResponse | null> {
  return fetchWithTimeout<Data90hResponse>("/data?window=90h");
}

export function fetchData90d(): Promise<Data90dResponse | null> {
  return fetchWithTimeout<Data90dResponse>("/data?window=90d");
}

export function fetchNodeList(): Promise<NodeListResponse | null> {
  return fetchWithTimeout<NodeListResponse>("/node-list");
}

export { fetchData90m as fetchData30m, fetchData90d as fetchData30d };
