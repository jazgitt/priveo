import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Loader2, Lock, LockOpen, Play, TriangleAlert } from "lucide-react";
import { useState } from "react";
import { useSearchParams } from "react-router-dom";

import { api, ApiError } from "@/api/client";
import { useConfirm } from "@/blocks/confirm";
import { DataTable } from "@/blocks/DataTable";
import { Field, SelectBox } from "@/blocks/fields";
import { FormDialog } from "@/blocks/FormDialog";
import { DetailList, EmptyState, ErrorState, PageHeader, Panel } from "@/blocks/layout";
import { errorMessage, useAppMutation } from "@/blocks/mutation";
import { StatusBadge } from "@/blocks/status";
import { useTasks } from "@/blocks/tasks";
import { Tabs } from "@/components";
import { cn } from "@/lib/utils";
import { useSite } from "@/site/SiteContext";
import { Button } from "@/ui/button";
import { Input } from "@/ui/input";
import { Skeleton } from "@/ui/skeleton";

import { DayLanes, JobFlags, JobLabel, StatusSummary } from "./Board";
import { CutoffRequests, DraftImprovements, PendingAddons } from "./ScheduleActions";
import {
  datesOf, daysInMonthFrom, fmtDate, hhmm, minuteOf, nextSunday, toIso, useBoard, useBoards,
  useNeedsScheduling, useSchedules, weekday,
  type AdminJob, type Board, type RunResult, type ScheduleOut,
} from "./api";
import "./schedule.css";

type Period = "daily" | "weekly" | "monthly";
const PERIODS: { value: Period; label: string }[] = [
  { value: "daily", label: "Daily" }, { value: "weekly", label: "Weekly" }, { value: "monthly", label: "Monthly" },
];

/** How far back the Board offers days (ADM-SCH-35). */
const BOARD_DAYS_BACK = 30;

/** The sections of the page, one tab each (ADM-SCH-32). */
const SCHEDULE_TABS = (waiting?: number) => [
  { id: "run", label: "Run" },
  { id: "board", label: "Board" },
  { id: "needs", label: waiting ? `Needs scheduling (${waiting})` : "Needs scheduling" },
  { id: "cutoff", label: "Cutoff requests" },
  { id: "improve", label: "Draft improvements" },
] as const;

function periodDays(period: Period, start: string): number {
  if (period === "daily") return 1;
  if (period === "monthly") return daysInMonthFrom(start);
  return 7;
}

function periodStart(period: Period, start: string, weekStart: number): string {
  if (period === "monthly") return `${start.slice(0, 7)}-01`;
  if (period !== "weekly") return start;
  const d = new Date(`${start}T00:00:00Z`);
  const mondayDay = (d.getUTCDay() + 6) % 7;
  d.setUTCDate(d.getUTCDate() - (mondayDay - weekStart + 7) % 7);
  return d.toISOString().slice(0, 10);
}

