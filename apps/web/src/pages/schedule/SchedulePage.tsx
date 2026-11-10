import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ChartGantt, Columns3, ExternalLink, Info, Maximize2, Table2, Loader2, Lock, LockOpen, Play, Search, TriangleAlert } from "lucide-react";
import { useEffect, useState } from "react";
import { useHref, useSearchParams } from "react-router-dom";

import { api, ApiError } from "@/api/client";
import { useConfirm } from "@/blocks/confirm";
import { Field, SelectBox } from "@/blocks/fields";
import { FormDialog } from "@/blocks/FormDialog";
import { DetailList, EmptyState, ErrorState } from "@/blocks/layout";
import { EVENTS } from "@/analytics/events";
import { errorMessage, useAppMutation } from "@/blocks/mutation";
import { StatusBadge } from "@/blocks/status";
import { useTasks } from "@/blocks/tasks";
import { HoverTip, Tabs } from "@/components";
import { cn } from "@/lib/utils";
import { useSite } from "@/site/SiteContext";
import { Button } from "@/ui/button";
import {
  Dialog, DialogContent, DialogDescription, DialogTitle,
} from "@/ui/dialog";
import { Input } from "@/ui/input";
import { Skeleton } from "@/ui/skeleton";

import { breached, isOpen, JobFlags, matches, parkingPlace, serviceCode, StatusSummary, typeClass } from "./Board";
import { CrewPicker, FlagKey, ServicesFilter, ShowAll } from "./BoardFilters";
import { JobTable } from "./JobTable";
import { CardBoard, type Density } from "./CardBoard";
import { addDays, DateBar } from "./DateBar";
import { NameRain } from "./NameRain";
import { MoveToDateDialog } from "./JobOps";
import { QueuePanel } from "./QueuePanel";
import { REPORT_SECTIONS } from "./reports";
import { RulesPanel } from "./rules/RulesPanel";
import { CutoffRequests, DraftImprovements, JobCardButtons, PendingAddons } from "./ScheduleActions";
import { NeedsAttention } from "./NeedsAttention";
import { SkippedJobs } from "./SkippedJobs";
import { Timeline } from "./Timeline";
import { useBoardSync } from "./dnd";
import { Fireworks } from "./RunFireworks";
import { isRunMusicMuted, setRunMusicMuted, startRunMusic, stopRunMusic } from "./runMusic";
import {
  datesOf, fmtDate, hhmm, minuteOf, toIso, useCutoffRequests, useInteriorDayMissing, useNeedsScheduling,
  useAutoFreezeOn, useScheduleBoard, useSchedules, weekday,
  type AdminJob, type Board, type RunResult, type ScheduleOut,
} from "./api";
import "./schedule.css";

/** How far back the day strip goes (ADM-SCH-35). */
const DAYS_BACK = 30;

const DENSITIES: [Density, string][] = [["compact", "Compact"], ["standard", "Standard"], ["detailed", "Detail"]];
const DENSITY_KEY = "priveo.schedule.card-density";

/** How much each card shows, remembered in the browser. */
function useDensity(): [Density, (d: Density) => void] {
  const [density, set] = useState<Density>(() => {
    try {
      const v = localStorage.getItem(DENSITY_KEY);
      return v === "compact" || v === "detailed" ? v : "standard";
    } catch { return "standard"; }
  });
  return [density, (d) => {
    set(d);
    try { localStorage.setItem(DENSITY_KEY, d); } catch { /* A private window keeps nothing; the choice still applies now. */ }
  }];
}

const count = (label: string, n: number) => (n ? `${label} (${n})` : label);

/** The sections of the page, one tab each, all for the chosen day (ADM-SCH-32). Run is a button in the top bar. */
const SCHEDULE_TABS = (n: { attention: number; skipped: number; cutoff: number }) => [
  { id: "board", label: "Board" },
  { id: "attention", label: count("Needs Attention", n.attention) },
  { id: "skipped", label: count("Skipped and paused", n.skipped) },
  { id: "cutoff", label: count("Cutoff requests", n.cutoff) },
  { id: "queue", label: "Crew queue" },
  { id: "improve", label: "Draft improvements" },
  // The per-site scheduling rules (moved from Site Setup).
  { id: "rules", label: "Rules" },
  // Shown only when a report section file exists in ./reports.
  ...(REPORT_SECTIONS.length ? [{ id: "reports", label: "Reports" }] : []),
] as const;

/** The reports of the chosen day, one block per section file found in the reports folder. */
function ReportsPanel({ societyId, date }: { societyId: string; date: string }) {
  if (!societyId) return <EmptyState title="Choose a site">Pick a site at the top left to see its reports.</EmptyState>;
  return (
    <div className="flex flex-col gap-8">
      {REPORT_SECTIONS.map(({ id, title, component: Report }) => (
        <section key={id} aria-labelledby={`report-${id}`} className="flex flex-col gap-3">
          <h2 id={`report-${id}`} className="text-lg font-semibold">{title}</h2>
          <Report societyId={societyId} date={date} />
        </section>
      ))}
    </div>
  );
}

