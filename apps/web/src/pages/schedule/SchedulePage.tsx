import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ChartGantt, Columns3, Loader2, Lock, LockOpen, Play, Search, TriangleAlert } from "lucide-react";
import { useState } from "react";
import { useSearchParams } from "react-router-dom";

import { api, ApiError } from "@/api/client";
import { useConfirm } from "@/blocks/confirm";
import { DataTable } from "@/blocks/DataTable";
import { Field, SelectBox } from "@/blocks/fields";
import { FormDialog } from "@/blocks/FormDialog";
import { DetailList, EmptyState, ErrorState, PageHeader, Panel } from "@/blocks/layout";
import { EVENTS } from "@/analytics/events";
import { errorMessage, useAppMutation } from "@/blocks/mutation";
import { StatusBadge } from "@/blocks/status";
import { useTasks } from "@/blocks/tasks";
import { Tabs } from "@/components";
import { cn } from "@/lib/utils";
import { useSite } from "@/site/SiteContext";
import { Button } from "@/ui/button";
import { Input } from "@/ui/input";
import { Skeleton } from "@/ui/skeleton";

import { isOpen, JobFlags, JobLabel, StatusSummary } from "./Board";
import { CardBoard } from "./CardBoard";
import { addDays, DateBar } from "./DateBar";
import { CutoffRequests, DraftImprovements, OtherDays, PendingAddons } from "./ScheduleActions";
import { SkippedJobs } from "./SkippedJobs";
import { Timeline } from "./Timeline";
import {
  datesOf, daysInMonthFrom, fmtDate, hhmm, minuteOf, toIso, useCutoffRequests, useNeedsScheduling,
  useScheduleBoard, useSchedules, weekday,
  type AdminJob, type Board, type RunResult, type ScheduleOut,
} from "./api";
import "./schedule.css";

type Period = "daily" | "weekly" | "monthly";
const PERIODS: { value: Period; label: string }[] = [
  { value: "daily", label: "Daily" }, { value: "weekly", label: "Weekly" }, { value: "monthly", label: "Monthly" },
];

/** How far back the day strip goes (ADM-SCH-35). */
const DAYS_BACK = 30;

const count = (label: string, n: number) => (n ? `${label} (${n})` : label);

/** The sections of the page, one tab each, all for the chosen day (ADM-SCH-32). */
const SCHEDULE_TABS = (n: { needs: number; skipped: number; cutoff: number }) => [
  { id: "run", label: "Run" },
  { id: "board", label: "Board" },
  { id: "needs", label: count("Needs scheduling", n.needs) },
  { id: "skipped", label: count("Skipped and paused", n.skipped) },
  { id: "cutoff", label: count("Cutoff requests", n.cutoff) },
  { id: "improve", label: "Draft improvements" },
] as const;

function periodDays(period: Period, start: string): number {
  if (period === "daily") return 1;
  if (period === "monthly") return daysInMonthFrom(start);
  return 7;
}

/** The first day of the period that contains `date`. */
function periodStart(period: Period, date: string, weekStart: number): string {
  if (period === "monthly") return `${date.slice(0, 7)}-01`;
  if (period !== "weekly") return date;
  const d = new Date(`${date}T00:00:00Z`);
  const mondayDay = (d.getUTCDay() + 6) % 7;
  d.setUTCDate(d.getUTCDate() - (mondayDay - weekStart + 7) % 7);
  return d.toISOString().slice(0, 10);
}

const dayText = (iso: string) => `${weekday(iso)} ${fmtDate(iso)}`;
const isDate = (s: string | null): s is string => Boolean(s && /^\d{4}-\d{2}-\d{2}$/.test(s));

function freezeText(s: ScheduleOut): string {
  if (s.status === "Frozen") return `Frozen${s.frozen_at ? ` on ${fmtDate(s.frozen_at)}` : ""}. Crew see it as their cards.`;
  const t = new Date(s.freeze_deadline).toLocaleTimeString("en-IN", {
    hour: "2-digit", minute: "2-digit", hour12: false, timeZone: "Asia/Kolkata",
  });
  return `Freezes by itself at ${t} on ${fmtDate(s.freeze_deadline)}.`;
}

