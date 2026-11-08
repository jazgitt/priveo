import { Check, ChevronsLeft, ChevronsRight, Lock, Trash2, Unlock, X } from "lucide-react";
import { useEffect, useRef, useState, type DragEvent, type PointerEvent, type ReactNode, type WheelEvent } from "react";

import { useConfirm } from "@/blocks/confirm";
import { useAppMutation } from "@/blocks/mutation";
import { cn } from "@/lib/utils";

import { HoverTip } from "../../components";
import {
  breached, cardLines, clashMessage, clashOf, type CardPart, type Density, fitsAt, freeSlots, freeStart, gaps, hm, isOpen, isSpa,
  isUnplaced, jobLabel, matches, minutesOf, Reasoning, stepOf, statusClass, typeClass, windowsOf, zoneShort, zonesOf, zoneStyle,
} from "./Board";
import { aroundBreak, BreakBlock, breakOf } from "./BreakBlock";
import { Scroller } from "./Scroller";
import { api } from "@/api/client";
import { hhmm, type AdminJob, type CrewDayAvailability, type SchedulingCrew } from "./api";

export type { Density } from "./Board";

const UNSCHEDULED = "unscheduled";

const FOLD_KEY = "priveo.schedule.folded-lanes";

/** A crew member's home zone names, in the order the API gives them: "Zone 2, Zone 5". */
export const homeZonesText = (member: SchedulingCrew): string => (member.home_zones ?? []).map((z) => z.name).join(", ");
/** The home zones as short labels on the header line, such as Z1, Z2 (owner, 8-Nov-26). The full names stay in the tip. */
export const homeZonesShort = (member: SchedulingCrew): string => (member.home_zones ?? []).map((z) => zoneShort(z.name)).join(", ");

/** What the lock icon of a card placed by hand says it will do when clicked (owner, item 15). */
export const LOCK_TIP = {
  locked: "Locked. The scheduler keeps this card here on every run. Click to unlock; the next run may then move it.",
  unlocked: "Unlocked. The next scheduler run may move this card. Click to lock it here.",
} as const;

/** The crew members whose lanes are folded to a thin strip, remembered in the browser. */
function useFoldedLanes(): [Set<string>, (id: string) => void] {
  const [ids, setIds] = useState<Set<string>>(() => {
    try { return new Set<string>(JSON.parse(localStorage.getItem(FOLD_KEY) ?? "[]")); } catch { return new Set<string>(); }
  });
  return [ids, (id) => setIds((cur) => {
    const next = new Set(cur);
    if (next.has(id)) next.delete(id); else next.add(id);
    try { localStorage.setItem(FOLD_KEY, JSON.stringify([...next])); } catch { /* A private window keeps nothing; the fold still applies now. */ }
    return next;
  })];
}

const byStart = (a: AdminJob, b: AdminJob) => (a.start_minute ?? 0) - (b.start_minute ?? 0);

/** Where a dragged card would land: before the index-th card, or at a time in a free slot. */
interface Over { col: string; index: number; gap?: number; at?: number }

/** A free slot's height on the board, so a longer slot looks longer. */
const gapHeight = (minutes: number) => Math.round(Math.min(360, Math.max(30, minutes * 1.4)));

/**
 * The start time for a card dropped on a free slot: as far into the slot as the
 * pointer is, snapped to `step` minutes (5, or 15 on the detailed layout), and
 * never past the slot's end.
 */
export function slotTime(el: HTMLElement, y: number, duration: number, step = 5): number {
  const start = Number(el.dataset.start);
  const end = Number(el.dataset.end);
  const base = Math.ceil(start / step) * step;
  const room = end - duration - base;
  if (room < 0) return start;
  const r = el.getBoundingClientRect();
  const frac = r.height ? Math.min(1, Math.max(0, (y - r.top) / r.height)) : 0;
  return base + Math.round(frac * Math.floor(room / step)) * step;
}

