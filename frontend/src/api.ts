import { mockFetchOverview, mockNextEvent, mockReset } from "./mockData";
import { NextEventResponse, Overview, ResetResponse } from "./types";

export const USE_MOCK = import.meta.env.VITE_USE_MOCK === "true";
export const API_URL = (import.meta.env.VITE_API_URL || "http://localhost:8000").replace(/\/$/, "");

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      Accept: "application/json",
      ...init?.headers,
    },
  });

  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const data = (await res.json()) as { detail?: unknown };
      if (typeof data?.detail === "string" && data.detail.trim()) {
        detail = data.detail;
      }
    } catch {
      // Ignore non-JSON error bodies
    }
    throw new Error(detail);
  }

  return (await res.json()) as T;
}

export function fetchOverview(): Promise<Overview> {
  if (USE_MOCK) return mockFetchOverview();
  return requestJson<Overview>("/demo/overview");
}

export function resetDemo(): Promise<ResetResponse> {
  if (USE_MOCK) return mockReset();
  return requestJson<ResetResponse>("/demo/reset", { method: "POST" });
}

export function triggerNextEvent(): Promise<NextEventResponse> {
  if (USE_MOCK) return mockNextEvent();
  return requestJson<NextEventResponse>("/demo/next-event", { method: "POST" });
}
