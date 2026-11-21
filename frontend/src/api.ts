import { mockFetchOverview, mockNextEvent, mockReset } from "./mockData";
import { NextEventResponse, Overview, ResetResponse, Track } from "./types";

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

function normalizeOverview(raw: Overview): Overview {
  return {
    ...raw,
    tasks: Array.isArray(raw.tasks) ? raw.tasks : [],
    outbox: Array.isArray(raw.outbox) ? raw.outbox : [],
    memory: Array.isArray(raw.memory)
      ? raw.memory.map((item) => ({
          ...item,
          caught: Array.isArray(item.caught) ? item.caught : [],
        }))
      : [],
    last_event: raw.last_event ?? null,
    remaining_events: {
      tech: raw.remaining_events?.tech ?? 0,
      finance: raw.remaining_events?.finance ?? 0,
    },
    next_step: {
      tech: raw.next_step?.tech ?? null,
      finance: raw.next_step?.finance ?? null,
    },
  };
}

export async function fetchOverview(): Promise<Overview> {
  if (USE_MOCK) return normalizeOverview(await mockFetchOverview());
  return normalizeOverview(await requestJson<Overview>("/demo/overview"));
}

export function resetDemo(): Promise<ResetResponse> {
  if (USE_MOCK) return mockReset();
  return requestJson<ResetResponse>("/demo/reset", { method: "POST" });
}

export function triggerNextEvent(track: Track): Promise<NextEventResponse> {
  if (USE_MOCK) return mockNextEvent(track);
  return requestJson<NextEventResponse>(`/demo/next-event?track=${track}`, { method: "POST" });
}
