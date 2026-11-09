// Pointer-based drag for the scheduler board (P0-1). It replaces the native
// HTML5 drag: a ghost card follows the pointer, the lanes show where the card
// would land, and a drop saves at once with no confirmation (decision 4). A
// refused drop puts the board back and shows why (commit.ts).
//
// API (import from "./dnd" or "../dnd"):
//
// 1. Wrap every editable board (Cards in all views, Focus, own tab, Timeline) once:
//      <DragEngineProvider boardKey={["board", "id", scheduleId]} plan={planDrop} onSaved={...}>
//    - boardKey: the board query. The optimistic move and the refresh use it.
//    - plan(drop, item): called on drop. `drop` = { laneId, index, laneEl, clientX, clientY };
//      `item` = { id, data } of the dragged card. Return
//        { moves: BatchMove[] }  to save (build them with movesFor() and planInsertion(), or planFreeDrop()),
//        { refused: "text" }     to show a message and leave the board alone,
//        null                    to do nothing.
//    - onSaved(result): optional, gets the warnings of a saved batch (crew or service hours).
//    The provider also re-reads the board when another tab of this browser saves (sync.ts).
//
// 2. Each draggable card:
//      const drag = useDragSource(job.id, job, !editable);
//      <div data-dnd-card={job.id} onPointerDown={drag.onPointerDown} className={drag.dragging ? "..." : ...}>
//    drag.dragging is true for the card being held. A press on a button, link or input inside
//    the card does not start a drag, so the lock and delete icons keep working.
//
// 3. Each lane (a crew column, Unscheduled, a timeline row):
//      <div data-dnd-lane={laneId}> ...cards with data-dnd-card... </div>
//    laneId is any non-empty string the plan understands (crew id, or "unscheduled").
//    The engine finds the lane under the pointer and the index among its cards (drop.index).
//
// 4. Live shift while dragging: useDragState() returns { activeId, hit: { laneId, index } | null }.
//    Render a gap at hit.index in the lane whose laneId matches; the cards below move down with it.
//
// Behaviour: a press must move 5 px before a drag starts (a click still opens the card).
// Touch starts after a 250 ms hold; a move of more than 10 px before that is a scroll. Escape
// or a pointer cancel drops nothing. Outside any lane, nothing is saved.
import {
  createContext, useContext, useEffect, useRef, useState,
  type PointerEvent as ReactPointerEvent, type ReactNode,
} from "react";
import type { QueryKey } from "@tanstack/react-query";
import { toast } from "sonner";

import type { BatchMove, BatchMoveResult } from "../api";
import { useBatchMove } from "./commit";
import { insertionIndex } from "./geometry";

const THRESHOLD_PX = 5;
const TOUCH_HOLD_MS = 250;
const TOUCH_SLOP_PX = 10;

/** The card being dragged. `data` is whatever the card passed to useDragSource. */
export interface DragItem {
  id: string;
  data?: unknown;
}

/** Where the pointer is over a lane when the card is dropped or held. */
export interface DropHit {
  laneId: string;
  /** Position among the lane's cards, the dragged card left out. 0 is the top. */
  index: number;
  laneEl: HTMLElement;
  clientX: number;
  clientY: number;
}

/** What the plan says to do with a drop. */
export type DropOutcome = { moves: BatchMove[] } | { refused: string } | null;

export interface DragEngineProps {
  boardKey: QueryKey;
  plan: (drop: DropHit, item: DragItem) => DropOutcome;
  onSaved?: (result: BatchMoveResult) => void;
  /** Gets the error of a refused drop (for example a frozen day), or null once a drop is saved. */
  onSettled?: (error: unknown) => void;
  children: ReactNode;
}

export interface DragState {
  activeId: string | null;
  hit: { laneId: string; index: number } | null;
}

interface DragContextValue extends DragState {
  begin: (e: ReactPointerEvent<HTMLElement>, item: DragItem) => void;
}

const DragContext = createContext<DragContextValue>({
  activeId: null,
  hit: null,
  begin: () => {},
});

