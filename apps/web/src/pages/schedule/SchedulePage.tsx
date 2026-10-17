import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useSite } from "../../site/SiteContext";
import { useCallback, useState } from "react";

import { api, ApiError } from "../../api/client";
import {
  Button, Card, Dialog, SelectField, StatusChip, Table, Tabs, TextField, useToast,
} from "../../components";
import { DayLanes, JobFlags, JobLabel } from "./Board";
import { ScheduleActions } from "./ScheduleActions";
import { ApiErrorNote } from "../../components/ApiErrorNote";
import {
  daysInMonthFrom, errorText, fmtDate, hhmm, minuteOf, nextSunday, useBoard,
  useNeedsScheduling, weekday,
  type AdminJob, type Board, type RunResult, type ScheduleOut,
} from "./api";
import "./schedule.css";

type Period = "daily" | "weekly" | "monthly";

interface Problem { code: string; message: string }

/** The sections of the page, one tab each. */
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

function freezeText(s: ScheduleOut): string {
  if (s.status === "Frozen") return `Frozen${s.frozen_at ? ` on ${fmtDate(s.frozen_at)}` : ""}`;
  const t = new Date(s.freeze_deadline).toLocaleTimeString("en-IN", {
    hour: "2-digit", minute: "2-digit", hour12: false, timeZone: "Asia/Kolkata",
  });
  return `Freezes by itself at ${t} on ${fmtDate(s.freeze_deadline)}`;
}