const dayText = (iso: string) => `${weekday(iso)} ${fmtDate(iso)}`;

/** The result of a run in words: "12 placed, 1 unscheduled, 0 late." */
const runSummary = (r: { schedules: RunResult[] }) => {
  const sum = (k: "placed" | "unscheduled" | "late") => r.schedules.reduce((n, s) => n + s[k], 0);
  return `${sum("placed")} placed, ${sum("unscheduled")} unscheduled, ${sum("late")} late.`;
};
const isDate = (s: string | null): s is string => Boolean(s && /^\d{4}-\d{2}-\d{2}$/.test(s));

/** A draft's freeze time, only while "Freeze by itself" is on (scheduler.auto_freeze). */
function freezeText(s: ScheduleOut, autoFreeze: boolean): string {
  if (s.status === "Frozen") return `Frozen${s.frozen_at ? ` on ${fmtDate(s.frozen_at)}` : ""}. Crew see it as their cards.`;
  if (!autoFreeze) return "";
  const t = new Date(s.freeze_deadline).toLocaleTimeString("en-IN", {
    hour: "2-digit", minute: "2-digit", hour12: false, timeZone: "Asia/Kolkata",
  });
  return `Freezes by itself at ${t} on ${fmtDate(s.freeze_deadline)}.`;
}

/**
 * `page` is the Schedule page with all its tabs. `focus` is the Board alone in a full-screen
 * dialog over the page, and `solo` is the Board alone in its own browser tab. The two board-only
 * modes drop the tabs and the run and reassign buttons, so the admin can work on the day's
 * jobs with the whole screen (ADM-SCH-33).
 */
export type ScheduleMode = "page" | "focus" | "solo";

