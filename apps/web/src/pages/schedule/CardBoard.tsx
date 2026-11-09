import { Check, ChevronsLeft, ChevronsRight, Trash2, X } from "lucide-react";
import { useEffect, useRef, useState, type Dispatch, type PointerEvent, type ReactNode, type SetStateAction, type WheelEvent } from "react";

import { useConfirm } from "@/blocks/confirm";
import { useAppMutation } from "@/blocks/mutation";
import { cn } from "@/lib/utils";

import { HoverTip } from "../../components";
import {
  breached, cardLines, clashMessage, clashOf, type CardPart, type Density, fitsAt, freeSlots, freeStart, gaps, hm, isOpen, isShown, isSpa,
  isUnplaced, jobLabel, matches, minutesOf, Reasoning, stepOf, statusClass, typeClass, unscheduledOrder, windowsOf, zoneShort, zonesOf,
  zoneStyle,
} from "./Board";
import { aroundBreak, BreakBlock, breakOf } from "./BreakBlock";
import { LockGlyph } from "./LockGlyph";
import { Scroller } from "./Scroller";
import { api } from "@/api/client";
import { hhmm, type AdminJob, type CrewDayAvailability, type SchedulingCrew } from "./api";
import {
  DragEngineProvider, planFreeDrop, planInsertion, snapUpMinute, useDragSource, useDragState,
  type DragItem, type DropHit, type DropOutcome, type DropPlan, type LaneCard, type Shift,
} from "./dnd";

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

/** The card's drag source, as a component, so the hook runs once per card. */
function DragSource({ id, data, disabled, children }: {
  id: string;
  data: unknown;
  disabled: boolean;
  children: (drag: { dragging: boolean; onPointerDown: (e: PointerEvent<HTMLElement>) => void }) => ReactNode;
}) {
  const drag = useDragSource(id, data, disabled);
  return <>{children(drag)}</>;
}

const toLane = (j: AdminJob): LaneCard => ({ id: j.id, start: j.start_minute ?? 0, duration: j.duration_minutes });

/**
 * Moves the cards in a crew lane out of the way of a group that has been placed
 * (P0-8). `fixed` are the group's cards at their new times; `others` are the
 * rest of the lane. A card that overlaps a fixed card, or the card above it, moves
 * down to the first free time after it. Nothing moves up. Returns the changed
 * cards only.
 */
export function settleAround(others: LaneCard[], fixed: LaneCard[], top: number, step = 5): Shift[] {
  const fixedSorted = [...fixed].sort((a, b) => a.start - b.start);
  const changed: Shift[] = [];
  let cursor = snapUpMinute(top, step);
  for (const o of [...others].sort((a, b) => a.start - b.start)) {
    let start = o.start < cursor ? snapUpMinute(cursor, step) : o.start;
    let again = true;
    while (again) {
      again = false;
      for (const f of fixedSorted) {
        if (f.start < start + o.duration && start < f.start + f.duration) {
          start = snapUpMinute(f.start + f.duration, step);
          again = true;
          break;
        }
      }
    }
    if (start !== o.start) changed.push({ id: o.id, start });
    cursor = start + o.duration;
  }
  return changed;
}

/** The free slot under a pointer height in a lane, if the pointer is over one. */
export function slotUnder(laneEl: HTMLElement, y: number): HTMLElement | null {
  return [...laneEl.querySelectorAll<HTMLElement>("[data-slot]")].find((el) => {
    const r = el.getBoundingClientRect();
    return y >= r.top && y <= r.bottom;
  }) ?? null;
}

export interface BoardDropInput {
  drop: DropHit;
  /** The card that was held. */
  draggedId: string;
  /** The cards picked with their checkboxes. A picked card drags the whole picked group (P0-8). */
  picked: ReadonlySet<string>;
  jobs: AdminJob[];
  crew: SchedulingCrew[];
  availability: CrewDayAvailability[];
  folded: ReadonlySet<string>;
  /** Whether a card is drawn with the current filters. The drop index counts only drawn cards. */
  shown: (job: AdminJob) => boolean;
  step: number;
}

