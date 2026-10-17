import { CircleCheck, Loader2, OctagonX, X } from "lucide-react";
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";

import { errorMessage } from "@/blocks/mutation";
import { Button } from "@/ui/button";

/** What a finished task reports, and where its result can be opened. */
export interface TaskOutcome { message: string; link?: { label: string; to: string } }

export interface TaskSpec<T> {
  /** For example "Scheduler, DLF Meadows, 18-Oct-26 to 24-Oct-26". */
  label: string;
  /** What is happening while it runs. */
  detail: string;
  run: () => Promise<T>;
  done: (result: T) => TaskOutcome;
  failed?: (error: unknown) => TaskOutcome;
}

interface Task {
  id: number;
  label: string;
  detail: string;
  startedAt: number;
  state: "running" | "done" | "failed";
  outcome?: TaskOutcome;
}

interface TasksApi {
  tasks: Task[];
  /** Starts a long action. It keeps running when the admin leaves the page. */
  start: <T>(spec: TaskSpec<T>) => Promise<T>;
  isRunning: (label: string) => boolean;
  dismiss: (id: number) => void;
}

const TasksContext = createContext<TasksApi | null>(null);

/**
 * Long actions, such as a scheduler run, live here rather than in the page
 * that started them. The panel in the top bar shows each with its elapsed
 * time; when one ends a toast says what happened and links to the result.
 */
export function TasksProvider({ children }: { children: ReactNode }) {
  const [tasks, setTasks] = useState<Task[]>([]);
  const next = useRef(1);
  const navigate = useNavigate();

  const dismiss = useCallback((id: number) => setTasks((ts) => ts.filter((t) => t.id !== id)), []);

  const start = useCallback(async <T,>(spec: TaskSpec<T>): Promise<T> => {
    const id = next.current++;
    setTasks((ts) => [...ts, { id, label: spec.label, detail: spec.detail, startedAt: Date.now(), state: "running" }]);
    try {
      const result = await spec.run();
      const outcome = spec.done(result);
      setTasks((ts) => ts.map((t) => (t.id === id ? { ...t, state: "done", outcome } : t)));
      toast.success(spec.label, {
        description: outcome.message,
        duration: 10000,
        action: outcome.link ? { label: outcome.link.label, onClick: () => navigate(outcome.link!.to) } : undefined,
      });
      setTimeout(() => dismiss(id), 15000);
      return result;
    } catch (e) {
      const outcome = spec.failed?.(e) ?? { message: errorMessage(e) };
      setTasks((ts) => ts.map((t) => (t.id === id ? { ...t, state: "failed", outcome } : t)));
      toast.error(spec.label, { description: outcome.message, duration: 12000 });
      throw e;
    }
  }, [dismiss, navigate]);

  const value = useMemo<TasksApi>(() => ({
    tasks, start, dismiss,
    isRunning: (label) => tasks.some((t) => t.state === "running" && t.label === label),
  }), [tasks, start, dismiss]);

  return <TasksContext.Provider value={value}>{children}</TasksContext.Provider>;
}

export function useTasks(): TasksApi {
  const v = useContext(TasksContext);
  if (!v) throw new Error("useTasks needs a TasksProvider");
  return v;
}

function Elapsed({ from }: { from: number }) {
  const [now, setNow] = useState(Date.now());
  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(t);
  }, []);
  const s = Math.max(0, Math.floor((now - from) / 1000));
  return <span className="tabular-nums">{Math.floor(s / 60)}:{String(s % 60).padStart(2, "0")}</span>;
}

/** The running and recently finished tasks, shown in the top bar. */
export function TaskTray() {
  const { tasks, dismiss } = useTasks();
  const navigate = useNavigate();
  if (tasks.length === 0) return null;
  return (
    <div className="flex flex-wrap items-center gap-2" aria-live="polite">
      {tasks.map((t) => (
        <div key={t.id} role="status"
             className="flex items-center gap-2 rounded-lg border bg-card py-1 pr-1 pl-3 text-sm shadow-xs">
          {t.state === "running" && <Loader2 className="size-4 animate-spin text-gold-text" aria-hidden />}
          {t.state === "done" && <CircleCheck className="size-4 text-ok" aria-hidden />}
          {t.state === "failed" && <OctagonX className="size-4 text-destructive" aria-hidden />}
          <span className="font-medium">{t.label}</span>
          <span className="text-muted-foreground">
            {t.state === "running" ? <>{t.detail} <Elapsed from={t.startedAt} /></> : t.outcome?.message}
          </span>
          {t.state === "done" && t.outcome?.link && (
            <Button size="sm" variant="ghost" onClick={() => navigate(t.outcome!.link!.to)}>
              {t.outcome.link.label}
            </Button>
          )}
          {t.state !== "running" && (
            <Button size="icon-sm" variant="ghost" aria-label="Dismiss" onClick={() => dismiss(t.id)}>
              <X />
            </Button>
          )}
        </div>
      ))}
    </div>
  );
}