export function SchedulePage({ mode = "page" }: { mode?: ScheduleMode }) {
  const boardOnly = mode !== "page";
  const [focusOpen, setFocusOpen] = useState(false);
  const qc = useQueryClient();
  const tasks = useTasks();
  const confirm = useConfirm();
  const site = useSite();
  const societyId = site.id;
  // The day, the tab and the board view are in the address, so a finished run can link to its board.
  const [params, setParams] = useSearchParams();
  const setParam = (key: string, value: string | null) => setParams((p) => {
    const next = new URLSearchParams(p);
    if (value) next.set(key, value); else next.delete(key);
    return next;
  }, { replace: true });

  const today = toIso(new Date());
  const schedulesQ = useSchedules(societyId, addDays(today, -DAYS_BACK));
  const scheduleOf = new Map<string, ScheduleOut>();
  // Where two schedules cover a date, the later-starting one (the newer run) shows it.
  for (const s of schedulesQ.data ?? []) for (const d of datesOf(s.start_date, s.end_date)) scheduleOf.set(d, s);
  const allDays = [...scheduleOf.keys()].sort();
  // Today at first, or the next scheduled day when today has no schedule (ADM-SCH-35).
  const date = isDate(params.get("date")) ? params.get("date")!
    : scheduleOf.has(today) ? today : allDays.find((d) => d >= today) ?? today;
  const schedule = scheduleOf.get(date);
  const boardQ = useScheduleBoard(schedule?.id);
  const board: Board | null = boardQ.data ?? null;

  const autoFreeze = useAutoFreezeOn();
  const preferences = useQuery({ queryKey: ["admin-settings"], queryFn: () => api<{ key: string; value: string | number }[]>("/v1/admin/directory/settings") });
  // Runs are daily only (ADM-SCH-09): the run covers the chosen day.
  const runStart = date;
  const runDays = 1;

  const [focusStatus, setFocusStatus] = useState("");
  const [focusType, setFocusType] = useState("");
  const [focusFlag, setFocusFlag] = useState("");
  // Off, the filters hide the cards, blocks and rows they do not keep; on, those show in disabled form (P1-4).
  const [showAll, setShowAll] = useState(false);
  // Which crew members' lanes and rows are shown; none chosen shows everyone.
  const [crewSel, setCrewSel] = useState<string[]>([]);
  const [hideOff, setHideOff] = useState(false);
  const [density, setDensity] = useDensity();
  // The result of the last run, shown as a celebration until it ends.
  const [celebration, setCelebration] = useState<string | null>(null);
  // The run music (ux9): it starts from the Run click and stops when the celebration ends or the run fails.
  const [musicMuted, setMusicMuted] = useState(isRunMusicMuted);
  useEffect(() => () => stopRunMusic(), []);
  const [search, setSearch] = useState("");
  const [problem, setProblem] = useState<{ code: string; message: string; scheduleId: string } | null>(null);
  const [open, setOpen] = useState<AdminJob | null>(null);
  const [movingDate, setMovingDate] = useState<AdminJob | null>(null);
  const [unfreezing, setUnfreezing] = useState<ScheduleOut | null>(null);

  const needsQ = useNeedsScheduling(societyId);
  const cutoffQ = useCutoffRequests();
  const needsAll = needsQ.data?.jobs ?? [];
  const addons = (needsQ.data?.pending_addons ?? []).filter((a) => a.date === date);
  const interiorQ = useInteriorDayMissing(societyId);
  const interiorMissing = interiorQ.data?.length ?? 0;
  const cutoffs = (cutoffQ.data ?? []).filter((r) => r.date === date);
  const attention = new Set([...needsAll.map((j) => j.date), ...(cutoffQ.data ?? []).map((r) => r.date)]);

  const dayJobs = board?.jobs.filter((j) => j.date === date) ?? [];
  // Skipped and paused jobs have their own tab, so the Board shows only work to do (ADM-SCH-36).
  const jobs = dayJobs.filter((j) => j.status !== "Skipped");
  const skippedCount = dayJobs.length - jobs.length;
  const availability = board?.days.find((d) => d.date === date)?.availability ?? [];
  const view = params.get("view") === "timeline" ? "timeline" : params.get("view") === "table" ? "table" : "cards";
  const isOff = (id: string) => availability.find((a) => a.crew_id === id)?.status === "Off";
  const shownCrew = (board?.crew ?? []).filter((c) => (crewSel.length === 0 || crewSel.includes(c.id)) && !(hideOff && isOff(c.id)));
  // The table lists only what the search and the chips keep, unless "Show all" is on; then the rest show in disabled form.
  const crewJobs = jobs.filter((j) => crewSel.length === 0 || (j.crew_id !== null && crewSel.includes(j.crew_id)));
  const keptByFilters = (j: AdminJob) => matches(j, focusStatus, search, focusType, focusFlag);
  const tableJobs = showAll ? crewJobs : crewJobs.filter(keptByFilters);

  // An old link with tab=run opens the board with the Run dialog.
  // An old link with tab=needs (the Needs scheduling tab, now on the Board's Unscheduled column) opens the board.
  const tab = !boardOnly && params.get("tab") && !["run", "needs"].includes(params.get("tab")!) ? params.get("tab")! : "board";
  const [runOpen, setRunOpen] = useState(!boardOnly && params.get("tab") === "run");
  const runLabel = `Scheduler, ${site.name || "site"}`;
  const running = tasks.isRunning(runLabel);
  // Changing the day keeps the tab, so the admin stays on the section they are working in.
  const chooseDate = (d: string) => {
    setProblem(null);
    setParams((p) => { const next = new URLSearchParams(p); next.set("date", d); next.set("tab", tab); return next; }, { replace: true });
  };

  /** A move changes the board, the lists of what needs scheduling and the capacity, nothing else. */
  // F opens the focus view, unless the admin is typing or a dialog is already open.
  useEffect(() => {
    if (mode !== "page") return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key.toLowerCase() !== "f" || e.ctrlKey || e.metaKey || e.altKey) return;
      const t = e.target as HTMLElement | null;
      if (t?.closest("input,textarea,select,[contenteditable=true]")) return;
      if (document.querySelector("[role=dialog],[role=alertdialog],[role=menu]")) return;
      e.preventDefault();
      setFocusOpen(true);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [mode]);
  const soloPath = useHref("/schedule/board");

  const refreshAfterMove = () => Promise.all([
    qc.invalidateQueries({ queryKey: ["board"] }),
    qc.invalidateQueries({ queryKey: ["needs-scheduling"] }),
    qc.invalidateQueries({ queryKey: ["capacity"] }),
  ]);

  const refresh = () => Promise.all([
    qc.invalidateQueries({ queryKey: ["board"] }),
    qc.invalidateQueries({ queryKey: ["schedules"] }),
    qc.invalidateQueries({ queryKey: ["needs-scheduling"] }),
    qc.invalidateQueries({ queryKey: ["skipped"] }),
    qc.invalidateQueries({ queryKey: ["capacity"] }),
  ]);

  const toggleMusic = () => {
    const next = !musicMuted;
    setRunMusicMuted(next);
    setMusicMuted(next);
  };

  const run = () => {
    // Called from the click, so the browser allows the sound to start.
    startRunMusic();
    setRunOpen(false);
    setCelebration(null);
    const start = runStart;
    const day = date;
    void tasks.start({
      label: runLabel,
      detail: `${dayText(start)} to ${dayText(addDays(start, runDays - 1))}, placing jobs…`,
      run: async () => {
        const r = await api<{ schedules: RunResult[] }>("/v1/admin/scheduling/run", {
          method: "POST", body: { society_id: societyId || null, start_date: start, days: runDays },
        });
        await refresh();
        return r;
      },
      done: (r) => ({
        message: runSummary(r),
        link: { label: "Open board", to: `/schedule?date=${day}&tab=board` },
      }),
    }).then((r) => {
      setProblem(null);
      setParams({ date: day, tab: "board" }, { replace: true });
      setCelebration(runSummary(r));
    }, () => { stopRunMusic(); /* The task tray and a toast say why it failed. */ });
  };

  // A move shows on the board at once and is put back if the server refuses it (ADM-SCH-33).
  const boardKey = ["board", "id", schedule?.id];
  // Another tab of this browser that saves a change re-reads this board (P0-9, same browser only).
  useBoardSync();
  const move = useAppMutation<{ job: AdminJob; crewId: string | null; startMinute: number | null; override?: boolean }, AdminJob>({
    mutationFn: (v) => api(`/v1/admin/scheduling/jobs/${v.job.id}/move`, {
      method: "POST", body: { crew_id: v.crewId, start_minute: v.startMinute, ...(v.override ? { override: true } : {}) },
    }),
    pending: false,
    optimistic: async (v) => {
      await qc.cancelQueries({ queryKey: boardKey });
      const before = qc.getQueryData<Board>(boardKey);
      if (before) {
        const crewName = before.crew.find((c) => c.id === v.crewId)?.name ?? null;
        const placed = v.crewId !== null && v.startMinute !== null;
        qc.setQueryData<Board>(boardKey, {
          ...before,
          jobs: before.jobs.map((j) => (j.id !== v.job.id ? j : {
            ...j, crew_id: v.crewId, crew_name: crewName, manual: true,
            start_minute: placed ? v.startMinute : null,
            start_time: placed ? hhmm(v.startMinute!) : null,
            end_time: placed ? hhmm(v.startMinute! + j.duration_minutes) : null,
          })),
        });
      }
      setOpen(null);
      return () => qc.setQueryData(boardKey, before);
    },
    success: (_d, v) => (v.crewId
      ? `${v.job.registration} moved to ${board?.crew.find((c) => c.id === v.crewId)?.name ?? "the crew member"} at ${hhmm(v.startMinute ?? 0)}.`
      : `${v.job.registration} taken off its crew member.`),
    // Undo puts the job back where it was, through the same move.
    action: (_d, v) => (v.job.crew_id === v.crewId && v.job.start_minute === v.startMinute ? undefined : {
      label: "Undo",
      onClick: () => move.mutate({ job: v.job, crewId: v.job.crew_id, startMinute: v.job.start_minute }),
    }),
    onSuccess: () => { setProblem(null); void refreshAfterMove(); },
    onError: (e, v) => {
      setOpen(null);
      // SCHS-22: a placement against a rule is allowed once the admin has seen what it breaks.
      if (e instanceof ApiError && e.code === "placement_warning") {
        void confirm({
          title: `Place ${v.job.registration} against the rules?`,
          description: (
            <ul className="list-disc pl-5">
              {Object.entries(e.fields).map(([code, message]) => <li key={code}>{message}</li>)}
            </ul>
          ),
          confirmLabel: "Place anyway",
        }).then((ok) => { if (ok) move.mutate({ ...v, override: true }); });
        return;
      }
      if (e instanceof ApiError && e.code === "schedule_frozen") {
        setProblem({ code: e.code, message: e.message, scheduleId: v.job.schedule_id });
      }
    },
  });
  const onMove = (job: AdminJob, crewId: string | null, startMinute: number | null) => move.mutate({ job, crewId, startMinute });
  // A refused drop (the card is already back) says why above the board; a frozen day offers the code there.
  const onDropSettled = (e: unknown) => {
    if (e instanceof ApiError && e.code === "schedule_frozen" && schedule) {
      setProblem({ code: e.code, message: e.message, scheduleId: schedule.id });
    } else {
      setProblem(null);
    }
  };

  const freeze = useAppMutation<string>({
    event: EVENTS.scheduleFrozen,
    mutationFn: (id) => api(`/v1/admin/scheduling/schedules/${id}/freeze`, { method: "POST" }),
    pending: "Freezing…",
    success: "The schedule is frozen. Crew can now see it.",
    onSuccess: () => { setProblem(null); void refresh(); },
  });

  const askFreeze = async (s: ScheduleOut) => {
    const days = s.start_date === s.end_date ? dayText(s.start_date) : `every day from ${dayText(s.start_date)} to ${dayText(s.end_date)}`;
    if (await confirm({
      title: "Freeze this schedule?",
      description: `${s.society_name}, ${days}. Crew see a frozen schedule as their cards. After this, moving or adding work needs the code.`,
      confirmLabel: "Freeze",
    })) freeze.mutate(s.id);
  };

  const hint = view === "timeline"
    ? "View only. Hover a block, or move to it with Tab, for its details. Use Cards to move jobs."
    : view === "table"
    ? "Every job of the day with its crew member. Click a heading to sort. Click a row to open the job and move it."
    : schedule?.status === "Frozen"
      ? "This schedule is frozen. Dropping a card on Unscheduled needs no code. Moving or adding work needs the code."
      : "Drag a card onto a free slot to start it where you drop it, or between two cards to take the first free time after the card above. Click a card to set an exact time.";
  const unfreezeTarget = problem ? (schedulesQ.data ?? []).find((s) => s.id === problem.scheduleId) : undefined;
  const from = allDays[0] && allDays[0] < today ? (allDays[0] > addDays(today, -DAYS_BACK) ? allDays[0] : addDays(today, -DAYS_BACK)) : addDays(today, -7);
  const lastDay = allDays[allDays.length - 1];
  const to = lastDay && lastDay > addDays(today, 13) ? lastDay : addDays(today, 13);

  const boardPanel = !societyId ? <EmptyState title="Choose a site">Pick a site at the top left to see its board.</EmptyState> : (
          <div className="flex h-full min-h-0 flex-col gap-2">
            {schedulesQ.isPending && <Skeleton className="h-72 w-full" />}
            {schedulesQ.isError && <ErrorState message={errorMessage(schedulesQ.error)} onRetry={() => void schedulesQ.refetch()} />}
            {schedulesQ.isSuccess && !schedule && (
              <EmptyState title={`No schedule for ${dayText(date)}`}
                          action={<Button onClick={() => setRunOpen(true)}>Run the scheduler</Button>}>
                Run the scheduler to make a draft for this day, or choose another day at the top.
              </EmptyState>
            )}
            {schedule && boardQ.isPending && <Skeleton className="h-72 w-full" />}
            {boardQ.isError && <ErrorState message={errorMessage(boardQ.error)} onRetry={() => void boardQ.refetch()} />}
            {schedule && board && (
              <>
                <div className="sch-toolbar flex flex-wrap items-center gap-x-2 gap-y-1.5">
                  <div className="sch-views" role="group" aria-label="Board view">
                    <button type="button" aria-pressed={view === "cards"} onClick={() => setParam("view", null)}>
                      <Columns3 aria-hidden /> Cards
                    </button>
                    <button type="button" aria-pressed={view === "timeline"} onClick={() => setParam("view", "timeline")}>
                      <ChartGantt aria-hidden /> Timeline
                    </button>
                    <button type="button" aria-pressed={view === "table"} onClick={() => setParam("view", "table")}>
                      <Table2 aria-hidden /> Table
                    </button>
                  </div>
                  <label className="relative">
                    <span className="sr-only">Find a job</span>
                    <Search className="pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted-foreground" aria-hidden />
                    <Input type="search" className="h-8 w-32 pl-8 transition-[width] focus:w-72" placeholder="Find a job" value={search}
                           onChange={(e) => setSearch(e.target.value)} />
                  </label>
                  <StatusSummary jobs={jobs} focus={focusStatus} onFocus={setFocusStatus} />
                  <ServicesFilter jobs={jobs} type={focusType} onType={setFocusType} />
                  <FlagKey flag={focusFlag} onFlag={setFocusFlag} />
                  <ShowAll checked={showAll} onChange={setShowAll} />
                  <CrewPicker crew={board.crew} selected={crewSel} onChange={setCrewSel} hideOff={hideOff} onHideOff={setHideOff} />
                  {/* The card detail switch works for all three views (ADM-SCH-32). */}
                  <div className="sch-views" role="group" aria-label="Card detail" title="How much each job shows">
                    {DENSITIES.map(([id, label]) => (
                      <button key={id} type="button" aria-pressed={density === id} onClick={() => setDensity(id)}>{label}</button>
                    ))}
                  </div>
                  {/* The hint shows at once on hover or focus, unlike a native title, which waits (owner, 8-Nov-26). */}
                  <HoverTip label={<Info className="size-4 text-muted-foreground" aria-hidden />} ariaLabel={hint}>
                    <span className="block max-w-xs">{hint}</span>
                  </HoverTip>
                  <span className="ml-auto flex items-center gap-1.5">
                    <JobCardButtons scheduleId={schedule.id} date={date} jobs={dayJobs} />
                    {skippedCount > 0 && !boardOnly && (
                      <Button size="sm" variant="link" className="mr-2 h-auto p-0" onClick={() => setParam("tab", "skipped")}>
                        {skippedCount} skipped or paused, not shown
                      </Button>
                    )}
                    {mode === "page" && (
                      <>
                        <Button size="sm" variant="outline" className="h-8" title="Only the board, filling the window (key F)"
                                onClick={() => setFocusOpen(true)}>
                          <Maximize2 aria-hidden /> Focus
                        </Button>
                        <Button size="sm" variant="outline" className="h-8" asChild>
                          <a href={`${soloPath}?${new URLSearchParams({ date, ...(view !== "cards" ? { view } : {}) })}`}
                             target="_blank" rel="noopener" title="Only the board, in its own browser tab">
                            <ExternalLink aria-hidden /> New tab<span className="sr-only"> (opens the board alone)</span>
                          </a>
                        </Button>
                      </>
                    )}
                  </span>
                </div>
                {view === "table" ? (
                  <JobTable jobs={tableJobs} total={jobs.length} onOpen={setOpen} density={density} faded={(j) => !keptByFilters(j)}
                            fileName={`schedule-${(site.name || "site").replace(/[^A-Za-z0-9]+/g, "-")}-${date}.csv`} />
                ) : view === "cards" ? (
                  <CardBoard crew={shownCrew} jobs={jobs} availability={availability} focus={focusStatus} search={search}
                             type={focusType} flag={focusFlag} density={density} showAll={showAll} savingId={move.isPending ? move.variables?.job.id ?? null : null}
                             onOpen={setOpen} onMove={onMove} onDropSettled={onDropSettled} />
                ) : (
                  <Timeline crew={shownCrew} jobs={jobs} availability={availability} focus={focusStatus} search={search} type={focusType} flag={focusFlag} density={density} showAll={showAll} boardKey={boardKey}
                            now={date === today ? new Date().getHours() * 60 + new Date().getMinutes() : undefined} onDropSettled={onDropSettled} />
                )}
              </>
            )}
          </div>
        );

  // The names that fall while a run works: every crew member and every car (registration) the loaded data shows.
  const rainNames = [...new Set([
    ...(board?.crew ?? []).map((c) => c.name),
    ...(board?.jobs ?? []).map((j) => j.registration),
    ...needsAll.map((j) => j.registration),
  ].filter(Boolean))];

  return (
    <div className={cn("sch-page", mode !== "page" && mode)}>
      {/* One slim bar: title, the day, the schedule of the day and its actions. The day strip folds away (ADM-SCH-35). */}
      <DateBar title="Schedule" site={site.name || undefined} startFolded={boardOnly} date={date} today={today} from={from} to={to}
               scheduleOf={scheduleOf} attention={attention} onChange={chooseDate}>
        {!societyId ? (
          <span className="text-sm text-muted-foreground">Pick a site at the top left to see its schedule.</span>
        ) : schedulesQ.isPending ? <Skeleton className="h-6 w-60" />
          : (
          <div role="group" aria-label="Schedule of this day" className="flex min-w-0 flex-1 flex-nowrap items-center gap-x-3">
            {schedule ? (
              <>
                <StatusBadge status={schedule.status} />
                <span className="min-w-0 truncate text-sm text-muted-foreground"
                      title={schedule.start_date === schedule.end_date ? "A schedule for this day only."
                        : `Part of the schedule for ${dayText(schedule.start_date)} to ${dayText(schedule.end_date)}. Freezing applies to all its days.`}>
                  {freezeText(schedule, autoFreeze)}
                </span>
              </>
            ) : (
              <span className="text-sm text-muted-foreground">No schedule covers this day yet. Run the scheduler to make a draft.</span>
            )}
            <div className="ml-auto flex shrink-0 items-center gap-2">
              {/* The Run button is on the page and in the focus view's top bar; the own-tab board has none. */}
              {mode !== "solo" && (
                <Button size="sm" variant={schedule ? "outline" : "default"} onClick={() => setRunOpen(true)} disabled={running}
                        aria-busy={running || undefined}>
                  {running ? <Loader2 className="animate-spin" aria-hidden /> : <Play aria-hidden />}
                  {running ? "Running…" : "Run"}
                </Button>
              )}
              {schedule && (
                <>
                  {schedule.status === "Draft" ? (
                    <Button size="sm" onClick={() => void askFreeze(schedule)} disabled={freeze.isPending}>
                      <Lock aria-hidden /> Freeze
                    </Button>
                  ) : (
                    <Button size="sm" variant="outline" onClick={() => setUnfreezing(schedule)}>
                      <LockOpen aria-hidden /> Unfreeze
                    </Button>
                  )}
                </>
              )}
            </div>
          </div>
        )}
      </DateBar>

      {problem && (
        <div role="alert" className="mb-2 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm text-destructive">
          <span className="flex items-center gap-2"><TriangleAlert className="size-4" aria-hidden />{problem.message}</span>
          {problem.code === "schedule_frozen" && unfreezeTarget && (
            <Button variant="outline" size="sm" onClick={() => setUnfreezing(unfreezeTarget)}>Unfreeze with code</Button>
          )}
        </div>
      )}

      {boardOnly ? <div className="sch-panel">{boardPanel}</div> : <Tabs tabs={SCHEDULE_TABS({ attention: interiorMissing, skipped: skippedCount, cutoff: cutoffs.length })} active={tab}
            label="Schedule sections" onChange={(t) => setParam("tab", t)}>
        {tab === "board" && <>{boardPanel}<PendingAddons addons={addons} /></>}

        {tab === "attention" && <NeedsAttention societyId={societyId} />}
        {tab === "skipped" && (!societyId
          ? <EmptyState title="Choose a site">Pick a site at the top left to see its skipped and paused jobs.</EmptyState>
          : <SkippedJobs key={`${societyId}-${date}`} societyId={societyId} date={date} />)}
        {tab === "cutoff" && <CutoffRequests date={date} onDate={chooseDate} refresh={refresh} />}
        {tab === "queue" && (board
          ? <QueuePanel key={date} crew={board.crew} jobs={dayJobs} date={date} refresh={refresh} />
          : <EmptyState title="No schedule for this day">Run the scheduler for this day to make a draft first.</EmptyState>)}
        {tab === "improve" && <DraftImprovements key={date} board={board} date={date} refresh={refresh} />}
        {tab === "rules" && <RulesPanel />}
        {tab === "reports" && REPORT_SECTIONS.length > 0 && <ReportsPanel societyId={societyId} date={date} />}
      </Tabs>}

      {open && (
        <JobDialog key={open.id} job={open} board={board} busy={move.isPending} onClose={() => setOpen(null)}
                   onMove={onMove} onMoveDate={(j) => { setOpen(null); setMovingDate(j); }} />
      )}
      {movingDate && (
        <MoveToDateDialog job={movingDate} today={today} onClose={() => setMovingDate(null)}
                          onDone={() => { setMovingDate(null); void refresh(); }} />
      )}
      {unfreezing && (
        <UnfreezeDialog schedule={unfreezing} onClose={() => setUnfreezing(null)}
                        onDone={() => { setUnfreezing(null); setProblem(null); void refresh(); }} />
      )}
      {focusOpen && (
        <Dialog open onOpenChange={(o) => { if (!o) setFocusOpen(false); }}>
          <DialogContent aria-describedby={undefined}
                         className="top-0 left-0 h-dvh w-screen max-w-none translate-x-0 translate-y-0 grid-cols-[minmax(0,1fr)] gap-0 rounded-none border-0 bg-background p-3 sm:max-w-none">
            <DialogTitle className="sr-only">Schedule board, focus view</DialogTitle>
            <DialogDescription className="sr-only">The board alone, filling the screen. Press Escape to go back to the page.</DialogDescription>
            <SchedulePage mode="focus" />
          </DialogContent>
        </Dialog>
      )}
      {runOpen && (
        <FormDialog open onOpenChange={(o) => !o && setRunOpen(false)} title={`Run the scheduler, ${site.name || "no site chosen"}`}
                    description="It runs for the chosen site and the chosen day. A run keeps every change made by hand. On a frozen schedule it places only the jobs that have no crew member."
                    size="lg" submitLabel={schedule ? "Run again" : "Run scheduler"} disabled={!societyId || running}
                    onSubmit={run}>
          <div className="flex min-h-9 flex-col justify-center text-sm">
            <span className="text-xs font-medium text-muted-foreground">Day to schedule</span>
            <span>{dayText(runStart)}</span>
          </div>
          <p className="m-0 text-sm text-muted-foreground">
            To schedule another day, choose it at the top.
          </p>
          {preferences.error ? <ErrorState message={errorMessage(preferences.error)} /> : null}
        </FormDialog>
      )}
      {/* Last in the page, so it never takes the first child's place in the focus view. Under an open focus
          view the rain falls on that view instead, so it is not drawn twice. */}
      <NameRain names={rainNames} active={running && !focusOpen} />
      {running && <Fireworks mode="running" muted={musicMuted} onToggleMute={toggleMusic} />}
      {celebration && <Fireworks mode="celebrate" message={celebration} muted={musicMuted} onToggleMute={toggleMusic}
                                 onEnd={() => { stopRunMusic(); setCelebration(null); }} />}
    </div>
  );
}

