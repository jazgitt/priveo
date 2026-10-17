import { useRef, useState, type DragEvent, type ReactNode } from "react";

import { useConfirm } from "@/blocks/confirm";
import { cn } from "@/lib/utils";

import { HoverTip } from "../../components";
import {
  fitsAt, freeSlots, freeStart, gaps, hm, isOpen, isSpa, isUnplaced, jobLabel, matches, minutesOf, Reasoning,
  serviceCode, SNAP, statusClass, windowsOf,
} from "./Board";
import { Scroller } from "./Scroller";
import { hhmm, type AdminJob, type CrewDayAvailability, type SchedulingCrew } from "./api";

const UNSCHEDULED = "unscheduled";

const byStart = (a: AdminJob, b: AdminJob) => (a.start_minute ?? 0) - (b.start_minute ?? 0);

/** Where a dragged card would land: before the index-th card, or at a time in a free slot. */
interface Over { col: string; index: number; gap?: number; at?: number }

/** A free slot's height on the board, so a longer slot looks longer. */
const gapHeight = (minutes: number) => Math.round(Math.min(360, Math.max(30, minutes * 1.4)));

/**
 * The start time for a card dropped on a free slot: as far into the slot as the
 * pointer is, snapped to 5 minutes, and never past the slot's end.
 */
function slotTime(el: HTMLElement, y: number, duration: number): number {
  const start = Number(el.dataset.start);
  const end = Number(el.dataset.end);
  const base = Math.ceil(start / SNAP) * SNAP;
  const room = end - duration - base;
  if (room < 0) return start;
  const r = el.getBoundingClientRect();
  const frac = r.height ? Math.min(1, Math.max(0, (y - r.top) / r.height)) : 0;
  return base + Math.round((frac * room) / SNAP) * SNAP;
}

/**
 * The chosen day as columns of job cards, like a task board: the jobs with no
 * crew member first, then one column for each crew member with that member's
 * jobs and free slots in time order. A card is dragged onto a free slot (it
 * starts where it is dropped in the slot) or between two cards (it takes the
 * first free time after the card above). Dropping a card on Unscheduled takes
 * it off its crew member. Clicking a card opens its dialog to set an exact
 * time. A crew member who cannot work that day is greyed out and takes no card
 * (ADM-SCH-32, -33).
 */
