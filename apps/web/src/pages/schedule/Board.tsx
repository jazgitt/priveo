import { useEffect, useRef, useState, type DragEvent } from "react";

import { Button } from "@/ui/button";

import { StatusBadge } from "@/blocks/status";

import { HoverTip } from "../../components";
import { hhmm, type AdminJob, type CrewDayAvailability, type SchedulingCrew } from "./api";

/** Pixels for one minute along the time ruler. A 20 minute job is 80 px wide. */
export const PX_PER_MIN = 4;
const SNAP = 5;
/** The chart shows 05:00 to 22:00 unless the day needs more. */
const DAY_START = 5 * 60;
const DAY_END = 22 * 60;

const CODES: Record<string, string> = {
  "Cleaning-External": "EXT", "Cleaning-Internal": "INT", "Deep Spa": "SPA",
};

/** EXT, INT or SPA for a service. */
export function serviceCode(service: string): string {
  return CODES[service] ?? service.replace(/[^A-Za-z]/g, "").slice(0, 3).toUpperCase();
}

/** "EXT,HR26AB2324,B1-24": service code, vehicle number and parking place. */
export function jobLabel(job: AdminJob): string {
  return `${serviceCode(job.service)},${job.registration},${job.parking || "-"}`;
}

function isSpa(job: AdminJob): boolean {
  return job.service.toLowerCase().includes("spa");
}

/** The job statuses in the order the work moves through them. */
export const JOB_STATUSES = ["Scheduled", "In progress", "Completed", "Skipped", "Could not complete"] as const;

/** The fill of a job on the chart: green when completed, red when it could not be done (ADM-SCH-34). */
function statusClass(job: AdminJob): string {
  if (job.status === "Completed") return " done";
  if (job.status === "Could not complete") return " failed";
  return "";
}

/**
 * How many of the day's jobs are in each status. Pressing a status keeps only
 * its jobs bright on the chart; pressing it again shows all (ADM-SCH-34).
 */
export function StatusSummary({ jobs, focus, onFocus }: {
  jobs: AdminJob[];
  focus: string;
  onFocus: (status: string) => void;
}) {
  const counts = new Map<string, number>();
  for (const j of jobs) counts.set(j.status, (counts.get(j.status) ?? 0) + 1);
  const shown = [...JOB_STATUSES.filter((s) => counts.has(s)),
    ...[...counts.keys()].filter((s) => !(JOB_STATUSES as readonly string[]).includes(s))];
  const chip = (status: string, label: string, n: number) => (
    <button key={status || "all"} type="button" aria-pressed={focus === status}
            onClick={() => onFocus(focus === status ? "" : status)}
            className={`sch-chip${status ? ` st-${status.toLowerCase().replace(/ /g, "-")}` : ""}`}>
      {label} <b>{n}</b>
    </button>
  );
  return (
    <div className="flex flex-wrap items-center gap-2" role="group" aria-label="Job status">
      {chip("", "All jobs", jobs.length)}
      {shown.map((s) => chip(s, s, counts.get(s) ?? 0))}
    </div>
  );
}

export function JobLabel({ job }: { job: AdminJob }) {
  return (
    <span className="flex min-w-0 flex-col">
      <strong className="truncate reg text-[0.8125rem]">{job.registration}</strong>
      <span className="truncate text-xs text-muted-foreground">{job.service}{job.parking ? ` · ${job.parking}` : ""}</span>
    </span>
  );
}

export function JobFlags({ job }: { job: AdminJob }) {
  return (
    <>
      {job.late && <StatusBadge status="Late" tone="error" />}
      {job.manual && <StatusBadge status="Changed by hand" tone="info" />}
    </>
  );
}

interface Win { start: number; end: number }

/** The windows a member can take work in on the day shown. */
function windowsOf(member: SchedulingCrew, avail: CrewDayAvailability | undefined): Win[] {
  return avail ? avail.windows : [{ start: member.start_minute, end: member.end_minute }];
}

/** The stretches of [first, last) that lie outside every window. */
function gaps(wins: Win[], first: number, last: number): Win[] {
  const out: Win[] = [];
  let at = first;
  for (const w of [...wins].sort((a, b) => a.start - b.start)) {
    if (w.start > at) out.push({ start: at, end: Math.min(w.start, last) });
    at = Math.max(at, w.end);
  }
  if (at < last) out.push({ start: at, end: last });
  return out;
}