export function SchedulePage() {
  const qc = useQueryClient();
  const toast = useToast();

  const site = useSite();
  const societyId = site.id;
  const [startDate, setStartDate] = useState(nextSunday());
  const [chosenPeriod, setPeriod] = useState<Period | null>(null);
  const preferences = useQuery({ queryKey: ["admin-settings"], queryFn: () => api<{key: string; value: string | number}[]>("/v1/admin/directory/settings") });
  const configured = String(preferences.data?.find(p => p.key === "schedule.period")?.value ?? "Weekly").toLowerCase();
  const period: Period = chosenPeriod ?? (configured === "daily" ? "daily" : configured === "monthly" ? "monthly" : "weekly");
  const savePeriod = useMutation({ mutationFn: (value: Period) => api("/v1/admin/directory/settings/schedule.period", { method: "PUT", body: {value: value[0].toUpperCase() + value.slice(1)} }) });
  const [pickedDay, setPickedDay] = useState("");
  // Until the admin picks a tab: the board once there is one, otherwise Run.
  const [chosenTab, setTab] = useState<string | null>(null);
  const [problem, setProblem] = useState<Problem | null>(null);
  const [open, setOpen] = useState<AdminJob | null>(null);
  const [freezing, setFreezing] = useState(false);
  const [unfreezing, setUnfreezing] = useState(false);
  const [code, setCode] = useState("");
  const [codeError, setCodeError] = useState("");

  const boardQ = useBoard(societyId, startDate);
  const needsQ = useNeedsScheduling(societyId);
  const board: Board | null | undefined = boardQ.data;

  const refresh = () => {
    void qc.invalidateQueries({ queryKey: ["board"] });
    void qc.invalidateQueries({ queryKey: ["needs-scheduling"] });
    void qc.invalidateQueries({ queryKey: ["capacity"] });
  };

  const run = useMutation({
    mutationFn: () => api<{ schedules: RunResult[] }>("/v1/admin/scheduling/run", {
      method: "POST",
      body: {
        society_id: societyId || null,
        start_date: periodStart(period, startDate, Number(preferences.data?.find(p => p.key === "schedule.week_start")?.value ?? 6)),
        days: periodDays(period, periodStart(period, startDate, Number(preferences.data?.find(p => p.key === "schedule.week_start")?.value ?? 6))),
      },
    }),
    onSuccess: (r) => {
      setStartDate(periodStart(period, startDate, Number(preferences.data?.find(p => p.key === "schedule.week_start")?.value ?? 6)));
      setProblem(null);
      const sum = (k: "placed" | "unscheduled" | "late") =>
        r.schedules.reduce((n, s) => n + s[k], 0);
      toast.show(
        `Scheduler ran for ${r.schedules.length} ${r.schedules.length === 1 ? "society" : "societies"}: `
        + `${sum("placed")} placed, ${sum("unscheduled")} unscheduled, ${sum("late")} late.`, "ok");
      refresh();
      setTab("board");
    },
    onError: (e) => setProblem({
      code: e instanceof ApiError ? e.code : "error", message: errorText(e),
    }),
  });

  const move = useMutation({
    mutationFn: (v: { job: AdminJob; crewId: string | null; startMinute: number | null }) =>
      api<AdminJob>(`/v1/admin/scheduling/jobs/${v.job.id}/move`, {
        method: "POST", body: { crew_id: v.crewId, start_minute: v.startMinute },
      }),
    onSuccess: (_, v) => {
      setProblem(null);
      setOpen(null);
      toast.show(v.crewId ? "The job is moved." : "The job is taken off its crew member.", "ok");
      refresh();
    },
    onError: (e) => {
      setOpen(null);
      setProblem({ code: e instanceof ApiError ? e.code : "error", message: errorText(e) });
    },
  });

  const freeze = useMutation({
    mutationFn: (id: string) => api<ScheduleOut>(`/v1/admin/scheduling/schedules/${id}/freeze`,
      { method: "POST" }),
    onSuccess: () => {
      setFreezing(false);
      setProblem(null);
      toast.show("The schedule is frozen. Crew can now see it.", "ok");
      refresh();
    },
    onError: (e) => {
      setFreezing(false);
      setProblem({ code: e instanceof ApiError ? e.code : "error", message: errorText(e) });
    },
  });

  const unfreeze = useMutation({
    mutationFn: (v: { id: string; code: string }) =>
      api<ScheduleOut>(`/v1/admin/scheduling/schedules/${v.id}/unfreeze`,
        { method: "POST", body: { code: v.code } }),
    onSuccess: () => {
      setUnfreezing(false);
      setCode("");
      setCodeError("");
      setProblem(null);
      toast.show("The schedule is a draft again.", "ok");
      refresh();
    },
    onError: (e) => setCodeError(errorText(e)),
  });

  const day = board && board.days.some((d) => d.date === pickedDay)
    ? pickedDay : board?.days[0]?.date ?? "";
  const dayJobs = board ? board.jobs.filter((j) => j.date === day) : [];
  const schedule = board?.schedule;
  const tab = chosenTab ?? (board ? "board" : "run");
  const dayAvailability = board?.days.find((d) => d.date === day)?.availability ?? [];

  // The dialogs take stable close handlers: the Dialog refocuses itself
  // whenever `onClose` changes, which would drop focus on every keystroke.
  const closeUnfreeze = useCallback(() => {
    setUnfreezing(false);
    setCode("");
    setCodeError("");
  }, []);
  const closeFreeze = useCallback(() => setFreezing(false), []);
  const closeJob = useCallback(() => setOpen(null), []);

  return (
    <>
      <h1 className="page-title">Schedule</h1>

      {problem && (
        <div className="sch-banner" role="alert" style={{ marginTop: "1rem" }}>
          <span>{problem.message}</span>
          {problem.code === "schedule_frozen" && (
            <Button variant="secondary" onClick={() => setUnfreezing(true)}>
              Unfreeze with code
            </Button>
          )}
        </div>
      )}

      <Tabs tabs={SCHEDULE_TABS(needsQ.data?.length)} active={tab} label="Schedule sections"
            onChange={setTab}>
        {tab === "run" && (
          <>
      <Card title={`Run the scheduler, ${site.name || "no site chosen"}`}>
        <form className="sch-controls" onSubmit={(e) => { e.preventDefault(); run.mutate(); }}>
          <SelectField label="Period" value={period}
                       onChange={(e) => { const value = e.target.value as Period; setPeriod(value); savePeriod.mutate(value); }}>
            <option value="daily">Daily</option>
            <option value="weekly">Weekly</option>
            <option value="monthly">Monthly</option>
          </SelectField>
          <TextField label="Start date" type="date" value={startDate}
                     hint={startDate ? `${weekday(startDate)} ${fmtDate(startDate)}. Weeks start on Sunday.` : undefined}
                     onChange={(e) => { setStartDate(e.target.value); setPickedDay(""); }} />
          <Button type="submit" busy={run.isPending} disabled={!startDate}>
            {board ? "Run again" : "Run scheduler"}
          </Button>
        </form>
        <p className="muted">
          It runs for the chosen site only. A run keeps every change made by hand. On a frozen schedule it places only the jobs
          that have no crew member.
        </p>
        <ApiErrorNote error={savePeriod.error ?? preferences.error} />
      </Card>
          </>
        )}
        {tab === "board" && (
          !societyId ? <p className="muted">Choose a site.</p> : (
            <>
          <Card title="Board">
            {boardQ.isLoading && <p className="loading">Loading...</p>}
            {boardQ.isError && (
              <p className="form-error" role="alert">{errorText(boardQ.error)}</p>
            )}
            {board === null && (
              <p className="table-empty">
                No schedule has been run for this society from {fmtDate(startDate)}. Run the
                scheduler to make a draft.
              </p>
            )}
            {board && schedule && (
              <>
                <div className="sch-status">
                  <strong>{schedule.society_name}</strong>
                  <span>{fmtDate(schedule.start_date)} to {fmtDate(schedule.end_date)}</span>
                  <StatusChip tone={schedule.status === "Frozen" ? "info" : "warn"}>
                    {schedule.status}
                  </StatusChip>
                  <span className="muted">{freezeText(schedule)}</span>
                  {schedule.status === "Draft" ? (
                    <Button onClick={() => setFreezing(true)}>Freeze</Button>
                  ) : (
                    <Button variant="secondary" onClick={() => setUnfreezing(true)}>
                      Unfreeze
                    </Button>
                  )}
                </div>

                <div className="sch-days" role="group" aria-label="Days">
                  {board.days.map((d) => {
                    const left = board.jobs.filter((j) => j.date === d.date && j.crew_id === null).length;
                    return (
                      <button key={d.date} type="button"
                              className={`sch-day${d.over_capacity ? " over" : ""}`}
                              aria-pressed={d.date === day}
                              onClick={() => setPickedDay(d.date)}>
                        {weekday(d.date)} {fmtDate(d.date)}
                        <small>
                          {d.scheduled_minutes}/{d.demand_minutes} min
                          {d.over_capacity ? ", over capacity" : ""}
                          {left > 0 ? `, ${left} unscheduled` : ""}
                        </small>
                      </button>
                    );
                  })}
                </div>

                {schedule.status === "Frozen" && (
                  <p className="muted">
                    This schedule is frozen. Taking a job off needs no code. Moving or adding
                    needs the code.
                  </p>
                )}
                <DayLanes
                  crew={board.crew}
                  jobs={dayJobs}
                  availability={dayAvailability}
                  onOpen={setOpen}
                  onMove={(job, crewId, startMinute) => move.mutate({ job, crewId, startMinute })}
                />
              </>
            )}
          </Card>
            </>
          )
        )}
        {tab === "needs" && (
          <>
        <Card title="Needs scheduling">
          {needsQ.isError && <p className="form-error" role="alert">{errorText(needsQ.error)}</p>}
          {needsQ.data && (
            <Table
              rows={needsQ.data}
              rowKey={(j) => j.id}
              empty="Nothing needs scheduling."
              columns={[
                { key: "d", header: "Date", render: (j) => `${weekday(j.date)} ${fmtDate(j.date)}` },
                { key: "v", header: "Vehicle", render: (j) => <JobLabel job={j} /> },
                { key: "c", header: "Customer", render: (j) => j.customer_name },
                { key: "f", header: "Finish by", render: (j) => j.finish_by ?? "" },
                { key: "r", header: "Reason", render: (j) => j.reason || "No crew member fits." },
                { key: "a", header: "", render: (j) => board && j.schedule_id === board.schedule.id
                  ? <Button variant="ghost" onClick={() => setOpen(j)}>Place</Button> : null },
              ]}
            />
          )}
        </Card>
          </>
        )}
        {tab === "cutoff" && <ScheduleActions section="cutoff" board={board ?? null} refresh={refresh} />}
        {tab === "improve" && <ScheduleActions section="improve" board={board ?? null} refresh={refresh} />}
      </Tabs>

      <JobDialog
        job={open}
        board={board ?? null}
        busy={move.isPending}
        onClose={closeJob}
        onMove={(job, crewId, startMinute) => move.mutate({ job, crewId, startMinute })}
      />

      <Dialog open={freezing} title="Freeze this schedule?" onClose={closeFreeze}
              footer={<>
                <Button variant="secondary" onClick={closeFreeze}>Cancel</Button>
                <Button busy={freeze.isPending}
                        onClick={() => schedule && freeze.mutate(schedule.id)}>Freeze</Button>
              </>}>
        <p>
          Crew see a frozen schedule as their cards. After this, moving or adding work needs
          the code.
        </p>
      </Dialog>

      <Dialog open={unfreezing} title="Unfreeze with the code" onClose={closeUnfreeze}
              footer={<>
                <Button variant="secondary" onClick={closeUnfreeze}>Cancel</Button>
                <Button busy={unfreeze.isPending} disabled={!code}
                        onClick={() => schedule && unfreeze.mutate({ id: schedule.id, code })}>
                  Unfreeze
                </Button>
              </>}>
        <TextField label="Code" value={code} error={codeError || undefined} autoComplete="off"
                   onChange={(e) => { setCode(e.target.value); setCodeError(""); }} />
      </Dialog>
    </>
  );
}

