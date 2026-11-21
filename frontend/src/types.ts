export type Team = "sales" | "tech" | "finance";
export type Visibility = Team | "all";

export interface Person {
  id: string;
  name: string;
  team: Team;
  is_lead: boolean;
  title: string;
}

export interface Source {
  id: string;
  type: "email" | "chat" | "doc" | "task" | "pr";
  title: string;
  author: string;
  timestamp: string;
  body: string;
  team: Team;
  visible_to: Visibility[];
  assignee?: string;
  due_date?: string;
  status?: "todo" | "in_progress" | "done";
}

export interface Citation {
  n: number;
  source_id: string;
  type: Source["type"];
  label: string;
  quote: string | null;
}

export interface MemoryItem {
  id: string;
  statement: string;
  team: Team;
  visible_to: Visibility[];
  status: "proposed" | "approved" | "rejected";
  citations: Citation[];
  created_at: string;
  decided_by: string | null;
  decided_at: string | null;
  can_decide: boolean;
  caught: string[];
}

export type Effect =
  | { type: "update_task"; task_id: string; changes: { due_date?: string; status?: string } }
  | { type: "create_task"; title: string; assignee: string; due_date: string }
  | { type: "send_message"; to: string; text: string };

export interface Action {
  id: string;
  title: string;
  reason: string;
  for_user: string;
  status: "pending" | "approved" | "rejected";
  effects: Effect[];
  citations: Citation[];
  created_at: string;
  decided_at: string | null;
}

export interface OutboxMessage {
  id: string;
  to: string;
  text: string;
  sent_at: string;
  action_id: string;
}

export interface Overview {
  now: string;
  tasks: Source[];
  outbox: OutboxMessage[];
  memory: MemoryItem[];
  last_event: Source | null;
  remaining_events: Record<Track, number>;
  next_step: Record<Track, string | null>;
}

/** The two demo buttons: one script for the Tech Lead, one for the Finance Manager. */
export type Track = "tech" | "finance";
export const TRACKS: Array<{ id: Track; label: string }> = [
  { id: "tech", label: "Simulate tech event" },
  { id: "finance", label: "Simulate finance event" },
];

export interface NextEventResponse {
  event: Source | null;
  remaining: number;
}

export interface ResetResponse {
  ok: boolean;
}

export const PEOPLE_BY_ID: Record<string, Person> = {
  sara: { id: "sara", name: "Sara Conti", team: "sales", is_lead: true, title: "Head of Sales" },
  giulia: { id: "giulia", name: "Giulia Ferri", team: "tech", is_lead: true, title: "Tech Lead" },
  marco: { id: "marco", name: "Marco Riva", team: "tech", is_lead: false, title: "Backend Developer" },
  luca: { id: "luca", name: "Luca Moretti", team: "finance", is_lead: true, title: "Finance Manager" },
};

export const SOURCE_TYPE_LABEL: Record<Source["type"], string> = {
  email: "Email",
  chat: "Chat",
  task: "Task",
  doc: "Doc",
  pr: "Pull request",
};
