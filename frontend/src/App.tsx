import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { API_URL, fetchOverview, resetDemo, triggerNextEvent, USE_MOCK } from "./api";
import "./App.css";
import {
  formatDueDate,
  formatHeaderNow,
  formatRecipient,
  formatShortTimestamp,
  formatVisibility,
  personFirstName,
  personFullName,
} from "./format";
import { MemoryItem, Overview, SOURCE_TYPE_LABEL, Source } from "./types";

const POLL_INTERVAL_MS = 2000;
const HIGHLIGHT_DURATION_MS = 3200;

type HighlightKind = "new" | "updated";

const TASK_COLUMNS: Array<{ status: NonNullable<Source["status"]>; label: string }> = [
  { status: "todo", label: "To do" },
  { status: "in_progress", label: "In progress" },
  { status: "done", label: "Done" },
];

const MEMORY_STATUS_LABEL: Record<MemoryItem["status"], string> = {
  proposed: "Proposed",
  approved: "Approved",
  rejected: "Rejected",
};

function sortTasks(tasks: Source[]): Source[] {
  return [...tasks].sort((a, b) => {
    const dueA = a.due_date ?? "9999-99-99";
    const dueB = b.due_date ?? "9999-99-99";
    if (dueA !== dueB) return dueA.localeCompare(dueB);
    return a.title.localeCompare(b.title);
  });
}

function sortMemory(items: MemoryItem[]): MemoryItem[] {
  return [...items].sort((a, b) => {
    const aProposed = a.status === "proposed" ? 0 : 1;
    const bProposed = b.status === "proposed" ? 0 : 1;
    if (aProposed !== bProposed) return aProposed - bProposed;

    if (aProposed === 0) {
      return b.created_at.localeCompare(a.created_at);
    }

    const aTime = a.decided_at ?? a.created_at;
    const bTime = b.decided_at ?? b.created_at;
    return bTime.localeCompare(aTime);
  });
}

function diffOverview(prev: Overview, next: Overview): Record<string, HighlightKind> {
  const changes: Record<string, HighlightKind> = {};

  const prevTasks = new Map(prev.tasks.map((t) => [t.id, t]));
  for (const task of next.tasks) {
    const old = prevTasks.get(task.id);
    if (!old) {
      changes[`task:${task.id}`] = "new";
    } else if (
      old.due_date !== task.due_date ||
      old.status !== task.status ||
      old.title !== task.title ||
      old.assignee !== task.assignee
    ) {
      changes[`task:${task.id}`] = "updated";
    }
  }

  const prevOutboxIds = new Set(prev.outbox.map((m) => m.id));
  for (const msg of next.outbox) {
    if (!prevOutboxIds.has(msg.id)) {
      changes[`outbox:${msg.id}`] = "new";
    }
  }

  const prevMemory = new Map(prev.memory.map((m) => [m.id, m]));
  for (const item of next.memory) {
    const old = prevMemory.get(item.id);
    if (!old) {
      changes[`mem:${item.id}`] = "new";
    } else if (
      old.status !== item.status ||
      old.decided_by !== item.decided_by ||
      old.statement !== item.statement
    ) {
      changes[`mem:${item.id}`] = "updated";
    }
  }

  if (
    next.last_event &&
    (!prev.last_event ||
      prev.last_event.id !== next.last_event.id ||
      prev.last_event.timestamp !== next.last_event.timestamp)
  ) {
    changes["last_event"] = "new";
  }

  return changes;
}