/** Why the jobs of a lane are where they are: hours, load and the scheduler notes. */
function Reasoning({ member, avail, jobs }: {
  member: SchedulingCrew; avail: CrewDayAvailability | undefined; jobs: AdminJob[];
}) {
  const wins = windowsOf(member, avail);
  const available = wins.reduce((n, w) => n + (w.end - w.start), 0);
  const booked = jobs.reduce((n, j) => n + j.duration_minutes, 0);
  const byService = new Map<string, number>();
  for (const j of jobs) byService.set(j.service, (byService.get(j.service) ?? 0) + 1);
  const notes = jobs.filter((j) => j.reason).slice(0, 5);
  return (
    <>
      <strong>{member.name}, {member.role}</strong>
      <span className="cap-tip-row"><span>{avail?.reason ?? "Works the hours shown."}</span></span>
      {wins.length > 0 && (
        <span className="cap-tip-row"><span>Slots</span>
          <b>{wins.map((w) => `${hhmm(w.start)}-${hhmm(w.end)}`).join(", ")}</b></span>
      )}
      <span className="cap-tip-row"><span>Booked</span>
        <b>{booked} of {available} min, {jobs.length} {jobs.length === 1 ? "job" : "jobs"}</b></span>
      {[...byService].map(([service, n]) => (
        <span key={service} className="cap-tip-row"><span>{service}</span><b>{n}</b></span>
      ))}
      <small className="cap-tip-why">
        {jobs.length === 0
          ? (avail?.status === "Off" ? "Cannot take work this day." : "No job was given to this member.")
          : "Jobs were placed inside these slots, in time order, within each finish-by time."}
      </small>
      {notes.map((j) => (
        <small key={j.id} className="cap-tip-why">{j.start_time} {j.registration}: {j.reason}</small>
      ))}
    </>
  );
}

/**
 * The day as a Gantt chart: the time ruler on top (05:00 to 22:00, a tick every
 * 30 minutes), then one row for each crew member with that member's jobs placed
 * on the ruler. A job is dragged onto a row, and the drop point gives the start
 * time, snapped to 5 minutes. The unscheduled jobs of the day are dragged from
 * the list below the chart. Clicking a job opens its dialog, which does the same
 * without a mouse. Time a crew member cannot work (day off, exception, between
 * slots) is greyed out and takes no job. Hovering a name gives the reasoning
 * (ADM-SCH-32, ADM-SCH-33).
 */