/**
 * What a drop on the board does, as the drag engine asks for it (P0-5, P0-7, P0-8).
 * Unscheduled takes the cards off their crew members, with no confirmation (P0-7). A
 * crew lane places the card at the drop, pushing the cards it runs into down (P0-5);
 * a picked group keeps its relative times and is saved as one batch (P0-8). A drop on
 * a member who cannot work is refused. Crew hours and service hours never refuse: the
 * server returns them as warnings. An overlap is refused by the server.
 */
export function planBoardMoves(input: BoardDropInput): DropOutcome {
  const { drop, draggedId, picked, jobs, crew, availability, folded, shown, step } = input;
  const dragged = jobs.find((j) => j.id === draggedId);
  if (!dragged) return null;
  const group = picked.has(draggedId) ? jobs.filter((j) => picked.has(j.id) && isOpen(j)) : [];
  const moving = group.length > 1 ? group : [dragged];
  const movingIds = new Set(moving.map((j) => j.id));

  if (drop.laneId === UNSCHEDULED) {
    const moves = moving
      .filter((j) => j.crew_id !== null)
      .map((j) => ({ job_id: j.id, crew_id: null, start_minute: null }));
    return moves.length > 0 ? { moves } : null;
  }

  const member = crew.find((c) => c.id === drop.laneId);
  if (!member) return null;
  const avail = availability.find((a) => a.crew_id === member.id);
  if (avail?.status === "Off") return { refused: `${member.name} cannot take work this day. ${avail.reason}`.trim() };
  if (moving.length > 1 && moving.some((j) => j.start_minute === null)) {
    return { refused: "Cards with no time yet cannot be moved as a group. Take them out of the selection first." };
  }

  const wins = windowsOf(member, avail);
  const top = wins.length > 0 ? wins[0].start : 0;
  const laneJobs = jobs
    .filter((j) => j.crew_id === member.id && j.start_minute !== null)
    .sort(byStart);
  // A single card stays in the lane list, so a move within its own lane closes the gap it leaves.
  const laneArg = moving.length === 1 ? laneJobs : laneJobs.filter((j) => !movingIds.has(j.id));
  const others = laneArg.filter((j) => j.id !== draggedId);
  const pos = new Map<string, number>(others.map((j, i) => [j.id, i] as [string, number]));
  // The drop index counts the cards drawn in the lane, the held card left out. Insert after the last of them that is in `others`.
  const drawn = laneJobs.filter((j) => j.id !== draggedId && shown(j));
  let at = 0;
  for (let k = Math.min(drop.index, drawn.length); k > 0; k--) {
    const p = pos.get(drawn[k - 1].id);
    if (p !== undefined) { at = p + 1; break; }
  }

  // Only a card moved within its own lane keeps its old time (planInsertion closes the gap it leaves). Any other card starts at the drop.
  const stays = moving.length === 1 && member.id === dragged.crew_id && dragged.start_minute !== null;
  const anchor: LaneCard = { id: draggedId, start: stays ? dragged.start_minute! : 0, duration: dragged.duration_minutes };
  let plan: DropPlan;
  if (folded.has(member.id)) {
    // A folded lane has no cards to drop among: the card takes the member's first free time.
    const start = freeStart(wins, others, 0, dragged.duration_minutes, step);
    if (start === null) return { refused: `${member.name} has no free ${dragged.duration_minutes} minutes in their slots this day.` };
    plan = { start, shifts: [] };
  } else {
    const slot = slotUnder(drop.laneEl, drop.clientY);
    const lane = laneArg.map(toLane);
    plan = slot
      ? planFreeDrop(lane, anchor, slotTime(slot, drop.clientY, dragged.duration_minutes, step), at, { top, step })
      : planInsertion(lane, anchor, at, { top, step });
  }

  if (moving.length === 1) {
    if (member.id === dragged.crew_id && plan.start === dragged.start_minute && plan.shifts.length === 0) return null;
    return {
      moves: [
        { job_id: draggedId, crew_id: member.id, start_minute: plan.start },
        ...plan.shifts.map((s) => ({ job_id: s.id, crew_id: member.id, start_minute: s.start })),
      ],
    };
  }

  // A group keeps its relative times from the held card. Its cards fix the lane; the rest of the lane moves out of their way.
  const base = dragged.start_minute ?? 0;
  const placed: LaneCard[] = moving.map((j) => ({
    id: j.id,
    start: Math.max(snapUpMinute(top, step), plan.start + ((j.start_minute ?? 0) - base)),
    duration: j.duration_minutes,
  }));
  const shifts = settleAround(others.map(toLane), placed, top, step);
  return {
    moves: [
      ...placed.map((p) => ({ job_id: p.id, crew_id: member.id, start_minute: p.start })),
      ...shifts.map((s) => ({ job_id: s.id, crew_id: member.id, start_minute: s.start })),
    ],
  };
}