function addDays(iso: string, n: number): string {
  const d = new Date(`${iso}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() + n);
  return d.toISOString().slice(0, 10);
}

const dayText = (iso: string) => `${weekday(iso)} ${fmtDate(iso)}`;

function freezeText(s: ScheduleOut): string {
  if (s.status === "Frozen") return `Frozen${s.frozen_at ? ` on ${fmtDate(s.frozen_at)}` : ""}`;
  const t = new Date(s.freeze_deadline).toLocaleTimeString("en-IN", {
    hour: "2-digit", minute: "2-digit", hour12: false, timeZone: "Asia/Kolkata",
  });
  return `Freezes by itself at ${t} on ${fmtDate(s.freeze_deadline)}`;
}

export function SchedulePage() {
  const qc = useQueryClient();
  const tasks = useTasks();
  const confirm = useConfirm();
  const site = useSite();
  const societyId = site.id;
  // The period start and the tab are in the address, so a finished run can link to its board.
  const [params, setParams] = useSearchParams();
  const startDate = params.get("start") ?? nextSunday();
  const setParam = (key: string, value: string | null) => setParams((p) => {
    const next = new URLSearchParams(p);
    if (value) next.set(key, value); else next.delete(key);
    return next;
  }, { replace: true });

  const preferences = useQuery({ queryKey: ["admin-settings"], queryFn: () => api<{ key: string; value: string | number }[]>("/v1/admin/directory/settings") });
  const configured = String(preferences.data?.find((p) => p.key === "schedule.period")?.value ?? "Weekly").toLowerCase();
  const configuredPeriod: Period = configured === "daily" ? "daily" : configured === "monthly" ? "monthly" : "weekly";
  const [chosenPeriod, setPeriod] = useState<Period | null>(null);
  const period = chosenPeriod ?? configuredPeriod;
  const weekStart = Number(preferences.data?.find((p) => p.key === "schedule.week_start")?.value ?? 6);
  const runStart = startDate ? periodStart(period, startDate, weekStart) : "";
  const runDays = runStart ? periodDays(period, runStart) : 0;

  const [focusStatus, setFocusStatus] = useState("");
  const [problem, setProblem] = useState<{ code: string; message: string; scheduleId: string } | null>(null);
  const [open, setOpen] = useState<AdminJob | null>(null);
  const [unfreezing, setUnfreezing] = useState<ScheduleOut | null>(null);

  // The Board offers every day of the site's schedules from 30 days back, and
  // shows each chosen day as a chart of its own (ADM-SCH-35).
  const today = toIso(new Date());
  const schedulesQ = useSchedules(societyId, addDays(today, -BOARD_DAYS_BACK));
  const scheduleOf = new Map<string, ScheduleOut>();
  // Where two schedules cover a date, the later-starting one (the newer run) shows it.
  for (const s of schedulesQ.data ?? []) for (const d of datesOf(s.start_date, s.end_date)) scheduleOf.set(d, s);
  const allDays = [...scheduleOf.keys()].sort();
  const defaultDay = allDays.find((d) => d >= today) ?? allDays[allDays.length - 1] ?? "";
  const chosen = (params.get("days") ?? "").split(",").filter((d) => scheduleOf.has(d)).sort();
  const selectedDays = chosen.length ? chosen : defaultDay ? [defaultDay] : [];
  const selectedSchedules = [...new Map(selectedDays.map((d) => [scheduleOf.get(d)!.id, scheduleOf.get(d)!])).values()];
  const boardsQ = useBoards(selectedSchedules.map((s) => s.id));
  const boardOf = (scheduleId: string) => boardsQ[selectedSchedules.findIndex((s) => s.id === scheduleId)]?.data;
  /** The board of the first chosen day: Draft improvements and the job dialog use it. */
  const board: Board | null = selectedSchedules[0] ? boardOf(selectedSchedules[0].id) ?? null : null;
  const toggleDay = (d: string) => {
    const next = selectedDays.includes(d) ? selectedDays.filter((x) => x !== d) : [...selectedDays, d].sort();
    setParam("days", (next.length ? next : [d]).join(","));
  };

  const boardQ = useBoard(societyId, startDate);
  const needsQ = useNeedsScheduling(societyId);
  const runBoard: Board | null | undefined = boardQ.data;
  const tab = params.get("tab") ?? (allDays.length ? "board" : "run");
  const runLabel = `Scheduler, ${site.name || "site"}`;
  const running = tasks.isRunning(runLabel);

  const refresh = () => Promise.all([
    qc.invalidateQueries({ queryKey: ["board"] }),
    qc.invalidateQueries({ queryKey: ["schedules"] }),
    qc.invalidateQueries({ queryKey: ["needs-scheduling"] }),
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
          link: { label: "Open board", to: `/schedule?start=${start}&tab=board&days=${start}` },
        };
      },
    }).then(() => {
      setProblem(null);
      setParams({ start, tab: "board", days: start }, { replace: true });
    }, () => { /* The task tray and a toast say why it failed. */ });
  };

  const move = useAppMutation<{ job: AdminJob; crewId: string | null; startMinute: number | null }, AdminJob>({
    mutationFn: (v) => api(`/v1/admin/scheduling/jobs/${v.job.id}/move`, {
      method: "POST", body: { crew_id: v.crewId, start_minute: v.startMinute },
    }),
    pending: "Moving the job…",
    success: (_d, v) => (v.crewId ? `${v.job.registration} moved.` : `${v.job.registration} taken off its crew member.`),
    onSuccess: () => { setProblem(null); setOpen(null); void refresh(); },
    onError: (e, v) => {
      setOpen(null);
      if (e instanceof ApiError && e.code === "schedule_frozen") {
        setProblem({ code: e.code, message: e.message, scheduleId: v.job.schedule_id });
      }
    },
  });

  const freeze = useAppMutation<string>({
    mutationFn: (id) => api(`/v1/admin/scheduling/schedules/${id}/freeze`, { method: "POST" }),
    pending: "Freezing…",
    success: "The schedule is frozen. Crew can now see it.",
    onSuccess: () => { setProblem(null); void refresh(); },
  });

  const askFreeze = async (schedule: ScheduleOut) => {
    if (await confirm({
      title: "Freeze this schedule?",
      description: `${schedule.society_name}, ${fmtDate(schedule.start_date)} to ${fmtDate(schedule.end_date)}. Crew see a frozen schedule as their cards. After this, moving or adding work needs the code.`,
      confirmLabel: "Freeze",
    })) freeze.mutate(schedule.id);
  };

  const jobsOn = (d: string) => boardOf(scheduleOf.get(d)?.id ?? "")?.jobs.filter((j) => j.date === d) ?? [];
  const selectedJobs = selectedDays.flatMap(jobsOn);
  const boardsPending = boardsQ.some((q) => q.isPending);
  const boardsError = boardsQ.find((q) => q.isError)?.error;
  const unfreezeTarget = problem ? (schedulesQ.data ?? []).find((s) => s.id === problem.scheduleId) : undefined;

  return (
    <>
      <PageHeader
        title="Schedule"
        site={site.name || undefined}
        description="Run the scheduler, review and change the draft, then freeze it by 8 PM the day before."
      />

      {/* The state of the schedules of the chosen days, on every tab (ADM-SCH-11, -16, -25). */}
      {societyId && (
        <div className="mb-5 flex flex-col divide-y rounded-xl border bg-card shadow-xs">
          {schedulesQ.isPending ? <div className="px-5 py-3"><Skeleton className="h-6 w-80" /></div>
            : selectedSchedules.length ? selectedSchedules.map((schedule) => (
            <div key={schedule.id} className="flex flex-wrap items-center gap-x-4 gap-y-2 px-5 py-3">
              <span className="font-medium">
                {schedule.start_date === schedule.end_date ? dayText(schedule.start_date)
                  : `${dayText(schedule.start_date)} to ${dayText(schedule.end_date)}`}
              </span>
              <StatusBadge status={schedule.status} />
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
          )) : (
            <span className="px-5 py-3 text-sm text-muted-foreground">
              No schedule for this site yet. Run the scheduler to make a draft.
            </span>
          )}
        </div>
      )}

      {problem && (
        <div role="alert" className="mb-5 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm text-destructive">
          <span className="flex items-center gap-2"><TriangleAlert className="size-4" aria-hidden />{problem.message}</span>
          {problem.code === "schedule_frozen" && unfreezeTarget && (
            <Button variant="outline" size="sm" onClick={() => setUnfreezing(unfreezeTarget)}>Unfreeze with code</Button>
          )}
        </div>
      )}

      <Tabs tabs={SCHEDULE_TABS(needsQ.data?.jobs.length)} active={tab} label="Schedule sections"
            onChange={(t) => setParam("tab", t)}>
        {tab === "run" && (
          <Panel title={`Run the scheduler, ${site.name || "no site chosen"}`}
                 description="It runs for the chosen site only. A run keeps every change made by hand. On a frozen schedule it places only the jobs that have no crew member.">
            <form className="grid grid-cols-1 items-end gap-4 sm:grid-cols-[12rem_12rem_minmax(0,1fr)_auto]"
                  onSubmit={(e) => { e.preventDefault(); if (!running) run(); }}>
              <Field label="Period">
                {(p) => <SelectBox {...p} value={period} onChange={(v) => setPeriod(v as Period)} choices={PERIODS} />}
              </Field>
              <Field label="Start date">
                {(p) => <Input {...p} type="date" value={startDate}
                               onChange={(e) => setParam("start", e.target.value)} />}
              </Field>
              <div className="flex min-h-9 flex-col justify-center text-sm">
                <span className="text-xs font-medium text-muted-foreground">Period to schedule</span>
                <span>{runStart ? `${dayText(runStart)} to ${dayText(addDays(runStart, runDays - 1))}` : "-"}</span>
              </div>
              <Button type="submit" disabled={!startDate || !societyId || running} aria-busy={running || undefined}>
                {running ? <Loader2 className="animate-spin" aria-hidden /> : <Play aria-hidden />}
                {running ? "Running…" : runBoard ? "Run again" : "Run scheduler"}
              </Button>
            </form>
            {period !== configuredPeriod && (
              <p className="mt-3 text-sm text-muted-foreground">
                This run uses {period}; the default is {configuredPeriod}.{" "}
                <Button variant="link" size="sm" className="h-auto p-0" disabled={savePeriod.isPending}
                        onClick={() => savePeriod.mutate(period)}>
                  Make {period} the default
                </Button>
              </p>
            )}
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
          <div className="flex flex-col gap-5">
            {schedulesQ.isPending && <Skeleton className="h-72 w-full" />}
            {schedulesQ.isError && <ErrorState message={errorMessage(schedulesQ.error)} onRetry={() => void schedulesQ.refetch()} />}
            {schedulesQ.data && allDays.length === 0 && (
              <EmptyState title="No schedule yet"
                          action={<Button onClick={() => setParam("tab", "run")}>Go to Run</Button>}>
                No schedule has been run for this society in the last {BOARD_DAYS_BACK} days or after. Run the scheduler to make a draft.
              </EmptyState>
            )}
            {allDays.length > 0 && (
              <>
                <div className="flex flex-col gap-2">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <p className="m-0 text-sm text-muted-foreground">Click days to add or take them off the view. Each chosen day shows as a chart of its own.</p>
                    {(selectedDays.length > 1 || (allDays.includes(today) && selectedDays[0] !== today)) && (
                      <Button size="sm" variant="ghost" onClick={() => setParam("days", allDays.includes(today) ? today : null)}>
                        {allDays.includes(today) ? "Today only" : "Clear"}
                      </Button>
                    )}
                  </div>
                  <div className="grid grid-cols-[repeat(auto-fill,minmax(9.5rem,1fr))] gap-2" role="group" aria-label="Days">
                    {allDays.map((date) => {
                      const s = scheduleOf.get(date)!;
                      const cap = boardOf(s.id)?.days.find((d) => d.date === date);
                      const left = jobsOn(date).filter((j) => j.crew_id === null).length;
                      const on = selectedDays.includes(date);
                      return (
                        <button key={date} type="button" aria-pressed={on} onClick={() => toggleDay(date)}
                                className={cn("flex flex-col items-start rounded-lg border bg-card px-3 py-2 text-left transition-colors hover:bg-accent",
                                  date < today && "bg-muted/50",
                                  on && "border-foreground bg-card shadow-[inset_0_-2px_0_var(--c-gold)]")}>
                          <span className="text-sm font-medium">{dayText(date)}{date === today ? " · Today" : ""}</span>
                          <span className="text-xs text-muted-foreground">{s.status}</span>
                          {cap && (
                            <span className={cn("text-xs text-muted-foreground", cap.over_capacity && "text-destructive")}>
                              {cap.scheduled_minutes}/{cap.demand_minutes} min{cap.over_capacity ? ", over capacity" : ""}
                            </span>
                          )}
                          {left > 0 && <span className="text-xs font-medium text-[#9a6513]">{left} unscheduled</span>}
                        </button>
                      );
                    })}
                  </div>
                </div>
                {boardsError ? <ErrorState message={errorMessage(boardsError)} onRetry={() => void refresh()} /> : null}
                {boardsPending && <Skeleton className="h-72 w-full" />}
                {!boardsPending && (
                  <>
                    <StatusSummary jobs={selectedJobs} focus={focusStatus} onFocus={setFocusStatus} />
                    {selectedDays.map((date) => {
                      const s = scheduleOf.get(date)!;
                      const b = boardOf(s.id);
                      if (!b) return null;
                      return (
                        <section key={date} aria-label={dayText(date)} className="flex flex-col gap-2">
                          {selectedDays.length > 1 && (
                            <h3 className="m-0 flex items-center gap-2 text-sm font-semibold">
                              {dayText(date)} <StatusBadge status={s.status} />
                            </h3>
                          )}
                          {s.status === "Frozen" && (
                            <p className="m-0 text-sm text-muted-foreground">This schedule is frozen. Taking a job off needs no code. Moving or adding needs the code.</p>
                          )}
                          <DayLanes crew={b.crew} jobs={jobsOn(date)} focus={focusStatus} onOpen={setOpen}
                                    availability={b.days.find((d) => d.date === date)?.availability ?? []}
                                    onMove={(job, crewId, startMinute) => move.mutate({ job, crewId, startMinute })} />
                        </section>
                      );
                    })}
                  </>
                )}
              </>
            )}
          </div>
        ))}

        {tab === "needs" && (
          <div className="flex flex-col gap-6">
            <Panel title="Needs scheduling" description="Visits left without a crew member after the freeze, or that no crew member fits (ADM-SCH-28)." bodyClassName="p-0">
              {needsQ.isError ? <div className="p-4"><ErrorState message={errorMessage(needsQ.error)} /></div> : (
                <DataTable
                  className="[&>div]:rounded-none [&>div]:border-0"
                  rows={needsQ.data?.jobs}
                  loading={needsQ.isPending}
                  rowKey={(j) => j.id}
                  empty={<p className="text-sm text-muted-foreground">Nothing needs scheduling.</p>}
                  columns={[
                    { key: "d", header: "Date", width: "9rem", cell: (j) => dayText(j.date) },
                    { key: "v", header: "Vehicle", width: "14rem", cell: (j) => <JobLabel job={j} /> },
                    { key: "c", header: "Customer", width: "12rem", cell: (j) => j.customer_name },
                    { key: "f", header: "Finish by", width: "6rem", cell: (j) => j.finish_by ?? "-" },
                    { key: "r", header: "Reason", wrap: true, cell: (j) => j.reason || "No crew member fits." },
                    { key: "a", header: "", width: "6rem", align: "right", cell: (j) => (board
                      ? <Button size="sm" variant="outline" onClick={() => setOpen(j)}>Place</Button> : null) },
                  ]}
                />
              )}
            </Panel>
            <PendingAddons addons={needsQ.data?.pending_addons ?? []} />
          </div>
        )}
        {tab === "cutoff" && <CutoffRequests refresh={refresh} />}
        {tab === "improve" && <DraftImprovements board={board ?? null} refresh={refresh} />}
      </Tabs>

      {open && (
        <JobDialog key={open.id} job={open} board={boardOf(open.schedule_id) ?? board} busy={move.isPending} onClose={() => setOpen(null)}
                   onMove={(job, crewId, startMinute) => move.mutate({ job, crewId, startMinute })} />
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
  return (
    <FormDialog open onOpenChange={(o) => !o && onClose()} title="Unfreeze with the code" size="sm"
                description="The schedule becomes a draft so work can be added or moved. Crew keep seeing it until you change it."
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
      description: "The job goes to the unscheduled list of its day. You can place it again later.",
      confirmLabel: "Take off crew member", tone: "danger",
    })) onMove(job, null, null);
  };

  return (
    <FormDialog open onOpenChange={(o) => !o && onClose()} title={`${job.registration}, ${job.service}`} size="md"
                submitLabel="Move here" busy={busy} onSubmit={submit}
                extraActions={job.crew_id ? (
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
      ]} />
      {(job.late || job.manual) && <div className="flex gap-2"><JobFlags job={job} /></div>}
      {job.reason && <p className="rounded-md bg-muted px-3 py-2 text-sm text-muted-foreground">{job.reason}</p>}
      <div className="grid grid-cols-1 gap-4 border-t pt-4 sm:grid-cols-[minmax(0,1fr)_9rem]">
        <Field label="Crew member">
          {(p) => <SelectBox {...p} value={crewId} onChange={setCrewId}
                             choices={crew.map((c) => ({ value: c.id, label: `${c.name} (${hhmm(c.start_minute)} to ${hhmm(c.end_minute)})` }))} />}
        </Field>
        <Field label="Start time" error={error || undefined}>
          {(p) => <Input {...p} type="time" step={300} value={time} onChange={(e) => setTime(e.target.value)} />}
        </Field>
      </div>
    </FormDialog>
  );
}
