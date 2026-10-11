import { useRef, useState, type DragEvent } from "react";

import { StatusChip } from "../../components";
import { hhmm, type AdminJob, type SchedulingCrew } from "./api";

/** Pixels for one minute on a crew lane. A 20 minute job is 60 px high. */
export const PX_PER_MIN = 3;
const SNAP = 5;

function isSpa(job: AdminJob): boolean {
  return job.service.toLowerCase().includes("spa");
}

export function JobLabel({ job }: { job: AdminJob }) {
  return (
    <>
      <strong>{job.registration}</strong>
      <span>{job.service}</span>
    </>
  );
}

export function JobFlags({ job }: { job: AdminJob }) {
  return (
    <>
      {job.late && <StatusChip tone="error">Late</StatusChip>}
      {job.manual && <StatusChip tone="info">Changed by hand</StatusChip>}
    </>
  );
}

/**
 * One day of the board: a lane for each crew member. A job is dragged onto a
 * lane, and the drop point gives the start time, snapped to 5 minutes.
 * The unscheduled jobs of the day are dragged from the list below the lanes.
 * Clicking a job opens its dialog, which does the same without a mouse.
 */
export function DayLanes({ crew, jobs, onMove, onOpen }: {
  crew: SchedulingCrew[];
  jobs: AdminJob[];
  onMove: (job: AdminJob, crewId: string, startMinute: number) => void;
  onOpen: (job: AdminJob) => void;
}) {
  const dragging = useRef<AdminJob | null>(null);
  const [over, setOver] = useState<string | null>(null);

  if (crew.length === 0) {
    return <p className="table-empty">No crew is set up for this society.</p>;
  }
  const first = Math.min(...crew.map((c) => c.start_minute));
  const last = Math.max(...crew.map((c) => c.end_minute));
  const height = (last - first) * PX_PER_MIN;
  const ticks: number[] = [];
  for (let m = first; m < last; m += 60) ticks.push(m);

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
    const y = (e.clientY || 0) - e.currentTarget.getBoundingClientRect().top;
    const raw = first + Math.max(0, y) / PX_PER_MIN;
    let start = Math.round(raw / SNAP) * SNAP;
    // Keep the whole job inside this crew member's hours.
    start = Math.min(Math.max(start, member.start_minute), member.end_minute - job.duration_minutes);
    onMove(job, member.id, start);
  };

  return (
    <div>
      <div className="sch-lanes">
        <div className="sch-axis" aria-hidden="true">
          <div style={{ height: "1.9rem" }} />
          <div style={{ position: "relative", height }}>
            {ticks.map((m) => (
              <span key={m} style={{ top: (m - first) * PX_PER_MIN }}>{hhmm(m)}</span>
            ))}
          </div>
        </div>
        {crew.map((member) => {
          const mine = jobs.filter((j) => j.crew_id === member.id && j.start_minute !== null);
          return (
            <div className="sch-lane" key={member.id} data-testid={`lane-${member.id}`}>
              <h3>
                {member.name} <small>{member.role}</small>
              </h3>
              <div
                className="sch-track"
                style={{
                  height,
                  outline: over === member.id ? "2px dashed var(--c-gold)" : undefined,
                  backgroundSize: `100% ${20 * PX_PER_MIN}px`,
                  backgroundImage:
                    "linear-gradient(to bottom, transparent calc(100% - 1px), var(--c-line) 0)",
                }}
                onDragOver={(e) => { e.preventDefault(); setOver(member.id); }}
                onDragLeave={() => setOver((o) => (o === member.id ? null : o))}
                onDrop={drop(member)}
                aria-label={`${member.name}, ${hhmm(member.start_minute)} to ${hhmm(member.end_minute)}`}
              >
                <div className="sch-off"
                     style={{ top: 0, height: (member.start_minute - first) * PX_PER_MIN }} />
                <div className="sch-off"
                     style={{ top: (member.end_minute - first) * PX_PER_MIN,
                              height: (last - member.end_minute) * PX_PER_MIN }} />
                {mine.map((job) => (
                  <div
                    key={job.id}
                    role="button"
                    tabIndex={0}
                    draggable
                    className={`sch-job${job.late ? " late" : ""}${isSpa(job) ? " spa" : ""}${job.manual ? " manual" : ""}`}
                    style={{ top: ((job.start_minute ?? 0) - first) * PX_PER_MIN,
                             height: job.duration_minutes * PX_PER_MIN - 2 }}
                    title={job.reason || undefined}
                    onDragStart={startDrag(job)}
                    onClick={() => onOpen(job)}
                    onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") onOpen(job); }}
                  >
                    <strong>{job.start_time} {job.registration}</strong>
                    <span>{job.service}{job.late ? " (late)" : ""}{job.manual ? " (hand)" : ""}</span>
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>
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
    <section aria-label="Unscheduled on this day" style={{ marginTop: "1rem" }}>
      <h3 style={{ fontSize: "var(--fs-4)" }}>Unscheduled on this day ({jobs.length})</h3>
      {jobs.length === 0 ? (
        <p className="table-empty">Every job of this day has a crew member.</p>
      ) : (
        <ul className="sch-list">
          {jobs.map((job) => (
            <li key={job.id} className="sch-item" draggable onDragStart={startDrag(job)}>
              <JobLabel job={job} />
              <span>{job.customer_name}</span>
              {job.finish_by && <span>Finish by {job.finish_by}</span>}
              <StatusChip tone="warn">Unscheduled</StatusChip>
              <button className="btn btn-ghost" onClick={() => onOpen(job)}>
                Place {job.registration}
              </button>
              {job.reason && <p>{job.reason}</p>}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
