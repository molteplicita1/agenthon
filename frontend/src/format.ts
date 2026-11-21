import { PEOPLE_BY_ID, Visibility } from "./types";

const WEEKDAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

interface LocalParts {
  year: number;
  month: number;
  day: number;
  hour: number;
  minute: number;
  second: number;
  date: Date;
}

function parseLocalIso(value: string): LocalParts | null {
  const match = /^(\d{4})-(\d{2})-(\d{2})(?:T(\d{2}):(\d{2})(?::(\d{2}))?)?/.exec(value.trim());
  if (!match) return null;
  const year = Number(match[1]);
  const month = Number(match[2]);
  const day = Number(match[3]);
  const hour = Number(match[4] ?? "0");
  const minute = Number(match[5] ?? "0");
  const second = Number(match[6] ?? "0");
  const date = new Date(year, month - 1, day, hour, minute, second);
  return { year, month, day, hour, minute, second, date };
}

function pad2(n: number): string {
  return String(n).padStart(2, "0");
}

function capitalize(s: string): string {
  return s ? s.charAt(0).toUpperCase() + s.slice(1) : s;
}

export function formatHeaderNow(iso: string): string {
  const parts = parseLocalIso(iso);
  if (!parts) return iso;
  const weekday = WEEKDAYS[parts.date.getDay()];
  const month = MONTHS[parts.month - 1];
  return `${weekday} ${parts.day} ${month} ${parts.year} · ${pad2(parts.hour)}:${pad2(parts.minute)}`;
}

export function formatDueDate(ymd?: string): string {
  if (!ymd) return "No due date";
  const parts = parseLocalIso(ymd);
  if (!parts) return ymd;
  const month = MONTHS[parts.month - 1];
  if (parts.year !== 2026) {
    return `${parts.day} ${month} ${parts.year}`;
  }
  return `${parts.day} ${month}`;
}

export function formatShortTimestamp(iso: string): string {
  const parts = parseLocalIso(iso);
  if (!parts) return iso;
  const month = MONTHS[parts.month - 1];
  return `${parts.day} ${month} · ${pad2(parts.hour)}:${pad2(parts.minute)}`;
}

export function personFirstName(id?: string | null): string {
  if (!id) return "Unassigned";
  const person = PEOPLE_BY_ID[id];
  if (person) return person.name.split(" ")[0];
  return capitalize(id);
}

export function personFullName(id?: string | null): string {
  if (!id) return "Unassigned";
  const person = PEOPLE_BY_ID[id];
  if (person) return person.name;
  return capitalize(id);
}

export function formatRecipient(to: string): string {
  if (to.startsWith("#")) return to;
  return personFullName(to);
}

export function formatVisibility(vis: Visibility[]): string {
  if (vis.includes("all")) return "All";
  return vis.map(capitalize).join(", ");
}