/** One piece of a card's line. The same kind looks the same at every size: zone, car number, cutoff, code and slot. */
function Piece({ part, zones }: { part: CardPart; zones: string[] }) {
  switch (part.kind) {
    case "zone":
      return part.text
        ? <span className="sch-zone" style={zoneStyle(part.text, zones)} title={part.text}>{zoneShort(part.text)}</span>
        : <span className="sch-zone sch-zone-none" role="img" aria-label="No zone" title="No zone"><X aria-hidden /></span>;
    case "reg":
      return <strong className="reg sch-reg">{part.text}</strong>;
    case "model":
      return <span className="sch-model">{part.text}</span>;
    case "customer":
      return <span className="sch-customer">{part.text}</span>;
    case "cutoff":
      return <span className="sch-cut">{part.text}</span>;
    case "code":
      return <span className={`sch-code ${part.text.toLowerCase()}`}>{part.text}</span>;
    case "slot":
      return <span className="sch-time">{part.text}</span>;
  }
}

/**
 * The face of a card or a timeline block: its lines at the chosen size (owner review, 8-Nov-26),
 * with the status icon and the flags on the line of the kind of clean. Shared by the board and
 * the timeline, so both show the same lines.
 */
export function CardFace({ job, density, zones }: { job: AdminJob; density: Density; zones: string[] }) {
  const flagLine = density === "compact" ? 0 : 1;
  const flags = (
    <>
      {job.status === "Completed" && <Check className="sch-st done" aria-hidden />}
      {job.status === "Could not complete" && <X className="sch-st failed" aria-hidden />}
      {job.status === "In progress" && <i className="sch-st active" aria-hidden />}
      {job.late && <span className="sch-flag late">Late</span>}
      {job.manual && <span className="sch-flag">By hand</span>}
    </>
  );
  return (
    <>
      {cardLines(job, density).map((line, i) => (
        <span key={i} className="sch-card-line">
          {line.map((part) => <Piece key={part.kind} part={part} zones={zones} />)}
          {i === flagLine && flags}
        </span>
      ))}
    </>
  );
}

/**
 * The chosen day as columns of job cards, like a task board: the jobs with no
 * crew member first, then one column for each crew member with that member's
 * jobs and free slots in time order. A card is dragged onto a free slot (it
 * starts where it is dropped in the slot) or between two cards (it takes the
 * first free time after the card above). On the detailed layout the start moves
 * in 15-minute steps. Dropping a card on Unscheduled takes it off its crew
 * member. Clicking a card opens its dialog to set an exact time. A crew member
 * who cannot work that day is greyed out and takes no card (ADM-SCH-32, -33).
 * A drop that would overlap another job is refused with the job in the way.
 */
