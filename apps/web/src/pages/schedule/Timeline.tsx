import type { QueryKey } from "@tanstack/react-query";
import { useRef, useState, type CSSProperties, type PointerEvent as ReactPointerEvent } from "react";

import { cn } from "@/lib/utils";

import {
  breached, gaps, isOpen, isShown, isSpa, isUnplaced, jobLabel, matches, minutesOf, serviceCode, statusClass, typeClass, windowsOf, zonesOf,
  type Density,
} from "./Board";
import { CardFace } from "./CardBoard";
import {
  DragEngineProvider, minuteAt, movesFor, planFreeDrop, useDragSource,
  type DragItem, type DropHit, type DropOutcome, type LaneCard,
} from "./dnd";
import { Scroller } from "./Scroller";
import { hhmm, type AdminJob, type CrewDayAvailability, type SchedulingCrew } from "./api";

/** The timeline opens at 05:00 and closes at 22:00 when the day has no hours to go by. */
const DAY_START = 5 * 60;
const DAY_END = 22 * 60;
/**
 * One minute on the timeline, in rem. The ruler and every block use this one scale,
 * so a block is as long as its job and sits under its own time on the ruler (ux9).
 * The track is this wide at every layout, so a short job keeps its whole card in view.
 */
export const REM_PER_MINUTE = 0.8;

interface Tip { job: AdminJob; x: number; y: number }

/** What a dragged timeline block carries: the job, and the grab point in px from the block's left edge. */
interface TimelineDrag {
  job: AdminJob;
  grab: { dx: number };
}

/** The root font size in px, which is what one rem is on the timeline. */
function remPx(): number {
  const px = parseFloat(getComputedStyle(document.documentElement).fontSize);
  return Number.isFinite(px) && px > 0 ? px : 16;
}

/** A job as the drag engine's geometry sees it: its start and its length in minutes. */
function laneCardOf(job: AdminJob): LaneCard {
  return { id: job.id, start: job.start_minute ?? 0, duration: job.duration_minutes };
}

/**
 * The chosen day as a Gantt chart: one thin row for each
 * crew member against an hour ruler that spans the day's working hours, so a
 * large crew fits on one screen. Each job is a small block at its start time,
 * as wide as its duration and coloured by its status. Hovering or focusing a
 * block shows its details. A block can be dragged along the time axis (snapped to
 * 5 minutes, decision 10) and onto another crew row, with the same drop rules as the
 * Cards view (P0-6). The filters hide the blocks they do not keep; "Show all" brings
 * them back in disabled form (P1-4).
 */