function UnfreezeDialog({ schedule, onClose, onDone }: { schedule: ScheduleOut; onClose: () => void; onDone: () => void }) {
  const [code, setCode] = useState("");
  const [codeError, setCodeError] = useState("");
  const unfreeze = useAppMutation<string>({
    mutationFn: (c) => api(`/v1/admin/scheduling/schedules/${schedule.id}/unfreeze`, { method: "POST", body: { code: c } }),
    pending: "Unfreezing…",
    success: "The schedule is a draft again. Freeze it again when you are done.",
    onSuccess: onDone,
    onError: (e) => setCodeError(errorMessage(e)),
  });
  const days = schedule.start_date === schedule.end_date ? dayText(schedule.start_date)
    : `${dayText(schedule.start_date)} to ${dayText(schedule.end_date)}`;
  return (
    <FormDialog open onOpenChange={(o) => !o && onClose()} title="Unfreeze with the code" size="sm"
                description={`The schedule for ${days} becomes a draft so work can be added or moved. Crew keep seeing it until you change it.`}
                submitLabel="Unfreeze" busy={unfreeze.isPending} disabled={!code}
                onSubmit={() => unfreeze.mutate(code)}>
      <Field label="Code" error={codeError || undefined}>
        {(p) => <Input {...p} autoComplete="off" value={code} onChange={(e) => { setCode(e.target.value); setCodeError(""); }} />}
      </Field>
    </FormDialog>
  );
}