export function CardBoard({ crew, jobs, availability, focus, search, type = "", flag = "", density = "standard", savingId = null, onOpen, onMove }: {
  crew: SchedulingCrew[];
  jobs: AdminJob[];
  availability: CrewDayAvailability[];
  focus: string;
  search: string;
  /** EXT, INT or SPA keeps only that kind bright; empty shows all. */
  type?: string;
  /** "late" or "manual" keeps only those jobs bright; empty shows all. */
  flag?: string;
  density?: Density;
  /** The job whose move is being saved, shown as working. */
  savingId?: string | null;
  onOpen: (job: AdminJob) => void;
  onMove: (job: AdminJob, crewId: string | null, startMinute: number | null) => void;
}) {
  const confirm = useConfirm();
  // Lock or unlock a card placed by hand; the board is read again so the icon and the card follow the server (item 15).
  const lockOf = useAppMutation<{ job: AdminJob; locked: boolean }, AdminJob>({
    mutationFn: (v) => api(`/v1/admin/scheduling/jobs/${v.job.id}/hand-lock`, { method: "PUT", body: { locked: v.locked } }),
    pending: false,
    success: (_d, v) => `${v.job.registration} is ${v.locked ? "locked" : "unlocked"}.`,
    invalidate: [["board"]],
  });
  const zones = zonesOf(jobs);
  const step = stepOf(density);
  const dragging = useRef<AdminJob | null>(null);
  const [dragId, setDragId] = useState<string | null>(null);
  const [over, setOver] = useState<Over | null>(null);
  const [blocked, setBlocked] = useState("");
  const root = useRef<HTMLDivElement>(null);
  const strip = useRef<HTMLDivElement | null>(null);
  const pan = useRef<{ x: number; left: number } | null>(null);
  const [panning, setPanning] = useState(false);
  const [folded, toggleFold] = useFoldedLanes();
  // Searching brings the first match into view, so a car in a long lane is not hunted for.
  useEffect(() => {
    if (!search.trim()) return;
    root.current?.querySelector<HTMLElement>("[data-card]:not(.dim)")?.scrollIntoView?.({ block: "nearest", inline: "nearest" });
  }, [search]);

  if (crew.length === 0) {
    return <p className="text-sm text-muted-foreground">No crew is set up for this site.</p>;
  }
  const availOf = (id: string) => availability.find((a) => a.crew_id === id);
  // Members who cannot work go to the end, so the columns that take work come first.
  const members = [...crew].sort((a, b) =>
    Number(availOf(a.id)?.status === "Off") - Number(availOf(b.id)?.status === "Off"));
  const unplaced = jobs.filter(isUnplaced);
  const dragged = dragId ? jobs.find((j) => j.id === dragId) ?? null : null;
  /** While a card is held, whether a crew member could take it at all: shown as green or red columns. */
  const takes = (member: SchedulingCrew): boolean | null => {
    if (!dragged) return null;
    const avail = availOf(member.id);
    if (avail?.status === "Off") return false;
    const others = jobs.filter((j) => j.crew_id === member.id && j.id !== dragged.id && j.start_minute !== null);
    return freeStart(windowsOf(member, avail), others, 0, dragged.duration_minutes, step) !== null;
  };
  /** Dragging the background or a column heading pans the board sideways, like grabbing paper. */
  const panStart = (e: PointerEvent<HTMLElement>) => {
    const t = e.target as HTMLElement;
    if (e.button !== 0 || !strip.current) return;
    if (!(t === e.currentTarget || t.closest(".sch-col-head")) || t.closest("button,a,input,[role=button]")) return;
    pan.current = { x: e.clientX, left: strip.current.scrollLeft };
    e.currentTarget.setPointerCapture?.(e.pointerId);
    setPanning(true);
  };
  const panMove = (e: PointerEvent<HTMLElement>) => {
    if (pan.current && strip.current) strip.current.scrollLeft = pan.current.left - (e.clientX - pan.current.x);
  };
  const panEnd = () => { pan.current = null; setPanning(false); };
  /** The wheel over the headings and the gaps, where there is nothing to scroll down, scrolls sideways. */
  const wheel = (e: WheelEvent<HTMLElement>) => {
    if ((e.target as HTMLElement).closest(".sch-col-body") || !strip.current) return;
    if (Math.abs(e.deltaY) > Math.abs(e.deltaX)) strip.current.scrollLeft += e.deltaY;
  };
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

  /** The delete icon takes a placed job off its crew member for the day; it goes to Unscheduled, nothing is deleted (item 6). */
  const takeOff = async (job: AdminJob) => {
    if (await confirm({
      title: `Take ${job.registration} off the day?`,
      description: `The job goes to Unscheduled for this day. It is not deleted: you can place it again later.`,
      confirmLabel: "Take off the day", tone: "danger",
    })) onMove(job, null, null);
  };

  const dragOver = (col: string) => (e: DragEvent<HTMLElement>) => {
    const job = dragging.current;
    if (!job) return;
    e.preventDefault();
    const slot = col === UNSCHEDULED ? null : slotOf(e);
    const next: Over = slot
      ? { col, index: -1, gap: Number(slot.dataset.start), at: slotTime(slot, e.clientY, job.duration_minutes, step) }
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
      start = slotTime(slot, e.clientY, job.duration_minutes, step);
      if (!fitsAt(wins, others, start, job.duration_minutes)) {
        // A free slot shorter than the card is named as such; the job next to it is not the reason.
        const free = Number(slot.dataset.end) - Number(slot.dataset.start);
        if (free < job.duration_minutes) {
          setBlocked(`Only ${hm(free)} is free there; ${job.registration} needs ${job.duration_minutes} min.`);
          return;
        }
        const blocker = clashOf(others, start, job.duration_minutes);
        if (blocker) {
          setBlocked(clashMessage(job, blocker, member.name, freeStart(wins, others, 0, job.duration_minutes, step)));
          return;
        }
        setBlocked(`Only ${hm(free)} is free there; ${job.registration} needs ${job.duration_minutes} min.`);
        return;
      }
    } else {
      start = freeStart(wins, others, index, job.duration_minutes, step);
    }
    if (start === null) {
      setBlocked(`${member.name} has no free ${job.duration_minutes} minutes in their slots this day.`);
      return;
    }
    if (job.crew_id === member.id && job.start_minute === start) return;
    setBlocked("");
    onMove(job, member.id, start);
  };

  /** Alt + Up or Down moves a placed card one step (5 minutes, or 15 on the detailed layout) earlier or later in its own column. */
  const nudge = (job: AdminJob, by: 1 | -1) => {
    const member = crew.find((c) => c.id === job.crew_id);
    if (!member || job.start_minute === null) return;
    // Lands on the next multiple of the step in that direction, so an odd start snaps too.
    const start = by > 0
      ? (Math.floor(job.start_minute / step) + 1) * step
      : (Math.ceil(job.start_minute / step) - 1) * step;
    const others = jobs.filter((j) => j.crew_id === member.id && j.id !== job.id && j.start_minute !== null);
    const wins = windowsOf(member, availOf(member.id));
    if (!fitsAt(wins, others, start, job.duration_minutes)) {
      const blocker = clashOf(others, start, job.duration_minutes);
      setBlocked(blocker
        ? clashMessage(job, blocker, member.name, freeStart(wins, others, 0, job.duration_minutes, step))
        : `${job.registration} cannot start at ${hhmm(start)}: that time is not free for ${member.name}.`);
      return;
    }
    setBlocked("");
    onMove(job, member.id, start);
  };

  const card = (job: AdminJob) => {
    const open = isOpen(job);
    const wine = breached(job);
    const tools = job.placed_by_hand || (open && job.crew_id);
    return (
      <div key={job.id} data-card data-job={job.id} role="button" tabIndex={0} draggable={open}
           aria-label={jobLabel(job)} aria-busy={savingId === job.id || undefined}
           title={`${job.start_time ? `${job.start_time}-${job.end_time} ` : ""}${job.vehicle}, ${job.service}.${job.parking ? ` ${job.parking}.` : ""} ${job.status}${job.reason ? `. ${job.reason}` : ""}${wine ? ` Placed by hand against a rule: ${(job.hand_breaches ?? []).join(" ")}` : ""}${open && job.crew_id ? ` Alt and the up or down arrow move it ${step} minutes.` : ""}`}
           className={cn("sch-card", typeClass(job), statusClass(job), density, isSpa(job) && "spa", job.late && "late", job.manual && "manual",
             wine && "wine", !matches(job, focus, search, type, flag) && "dim", dragId === job.id && "dragging", !open && "locked",
             savingId === job.id && "saving", tools && "has-tools")}
           onDragStart={open ? startDrag(job) : undefined} onDragEnd={endDrag}
           onClick={() => onOpen(job)}
           onKeyDown={(e) => {
             if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onOpen(job); }
             else if (e.altKey && open && (e.key === "ArrowUp" || e.key === "ArrowDown")) {
               e.preventDefault();
               nudge(job, e.key === "ArrowUp" ? -1 : 1);
             }
           }}>
        <CardFace job={job} density={density} zones={zones} />
        {density !== "compact" && job.status !== "Scheduled" && <span className="sch-card-status">{job.status}</span>}
        {job.crew_id && job.cross_zone_reason && density !== "compact" && (
          <span className="sch-why" role="note" title={job.cross_zone_reason} aria-label={job.cross_zone_reason}>Outside zone</span>
        )}
        {/* A card taken off a crew member shows the reason it has no place. */}
        {!job.crew_id && job.reason && density !== "compact" && <span className="sch-why">{job.reason}</span>}
        {wine && density !== "compact" && <span className="sch-why sch-breach">Placed by hand against a rule</span>}
        {tools && (
          // The icons sit at the bottom right (standard and detailed) or the right (compact). They never open the card.
          <span className="sch-card-tools" onClick={(e) => e.stopPropagation()}
                onKeyDown={(e) => e.stopPropagation()} onDragStart={(e) => e.preventDefault()}>
            {job.placed_by_hand && (() => {
              const locked = job.hand_locked === true;
              const tip = locked ? LOCK_TIP.locked : LOCK_TIP.unlocked;
              return (
                <button type="button" className="sch-tool lock" aria-pressed={locked} aria-disabled={!open || undefined}
                        aria-label={tip} title={tip}
                        onClick={() => { if (open) lockOf.mutate({ job, locked: !locked }); }}>
                  {locked ? <Lock aria-hidden /> : <Unlock aria-hidden />}
                </button>
              );
            })()}
            {open && job.crew_id && (
              // The name stays out of the button's label, so a search by registration still finds the card alone.
              <button type="button" className="sch-tool del" aria-label="Take off the day"
                      title={`Take ${job.registration} off the day`}
                      onClick={() => void takeOff(job)}>
                <Trash2 aria-hidden />
              </button>
            )}
          </span>
        )}
      </div>
    );
  };

  /** A member's day in time order: cards, free slots and the time between slots. */
  const lane = (member: SchedulingCrew, mine: AdminJob[], wins: { start: number; end: number }[], brk: { start: number; end: number } | null) => {
    // The card being moved does not block its own slot, so it can go back to where it was or a step either side.
    const others = mine.filter((j) => j.id !== dragId);
    const items: { start: number; node: () => ReactNode; card?: AdminJob }[] = [
      ...mine.map((j) => ({ start: j.start_minute!, card: j, node: () => card(j) })),
      ...freeSlots(aroundBreak(wins, brk), others).map((g) => ({ start: g.start, node: () => {
        const here = over?.col === member.id && over.gap === g.start;
        const tight = here && dragged !== null && g.end - g.start < dragged.duration_minutes;
        return (
          <div key={`free-${g.start}`} data-slot data-start={g.start} data-end={g.end}
               className={cn("sch-slot", here && "over", tight && "tight")} style={{ height: gapHeight(g.end - g.start) }}
               aria-label={`Free ${hhmm(g.start)}-${hhmm(g.end)}`}>
            <span>{tight ? `Too short for ${dragged?.duration_minutes} min` : here && over.at !== undefined ? `Drop at ${hhmm(over.at)}` : `Free ${hhmm(g.start)}-${hhmm(g.end)}`}</span>
            <span>{hm(g.end - g.start)}</span>
          </div>
        );
      } })),
      // The break holds no job: a block at the cleaner's break time (SCHR-BRK-09).
      ...(brk ? [{ start: brk.start, node: () => <BreakBlock key="break" start={brk.start} end={brk.end} /> }] : []),
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
    <div className="sch-fill" ref={root}>
      <Scroller wrapClassName="sch-board-wrap" innerRef={strip} className={cn("sch-board", panning && "panning")} role="group" aria-label="Day board"
                onPointerDown={panStart} onPointerMove={panMove} onPointerUp={panEnd} onPointerCancel={panEnd} onWheel={wheel}>
        {folded.has(UNSCHEDULED) ? (
          // A folded Unscheduled lane is a thin strip; a card dropped on it is taken off its crew member, as on the open lane.
          <section aria-label={`Unscheduled (${unplaced.length}), folded`} data-testid="col-unscheduled"
                   className={cn("sch-col unscheduled folded", over?.col === UNSCHEDULED && "over")}
                   onDragOver={dragOver(UNSCHEDULED)} onDragLeave={dragLeave} onDrop={(e) => void dropOn(null)(e)}>
            <button type="button" className="sch-fold-btn" aria-label="Show the Unscheduled lane" title="Show the lane"
                    onClick={() => toggleFold(UNSCHEDULED)}>
              <ChevronsRight aria-hidden />
            </button>
            <span className="sch-count">{unplaced.length}</span>
            <span className="sch-fold-name">Unscheduled</span>
          </section>
        ) : (
        <section aria-label={`Unscheduled (${unplaced.length})`} data-testid="col-unscheduled"
                 className={cn("sch-col unscheduled", over?.col === UNSCHEDULED && "over", dragged?.crew_id && "can")}>
          <header className="sch-col-head">
            <span className="flex items-baseline justify-between gap-2">
              <strong>Unscheduled</strong>
              <span className="flex items-center gap-1">
                <span className="sch-count">{unplaced.length}</span>
                <button type="button" className="sch-fold-btn small" aria-label="Fold the Unscheduled lane" title="Fold the lane to a thin strip"
                        onClick={() => toggleFold(UNSCHEDULED)}>
                  <ChevronsLeft aria-hidden />
                </button>
              </span>
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
        )}
        {members.map((member) => {
          const avail = availOf(member.id);
          const closed = avail?.status === "Off";
          const wins = windowsOf(member, avail);
          const mine = jobs.filter((j) => j.crew_id === member.id && j.start_minute !== null).sort(byStart);
          const brk = breakOf(avail);
          const available = minutesOf(aroundBreak(wins, brk));
          const booked = mine.reduce((n, j) => n + j.duration_minutes, 0);
          const pct = available ? Math.round((booked / available) * 100) : 0;
          const fold = folded.has(member.id);
          const state = cn("sch-col", closed && "closed", over?.col === member.id && "over",
            takes(member) === true && "can", takes(member) === false && "cannot");
          if (fold) {
            // A folded lane is a thin strip: name, jobs and use. A card dropped on it goes to its first free time.
            return (
              <section key={member.id} aria-label={`${member.name}, folded`} data-testid={`col-${member.id}`}
                       className={cn(state, "folded")}
                       onDragOver={dragOver(member.id)} onDragLeave={dragLeave} onDrop={(e) => void dropOn(member)(e)}>
                <button type="button" className="sch-fold-btn" aria-label={`Show ${member.name}'s lane`} title="Show the lane"
                        onClick={() => toggleFold(member.id)}>
                  <ChevronsRight aria-hidden />
                </button>
                <span className="sch-count">{mine.length}</span>
                <span className="sch-fold-name">{member.name}</span>
                {!closed && <span className="text-xs font-semibold tabular-nums">{pct}%</span>}
              </section>
            );
          }
          return (
            <section key={member.id} aria-label={member.name} data-testid={`col-${member.id}`} className={state}>
              <header className="sch-col-head">
                <span className="flex items-baseline justify-between gap-2">
                  <HoverTip label={<span className="sch-name-line"><strong>{member.name}</strong>
                              {(member.home_zones ?? []).length > 0 && (
                                <span className="sch-home-zones" title={homeZonesText(member)}> · {homeZonesShort(member)}</span>
                              )}</span>}
                            ariaLabel={`${member.name}, ${member.role}. Hover for how jobs are allocated.`}>
                    <Reasoning member={member} avail={avail} jobs={mine} />
                  </HoverTip>
                  <span className="flex items-center gap-1">
                    <span className="sch-count">{mine.length}</span>
                    <button type="button" className="sch-fold-btn small" aria-label={`Fold ${member.name}'s lane`} title="Fold the lane to a thin strip"
                            onClick={() => toggleFold(member.id)}>
                      <ChevronsLeft aria-hidden />
                    </button>
                  </span>
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
                  : lane(member, mine, wins, brk)}
              </Scroller>
            </section>
          );
        })}
      </Scroller>
      {blocked && <p className="mt-2 mb-0 text-sm text-destructive" role="alert">{blocked}</p>}
    </div>
  );
}