export function Timeline({ crew, jobs, availability, focus, search, type = "", flag = "", density = "standard", showAll = false, now, boardKey }: {
  crew: SchedulingCrew[];
  jobs: AdminJob[];
  availability: CrewDayAvailability[];
  /** The board query the drop refreshes and the other tabs of this browser re-read (P0-9). */
  boardKey: QueryKey;
  focus: string;
  search: string;
  /** EXT, INT or SPA keeps only that kind bright; empty shows all. */
  type?: string;
  /** "late" or "manual" keeps only those jobs bright; empty shows all. */
  flag?: string;
  /** How much a block shows, as on the cards: compact, standard or detailed. */
  density?: Density;
  /** Off, the filters hide the blocks they do not keep; on, those blocks show in disabled form (P1-4). */
  showAll?: boolean;
  /** Minutes after midnight when the day shown is today, for the now line. */
  now?: number;
}) {
  const [tip, setTip] = useState<Tip | null>(null);
  const zones = zonesOf(jobs);
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
  // Percentages of the track, which is span * REM_PER_MINUTE wide on the ruler and on every row.
  const pos = (m: number) => `${((m - first) / span) * 100}%`;
  const len = (m: number) => `${(m / span) * 100}%`;
  const trackWidth = `${span * REM_PER_MINUTE}rem`;
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

  // A drop on a crew row (P0-6). The block starts where its left edge is on the time axis,
  // snapped to 5 minutes. The same planner as the Cards view decides the other moves (P0-5, P0-7).
  const planDrop = (drop: DropHit, item: DragItem): DropOutcome => {
    const { job: dragged, grab } = item.data as TimelineDrag;
    const member = crew.find((c) => c.id === drop.laneId);
    if (!member) return null;
    const track = drop.laneEl.querySelector<HTMLElement>(".sch-tl-track") ?? drop.laneEl;
    const blockLeft = drop.clientX - grab.dx;
    const minute = minuteAt(blockLeft, { top: track.getBoundingClientRect().left, pxPerMinute: REM_PER_MINUTE * remPx(), dayStart: first });
    const lane = placed.filter((j) => j.crew_id === member.id).map(laneCardOf);
    // The drop position among the row's blocks: the blocks that start before the drop come first.
    const index = lane.filter((c) => c.id !== dragged.id && c.start < minute).length;
    const startTop = windowsOf(member, availOf(member.id))[0]?.start ?? first;
    const plan = planFreeDrop(lane, laneCardOf(dragged), minute, index, { top: startTop });
    if (member.id === dragged.crew_id && plan.start === dragged.start_minute && plan.shifts.length === 0) return null;
    return { moves: movesFor(member.id, dragged.id, plan) };
  };

  return (
    <DragEngineProvider boardKey={boardKey} plan={planDrop}>
    <div className="sch-fill">
      <Scroller className={cn("sch-tl", density)} role="group" aria-label="Day timeline">
        <div className="sch-tl-row sch-tl-head">
          <div className="sch-tl-name">Crew <span>booked/available</span></div>
          <div className="sch-tl-track" style={{ width: trackWidth }} aria-hidden>
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
            <div key={member.id} className={cn("sch-tl-row", closed && "closed")} data-testid={`row-${member.id}`} data-dnd-lane={member.id}>
              <div className="sch-tl-name" title={`${member.name}, ${member.role}. ${avail?.reason ?? ""}`.trim()}>
                <span className="truncate">{member.name}</span>
                <span className="tabular-nums">{closed ? "Off" : `${booked}/${minutesOf(wins)}`}</span>
              </div>
              <div className="sch-tl-track" style={{ ...grid, width: trackWidth }}>
                {gaps(wins, first, last).map((g) => (
                  <div key={g.start} className="sch-off" data-testid="grey" title={avail?.reason}
                       style={{ left: pos(g.start), width: len(g.end - g.start) }} />
                ))}
                {mine.filter((job) => isShown(job, showAll, focus, search, type, flag)).map((job) => (
                  <TimelineBlock key={job.id} job={job} kept={matches(job, focus, search, type, flag)} density={density} zones={zones}
                                 left={pos(job.start_minute!)} width={len(job.duration_minutes)} tipped={tip?.job.id === job.id}
                                 onShow={show} onHide={() => setTip(null)} />
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
        <span className="sch-legend"><i className="sch-tl-job t-ext" /> Exterior</span>
        <span className="sch-legend"><i className="sch-tl-job t-int" /> Interior</span>
        <span className="sch-legend"><i className="sch-tl-job t-spa" /> Deep Spa</span>
        <span className="sch-legend"><i className="sch-tl-job t-ext active" /> In progress</span>
        <span className="sch-legend"><i className="sch-tl-job t-ext done" /> Completed (✓)</span>
        <span className="sch-legend"><i className="sch-tl-job t-ext failed" /> Could not complete (✕)</span>
        <span className="sch-legend"><i className="sch-tl-job t-ext late" /> Late</span>
        <span className="sch-legend"><i className="sch-off-key" /> Cannot work</span>
        {unplaced > 0 && <span className="font-medium text-[#9a6513]">{unplaced} unscheduled, not on the timeline</span>}
      </div>
      {tip && <JobTip tip={tip} />}
    </div>
    </DragEngineProvider>
  );
}

/** One job on a crew row. It can be dragged along the time axis and onto another row (P0-6). */
function TimelineBlock({ job, kept, density, zones, left, width, tipped, onShow, onHide }: {
  job: AdminJob;
  kept: boolean;
  density: Density;
  zones: string[];
  left: string;
  width: string;
  /** The job tip is open for this block. */
  tipped: boolean;
  onShow: (job: AdminJob, el: HTMLElement) => void;
  onHide: () => void;
}) {
  const grab = useRef({ dx: 0 });
  const payload: TimelineDrag = { job, grab: grab.current };
  // Only a Scheduled job can move, as on the cards (isOpen).
  const drag = useDragSource(job.id, payload, !isOpen(job));
  const press = (e: ReactPointerEvent<HTMLDivElement>) => {
    grab.current.dx = e.clientX - e.currentTarget.getBoundingClientRect().left;
    drag.onPointerDown(e);
  };
  return (
    <div tabIndex={0} data-dnd-card={job.id} onPointerDown={press}
         aria-label={`${job.start_time}-${job.end_time} ${jobLabel(job)}, ${job.status}`}
         aria-describedby={tipped ? "sch-tl-tip" : undefined}
         aria-disabled={!kept || undefined}
         className={cn("sch-tl-job", typeClass(job), statusClass(job), isSpa(job) && "spa", job.late && "late",
           breached(job) && "wine", !kept && "dim")}
         style={{ left, width }}
         onMouseEnter={(e) => onShow(job, e.currentTarget)} onMouseLeave={onHide}
         onFocus={(e) => onShow(job, e.currentTarget)} onBlur={onHide}>
      {/* The block shows the lines of the card at this layout, so its height is the card's height. */}
      <span className="sch-tl-face">
        <CardFace job={job} density={density} zones={zones} />
      </span>
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