function JobDialog({ job, board, busy, onClose, onMove, onMoveDate }: {
  onMoveDate: (job: AdminJob) => void;
  job: AdminJob;
  board: Board | null;
  busy: boolean;
  onClose: () => void;
  onMove: (job: AdminJob, crewId: string | null, startMinute: number | null) => void;
}) {
  const confirm = useConfirm();
  const crew = board?.crew ?? [];
  const [crewId, setCrewId] = useState(job.crew_id ?? crew[0]?.id ?? "");
  const [time, setTime] = useState(
    job.start_minute !== null ? hhmm(job.start_minute) : crew[0] ? hhmm(crew[0].start_minute) : "",
  );
  const [error, setError] = useState("");

  const submit = () => {
    const minute = minuteOf(time);
    if (!crewId) return setError("Choose a crew member.");
    if (minute === null) return setError("Enter the time as HH:MM, for example 09:40.");
    setError("");
    onMove(job, crewId, minute);
  };
  const takeOff = async () => {
    if (await confirm({
      title: `Take ${job.registration} off ${job.crew_name ?? "its crew member"}?`,
      description: "The job goes to Unscheduled for this day. You can place it again later.",
      confirmLabel: "Take off crew member", tone: "danger",
    })) onMove(job, null, null);
  };

  const movable = isOpen(job);
  return (
    // The dialog takes the card's colour: the kind of work, or wine when the job was placed against a rule by hand.
    <FormDialog open onOpenChange={(o) => !o && onClose()} title={`${job.registration}, ${job.service}`} size="md"
                submitLabel={movable ? "Move here" : "Close"} cancelLabel={null}
                className={cn("sch-detail", breached(job) ? "wine" : typeClass(job))} style={{ background: "var(--type-bg)" }}
                busy={busy} onSubmit={movable ? submit : onClose}
                extraActions={movable ? (
                  <>
                    {job.crew_id && (
                      <Button type="button" variant="ghost" className="text-destructive" disabled={busy} onClick={() => void takeOff()}>
                        Take off crew member
                      </Button>
                    )}
                    <Button type="button" variant="outline" disabled={busy} onClick={() => onMoveDate(job)}>Move to date</Button>
                  </>
                ) : undefined}>
      <DetailList columns={2} items={[
        { label: "Zone", value: job.zone || "-" },
        { label: "Parking", value: parkingPlace(job) || "-" },
        { label: "Vehicle", value: job.vehicle },
        { label: "Customer", value: job.customer_name },
        { label: "Date", value: dayText(job.date) },
        { label: "Duration", value: `${job.duration_minutes} min` },
        { label: "Status", value: <StatusBadge status={job.status} /> },
        { label: "Now", value: job.crew_name ? `${job.crew_name} at ${job.start_time}` : "Unscheduled" },
        { label: "Finish by", value: job.finish_by },
        // The car's preferred Interior day, on Interior cards only (owner, item 1).
        ...(serviceCode(job.service) === "INT" ? [{ label: "Preferred Interior day", value: job.interior_day ?? "Not set" }] : []),
        ...(job.moved_to_date ? [{ label: "Moved", wide: true, value: `Moved to ${dayText(job.moved_to_date)}.` }] : []),
        ...(job.moved_from_date ? [{ label: "Moved", wide: true, value: `Moved from ${dayText(job.moved_from_date)}.` }] : []),
        ...(job.visit_outcome === "Partially Completed" ? [{
          label: "Visit outcome", wide: true,
          value: `Partially Completed. Delivered ${(job.delivered_services ?? []).join(", ") || "none"} of ${(job.planned_services ?? []).join(", ")}.`,
        }] : []),
      ]} />
      {(job.late || job.manual || job.visit_outcome === "Partially Completed") && <div className="flex gap-2"><JobFlags job={job} /></div>}
      {job.reason && <p className="rounded-md bg-muted px-3 py-2 text-sm text-muted-foreground">{job.reason}</p>}
      {breached(job) && (
        <p className="rounded-md border border-current px-3 py-2 text-sm">
          Placed by hand against a rule: {(job.hand_breaches ?? []).join(" ")}
        </p>
      )}
      {!movable && (
        <p className="m-0 border-t pt-4 text-sm text-muted-foreground">
          This job is {job.status}, so it can no longer be placed or moved.
        </p>
      )}
      {movable && <div className="grid grid-cols-1 gap-4 border-t pt-4 sm:grid-cols-[minmax(0,1fr)_9rem]">
        <Field label="Crew member">
          {(p) => <SelectBox {...p} value={crewId} onChange={setCrewId}
                             choices={crew.map((c) => ({ value: c.id, label: `${c.name} (${hhmm(c.start_minute)} to ${hhmm(c.end_minute)})` }))} />}
        </Field>
        <Field label="Start time" error={error || undefined}>
          {(p) => <Input {...p} type="time" step={300} value={time} onChange={(e) => setTime(e.target.value)} />}
        </Field>
      </div>}
    </FormDialog>
  );
}
