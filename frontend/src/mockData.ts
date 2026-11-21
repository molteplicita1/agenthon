import { NextEventResponse, Overview, ResetResponse, Source, Track } from "./types";

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
      caught: [],
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
      caught: [],
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
      caught: [],
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
      caught: [],
    },
  ],
  last_event: null,
  remaining_events: { tech: 4, finance: 1 },
  next_step: {
    tech: "Action for Giulia Ferri: Move 'Alpilog – API migration' to 2 Dec and notify #tech",
    finance: "Action for Luca Moretti: Send the first payment reminder to Kestrel Freight",
  },
};

interface MockStep {
  event: Source;
  now: string;
  nextStep: string | null;
  onRun?: (state: Overview) => void;
}

const TECH_STEPS: MockStep[] = [
  {
    event: {
      id: "src_email_golive",
      type: "email",
      title: "Alpilog go-live moved to 4 Dec",
      author: "Elisa Brandt (Alpilog)",
      timestamp: "2026-11-23T16:40:00",
      body: "Hi Sara, we need to bring the go-live forward to 4 December.",
      team: "sales",
      visible_to: ["all"],
    },
    now: "2026-11-24T09:01:00",
    nextStep:
      "Memory proposal for Giulia Ferri: For Alpilog we chose PostgreSQL over MongoDB because reporting needs joins across shipments and invoices.",
  },
  {
    event: {
      id: "src_chat_pg",
      type: "chat",
      title: "#tech",
      author: "Giulia Ferri",
      timestamp: "2026-11-23T10:15:00",
      body: "Giulia: Let's stick with PostgreSQL for Alpilog.\nMarco: Agreed, reporting needs joins across shipments and invoices.",
      team: "tech",
      visible_to: ["tech"],
    },
    now: "2026-11-24T09:02:00",
    nextStep: "Memory proposal for Giulia Ferri: Brightloop will migrate from AWS to Azure in 2027.",
  },
  {
    event: {
      id: "src_chat_azure",
      type: "chat",
      title: "#random",
      author: "Marco Riva",
      timestamp: "2026-11-23T13:30:00",
      body: "Marco: Next year we move from AWS to Azure, obviously 😄",
      team: "tech",
      visible_to: ["all"],
    },
    now: "2026-11-24T09:03:00",
    nextStep: "New pull request by Marco Riva: Add MongoDB store for Alpilog reports",
  },
  {
    event: {
      id: "src_pr_mongo",
      type: "pr",
      title: "Add MongoDB store for Alpilog reports",
      author: "Marco Riva",
      timestamp: "2026-11-24T09:05:00",
      body: "Description: adds a MongoDB collection that stores pre-aggregated shipment and invoice reports for Alpilog.\nState: open\nReviewers: Giulia Ferri\nFiles changed: 6 (+312 / -14)",
      team: "tech",
      visible_to: ["tech"],
    },
    now: "2026-11-24T09:05:00",
    nextStep: null,
    onRun: (state) => {
      state.memory = state.memory.map((item) =>
        item.id === "mem_pg"
          ? {
              ...item,
              status: "approved",
              decided_by: "giulia",
              decided_at: "2026-11-24T09:02:30",
              caught: ["Pull request · Add MongoDB store for Alpilog reports · Tue 24 Nov 09:05"],
            }
          : item
      );
    },
  },
];

const FINANCE_STEPS: MockStep[] = [
  {
    event: {
      id: "src_chat_kestrel",
      type: "chat",
      title: "#finance",
      author: "Elena Rota",
      timestamp: "2026-11-23T11:45:00",
      body: "Elena: bank reconciliation done up to Friday 20 Nov\nElena: every November payment is matched except Kestrel Freight, invoice 2026-031",
      team: "finance",
      visible_to: ["finance"],
    },
    now: "2026-11-24T09:06:00",
    nextStep: null,
  },
];

const MOCK_STEPS: Record<Track, MockStep[]> = { tech: TECH_STEPS, finance: FINANCE_STEPS };

let mockState: Overview = structuredClone(INITIAL_OVERVIEW);
let mockStepIndex: Record<Track, number> = { tech: 0, finance: 0 };

function wait(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export async function mockFetchOverview(): Promise<Overview> {
  return structuredClone(mockState);
}

export async function mockReset(): Promise<ResetResponse> {
  await wait(350);
  mockState = structuredClone(INITIAL_OVERVIEW);
  mockStepIndex = { tech: 0, finance: 0 };
  return { ok: true };
}

export async function mockNextEvent(track: Track): Promise<NextEventResponse> {
  await wait(450);
  const step = MOCK_STEPS[track][mockStepIndex[track]];
  if (!step) {
    return { event: null, remaining: 0 };
  }
  mockStepIndex[track] += 1;
  const remaining = MOCK_STEPS[track].length - mockStepIndex[track];
  const event = structuredClone(step.event);

  const nextState: Overview = {
    ...structuredClone(mockState),
    now: step.now,
    last_event: event,
    remaining_events: { ...mockState.remaining_events, [track]: remaining },
    next_step: { ...mockState.next_step, [track]: step.nextStep },
  };
  step.onRun?.(nextState);
  mockState = nextState;

  return { event, remaining };
}