interface Session {
  pointerId: number;
  item: DragItem;
  source: HTMLElement;
  pointerType: string;
  startX: number;
  startY: number;
  x: number;
  y: number;
  active: boolean;
  ghost: HTMLElement | null;
  offsetX: number;
  offsetY: number;
  hold: ReturnType<typeof setTimeout> | null;
  /** The exact listeners added for this press, so they are removed by identity. */
  handlers: { move: (e: PointerEvent) => void; up: (e: PointerEvent) => void; cancel: (e: PointerEvent) => void; key: (e: KeyboardEvent) => void };
}

/** The lane and index under a point, with the dragged card left out of the count. */
function hitAt(x: number, y: number, excludeId: string): DropHit | null {
  // jsdom and some embedded browsers have no hit testing: no lane under the point.
  if (typeof document.elementFromPoint !== "function") return null;
  const el = document.elementFromPoint(x, y) as HTMLElement | null;
  const laneEl = el?.closest<HTMLElement>("[data-dnd-lane]") ?? null;
  const laneId = laneEl?.dataset.dndLane;
  if (!laneEl || !laneId) return null;
  const rects = [...laneEl.querySelectorAll<HTMLElement>("[data-dnd-card]")].map((card) => {
    const r = card.getBoundingClientRect();
    return { id: card.dataset.dndCard ?? "", top: r.top, height: r.height };
  });
  return { laneId, index: insertionIndex(rects, y, excludeId), laneEl, clientX: x, clientY: y };
}

/** The listeners live on the window while a press is held, so they are removed together. */
function detach(s: Session): void {
  window.removeEventListener("pointermove", s.handlers.move);
  window.removeEventListener("pointerup", s.handlers.up);
  window.removeEventListener("pointercancel", s.handlers.cancel);
  window.removeEventListener("keydown", s.handlers.key);
  if (s.hold !== null) clearTimeout(s.hold);
}