export default function App() {
  const [overview, setOverview] = useState<Overview | null>(null);
  const [backendUnreachable, setBackendUnreachable] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [busyAction, setBusyAction] = useState<"reset" | "next" | null>(null);
  const [highlights, setHighlights] = useState<Record<string, HighlightKind>>({});

  const prevOverviewRef = useRef<Overview | null>(null);
  const requestSeqRef = useRef(0);
  const timersRef = useRef<Map<string, number>>(new Map());

  const clearAllHighlights = useCallback(() => {
    for (const timerId of timersRef.current.values()) {
      window.clearTimeout(timerId);
    }
    timersRef.current.clear();
    setHighlights({});
  }, []);

  const applyHighlights = useCallback((changes: Record<string, HighlightKind>) => {
    const entries = Object.entries(changes);
    if (entries.length === 0) return;

    setHighlights((prev) => ({ ...prev, ...changes }));

    for (const [key] of entries) {
      const existing = timersRef.current.get(key);
      if (existing !== undefined) {
        window.clearTimeout(existing);
      }
      const timerId = window.setTimeout(() => {
        timersRef.current.delete(key);
        setHighlights((curr) => {
          if (!(key in curr)) return curr;
          const next = { ...curr };
          delete next[key];
          return next;
        });
      }, HIGHLIGHT_DURATION_MS);
      timersRef.current.set(key, timerId);
    }
  }, []);

  const loadOverview = useCallback(async () => {
    const seq = ++requestSeqRef.current;
    try {
      const data = await fetchOverview();
      if (seq !== requestSeqRef.current) return;

      const prev = prevOverviewRef.current;
      if (prev) {
        applyHighlights(diffOverview(prev, data));
      }
      prevOverviewRef.current = data;
      setOverview(data);
      setBackendUnreachable(false);
    } catch {
      if (seq !== requestSeqRef.current) return;
      setBackendUnreachable(true);
    }
  }, [applyHighlights]);

  useEffect(() => {
    void loadOverview();
    const intervalId = window.setInterval(() => {
      void loadOverview();
    }, POLL_INTERVAL_MS);

    return () => {
      window.clearInterval(intervalId);
      for (const timerId of timersRef.current.values()) {
        window.clearTimeout(timerId);
      }
      timersRef.current.clear();
    };
  }, [loadOverview]);

  const handleReset = async () => {
    if (busyAction) return;
    setBusyAction("reset");
    setActionError(null);
    requestSeqRef.current++;
    try {
      await resetDemo();
      prevOverviewRef.current = null;
      clearAllHighlights();
      await loadOverview();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Failed to reset the day.");
    } finally {
      setBusyAction(null);
    }
  };

  const handleNextEvent = async () => {
    if (busyAction) return;
    setBusyAction("next");
    setActionError(null);
    requestSeqRef.current++;
    try {
      await triggerNextEvent();
      await loadOverview();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Failed to simulate incoming event.");
    } finally {
      setBusyAction(null);
    }
  };

  const tasksByStatus = useMemo(() => {
    const grouped: Record<NonNullable<Source["status"]>, Source[]> = {
      todo: [],
      in_progress: [],
      done: [],
    };
    if (!overview) return grouped;

    for (const task of overview.tasks) {
      const status = task.status ?? "todo";
      if (status in grouped) {
        grouped[status].push(task);
      } else {
        grouped.todo.push(task);
      }
    }

    return {
      todo: sortTasks(grouped.todo),
      in_progress: sortTasks(grouped.in_progress),
      done: sortTasks(grouped.done),
    };
  }, [overview]);

  const sortedOutbox = useMemo(() => {
    if (!overview) return [];
    return [...overview.outbox].reverse();
  }, [overview]);

  const sortedMemory = useMemo(() => {
    if (!overview) return [];
    return sortMemory(overview.memory);
  }, [overview]);

  const remainingEvents = overview?.remaining_events ?? 0;
  const lastEvent = overview?.last_event ?? null;
  const lastEventHighlight = highlights["last_event"];

  return (
    <div className="page">
      <header className="header">
        <div className="header-title-group">
          <h1 className="header-title">Brightloop · simulated tools</h1>
          <p className="header-subtitle">Demo control room. Not part of the product.</p>
        </div>

        <div className="header-meta">
          <div className="now-pill" aria-label="Fictional current time">
            {overview ? formatHeaderNow(overview.now) : "—"}
          </div>
          {USE_MOCK ? (
            <span className="status-badge status-mock">
              <span className="status-dot" aria-hidden="true" />
              Mock data
            </span>
          ) : backendUnreachable ? (
            <span className="status-badge status-offline">
              <span className="status-dot" aria-hidden="true" />
              Offline
            </span>
          ) : (
            <span className="status-badge status-live">
              <span className="status-dot" aria-hidden="true" />
              Live
            </span>
          )}
        </div>
      </header>

      {backendUnreachable && (
        <div className="error-banner" role="alert">
          <span>Cannot reach backend at {API_URL} — retrying every 2 seconds.</span>
        </div>
      )}

      <section className="controls-panel" aria-label="Demo controls">
        <div className="controls-row">
          <button
            type="button"
            className="btn btn-primary"
            onClick={handleReset}
            disabled={busyAction !== null}
          >
            {busyAction === "reset" && <span className="spinner" aria-hidden="true" />}
            <span>Start the day</span>
          </button>

          <button
            type="button"
            className="btn btn-secondary"
            onClick={handleNextEvent}
            disabled={busyAction !== null || !overview || remainingEvents === 0}
          >
            {busyAction === "next" && <span className="spinner" aria-hidden="true" />}
            <span>Simulate incoming event</span>
            <span className="btn-count">({remainingEvents} left)</span>
          </button>
        </div>

        {actionError && (
          <div className="action-error" role="alert">
            <span>{actionError}</span>
            <button
              type="button"
              className="dismiss-btn"
              onClick={() => setActionError(null)}
            >
              Dismiss
            </button>
          </div>
        )}

        <div className={`last-event-card${lastEventHighlight ? " is-highlighted" : ""}`}>
          {lastEvent ? (
            <>
              <div className="last-event-header">
                <div className="last-event-title">
                  <span className="last-event-label">Last event: </span>
                  {SOURCE_TYPE_LABEL[lastEvent.type]} · {lastEvent.author} · {lastEvent.title}
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  {lastEventHighlight && <span className="change-badge">New</span>}
                  <span className="last-event-time">
                    {formatShortTimestamp(lastEvent.timestamp)}
                  </span>
                </div>
              </div>
              <p className="last-event-body">{lastEvent.body}</p>
            </>
          ) : (
            <div className="last-event-empty">
              <span className="last-event-label">Last event: </span>
              None yet.
            </div>
          )}
        </div>
      </section>

      <section className="panel" aria-labelledby="task-board-heading">
        <div className="section-header">
          <h2 id="task-board-heading" className="section-title">
            Task board
          </h2>
          <span className="section-count">{overview ? overview.tasks.length : 0} tasks</span>
        </div>

        <div className="board-columns">
          {TASK_COLUMNS.map((col) => {
            const colTasks = tasksByStatus[col.status];
            return (
              <div key={col.status} className="board-column">
                <div className="column-header">
                  <span className="column-title">{col.label}</span>
                  <span className="column-count">{colTasks.length}</span>
                </div>

                <div className="task-list">
                  {colTasks.length === 0 ? (
                    <div className="column-empty">No tasks</div>
                  ) : (
                    colTasks.map((task) => {
                      const hl = highlights[`task:${task.id}`];
                      return (
                        <article
                          key={task.id}
                          className={`task-card${hl ? " is-highlighted" : ""}`}
                        >
                          <div className="task-top">
                            <h3 className="task-title">{task.title}</h3>
                            {hl && (
                              <span className="change-badge">
                                {hl === "new" ? "New" : "Updated"}
                              </span>
                            )}
                          </div>
                          <div className="task-meta">
                            {personFirstName(task.assignee)} · {formatDueDate(task.due_date)}
                          </div>
                        </article>
                      );
                    })
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </section>

      <div className="bottom-split">
        <section className="panel" aria-labelledby="sent-messages-heading">
          <div className="section-header">
            <h2 id="sent-messages-heading" className="section-title">
              Sent messages
            </h2>
            <span className="section-count">{sortedOutbox.length}</span>
          </div>

          {sortedOutbox.length === 0 ? (
            <p className="empty-state">Nothing has been sent.</p>
          ) : (
            <div className="stack-list">
              {sortedOutbox.map((msg) => {
                const hl = highlights[`outbox:${msg.id}`];
                return (
                  <article
                    key={msg.id}
                    className={`outbox-card${hl ? " is-highlighted" : ""}`}
                  >
                    <div className="outbox-header">
                      <span className="outbox-to">To: {formatRecipient(msg.to)}</span>
                      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                        {hl && <span className="change-badge">New</span>}
                        <span className="outbox-time">{formatShortTimestamp(msg.sent_at)}</span>
                      </div>
                    </div>
                    <p className="outbox-text">{msg.text}</p>
                  </article>
                );
              })}
            </div>
          )}
        </section>

        <section className="panel" aria-labelledby="company-memory-heading">
          <div className="section-header">
            <h2 id="company-memory-heading" className="section-title">
              Company memory
            </h2>
            <span className="section-count">{sortedMemory.length}</span>
          </div>

          {sortedMemory.length === 0 ? (
            <p className="empty-state">No memory items yet.</p>
          ) : (
            <div className="stack-list">
              {sortedMemory.map((item) => {
                const hl = highlights[`mem:${item.id}`];
                return (
                  <article
                    key={item.id}
                    className={`memory-card${hl ? " is-highlighted" : ""}`}
                  >
                    <div className="memory-tags">
                      <span className={`memory-status memory-status-${item.status}`}>
                        {MEMORY_STATUS_LABEL[item.status]}
                      </span>
                      <span className="visibility-tag">
                        Visible to: {formatVisibility(item.visible_to)}
                      </span>
                      {hl && (
                        <span className="change-badge" style={{ marginLeft: "auto" }}>
                          {hl === "new" ? "New" : "Updated"}
                        </span>
                      )}
                    </div>
                    <p className="memory-statement">{item.statement}</p>
                    {item.decided_by && (
                      <p className="memory-decided">
                        {MEMORY_STATUS_LABEL[item.status]} by {personFullName(item.decided_by)}
                      </p>
                    )}
                  </article>
                );
              })}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