export function SchedulePage() {
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

  const preferences = useQuery({ queryKey: ["admin-settings"], queryFn: () => api<{ key: string; value: string | number }[]>("/v1/admin/directory/settings") });
  const configured = String(preferences.data?.find((p) => p.key === "schedule.period")?.value ?? "Weekly").toLowerCase();
  const configuredPeriod: Period = configured === "daily" ? "daily" : configured === "monthly" ? "monthly" : "weekly";
  const [chosenPeriod, setPeriod] = useState<Period | null>(null);
  const period = chosenPeriod ?? configuredPeriod;
  const weekStart = Number(preferences.data?.find((p) => p.key === "schedule.week_start")?.value ?? 6);
  const runStart = periodStart(period, date, weekStart);
  const runDays = periodDays(period, runStart);

  const [focusStatus, setFocusStatus] = useState("");
  const [search, setSearch] = useState("");
  const [problem, setProblem] = useState<{ code: string; message: string; scheduleId: string } | null>(null);
  const [open, setOpen] = useState<AdminJob | null>(null);
  const [unfreezing, setUnfreezing] = useState<ScheduleOut | null>(null);

  const needsQ = useNeedsScheduling(societyId);
  const cutoffQ = useCutoffRequests();
  const needsAll = needsQ.data?.jobs ?? [];
  const needs = needsAll.filter((j) => j.date === date);
  const addons = (needsQ.data?.pending_addons ?? []).filter((a) => a.date === date);
  const cutoffs = (cutoffQ.data ?? []).filter((r) => r.date === date);
  const attention = new Set([...needsAll.map((j) => j.date), ...(cutoffQ.data ?? []).map((r) => r.date)]);

  const dayJobs = board?.jobs.filter((j) => j.date === date) ?? [];
  // Skipped and paused jobs have their own tab, so the Board shows only work to do (ADM-SCH-36).
  const jobs = dayJobs.filter((j) => j.status !== "Skipped");
  const skippedCount = dayJobs.length - jobs.length;
  const availability = board?.days.find((d) => d.date === date)?.availability ?? [];
  const view = params.get("view") === "timeline" ? "timeline" : "cards";

  const tab = params.get("tab") ?? (schedulesQ.isSuccess && !schedule ? "run" : "board");
  const runLabel = `Scheduler, ${site.name || "site"}`;
  const running = tasks.isRunning(runLabel);
  // Changing the day keeps the tab, so the admin stays on the section they are working in.
  const chooseDate = (d: string) => {
    setProblem(null);
    setParams((p) => { const next = new URLSearchParams(p); next.set("date", d); next.set("tab", tab); return next; }, { replace: true });
  };

  const refresh = () => Promise.all([
    qc.invalidateQueries({ queryKey: ["board"] }),
    qc.invalidateQueries({ queryKey: ["schedules"] }),
    qc.invalidateQueries({ queryKey: ["needs-scheduling"] }),
    qc.invalidateQueries({ queryKey: ["skipped"] }),
    qc.invalidateQueries({ queryKey: ["capacity"] }),
  ]);

  const savePeriod = useAppMutation<Period>({
    mutationFn: (value) => api("/v1/admin/directory/settings/schedule.period", {
      method: "PUT", body: { value: value[0].toUpperCase() + value.slice(1) },
    }),
    success: (_d, v) => `${v[0].toUpperCase() + v.slice(1)} is now the default period.`,
    invalidate: [["admin-settings"]],
  });

  const run = () => {
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
      done: (r) => {
        const sum = (k: "placed" | "unscheduled" | "late") => r.schedules.reduce((n, s) => n + s[k], 0);
        return {
          message: `${sum("placed")} placed, ${sum("unscheduled")} unscheduled, ${sum("late")} late.`,
          link: { label: "Open board", to: `/schedule?date=${day}&tab=board` },
        };
      },
    }).then(() => {
      setProblem(null);
      setParams({ date: day, tab: "board" }, { replace: true });
    }, () => { /* The task tray and a toast say why it failed. */ });
  };

  const move = useAppMutation<{ job: AdminJob; crewId: string | null; startMinute: number | null }, AdminJob>({
    mutationFn: (v) => api(`/v1/admin/scheduling/jobs/${v.job.id}/move`, {
      method: "POST", body: { crew_id: v.crewId, start_minute: v.startMinute },
    }),
    pending: "Moving the job…",
    success: (_d, v) => (v.crewId
      ? `${v.job.registration} moved to ${board?.crew.find((c) => c.id === v.crewId)?.name ?? "the crew member"} at ${hhmm(v.startMinute ?? 0)}.`
      : `${v.job.registration} taken off its crew member.`),
    onSuccess: () => { setProblem(null); setOpen(null); void refresh(); },
    onError: (e, v) => {
      setOpen(null);
      if (e instanceof ApiError && e.code === "schedule_frozen") {
        setProblem({ code: e.code, message: e.message, scheduleId: v.job.schedule_id });
      }
    },
  });
  const onMove = (job: AdminJob, crewId: string | null, startMinute: number | null) => move.mutate({ job, crewId, startMinute });

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

  const unfreezeTarget = problem ? (schedulesQ.data ?? []).find((s) => s.id === problem.scheduleId) : undefined;
  const from = allDays[0] && allDays[0] < today ? (allDays[0] > addDays(today, -DAYS_BACK) ? allDays[0] : addDays(today, -DAYS_BACK)) : addDays(today, -7);
  const lastDay = allDays[allDays.length - 1];
  const to = lastDay && lastDay > addDays(today, 13) ? lastDay : addDays(today, 13);

  return (
    <>
      <PageHeader
        title="Schedule"
        site={site.name || undefined}
        description="Choose a day. Every tab works on that day: run the scheduler, arrange its jobs, deal with what needs you, and freeze by 8 PM the day before."
      />

      {/* The day leads the page: every tab below shows and changes only this day (ADM-SCH-35). */}
      <DateBar date={date} today={today} from={from} to={to} scheduleOf={scheduleOf} attention={attention} onChange={chooseDate}>
        {!societyId ? (
          <p className="m-0 px-5 py-3 text-sm text-muted-foreground">Pick a site at the top left to see its schedule.</p>
        ) : schedulesQ.isPending ? <div className="px-5 py-3"><Skeleton className="h-6 w-80" /></div>
          : schedule ? (
          <div role="group" aria-label="Schedule of this day" className="flex flex-wrap items-center gap-x-4 gap-y-2 px-5 py-3">
            <StatusBadge status={schedule.status} />
            <span className="text-sm">
              {schedule.start_date === schedule.end_date ? "A schedule for this day only."
                : `Part of the schedule for ${dayText(schedule.start_date)} to ${dayText(schedule.end_date)}. Freezing applies to all its days.`}
            </span>
            <span className="text-sm text-muted-foreground">{freezeText(schedule)}</span>
            <div className="ml-auto flex gap-2">
              {schedule.status === "Draft" ? (
                <Button size="sm" onClick={() => void askFreeze(schedule)} disabled={freeze.isPending}>
                  <Lock aria-hidden /> Freeze
                </Button>
              ) : (
                <Button size="sm" variant="outline" onClick={() => setUnfreezing(schedule)}>
                  <LockOpen aria-hidden /> Unfreeze
                </Button>
              )}
            </div>
          </div>
        ) : (
          <div className="flex flex-wrap items-center gap-3 px-5 py-3">
            <span className="text-sm text-muted-foreground">No schedule covers this day yet. Run the scheduler to make a draft.</span>
            {tab !== "run" && <Button size="sm" variant="outline" className="ml-auto" onClick={() => setParam("tab", "run")}>Go to Run</Button>}
          </div>
        )}
      </DateBar>

      {problem && (
        <div role="alert" className="mb-5 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm text-destructive">
          <span className="flex items-center gap-2"><TriangleAlert className="size-4" aria-hidden />{problem.message}</span>
          {problem.code === "schedule_frozen" && unfreezeTarget && (
            <Button variant="outline" size="sm" onClick={() => setUnfreezing(unfreezeTarget)}>Unfreeze with code</Button>
          )}
        </div>
      )}

      <Tabs tabs={SCHEDULE_TABS({ needs: needs.length, skipped: skippedCount, cutoff: cutoffs.length })} active={tab}
            label="Schedule sections" onChange={(t) => setParam("tab", t)}>
        {tab === "run" && (
          <Panel title={`Run the scheduler, ${site.name || "no site chosen"}`}
                 description="It runs for the chosen site and the period that contains the chosen day. A run keeps every change made by hand. On a frozen schedule it places only the jobs that have no crew member.">
            <form className="grid grid-cols-1 items-end gap-4 sm:grid-cols-[12rem_minmax(0,1fr)_auto]"
                  onSubmit={(e) => { e.preventDefault(); if (!running) run(); }}>
              <Field label="Period">
                {(p) => <SelectBox {...p} value={period} onChange={(v) => setPeriod(v as Period)} choices={PERIODS} />}
              </Field>
              <div className="flex min-h-9 flex-col justify-center text-sm">
                <span className="text-xs font-medium text-muted-foreground">Period to schedule</span>
                <span>{runDays === 1 ? dayText(runStart) : `${dayText(runStart)} to ${dayText(addDays(runStart, runDays - 1))}`}</span>
              </div>
              <Button type="submit" disabled={!societyId || running} aria-busy={running || undefined}>
                {running ? <Loader2 className="animate-spin" aria-hidden /> : <Play aria-hidden />}
                {running ? "Running…" : schedule ? "Run again" : "Run scheduler"}
              </Button>
            </form>
            <p className="mt-3 mb-0 text-sm text-muted-foreground">
              To schedule another period, choose one of its days at the top.
              {period !== configuredPeriod && (
                <> This run uses {period}; the default is {configuredPeriod}.{" "}
                  <Button variant="link" size="sm" className="h-auto p-0" disabled={savePeriod.isPending}
                          onClick={() => savePeriod.mutate(period)}>
                    Make {period} the default
                  </Button>
                </>
              )}
            </p>
            {running && (
              <div role="status" className="mt-4 flex items-start gap-3 rounded-lg border border-gold/40 bg-gold/10 px-4 py-3 text-sm">
                <Loader2 className="mt-0.5 size-4 animate-spin text-gold-text" aria-hidden />
                <span>
                  The scheduler is placing the jobs. This can take up to a minute.
                  You can leave this page; the bar at the top shows the progress and you are told when it finishes.
                </span>
              </div>
            )}
            {preferences.error ? <div className="mt-3"><ErrorState message={errorMessage(preferences.error)} /></div> : null}
          </Panel>
        )}

        {tab === "board" && (!societyId ? <EmptyState title="Choose a site">Pick a site at the top left to see its board.</EmptyState> : (
          <div className="flex flex-col gap-4">
            {schedulesQ.isPending && <Skeleton className="h-72 w-full" />}
            {schedulesQ.isError && <ErrorState message={errorMessage(schedulesQ.error)} onRetry={() => void schedulesQ.refetch()} />}
            {schedulesQ.isSuccess && !schedule && (
              <EmptyState title={`No schedule for ${dayText(date)}`}
                          action={<Button onClick={() => setParam("tab", "run")}>Go to Run</Button>}>
                Run the scheduler to make a draft for this day, or choose another day at the top.
              </EmptyState>
            )}
            {schedule && boardQ.isPending && <Skeleton className="h-72 w-full" />}
            {boardQ.isError && <ErrorState message={errorMessage(boardQ.error)} onRetry={() => void boardQ.refetch()} />}
            {schedule && board && (
              <>
                <div className="flex flex-wrap items-center gap-3">
                  <div className="sch-views" role="group" aria-label="Board view">
                    <button type="button" aria-pressed={view === "cards"} onClick={() => setParam("view", null)}>
                      <Columns3 aria-hidden /> Cards
                    </button>
                    <button type="button" aria-pressed={view === "timeline"} onClick={() => setParam("view", "timeline")}>
                      <ChartGantt aria-hidden /> Timeline
                    </button>
                  </div>
                  <label className="relative">
                    <span className="sr-only">Find a vehicle</span>
                    <Search className="pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted-foreground" aria-hidden />
                    <Input type="search" className="h-8 w-52 pl-8" placeholder="Find a vehicle or parking" value={search}
                           onChange={(e) => setSearch(e.target.value)} />
                  </label>
                  <StatusSummary jobs={jobs} focus={focusStatus} onFocus={setFocusStatus} />
                  {skippedCount > 0 && (
                    <Button size="sm" variant="link" className="ml-auto h-auto p-0" onClick={() => setParam("tab", "skipped")}>
                      {skippedCount} skipped or paused, not shown
                    </Button>
                  )}
                </div>
                <p className={cn("m-0 text-sm text-muted-foreground", schedule.status === "Frozen" && view === "cards" && "text-foreground")}>
                  {view === "timeline"
                    ? "View only. Hover a block, or move to it with Tab, for its details. Use Cards to move jobs."
                    : schedule.status === "Frozen"
                      ? "This schedule is frozen. Dropping a card on Unscheduled needs no code. Moving or adding work needs the code."
                      : "Drag a card onto a free slot to start it where you drop it, or between two cards to take the first free time after the card above. Click a card to set an exact time."}
                </p>
                {view === "cards" ? (
                  <CardBoard crew={board.crew} jobs={jobs} availability={availability} focus={focusStatus} search={search}
                             onOpen={setOpen} onMove={onMove} />
                ) : (
                  <Timeline crew={board.crew} jobs={jobs} availability={availability} focus={focusStatus} search={search}
                            now={date === today ? new Date().getHours() * 60 + new Date().getMinutes() : undefined} />
                )}
              </>
            )}
          </div>
        ))}

        {tab === "needs" && (
          <div className="flex flex-col gap-6">
            <Panel title={`Needs scheduling on ${dayText(date)}`}
                   description="Jobs of this day left without a crew member after the freeze, or that no crew member fits (ADM-SCH-28)." bodyClassName="p-0">
              {needsQ.isError ? <div className="p-4"><ErrorState message={errorMessage(needsQ.error)} /></div> : (
                <DataTable
                  className="[&>div]:rounded-none [&>div]:border-0"
                  rows={needsQ.data ? needs : undefined}
                  loading={needsQ.isPending}
                  rowKey={(j) => j.id}
                  empty={<p className="text-sm text-muted-foreground">Nothing needs scheduling on this day.</p>}
                  columns={[
                    { key: "v", header: "Vehicle", width: "14rem", cell: (j) => <JobLabel job={j} /> },
                    { key: "c", header: "Customer", width: "12rem", cell: (j) => j.customer_name },
                    { key: "f", header: "Finish by", width: "6rem", cell: (j) => j.finish_by ?? "-" },
                    { key: "r", header: "Reason", wrap: true, cell: (j) => j.reason || "No crew member fits." },
                    { key: "a", header: "", width: "6rem", align: "right", cell: (j) => (board
                      ? <Button size="sm" variant="outline" onClick={() => setOpen(j)}>Place</Button> : null) },
                  ]}
                />
              )}
              <OtherDays dates={needsAll.map((j) => j.date)} date={date} onDate={chooseDate} what="job" />
            </Panel>
            <PendingAddons addons={addons} />
          </div>
        )}
        {tab === "skipped" && (!societyId
          ? <EmptyState title="Choose a site">Pick a site at the top left to see its skipped and paused jobs.</EmptyState>
          : <SkippedJobs key={`${societyId}-${date}`} societyId={societyId} date={date} />)}
        {tab === "cutoff" && <CutoffRequests date={date} onDate={chooseDate} refresh={refresh} />}
        {tab === "improve" && <DraftImprovements key={date} board={board} date={date} refresh={refresh} />}
      </Tabs>

      {open && (
        <JobDialog key={open.id} job={open} board={board} busy={move.isPending} onClose={() => setOpen(null)}
                   onMove={onMove} />
      )}
      {unfreezing && (
        <UnfreezeDialog schedule={unfreezing} onClose={() => setUnfreezing(null)}
                        onDone={() => { setUnfreezing(null); setProblem(null); void refresh(); }} />
      )}
    </>
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

function JobDialog({ job, board, busy, onClose, onMove }: {
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
    <FormDialog open onOpenChange={(o) => !o && onClose()} title={`${job.registration}, ${job.service}`} size="md"
                submitLabel={movable ? "Move here" : "Close"} cancelLabel={movable ? "Cancel" : null}
                busy={busy} onSubmit={movable ? submit : onClose}
                extraActions={movable && job.crew_id ? (
                  <Button type="button" variant="ghost" className="text-destructive" disabled={busy} onClick={() => void takeOff()}>
                    Take off crew member
                  </Button>
                ) : undefined}>
      <DetailList columns={2} items={[
        { label: "Vehicle", value: job.vehicle },
        { label: "Customer", value: job.customer_name },
        { label: "Date", value: dayText(job.date) },
        { label: "Duration", value: `${job.duration_minutes} min` },
        { label: "Status", value: <StatusBadge status={job.status} /> },
        { label: "Now", value: job.crew_name ? `${job.crew_name} at ${job.start_time}` : "Unscheduled" },
        { label: "Finish by", value: job.finish_by },
        ...(job.visit_outcome === "Partially Completed" ? [{
          label: "Visit outcome", wide: true,
          value: `Partially Completed. Delivered ${(job.delivered_services ?? []).join(", ") || "none"} of ${(job.planned_services ?? []).join(", ")}.`,
        }] : []),
      ]} />
      {(job.late || job.manual || job.visit_outcome === "Partially Completed") && <div className="flex gap-2"><JobFlags job={job} /></div>}
      {job.reason && <p className="rounded-md bg-muted px-3 py-2 text-sm text-muted-foreground">{job.reason}</p>}
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