export function DragEngineProvider({ boardKey, plan, onSaved, onSettled, children }: DragEngineProps) {
  const planRef = useRef(plan);
  const savedRef = useRef(onSaved);
  const settledRef = useRef(onSettled);
  const [view, setView] = useState<DragState>({ activeId: null, hit: null });
  const session = useRef<Session | null>(null);
  const commit = useBatchMove(boardKey, (r) => savedRef.current?.(r), (e) => settledRef.current?.(e));
  const commitRef = useRef(commit.mutate);
  // Sync is mounted once, by the schedule page (useBoardSync in SchedulePage), not here.

  useEffect(() => {
    planRef.current = plan;
    savedRef.current = onSaved;
    settledRef.current = onSettled;
    commitRef.current = commit.mutate;
  });

  const activate = (s: Session) => {
    if (s.active) return;
    const rect = s.source.getBoundingClientRect();
    const ghost = s.source.cloneNode(true) as HTMLElement;
    ghost.querySelectorAll("[id]").forEach((el) => el.removeAttribute("id"));
    ghost.removeAttribute("id");
    ghost.setAttribute("aria-hidden", "true");
    ghost.style.cssText += `;position:fixed;left:0;top:0;width:${rect.width}px;height:${rect.height}px;margin:0;` +
      `pointer-events:none;z-index:1000;opacity:0.92;box-shadow:0 12px 28px rgba(0,0,0,0.22);` +
      `transform:translate(${rect.left}px,${rect.top}px);`;
    document.body.appendChild(ghost);
    s.ghost = ghost;
    s.offsetX = s.x - rect.left;
    s.offsetY = s.y - rect.top;
    s.active = true;
    s.source.style.opacity = "0.35";
    document.body.style.cursor = "grabbing";
    document.body.style.userSelect = "none";
    setView({ activeId: s.item.id, hit: null });
  };

  /** Removes the ghost and puts the page back the way it was. */
  const clearVisuals = (s: Session) => {
    s.ghost?.remove();
    s.source.style.opacity = "";
    document.body.style.cursor = "";
    document.body.style.userSelect = "";
    setView({ activeId: null, hit: null });
  };

  /** A press that moved was a drag, so the click that ends it must not open the card. */
  const swallowClick = (ev: MouseEvent) => {
    ev.stopPropagation();
    ev.preventDefault();
  };

  const finish = (s: Session, cancelled: boolean, x: number, y: number) => {
    detach(s);
    session.current = null;
    if (!s.active) return;
    window.addEventListener("click", swallowClick, true);
    window.setTimeout(() => window.removeEventListener("click", swallowClick, true), 0);
    const hit = cancelled ? null : hitAt(x, y, s.item.id);
    clearVisuals(s);
    if (!hit) return;
    const outcome = planRef.current(hit, s.item);
    if (!outcome) return;
    if ("refused" in outcome) {
      toast.error(outcome.refused);
      return;
    }
    if (outcome.moves.length > 0) commitRef.current({ moves: outcome.moves });
  };

  function onMove(e: PointerEvent) {
    const s = session.current;
    if (!s || e.pointerId !== s.pointerId) return;
    s.x = e.clientX;
    s.y = e.clientY;
    if (!s.active) {
      const moved = Math.hypot(s.x - s.startX, s.y - s.startY);
      if (s.pointerType === "touch") {
        // A touch that moves before the hold is a scroll: this press is over.
        if (moved > TOUCH_SLOP_PX) finish(s, true, s.x, s.y);
        return;
      }
      if (moved < THRESHOLD_PX) return;
      activate(s);
    }
    e.preventDefault();
    if (s.ghost) s.ghost.style.transform = `translate(${s.x - s.offsetX}px, ${s.y - s.offsetY}px)`;
    const hit = hitAt(s.x, s.y, s.item.id);
    setView((v) => {
      const next = hit ? { laneId: hit.laneId, index: hit.index } : null;
      const same = (v.hit === null && next === null) ||
        (v.hit !== null && next !== null && v.hit.laneId === next.laneId && v.hit.index === next.index);
      return same ? v : { activeId: v.activeId, hit: next };
    });
  }

  function onUp(e: PointerEvent) {
    const s = session.current;
    if (s && e.pointerId === s.pointerId) finish(s, false, e.clientX, e.clientY);
  }

  function onCancel(e: PointerEvent) {
    const s = session.current;
    if (s && e.pointerId === s.pointerId) finish(s, true, e.clientX, e.clientY);
  }

  function onKey(e: KeyboardEvent) {
    const s = session.current;
    if (s && e.key === "Escape") finish(s, true, s.x, s.y);
  }

  const begin = (e: ReactPointerEvent<HTMLElement>, item: DragItem) => {
    if (session.current || e.button !== 0) return;
    const target = e.target as HTMLElement;
    if (target.closest("button,a,input,select,textarea,label,[contenteditable=true],[data-dnd-ignore]")) return;
    const s: Session = {
      pointerId: e.pointerId, item, source: e.currentTarget, pointerType: e.pointerType,
      startX: e.clientX, startY: e.clientY, x: e.clientX, y: e.clientY,
      active: false, ghost: null, offsetX: 0, offsetY: 0, hold: null,
      handlers: { move: onMove, up: onUp, cancel: onCancel, key: onKey },
    };
    session.current = s;
    window.addEventListener("pointermove", s.handlers.move);
    window.addEventListener("pointerup", s.handlers.up);
    window.addEventListener("pointercancel", s.handlers.cancel);
    window.addEventListener("keydown", s.handlers.key);
    if (e.pointerType === "touch") {
      s.hold = setTimeout(() => {
        s.hold = null;
        if (session.current === s && !s.active) activate(s);
      }, TOUCH_HOLD_MS);
    }
  };

  // Unmounting in the middle of a drag removes the ghost and the listeners.
  useEffect(() => () => {
    const s = session.current;
    if (!s) return;
    detach(s);
    session.current = null;
    s.ghost?.remove();
    s.source.style.opacity = "";
    document.body.style.cursor = "";
    document.body.style.userSelect = "";
  }, []);

  const value: DragContextValue = { activeId: view.activeId, hit: view.hit, begin };
  return <DragContext.Provider value={value}>{children}</DragContext.Provider>;
}

/**
 * For a draggable card. Spread `onPointerDown` on the card element and put
 * `data-dnd-card={id}` on it. `dragging` is true while this card is held.
 */
export function useDragSource(id: string, data?: unknown, disabled = false) {
  const ctx = useContext(DragContext);
  const onPointerDown = (e: ReactPointerEvent<HTMLElement>) => {
    if (disabled) return;
    ctx.begin(e, { id, data });
  };
  return { onPointerDown, dragging: ctx.activeId === id };
}

/** The drag in progress: which card is held, and the lane and index it would land in. */
export function useDragState(): DragState {
  const ctx = useContext(DragContext);
  return { activeId: ctx.activeId, hit: ctx.hit };
}
