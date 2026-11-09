import { describe, expect, it } from "vitest";

import { insertionIndex, laneOrder, minuteAt, planFreeDrop, planInsertion, snapMinute, snapUpMinute, type LaneCard } from "./geometry";

// Cards 1 to 5 back to back in one lane, each 60 minutes, from 09:00 (540).
const lane = (): LaneCard[] => [1, 2, 3, 4, 5].map((n) => ({ id: String(n), start: 540 + (n - 1) * 60, duration: 60 }));
const order = (cards: { id: string; start: number }[]) => [...cards].sort((a, b) => a.start - b.start).map((c) => c.id);

/** The lane after a plan: the dragged card at its start, the others at their shifted or unchanged start. */
function apply(cards: LaneCard[], dragged: LaneCard, plan: ReturnType<typeof planInsertion>) {
  const starts = new Map(plan.shifts.map((s) => [s.id, s.start]));
  return [
    ...cards.filter((c) => c.id !== dragged.id).map((c) => ({ id: c.id, start: starts.get(c.id) ?? c.start })),
    { id: dragged.id, start: plan.start },
  ];
}

describe("snapping", () => {
  it("rounds to the nearest 5 minutes", () => {
    expect(snapMinute(7)).toBe(5);
    expect(snapMinute(8)).toBe(10);
    expect(snapMinute(12)).toBe(10);
    expect(snapMinute(13)).toBe(15);
    expect(snapMinute(15, 15)).toBe(15);
  });

  it("rounds up to the next step for a start that must not overlap the card above", () => {
    expect(snapUpMinute(61)).toBe(65);
    expect(snapUpMinute(60)).toBe(60);
    expect(snapUpMinute(61, 15)).toBe(75);
  });

  it("maps a timeline pointer to a snapped minute", () => {
    // 1 px per minute, the axis starts at 09:00 (540) at y = 100.
    expect(minuteAt(100 + 7, { top: 100, pxPerMinute: 1, dayStart: 540 })).toBe(545);
    expect(minuteAt(100 + 8, { top: 100, pxPerMinute: 1, dayStart: 540 })).toBe(550);
  });
});

describe("insertion index", () => {
  const rects = [
    { id: "a", top: 0, height: 40 },
    { id: "b", top: 40, height: 40 },
    { id: "c", top: 80, height: 40 },
  ];

  it("counts the cards whose middle is above the pointer", () => {
    expect(insertionIndex(rects, 5)).toBe(0);
    expect(insertionIndex(rects, 30)).toBe(1);
    expect(insertionIndex(rects, 200)).toBe(3);
  });

  it("leaves the dragged card out of the count", () => {
    expect(insertionIndex(rects, 200, "c")).toBe(2);
  });

  it("orders a lane by start, without the dragged card", () => {
    expect(laneOrder(lane(), "2").map((c) => c.id)).toEqual(["1", "3", "4", "5"]);
  });
});

describe("planInsertion", () => {
  it("drag 2 between 4 and 5 gives 1 3 4 2 5, with 3 and 4 moved up", () => {
    const cards = lane();
    const dragged = cards[1];
    // Others in time order: 1, 3, 4, 5. Between 4 and 5 is index 3.
    const plan = planInsertion(cards, dragged, 3, { top: 540 });
    expect(plan.shifts).toEqual([{ id: "3", start: 600 }, { id: "4", start: 660 }]);
    expect(plan.start).toBe(720);
    const result = apply(cards, dragged, plan);
    expect(order(result)).toEqual(["1", "3", "4", "2", "5"]);
    // 5 stayed where it was: it did not overlap.
    expect(result.find((c) => c.id === "5")!.start).toBe(780);
  });

  it("drop at the top moves the cards in the way down, one after another", () => {
    const cards = lane();
    const dragged = cards[3]; // card 4
    const plan = planInsertion(cards, dragged, 0, { top: 540 });
    expect(plan.start).toBe(540);
    expect(plan.shifts).toEqual([
      { id: "1", start: 600 }, { id: "2", start: 660 }, { id: "3", start: 720 },
    ]);
    expect(order(apply(cards, dragged, plan))).toEqual(["4", "1", "2", "3", "5"]);
  });

  it("drop at the bottom pulls the cards up into the gap and starts after the last card", () => {
    const cards = lane();
    const dragged = cards[0]; // card 1
    const plan = planInsertion(cards, dragged, 4, { top: 540 });
    expect(plan.start).toBe(780);
    expect(plan.shifts).toEqual([
      { id: "2", start: 540 }, { id: "3", start: 600 }, { id: "4", start: 660 }, { id: "5", start: 720 },
    ]);
    expect(order(apply(cards, dragged, plan))).toEqual(["2", "3", "4", "5", "1"]);
  });

  it("a card dropped where it already is keeps its time and moves nothing", () => {
    const cards = lane();
    const dragged = cards[2]; // card 3, index 2 among the others
    const plan = planInsertion(cards, dragged, 2, { top: 540 });
    expect(plan.shifts).toEqual([]);
    expect(plan.start).toBe(660);
  });

  it("pulls a card up by the dragged card's length, never onto the card above it", () => {
    // 1 at 09:00-10:00, 2 at 10:30-11:30 (a gap), 3 at 12:00-13:00.
    const cards: LaneCard[] = [
      { id: "1", start: 540, duration: 60 },
      { id: "2", start: 630, duration: 60 },
      { id: "3", start: 720, duration: 60 },
    ];
    const dragged = cards[1];
    // Drop 2 after 3. 3 moves up by 2's length (60) to 11:00; 2 starts where 3 ends (12:00).
    const plan = planInsertion(cards, dragged, 2, { top: 540 });
    expect(plan.shifts).toEqual([{ id: "3", start: 660 }]);
    expect(plan.start).toBe(720);
  });

  it("starts at the top of the lane when it is the first card", () => {
    const cards: LaneCard[] = [{ id: "x", start: 600, duration: 30 }];
    const plan = planInsertion(cards, { id: "d", start: 900, duration: 30 }, 0, { top: 540 });
    // 540-570 is free, so x (at 600) does not move.
    expect(plan.start).toBe(540);
    expect(plan.shifts).toEqual([]);
  });
});

describe("planFreeDrop (a time in a free gap)", () => {
  it("starts at the snapped minute and moves nothing when the gap is clear", () => {
    const cards = lane();
    const plan = planFreeDrop(cards.slice(0, 2), { id: "x", start: 0, duration: 30 }, 1000 + 2, 2, { top: 540 });
    expect(plan).toEqual({ start: 1000, shifts: [] });
  });

  it("falls back to insertion when the time overlaps another card", () => {
    const cards = lane();
    const dragged = { id: "9", start: 0, duration: 60 };
    const plan = planFreeDrop(cards, dragged, 600, 1, { top: 540 });
    expect(plan.shifts.length).toBeGreaterThan(0);
    expect(plan.start).toBe(600); // end of card 1
  });
});