export function DayLanes({ crew, jobs, availability = [], focus = "", onMove, onOpen }: {
  crew: SchedulingCrew[];
  jobs: AdminJob[];
  availability?: CrewDayAvailability[];
  /** A job status to pick out; jobs in other statuses are dimmed. Empty shows all. */
  focus?: string;
  onMove: (job: AdminJob, crewId: string, startMinute: number) => void;
  onOpen: (job: AdminJob) => void;
}) {
  const dragging = useRef<AdminJob | null>(null);
  const chart = useRef<HTMLDivElement>(null);
  const [over, setOver] = useState<string | null>(null);
  const [blocked, setBlocked] = useState("");
  // Open the chart a little before the day's first job, not at 05:00.
  const firstJob = Math.min(...jobs.map((j) => j.start_minute ?? Infinity));
  useEffect(() => {
    if (chart.current && Number.isFinite(firstJob)) {
      chart.current.scrollLeft = Math.max(0, (firstJob - DAY_START - 30) * PX_PER_MIN);
    }
  }, [firstJob]);

  if (crew.length === 0) {
    return <p className="text-sm text-muted-foreground">No crew is set up for this society.</p>;
  }
  // 05:00 to 22:00, wider only when a crew member or a job lies outside it.
  const edges = [...crew.flatMap((c) => [c.start_minute, c.end_minute]),
    ...jobs.flatMap((j) => (j.start_minute === null ? [] : [j.start_minute, j.start_minute + j.duration_minutes]))];
  const first = Math.floor(Math.min(DAY_START, ...edges) / 30) * 30;
  const last = Math.ceil(Math.max(DAY_END, ...edges) / 30) * 30;
  const width = (last - first) * PX_PER_MIN;
  const ticks: number[] = [];
  for (let m = first; m <= last; m += 30) ticks.push(m);

  const startDrag = (job: AdminJob) => (e: DragEvent) => {
    dragging.current = job;
    e.dataTransfer?.setData("text/plain", job.id);
    if (e.dataTransfer) e.dataTransfer.effectAllowed = "move";
  };

  const drop = (member: SchedulingCrew) => (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setOver(null);
    const job = dragging.current;
    dragging.current = null;
    if (!job) return;
    const avail = availability.find((a) => a.crew_id === member.id);
    const x = (e.clientX || 0) - e.currentTarget.getBoundingClientRect().left;
    const raw = first + Math.max(0, x) / PX_PER_MIN;
    // Only a slot the member works can take the job.
    const win = windowsOf(member, avail).find((w) => raw >= w.start && raw < w.end);
    if (!win || win.end - win.start < job.duration_minutes) {
      setBlocked(`${member.name} cannot take work there. ${avail?.reason ?? ""}`.trim());
      return;
    }
    setBlocked("");
    let start = Math.round(raw / SNAP) * SNAP;
    // Keep the whole job inside that slot.
    start = Math.min(Math.max(start, win.start), win.end - job.duration_minutes);
    onMove(job, member.id, start);
  };

  const grid = {
    backgroundSize: `${30 * PX_PER_MIN}px 100%`,
    backgroundImage: "linear-gradient(to right, var(--c-line) 1px, transparent 1px)",
  };

  return (
    <div>
      <div className="sch-gantt" role="group" aria-label="Day plan" ref={chart}>
        <div className="sch-g-row sch-g-head">
          <div className="sch-g-name">Crew</div>
          <div className="sch-g-track sch-g-ruler" style={{ width }} aria-hidden="true">
            {ticks.map((m) => (
              <span key={m} className={m % 60 === 0 ? "hour" : "half"}
                    style={{ left: (m - first) * PX_PER_MIN }}>
                {m % 60 === 0 ? hhmm(m) : ""}
              </span>
            ))}
          </div>
        </div>
        {crew.map((member) => {
          const mine = jobs.filter((j) => j.crew_id === member.id && j.start_minute !== null);
          const avail = availability.find((a) => a.crew_id === member.id);
          const closed = avail?.status === "Off";
          return (
            <div className={`sch-g-row sch-lane${closed ? " closed" : ""}`} key={member.id}
                 data-testid={`lane-${member.id}`}>
              <div className="sch-g-name">
                <HoverTip label={<>{member.name} <small>{member.role}</small></>}
                          ariaLabel={`${member.name}, ${member.role}. Hover for how jobs are allocated.`}>
                  <Reasoning member={member} avail={avail} jobs={mine} />
                </HoverTip>
              </div>
              <div
                className="sch-g-track sch-track"
                style={{
                  width, ...grid,
                  outline: over === member.id ? "2px dashed var(--c-gold)" : undefined,
                }}
                onDragOver={(e) => { e.preventDefault(); setOver(member.id); }}
                onDragLeave={() => setOver((o) => (o === member.id ? null : o))}
                onDrop={drop(member)}
                aria-label={`${member.name}, ${hhmm(member.start_minute)} to ${hhmm(member.end_minute)}`}
              >
                {gaps(windowsOf(member, avail), first, last).map((g) => (
                  <div key={g.start} className="sch-off" data-testid="grey"
                       title={avail?.reason}
                       style={{ left: (g.start - first) * PX_PER_MIN,
                                width: (g.end - g.start) * PX_PER_MIN }}>
                    {closed && g.start === first && <span>{avail?.reason}</span>}
                  </div>
                ))}
                {mine.map((job) => {
                  const label = jobLabel(job);
                  return (
                    <div
                      key={job.id}
                      role="button"
                      tabIndex={0}
                      draggable
                      aria-label={label}
                      className={`sch-job${job.late ? " late" : ""}${isSpa(job) ? " spa" : ""}${job.manual ? " manual" : ""}${statusClass(job)}${focus && job.status !== focus ? " dim" : ""}`}
                      style={{ left: ((job.start_minute ?? 0) - first) * PX_PER_MIN,
                               width: job.duration_minutes * PX_PER_MIN - 2 }}
                      title={`${job.start_time}-${job.end_time} ${label}. ${job.status}${job.reason ? `. ${job.reason}` : ""}`}
                      onDragStart={startDrag(job)}
                      onClick={() => onOpen(job)}
                      onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") onOpen(job); }}
                    >
                      <strong>{serviceCode(job.service)}</strong>
                      <span>{job.registration}</span>
                      <span>{job.parking || "-"}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>
      {blocked && <p className="mt-2 mb-0 text-sm text-destructive" role="alert">{blocked}</p>}
      <UnscheduledList jobs={jobs.filter((j) => j.crew_id === null)} onOpen={onOpen}
                       startDrag={startDrag} />
    </div>
  );
}

function UnscheduledList({ jobs, onOpen, startDrag }: {
  jobs: AdminJob[];
  onOpen: (job: AdminJob) => void;
  startDrag: (job: AdminJob) => (e: DragEvent) => void;
}) {
  return (
    <section aria-label="Unscheduled on this day" className="mt-5">
      <h3 className="mt-0 mb-2 text-sm font-semibold">Unscheduled on this day ({jobs.length})</h3>
      {jobs.length === 0 ? (
        <p className="text-sm text-muted-foreground">Every job of this day has a crew member.</p>
      ) : (
        <>
          <p className="mt-0 mb-2 text-xs text-muted-foreground">Drag a job onto a crew row, or press Place.</p>
          <ul className="m-0 flex list-none flex-col divide-y rounded-lg border bg-card p-0">
            {jobs.map((job) => (
              <li key={job.id} draggable onDragStart={startDrag(job)}
                  className="grid cursor-grab grid-cols-1 items-start gap-x-4 gap-y-1 border-l-4 border-l-warn px-4 py-2.5 sm:grid-cols-[13rem_10rem_7rem_minmax(0,1fr)_auto]">
                <JobLabel job={job} />
                <span className="truncate text-sm">{job.customer_name}</span>
                <span className="text-sm text-muted-foreground">{job.finish_by ? `Finish by ${job.finish_by}` : "-"}</span>
                <span className="text-sm text-muted-foreground">{job.reason}</span>
                <span className="flex items-center gap-2 sm:justify-end">
                  <StatusBadge status="Unscheduled" tone="warn" />
                  <Button size="sm" variant="outline" onClick={() => onOpen(job)}>Place {job.registration}</Button>
                </span>
              </li>
            ))}
          </ul>
        </>
      )}
    </section>
  );
}