export function CardBoard({ crew, jobs, availability, focus, search, onOpen, onMove }: {
  crew: SchedulingCrew[];
  jobs: AdminJob[];
  availability: CrewDayAvailability[];
  focus: string;
  search: string;
  onOpen: (job: AdminJob) => void;
  onMove: (job: AdminJob, crewId: string | null, startMinute: number | null) => void;
}) {
  const confirm = useConfirm();
  const dragging = useRef<AdminJob | null>(null);
  const [dragId, setDragId] = useState<string | null>(null);
  const [over, setOver] = useState<Over | null>(null);
  const [blocked, setBlocked] = useState("");

  if (crew.length === 0) {
    return <p className="text-sm text-muted-foreground">No crew is set up for this site.</p>;
  }
  const availOf = (id: string) => availability.find((a) => a.crew_id === id);
  // Members who cannot work go to the end, so the columns that take work come first.
  const members = [...crew].sort((a, b) =>
    Number(availOf(a.id)?.status === "Off") - Number(availOf(b.id)?.status === "Off"));
  const unplaced = jobs.filter(isUnplaced);
  const slotOf = (e: DragEvent<HTMLElement>) => (e.target as HTMLElement).closest?.<HTMLElement>("[data-slot]") ?? null;

  /** Where among the column's other cards the pointer is: 0 is above the first. */
  const indexAt = (body: HTMLElement, y: number) =>
    [...body.querySelectorAll<HTMLElement>("[data-card]")]
      .filter((el) => el.dataset.job !== dragging.current?.id)
      .filter((el) => { const r = el.getBoundingClientRect(); return r.top + r.height / 2 < y; }).length;

  const startDrag = (job: AdminJob) => (e: DragEvent) => {
    dragging.current = job;
    setBlocked("");
    e.dataTransfer?.setData("text/plain", job.id);
    if (e.dataTransfer) e.dataTransfer.effectAllowed = "move";
    // Let the browser take its picture of the card before it is dimmed.
    requestAnimationFrame(() => setDragId(job.id));
  };
  const endDrag = () => { dragging.current = null; setDragId(null); setOver(null); };

  const dragOver = (col: string) => (e: DragEvent<HTMLElement>) => {
    const job = dragging.current;
    if (!job) return;
    e.preventDefault();
    const slot = col === UNSCHEDULED ? null : slotOf(e);
    const next: Over = slot
      ? { col, index: -1, gap: Number(slot.dataset.start), at: slotTime(slot, e.clientY, job.duration_minutes) }
      : { col, index: col === UNSCHEDULED ? 0 : indexAt(e.currentTarget, e.clientY) };
    if (over?.col !== next.col || over.index !== next.index || over.gap !== next.gap || over.at !== next.at) setOver(next);
  };
  const dragLeave = (e: DragEvent<HTMLElement>) => {
    if (!e.currentTarget.contains(e.relatedTarget as Node | null)) setOver(null);
  };

  const dropOn = (member: SchedulingCrew | null) => async (e: DragEvent<HTMLElement>) => {
    e.preventDefault();
    const job = dragging.current;
    const slot = member ? slotOf(e) : null;
    const index = member ? indexAt(e.currentTarget, e.clientY) : 0;
    endDrag();
    if (!job) return;
    if (!member) {
      if (!job.crew_id) return;
      if (await confirm({
        title: `Take ${job.registration} off ${job.crew_name ?? "its crew member"}?`,
        description: "The job goes to Unscheduled for this day. You can place it again later.",
        confirmLabel: "Take off crew member", tone: "danger",
      })) onMove(job, null, null);
      return;
    }
    const avail = availOf(member.id);
    if (avail?.status === "Off") {
      setBlocked(`${member.name} cannot take work this day. ${avail.reason}`.trim());
      return;
    }
    const wins = windowsOf(member, avail);
    const others = jobs.filter((j) => j.crew_id === member.id && j.id !== job.id && j.start_minute !== null).sort(byStart);
    let start: number | null;
    if (slot) {
      start = slotTime(slot, e.clientY, job.duration_minutes);
      if (!fitsAt(wins, others, start, job.duration_minutes)) {
        const free = Number(slot.dataset.end) - Number(slot.dataset.start);
        setBlocked(`Only ${hm(free)} is free there; ${job.registration} needs ${job.duration_minutes} min.`);
        return;
      }
    } else {
      start = freeStart(wins, others, index, job.duration_minutes);
    }
    if (start === null) {
      setBlocked(`${member.name} has no free ${job.duration_minutes} minutes in their slots this day.`);
      return;
    }
    if (job.crew_id === member.id && job.start_minute === start) return;
    setBlocked("");
    onMove(job, member.id, start);
  };

  const card = (job: AdminJob) => {
    const code = serviceCode(job.service);
    const open = isOpen(job);
    return (
      <div key={job.id} data-card data-job={job.id} role="button" tabIndex={0} draggable={open}
           aria-label={jobLabel(job)}
           title={`${job.start_time ? `${job.start_time}-${job.end_time} ` : ""}${job.vehicle}, ${job.service}. ${job.status}${job.reason ? `. ${job.reason}` : ""}`}
           className={cn("sch-card", statusClass(job), isSpa(job) && "spa", job.late && "late", job.manual && "manual",
             !matches(job, focus, search) && "dim", dragId === job.id && "dragging", !open && "locked")}
           onDragStart={open ? startDrag(job) : undefined} onDragEnd={endDrag}
           onClick={() => onOpen(job)}
           onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onOpen(job); } }}>
        <span className="sch-card-top">
          <span className="sch-time">{job.start_time ? `${job.start_time}-${job.end_time}` : `${job.duration_minutes} min`}</span>
          <span className={`sch-code ${code.toLowerCase()}`}>{code}</span>
          {job.late && <span className="sch-flag late">Late</span>}
          {job.manual && <span className="sch-flag">By hand</span>}
        </span>
        <span className="sch-card-main">
          <strong className="reg">{job.registration}</strong>
          <span>{job.parking || "-"}{job.finish_by ? ` · by ${job.finish_by}` : ""}</span>
        </span>
        {job.status !== "Scheduled" && <span className="sch-card-status">{job.status}</span>}
        {!job.crew_id && job.reason && <span className="sch-why">{job.reason}</span>}
      </div>
    );
  };

  /** A member's day in time order: cards, free slots and the time between slots. */
  const lane = (member: SchedulingCrew, mine: AdminJob[], wins: { start: number; end: number }[]) => {
    const items: { start: number; node: () => ReactNode; card?: AdminJob }[] = [
      ...mine.map((j) => ({ start: j.start_minute!, card: j, node: () => card(j) })),
      ...freeSlots(wins, mine).map((g) => ({ start: g.start, node: () => {
        const here = over?.col === member.id && over.gap === g.start;
        return (
          <div key={`free-${g.start}`} data-slot data-start={g.start} data-end={g.end}
               className={cn("sch-slot", here && "over")} style={{ height: gapHeight(g.end - g.start) }}
               aria-label={`Free ${hhmm(g.start)}-${hhmm(g.end)}`}>
            <span>{here && over.at !== undefined ? `Drop at ${hhmm(over.at)}` : `Free ${hhmm(g.start)}-${hhmm(g.end)}`}</span>
            <span>{hm(g.end - g.start)}</span>
          </div>
        );
      } })),
      ...(wins.length ? gaps(wins, Math.min(...wins.map((w) => w.start)), Math.max(...wins.map((w) => w.end))) : [])
        .map((g) => ({ start: g.start, node: () => (
          <div key={`off-${g.start}`} className="sch-break">Not working {hhmm(g.start)}-{hhmm(g.end)}</div>
        ) })),
    ];
    items.sort((a, b) => a.start - b.start || Number(Boolean(b.card)) - Number(Boolean(a.card)));
    return withLine(member.id, items);
  };

  /** The items of a column, with a line where the dragged card would go between cards. */
  const withLine = (col: string, items: { node: () => ReactNode; card?: AdminJob }[]) => {
    const out: ReactNode[] = [];
    const lineAt = over?.col === col && col !== UNSCHEDULED && over.index >= 0 ? over.index : -1;
    let at = 0;
    for (const it of items) {
      if (it.card && it.card.id !== dragId) {
        if (lineAt === at) out.push(<div key="drop" className="sch-drop-line" />);
        at += 1;
      }
      out.push(it.node());
    }
    if (lineAt === at) out.push(<div key="drop" className="sch-drop-line" />);
    return out;
  };

  return (
    <div>
      <Scroller wrapClassName="sch-board-wrap" className="sch-board" role="group" aria-label="Day board">
        <section aria-label={`Unscheduled (${unplaced.length})`} data-testid="col-unscheduled"
                 className={cn("sch-col unscheduled", over?.col === UNSCHEDULED && "over")}>
          <header className="sch-col-head">
            <span className="flex items-baseline justify-between gap-2">
              <strong>Unscheduled</strong><span className="sch-count">{unplaced.length}</span>
            </span>
            <span className="text-xs text-muted-foreground">No crew member yet. Drop a card here to take it off.</span>
          </header>
          <Scroller axis="y" wrapClassName="sch-col-scroll" className="sch-col-body"
                    onDragOver={dragOver(UNSCHEDULED)} onDragLeave={dragLeave} onDrop={(e) => void dropOn(null)(e)}>
            {unplaced.length === 0
              ? <p className="sch-col-empty">Every job of this day has a crew member.</p>
              : withLine(UNSCHEDULED, unplaced.map((j) => ({ card: j, node: () => card(j) })))}
          </Scroller>
        </section>
        {members.map((member) => {
          const avail = availOf(member.id);
          const closed = avail?.status === "Off";
          const wins = windowsOf(member, avail);
          const mine = jobs.filter((j) => j.crew_id === member.id && j.start_minute !== null).sort(byStart);
          const available = minutesOf(wins);
          const booked = mine.reduce((n, j) => n + j.duration_minutes, 0);
          const pct = available ? Math.round((booked / available) * 100) : 0;
          return (
            <section key={member.id} aria-label={member.name} data-testid={`col-${member.id}`}
                     className={cn("sch-col", closed && "closed", over?.col === member.id && "over")}>
              <header className="sch-col-head">
                <span className="flex items-baseline justify-between gap-2">
                  <HoverTip label={<strong>{member.name}</strong>}
                            ariaLabel={`${member.name}, ${member.role}. Hover for how jobs are allocated.`}>
                    <Reasoning member={member} avail={avail} jobs={mine} />
                  </HoverTip>
                  <span className="sch-count">{mine.length}</span>
                </span>
                <span className="truncate text-xs text-muted-foreground" title={avail?.reason}>
                  {member.role} · {closed ? avail?.reason || "Off" : wins.map((w) => `${hhmm(w.start)}-${hhmm(w.end)}`).join(", ")}
                </span>
                {!closed && (
                  <>
                    <span className="flex items-center gap-2 text-xs">
                      <span className={cn("sch-load", pct > 100 && "over")} aria-hidden><span style={{ width: `${Math.min(pct, 100)}%` }} /></span>
                      <span className="font-semibold tabular-nums">{pct}%</span>
                    </span>
                    <span className="text-xs text-muted-foreground tabular-nums">
                      {hm(booked)} of {hm(available)} used · {hm(Math.max(0, available - booked))} free
                    </span>
                  </>
                )}
              </header>
              <Scroller axis="y" wrapClassName="sch-col-scroll" className="sch-col-body"
                        onDragOver={dragOver(member.id)} onDragLeave={dragLeave} onDrop={(e) => void dropOn(member)(e)}>
                {closed ? <p className="sch-col-empty">{avail?.reason || "Cannot take work this day."}</p>
                  : lane(member, mine, wins)}
              </Scroller>
            </section>
          );
        })}
      </Scroller>
      {blocked && <p className="mt-2 mb-0 text-sm text-destructive" role="alert">{blocked}</p>}
    </div>
  );
}