export interface CardBoardProps {
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
  /** Off, the filters hide the cards they do not keep; on, those cards show in disabled form (P1-4). */
  showAll?: boolean;
  onOpen: (job: AdminJob) => void;
  onMove: (job: AdminJob, crewId: string | null, startMinute: number | null) => void;
  /** Gets the error of a refused drop (a frozen day offers the code), or null once a drop is saved. */
  onDropSettled?: (error: unknown) => void;
}

type GridProps = CardBoardProps & {
  folded: Set<string>;
  toggleFold: (id: string) => void;
  picked: Set<string>;
  setPicked: Dispatch<SetStateAction<Set<string>>>;
  /** The warnings of the last saved move, by job (crew hours, service hours). Shown in red; the move stands. */
  warned: Map<string, string>;
};

/**
 * The chosen day as columns of job cards, like a task board: the jobs with no
 * crew member first, then one column for each crew member with that member's
 * jobs and free slots in time order. A card is dragged with the drag engine
 * (dnd/): a ghost follows the pointer, the card's neighbours shift to show where
 * it lands, and a drop saves at once with no confirmation (P0-1, decision 4).
 * Dropping a card between two cards pushes the cards below it down; every card
 * it moves is marked By hand (P0-5). Dropping on Unscheduled takes the card off
 * its crew member, and a card from Unscheduled can go to any place in a lane (P0-7).
 * A card's checkbox picks it for a group move (P0-8). Clicking a card opens its
 * dialog to set an exact time. A crew member who cannot work that day is greyed
 * out and takes no card (ADM-SCH-32, -33). The filters hide the cards they do not
 * keep; "Show all" brings them back in disabled form (P1-4). A hidden card still
 * takes its time in its column.
 */
export function CardBoard(props: CardBoardProps) {
  const { crew, jobs, availability, focus, search, type = "", flag = "", density = "standard", showAll = false, onDropSettled } = props;
  const [folded, toggleFold] = useFoldedLanes();
  const [picked, setPicked] = useState<Set<string>>(() => new Set());
  const [warned, setWarned] = useState<Map<string, string>>(() => new Map());
  const step = stepOf(density);
  const plan = (drop: DropHit, item: DragItem): DropOutcome => planBoardMoves({
    drop, draggedId: item.id, picked, jobs, crew, availability, folded, step,
    shown: (j) => isShown(j, showAll, focus, search, type, flag),
  });
  // The board query of this schedule: the optimistic move and the refresh use it.
  const boardKey = ["board", "id", jobs[0]?.schedule_id];
  return (
    <DragEngineProvider
      boardKey={boardKey}
      plan={plan}
      onSaved={(r) => {
        setPicked(new Set());
        setWarned(new Map<string, string>(r.warnings.map((w) => [w.job_id, w.message] as [string, string])));
      }}
      onSettled={onDropSettled}
    >
      <CardGrid {...props} folded={folded} toggleFold={toggleFold} picked={picked} setPicked={setPicked} warned={warned} />
    </DragEngineProvider>
  );
}

