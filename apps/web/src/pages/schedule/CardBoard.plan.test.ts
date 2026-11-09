import { describe, expect, it } from "vitest";

import { planBoardMoves, settleAround, type BoardDropInput } from "./CardBoard";
import type { AdminJob, CrewDayAvailability, SchedulingCrew } from "./api";

// The drop maths of the card board, without the DOM: what a drop sends to the batch move.

const crew = [
  { id: "c1", name: "Asha", role: "Member", start_minute: 480, end_minute: 720 },
  { id: "c2", name: "Ravi", role: "Member", start_minute: 480, end_minute: 720 },
] as SchedulingCrew[];

const card = (id: string, extra: Partial<AdminJob> = {}) => ({
  id, registration: `CAR-${id.toUpperCase()}`, crew_id: "c1", crew_name: "Asha", start_minute: 540, start_time: "09:00",
  end_time: "09:20", duration_minutes: 20, status: "Scheduled", service: "Cleaning-External", parking: "", vehicle: "",
  customer_name: "", reason: "", late: false, manual: false, ...extra,
} as AdminJob);

/** A drop with no DOM: no slot under the pointer, and the lane's cards counted by `index`. */
const drop = (laneId: string, index: number) => ({
  laneId, index, clientX: 0, clientY: 0,
  laneEl: { querySelectorAll: () => [] } as unknown as HTMLElement,
});

function input(over: Partial<BoardDropInput> & Pick<BoardDropInput, "drop" | "draggedId" | "jobs">): BoardDropInput {
  return { picked: new Set(), crew, availability: [], folded: new Set(), shown: () => true, step: 5, ...over };
}

describe("planBoardMoves (P0-5, P0-7, P0-8)", () => {
  it("takes a card dropped on Unscheduled off its crew member, with crew_id null and no start time (P0-7)", () => {
    const out = planBoardMoves(input({ drop: drop("unscheduled", 0), draggedId: "a", jobs: [card("a")] }));
    expect(out).toEqual({ moves: [{ job_id: "a", crew_id: null, start_minute: null }] });
  });

  it("gives nothing to do for a card dropped on Unscheduled when it has no crew member already", () => {
    const out = planBoardMoves(input({ drop: drop("unscheduled", 0), draggedId: "u",
      jobs: [card("u", { crew_id: null, crew_name: null, start_minute: null })] }));
    expect(out).toBeNull();
  });

  it("places a card from Unscheduled at the drop in a crew lane", () => {
    const out = planBoardMoves(input({ drop: drop("c2", 0), draggedId: "u",
      jobs: [card("u", { crew_id: null, crew_name: null, start_minute: null })] }));
    expect(out).toEqual({ moves: [{ job_id: "u", crew_id: "c2", start_minute: 480 }] });
  });

  it("refuses a drop on a crew member who cannot work that day, with the reason", () => {
    const off: CrewDayAvailability[] = [{ crew_id: "c2", status: "Off", windows: [], reason: "Sick on this date." }];
    const out = planBoardMoves(input({ drop: drop("c2", 0), draggedId: "a", jobs: [card("a")], availability: off }));
    expect(out).toEqual({ refused: "Ravi cannot take work this day. Sick on this date." });
  });

  it("keeps the relative times of a picked group, and the dragged card lands at the drop (P0-8)", () => {
    const jobs = [card("a"), card("b", { start_minute: 600, start_time: "10:00", end_time: "10:20" })];
    const out = planBoardMoves(input({ drop: drop("c2", 0), draggedId: "a", jobs, picked: new Set(["a", "b"]) }));
    expect(out).toEqual({ moves: [
      { job_id: "a", crew_id: "c2", start_minute: 480 },
      { job_id: "b", crew_id: "c2", start_minute: 540 },
    ] });
  });

  it("does nothing for a drop that changes nothing", () => {
    expect(planBoardMoves(input({ drop: drop("c1", 0), draggedId: "a", jobs: [card("a")] }))).toBeNull();
  });
});

describe("settleAround (P0-8)", () => {
  it("moves only the cards a placed card runs into, down to the first free time after it", () => {
    const others = [{ id: "x", start: 500, duration: 20 }, { id: "y", start: 600, duration: 20 }];
    const fixed = [{ id: "g", start: 490, duration: 30 }];
    expect(settleAround(others, fixed, 480, 5)).toEqual([{ id: "x", start: 520 }]);
  });

  it("changes nothing when no card is in the way", () => {
    expect(settleAround([{ id: "x", start: 600, duration: 20 }], [{ id: "g", start: 480, duration: 60 }], 480, 5)).toEqual([]);
  });
});