function JobDialog({ job, board, busy, onClose, onMove }: {
  job: AdminJob | null;
  board: Board | null;
  busy: boolean;
  onClose: () => void;
  onMove: (job: AdminJob, crewId: string | null, startMinute: number | null) => void;
}) {
  // Remount the form for each job, so its fields start from that job.
  return (
    <Dialog open={job !== null} title={job ? `${job.registration}, ${job.service}` : ""}
            onClose={onClose}>
      {job && <JobForm key={job.id} job={job} board={board} busy={busy}
                       onClose={onClose} onMove={onMove} />}
    </Dialog>
  );
}

function JobForm({ job, board, busy, onClose, onMove }: {
  job: AdminJob;
  board: Board | null;
  busy: boolean;
  onClose: () => void;
  onMove: (job: AdminJob, crewId: string | null, startMinute: number | null) => void;
}) {
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

  return (
    <>
      <p>
        {job.vehicle} for {job.customer_name}. {fmtDate(job.date)}, {job.duration_minutes} minutes
        {job.finish_by ? `, finish by ${job.finish_by}` : ""}.
      </p>
      <p><JobFlags job={job} /></p>
      {job.reason && <p className="muted">{job.reason}</p>}
      <SelectField label="Crew member" value={crewId} onChange={(e) => setCrewId(e.target.value)}>
        {crew.map((c) => (
          <option key={c.id} value={c.id}>
            {c.name} ({hhmm(c.start_minute)} to {hhmm(c.end_minute)})
          </option>
        ))}
      </SelectField>
      <TextField label="Start time" value={time} placeholder="HH:MM" error={error || undefined}
                 onChange={(e) => setTime(e.target.value)} />
      <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
        <Button busy={busy} onClick={submit}>Move here</Button>
        {job.crew_id && (
          <Button variant="danger" busy={busy} onClick={() => onMove(job, null, null)}>
            Take off crew member
          </Button>
        )}
        <Button variant="secondary" onClick={onClose}>Close</Button>
      </div>
    </>
  );
}