function CardGrid({ crew, jobs, availability, focus, search, type = "", flag = "", density = "standard", savingId = null, showAll = false,
  onOpen, onMove, folded, toggleFold, picked, setPicked, warned }: GridProps) {
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
  const { activeId: dragId, hit } = useDragState();
  const [blocked, setBlocked] = useState("");
  const root = useRef<HTMLDivElement>(null);
  const strip = useRef<HTMLDivElement | null>(null);
  const pan = useRef<{ x: number; left: number } | null>(null);
  const [panning, setPanning] = useState(false);
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
  const unplaced = unscheduledOrder(jobs.filter(isUnplaced));
  const dragged = dragId ? jobs.find((j) => j.id === dragId) ?? null : null;
  const warnings = [...new Set(warned.values())];
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

  const togglePick = (id: string) => setPicked((cur) => {
    const next = new Set(cur);
    if (next.has(id)) next.delete(id); else next.add(id);
    return next;
  });

  /** The delete icon takes a placed job off its crew member for the day; it goes to Unscheduled, nothing is deleted (item 6). */
  const takeOff = async (job: AdminJob) => {
    if (await confirm({
      title: `Take ${job.registration} off the day?`,
      description: `The job goes to Unscheduled for this day. It is not deleted: you can place it again later.`,
      confirmLabel: "Take off the day", tone: "danger",
    })) onMove(job, null, null);
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
    // A card the filters do not keep is shown only with "Show all" on, and then it is disabled: no drag, no dialog.
    const kept = matches(job, focus, search, type, flag);
    const open = isOpen(job) && kept;
    const wine = breached(job);
    const tools = job.placed_by_hand || (open && job.crew_id);
    const isPicked = picked.has(job.id);
    const warning = warned.get(job.id);
    const outline = warning ? "2px solid var(--c-error)" : isPicked ? "2px solid var(--c-gold)" : undefined;
    return (
      <DragSource key={job.id} id={job.id} data={job} disabled={!open}>
        {(drag) => (
          <div data-card data-dnd-card={job.id} data-job={job.id} role="button" tabIndex={0}
               draggable={open ? undefined : false}
               aria-disabled={!kept || undefined} aria-label={jobLabel(job)} aria-busy={savingId === job.id || undefined}
               title={`${job.start_time ? `${job.start_time}-${job.end_time} ` : ""}${job.vehicle}, ${job.service}.${job.parking ? ` ${job.parking}.` : ""} ${job.status}${job.reason ? `. ${job.reason}` : ""}${wine ? ` Placed by hand against a rule: ${(job.hand_breaches ?? []).join(" ")}` : ""}${open && job.crew_id ? ` Alt and the up or down arrow move it ${step} minutes.` : ""}${warning ? ` ${warning}` : ""}`}
               style={outline ? { outline, outlineOffset: "1px" } : undefined}
               className={cn("sch-card", typeClass(job), statusClass(job), density, isSpa(job) && "spa", job.late && "late", job.manual && "manual",
                 wine && "wine", !kept && "dim", drag.dragging && "dragging", !open && "locked",
                 savingId === job.id && "saving", tools && "has-tools")}
               onPointerDown={drag.onPointerDown}
               onClick={() => { if (kept) onOpen(job); }}
               onKeyDown={(e) => {
                 if (!kept) return;
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
            {open && (
              // The checkbox sits at the top right. It picks the card for a group move and never opens the card.
              <span className="absolute right-1 top-1 z-[1] leading-none" onClick={(e) => e.stopPropagation()}
                    onKeyDown={(e) => e.stopPropagation()}>
                <input type="checkbox" className="m-0 h-3.5 w-3.5 cursor-pointer" checked={isPicked}
                       aria-label="Select this job" title="Select to move together with the other selected cards"
                       onChange={() => togglePick(job.id)} />
              </span>
            )}
            {tools && job.placed_by_hand && (() => {
              // The lock sits at the top right, on its own, and moves below the checkbox when the card has one. It never opens the card.
              const locked = job.hand_locked === true;
              const tip = locked ? LOCK_TIP.locked : LOCK_TIP.unlocked;
              return (
                <span className="sch-card-lock" style={open ? { top: "1.35rem" } : undefined}
                      onClick={(e) => e.stopPropagation()}
                      onKeyDown={(e) => e.stopPropagation()} onDragStart={(e) => e.preventDefault()}>
                  <button type="button" className={`sch-tool lock ${locked ? "is-locked" : "is-open"}`}
                          aria-pressed={locked} aria-disabled={!open || undefined}
                          aria-label={tip} title={tip}
                          onClick={() => { if (open) lockOf.mutate({ job, locked: !locked }); }}>
                    <LockGlyph locked={locked} />
                  </button>
                </span>
              );
            })()}
            {tools && (
              // The take-off icon sits at the bottom right (standard and detailed) or the right (compact). It never opens the card.
              <span className="sch-card-tools" onClick={(e) => e.stopPropagation()}
                    onKeyDown={(e) => e.stopPropagation()} onDragStart={(e) => e.preventDefault()}>
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
        )}
      </DragSource>
    );
  };

  /** A member's day in time order: cards, free slots and the time between slots. */
  const lane = (member: SchedulingCrew, mine: AdminJob[], wins: { start: number; end: number }[], brk: { start: number; end: number } | null) => {
    // The card being moved does not block its own slot, so it can go back to where it was or a step either side.
    const others = mine.filter((j) => j.id !== dragId);
    const items: { start: number; node: () => ReactNode; card?: AdminJob }[] = [
      ...mine.map((j) => ({ start: j.start_minute!, card: j, node: () => card(j) })),
      ...freeSlots(aroundBreak(wins, brk), others).map((g) => ({ start: g.start, node: () => {
        const tight = dragged !== null && g.end - g.start < dragged.duration_minutes;
        return (
          <div key={`free-${g.start}`} data-slot data-start={g.start} data-end={g.end}
               className={cn("sch-slot", tight && "tight")} style={{ height: gapHeight(g.end - g.start) }}
               aria-label={`Free ${hhmm(g.start)}-${hhmm(g.end)}`}>
            <span>{tight ? `Too short for ${dragged?.duration_minutes} min` : `Free ${hhmm(g.start)}-${hhmm(g.end)}`}</span>
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

  /** The items of a column, with a line where the held card would go between cards. A card the filters hide is left out. */
  const withLine = (col: string, items: { node: () => ReactNode; card?: AdminJob }[]) => {
    const out: ReactNode[] = [];
    // The engine counts the drawn cards of the lane, the held card left out; this line sits at that index.
    const lineAt = hit?.laneId === col ? hit.index : -1;
    let at = 0;
    for (const it of items) {
      if (it.card && !isShown(it.card, showAll, focus, search, type, flag)) continue;
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
      <Scroller wrapClassName="sch-board-wrap" innerRef={strip} className={cn("sch-board", density, panning && "panning")} role="group" aria-label="Day board"
                onPointerDown={panStart} onPointerMove={panMove} onPointerUp={panEnd} onPointerCancel={panEnd} onWheel={wheel}>
        {folded.has(UNSCHEDULED) ? (
          // A folded Unscheduled lane is a thin strip; a card dropped on it is taken off its crew member, as on the open lane.
          <section aria-label={`Unscheduled (${unplaced.length}), folded`} data-testid="col-unscheduled" data-dnd-lane={UNSCHEDULED}
                   className={cn("sch-col unscheduled folded", hit?.laneId === UNSCHEDULED && "over")}>
            <button type="button" className="sch-fold-btn" aria-label="Show the Unscheduled lane" title="Show the lane"
                    onClick={() => toggleFold(UNSCHEDULED)}>
              <ChevronsRight aria-hidden />
            </button>
            <span className="sch-count">{unplaced.length}</span>
            <span className="sch-fold-name">Unscheduled</span>
          </section>
        ) : (
        <section aria-label={`Unscheduled (${unplaced.length})`} data-testid="col-unscheduled"
                 className={cn("sch-col unscheduled", hit?.laneId === UNSCHEDULED && "over", dragged?.crew_id && "can")}>
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
          <Scroller axis="y" wrapClassName="sch-col-scroll" className="sch-col-body" data-dnd-lane={UNSCHEDULED}>
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
          const state = cn("sch-col", closed && "closed", hit?.laneId === member.id && "over",
            takes(member) === true && "can", takes(member) === false && "cannot");
          if (fold) {
            // A folded lane is a thin strip: name, jobs and use. A card dropped on it goes to its first free time.
            return (
              <section key={member.id} aria-label={`${member.name}, folded`} data-testid={`col-${member.id}`} data-dnd-lane={member.id}
                       className={cn(state, "folded")}>
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
              <Scroller axis="y" wrapClassName="sch-col-scroll" className="sch-col-body" data-dnd-lane={member.id}>
                {closed ? <p className="sch-col-empty">{avail?.reason || "Cannot take work this day."}</p>
                  : lane(member, mine, wins, brk)}
              </Scroller>
            </section>
          );
        })}
      </Scroller>
      {blocked && <p className="mt-2 mb-0 text-sm text-destructive" role="alert">{blocked}</p>}
      {warnings.length > 0 && (
        <p className="mt-2 mb-0 text-sm text-destructive" data-testid="board-warnings">{warnings.join(" ")}</p>
      )}
    </div>
  );
}
