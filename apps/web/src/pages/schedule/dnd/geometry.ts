// Pure drop maths for the drag engine (no DOM, no React), so it can be unit-tested.
// Times are minutes after midnight, as the scheduler stores them.

/** The board snaps every drop to this many minutes (decision 10 for the timeline). */
export const SNAP_MINUTES = 5;

/** The nearest multiple of `step`. */
export function snapMinute(minute: number, step = SNAP_MINUTES): number {
  return Math.round(minute / step) * step;
}

/** The first multiple of `step` at or after `minute`. Used so a card never starts inside the card above it. */
export function snapUpMinute(minute: number, step = SNAP_MINUTES): number {
  return Math.ceil(minute / step) * step;
}

/** A placed card in one crew lane: where it starts and how long it lasts. */
export interface LaneCard {
  id: string;
  start: number;
  duration: number;
}

/** A card whose start time changes because of a drop. */
export interface Shift {
  id: string;
  start: number;
}

/** The result of a drop: where the dragged card starts, and every other card that must move. */
export interface DropPlan {
  start: number;
  /** Changed cards only, in lane order. Each one becomes "By hand" on the server (decision 5). */
  shifts: Shift[];
}

export const byStart = (a: LaneCard, b: LaneCard) => a.start - b.start || (a.id < b.id ? -1 : a.id > b.id ? 1 : 0);

/** The lane in time order, with the dragged card left out. */
export function laneOrder(cards: LaneCard[], excludeId?: string): LaneCard[] {
  return cards.filter((c) => c.id !== excludeId).sort(byStart);
}

/**
 * The position a card dropped at height `y` takes among the cards in its lane:
 * the number of cards whose middle is above the pointer. `rects` are the cards
 * in DOM (lane) order with their top and height; the dragged card is skipped.
 */
export function insertionIndex(rects: { id: string; top: number; height: number }[], y: number, excludeId?: string): number {
  return rects.filter((r) => r.id !== excludeId && r.top + r.height / 2 < y).length;
}

/** The minute under a pointer on a time axis (the timeline), snapped to `step`. */
export function minuteAt(y: number, axis: { top: number; pxPerMinute: number; dayStart: number }, step = SNAP_MINUTES): number {
  return snapMinute(axis.dayStart + (y - axis.top) / axis.pxPerMinute, step);
}

/**
 * Plans a drop of `dragged` into a lane at position `index` (0 is the top, the
 * number of cards is the bottom), among the other cards of the lane.
 *
 * Rules (decision 5, P0-5):
 * - Removing the dragged card from its old place pulls the cards between that
 *   place and the drop position up by its length, never by more than that, and
 *   never onto the card above them (gaps are kept where they are).
 * - The dragged card starts at the end of the card above the drop position
 *   (the window start at the top of the lane).
 * - Cards below the drop position move down only where they overlap, one after
 *   another, until a card no longer overlaps. The rest of the lane stays put.
 *
 * Example: cards 1 2 3 4 5 back to back, drag 2 to the slot between 4 and 5:
 * 3 and 4 move up by 2's length and 2 starts where 4 ends (1 3 4 2 5).
 *
 * `top` is the first minute the lane can use (the start of its first working window).
 * `dragged.start` is where the card is now (used when it stays in the same place).
 */
export function planInsertion(
  lane: LaneCard[],
  dragged: LaneCard,
  index: number,
  opts: { top: number; step?: number },
): DropPlan {
  const step = opts.step ?? SNAP_MINUTES;
  // The others in time order; the dragged card's old index is how many of them come before it.
  const sorted = [...lane].sort(byStart);
  const found = sorted.findIndex((c) => c.id === dragged.id);
  const others = sorted.filter((c) => c.id !== dragged.id).map((c) => ({ ...c }));
  const oldIndex = found < 0 ? others.length : found;
  const at = Math.max(0, Math.min(others.length, Math.floor(index)));
  const changed = new Map<string, number>();
  const set = (c: LaneCard, start: number) => {
    if (start !== c.start) changed.set(c.id, start);
    c.start = start;
  };

  // 1. Pull up the cards between the old place and the drop position.
  if (at > oldIndex) {
    for (let j = oldIndex; j < at; j++) {
      const prevEnd = j === 0 ? opts.top : others[j - 1].start + others[j - 1].duration;
      const target = Math.max(snapUpMinute(prevEnd, step), snapUpMinute(others[j].start - dragged.duration, step));
      if (target < others[j].start) set(others[j], target);
    }
  }

  // 2. The dragged card goes after the card above the drop position.
  const above = at > 0 ? others[at - 1] : null;
  const anchor = above ? snapUpMinute(above.start + above.duration, step) : snapUpMinute(opts.top, step);
  // Dropped where it already is, the card keeps its own time if that is later than the anchor.
  // Only a card from this same lane keeps its time; a card from another lane takes the anchor.
  const sameLane = found >= 0;
  const start = sameLane && at === oldIndex ? snapUpMinute(Math.max(anchor, dragged.start), step) : anchor;

  // 3. Push down the cards below only where they now overlap.
  let cursor = start + dragged.duration;
  for (let j = at; j < others.length; j++) {
    if (others[j].start >= cursor) break;
    const next = snapUpMinute(cursor, step);
    set(others[j], next);
    cursor = next + others[j].duration;
  }

  const shifts = others.filter((c) => changed.has(c.id)).map((c) => ({ id: c.id, start: changed.get(c.id)! }));
  return { start, shifts };
}

/**
 * A drop at a time in a free gap (the timeline): the card starts at `minute`
 * when nothing overlaps it, so nothing else moves. Otherwise the drop is
 * planned as an insertion at `index`. `null` means it overlaps and no index
 * was given.
 */
export function planFreeDrop(
  lane: LaneCard[],
  dragged: LaneCard,
  minute: number,
  index: number,
  opts: { top: number; step?: number },
): DropPlan {
  const step = opts.step ?? SNAP_MINUTES;
  const start = Math.max(snapMinute(minute, step), snapUpMinute(opts.top, step));
  const clear = lane
    .filter((c) => c.id !== dragged.id)
    .every((c) => start + dragged.duration <= c.start || c.start + c.duration <= start);
  return clear ? { start, shifts: [] } : planInsertion(lane, dragged, index, opts);
}
