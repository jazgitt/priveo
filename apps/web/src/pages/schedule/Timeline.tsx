import { useState, type CSSProperties } from "react";

import { cn } from "@/lib/utils";

import { gaps, isSpa, isUnplaced, jobLabel, matches, minutesOf, serviceCode, statusClass, windowsOf } from "./Board";
import { Scroller } from "./Scroller";
import { hhmm, type AdminJob, type CrewDayAvailability, type SchedulingCrew } from "./api";

/** The timeline opens at 05:00 and closes at 22:00 when the day has no hours to go by. */
const DAY_START = 5 * 60;
const DAY_END = 22 * 60;

interface Tip { job: AdminJob; x: number; y: number }

/**
 * The chosen day as a compact, view-only Gantt chart: one thin row for each
 * crew member against an hour ruler that spans the day's working hours, so a
 * large crew fits on one screen. Each job is a small block at its start time,
 * as wide as its duration and coloured by its status. Hovering or focusing a
 * block shows its details. Nothing can be moved here (ADM-SCH-33).
 */
export function Timeline({ crew, jobs, availability, focus, search, now }: {
  crew: SchedulingCrew[];
  jobs: AdminJob[];
  availability: CrewDayAvailability[];
  focus: string;
  search: string;
  /** Minutes after midnight when the day shown is today, for the now line. */
  now?: number;
}) {
  const [tip, setTip] = useState<Tip | null>(null);
  if (crew.length === 0) {
    return <p className="text-sm text-muted-foreground">No crew is set up for this site.</p>;
  }
  const availOf = (id: string) => availability.find((a) => a.crew_id === id);
  const placed = jobs.filter((j) => j.crew_id && j.start_minute !== null);
  const edges = [
    ...crew.flatMap((c) => windowsOf(c, availOf(c.id)).flatMap((w) => [w.start, w.end])),
    ...placed.flatMap((j) => [j.start_minute!, j.start_minute! + j.duration_minutes]),
  ];
  const first = edges.length ? Math.floor(Math.min(...edges) / 60) * 60 : DAY_START;
  const last = Math.max(first + 4 * 60, edges.length ? Math.ceil(Math.max(...edges) / 60) * 60 : DAY_END);
  const span = last - first;
  const pos = (m: number) => `${((m - first) / span) * 100}%`;
  const len = (m: number) => `${(m / span) * 100}%`;
  const hours: number[] = [];
  for (let m = first; m <= last; m += 60) hours.push(m);
  const grid: CSSProperties = {
    backgroundImage: "linear-gradient(to right, var(--c-line) 1px, transparent 1px)",
    backgroundSize: `${(30 / span) * 100}% 100%`,
  };
  const unplaced = jobs.filter(isUnplaced).length;

  const show = (job: AdminJob, el: HTMLElement) => {
    const r = el.getBoundingClientRect();
    setTip({ job, x: Math.min(r.left, window.innerWidth - 300), y: r.bottom + 6 });
  };

  return (
    <div>
      <Scroller className="sch-tl" role="group" aria-label="Day timeline">
        <div className="sch-tl-row sch-tl-head">
          <div className="sch-tl-name">Crew <span>booked/available</span></div>
          <div className="sch-tl-track" aria-hidden>
            {hours.map((m) => (
              <span key={m} className="sch-tl-hour" style={{ left: pos(m) }}>{m < last ? hhmm(m) : ""}</span>
            ))}
          </div>
        </div>
        {crew.map((member) => {
          const avail = availOf(member.id);
          const wins = windowsOf(member, avail);
          const mine = placed.filter((j) => j.crew_id === member.id);
          const booked = mine.reduce((n, j) => n + j.duration_minutes, 0);
          const closed = avail?.status === "Off";
          return (
            <div key={member.id} className={cn("sch-tl-row", closed && "closed")} data-testid={`row-${member.id}`}>
              <div className="sch-tl-name" title={`${member.name}, ${member.role}. ${avail?.reason ?? ""}`.trim()}>
                <span className="truncate">{member.name}</span>
                <span className="tabular-nums">{closed ? "Off" : `${booked}/${minutesOf(wins)}`}</span>
              </div>
              <div className="sch-tl-track" style={grid}>
                {gaps(wins, first, last).map((g) => (
                  <div key={g.start} className="sch-off" data-testid="grey" title={avail?.reason}
                       style={{ left: pos(g.start), width: len(g.end - g.start) }} />
                ))}
                {mine.map((job) => (
                  <div key={job.id} tabIndex={0} aria-label={`${job.start_time}-${job.end_time} ${jobLabel(job)}, ${job.status}`}
                       aria-describedby={tip?.job.id === job.id ? "sch-tl-tip" : undefined}
                       className={cn("sch-tl-job", statusClass(job), isSpa(job) && "spa", job.late && "late",
                         !matches(job, focus, search) && "dim")}
                       style={{ left: pos(job.start_minute!), width: len(job.duration_minutes) }}
                       onMouseEnter={(e) => show(job, e.currentTarget)} onMouseLeave={() => setTip(null)}
                       onFocus={(e) => show(job, e.currentTarget)} onBlur={() => setTip(null)}>
                    <span>{serviceCode(job.service)}</span>
                  </div>
                ))}
                {now !== undefined && now >= first && now <= last && (
                  <div className="sch-tl-now" style={{ left: pos(now) }} aria-hidden />
                )}
              </div>
            </div>
          );
        })}
      </Scroller>
      <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted-foreground" aria-label="Legend">
        <span className="sch-legend"><i className="sch-tl-job" /> Scheduled</span>
        <span className="sch-legend"><i className="sch-tl-job active" /> In progress</span>
        <span className="sch-legend"><i className="sch-tl-job done" /> Completed</span>
        <span className="sch-legend"><i className="sch-tl-job failed" /> Could not complete</span>
        <span className="sch-legend"><i className="sch-tl-job spa" /> Deep Spa</span>
        <span className="sch-legend"><i className="sch-tl-job late" /> Late</span>
        <span className="sch-legend"><i className="sch-off-key" /> Cannot work</span>
        {unplaced > 0 && <span className="font-medium text-[#9a6513]">{unplaced} unscheduled, not on the timeline</span>}
      </div>
      {tip && <JobTip tip={tip} />}
    </div>
  );
}

