import { NextEventResponse, Overview, ResetResponse, Source } from "./types";

const INITIAL_OVERVIEW: Overview = {
  now: "2026-11-24T09:00:00",
  tasks: [
    {
      id: "task_reporting_ui",
      type: "task",
      title: "Alpilog – Reporting UI",
      author: "Giulia Ferri",
      timestamp: "2026-11-18T11:00:00",
      body: "Build shipment summary table and filters.",
      team: "tech",
      visible_to: ["all"],
      assignee: "marco",
      due_date: "2026-12-01",
      status: "todo",
    },
    {
      id: "task_pricing_2027",
      type: "task",
      title: "Finalize 2027 rate card",
      author: "Sara Conti",
      timestamp: "2026-11-20T15:30:00",
      body: "Align enterprise tier pricing with finance.",
      team: "sales",
      visible_to: ["sales", "finance"],
      assignee: "sara",
      due_date: "2026-12-05",
      status: "todo",
    },
    {
      id: "task_api_migration",
      type: "task",
      title: "Alpilog – API migration",
      author: "Giulia Ferri",
      timestamp: "2026-11-15T09:30:00",
      body: "Migrate Alpilog webhook endpoints to v2 before go-live.",
      team: "tech",
      visible_to: ["all"],
      assignee: "giulia",
      due_date: "2026-12-09",
      status: "in_progress",
    },
    {
      id: "task_invoice_m1",
      type: "task",
      title: "Prepare Alpilog milestone 1 invoice",
      author: "Luca Moretti",
      timestamp: "2026-11-19T14:15:00",
      body: "Issue first milestone invoice once kickoff sign-off arrives.",
      team: "finance",
      visible_to: ["finance"],
      assignee: "luca",
      due_date: "2026-11-28",
      status: "in_progress",
    },
    {
      id: "task_ci_cache",
      type: "task",
      title: "Speed up staging CI pipeline",
      author: "Marco Riva",
      timestamp: "2026-11-12T16:00:00",
      body: "Enable uv wheel cache in CI runner.",
      team: "tech",
      visible_to: ["tech"],
      assignee: "marco",
      due_date: "2026-11-21",
      status: "done",
    },
  ],
  outbox: [],
  memory: [
    {
      id: "mem_pg",
      statement:
        "For Alpilog we chose PostgreSQL over MongoDB because reporting needs joins across shipments and invoices.",
      team: "tech",
      visible_to: ["tech"],
      status: "proposed",
      citations: [
        {
          n: 1,
          source_id: "src_chat_pg",
          type: "chat",
          label: "Chat · #tech · Mon 23 Nov 10:15",
          quote: "reporting needs joins across shipments and invoices",
        },
      ],
      created_at: "2026-11-23T10:20:00",
      decided_by: null,
      decided_at: null,
      can_decide: false,
    },
    {
      id: "mem_azure",
      statement: "Brightloop will migrate from AWS to Azure in 2027.",
      team: "tech",
      visible_to: ["all"],
      status: "proposed",
      citations: [
        {
          n: 1,
          source_id: "src_chat_azure",
          type: "chat",
          label: "Chat · #random · Mon 23 Nov 13:30",
          quote: "move from AWS to Azure next year",
        },
      ],
      created_at: "2026-11-23T13:35:00",
      decided_by: null,
      decided_at: null,
      can_decide: false,
    },
    {
      id: "mem_golive",
      statement: "Alpilog go-live moved from 11 Dec to 4 Dec 2026.",
      team: "sales",
      visible_to: ["all"],
      status: "approved",
      citations: [
        {
          n: 1,
          source_id: "src_email_golive",
          type: "email",
          label: "Email · Elisa Brandt (Alpilog) · Mon 23 Nov 16:40",
          quote: "bring the go-live forward to 4 December",
        },
      ],
      created_at: "2026-11-23T16:45:00",
      decided_by: "sara",
      decided_at: "2026-11-23T17:05:00",
      can_decide: false,
    },
    {
      id: "mem_contract",
      statement: "The Alpilog contract for 2026 is worth €84,000, invoiced in three milestones.",
      team: "finance",
      visible_to: ["finance"],
      status: "approved",
      citations: [
        {
          n: 1,
          source_id: "src_doc_contract",
          type: "doc",
          label: "Doc · Alpilog – contract summary 2026",
          quote: "€84,000, three milestones",
        },
      ],
      created_at: "2026-11-20T10:00:00",
      decided_by: "luca",
      decided_at: "2026-11-20T11:15:00",
      can_decide: false,
    },
  ],
  last_event: null,
  remaining_events: 1,
};

const INCOMING_EVENT: Source = {
  id: "src_pr_mongo",
  type: "pr",
  title: "Add MongoDB store for Alpilog reports",
  author: "Marco Riva",
  timestamp: "2026-11-24T09:05:00",
  body: "Adds a MongoDB collection for pre-aggregated shipment and invoice reports. Reviewer: Giulia Ferri.",
  team: "tech",
  visible_to: ["tech"],
};

let mockState: Overview = structuredClone(INITIAL_OVERVIEW);

function wait(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export async function mockFetchOverview(): Promise<Overview> {
  return structuredClone(mockState);
}

export async function mockReset(): Promise<ResetResponse> {
  await wait(350);
  mockState = structuredClone(INITIAL_OVERVIEW);
  return { ok: true };
}

export async function mockNextEvent(): Promise<NextEventResponse> {
  await wait(450);
  if (mockState.remaining_events <= 0) {
    return { event: null, remaining: 0 };
  }
  const event = structuredClone(INCOMING_EVENT);
  mockState = {
    ...mockState,
    now: event.timestamp,
    last_event: event,
    remaining_events: 0,
  };
  return { event, remaining: 0 };
}