function JobTip({ tip: { job, x, y } }: { tip: Tip }) {
  const fitsBelow = y + 200 < window.innerHeight;
  return (
    <div id="sch-tl-tip" role="tooltip" className="sch-tl-tip"
         style={{ left: Math.max(8, x), ...(fitsBelow ? { top: y } : { bottom: window.innerHeight - y + 30 }) }}>
      <strong>{job.start_time}-{job.end_time} · {serviceCode(job.service)} · <span className="reg">{job.registration}</span></strong>
      <span className="cap-tip-row"><span>Vehicle</span><b>{job.vehicle}</b></span>
      <span className="cap-tip-row"><span>Parking</span><b>{job.parking || "-"}</b></span>
      <span className="cap-tip-row"><span>Customer</span><b>{job.customer_name}</b></span>
      <span className="cap-tip-row"><span>Crew member</span><b>{job.crew_name ?? "-"}</b></span>
      <span className="cap-tip-row"><span>Status</span><b>{job.status}</b></span>
      {job.finish_by && <span className="cap-tip-row"><span>Finish by</span><b>{job.finish_by}</b></span>}
      {(job.late || job.manual) && (
        <span className="cap-tip-row"><span>Flags</span><b>{[job.late && "Late", job.manual && "Changed by hand"].filter(Boolean).join(", ")}</b></span>
      )}
      {job.reason && <small className="cap-tip-why">{job.reason}</small>}
    </div>
  );
}
