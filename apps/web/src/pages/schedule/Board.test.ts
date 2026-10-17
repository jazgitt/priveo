import { describe, expect, it } from "vitest";

import { fitsAt, freeSlots, freeStart, gaps, hm, matches } from "./Board";
import type { AdminJob } from "./api";

const at = (start: number, duration = 20) => ({ start_minute: start, duration_minutes: duration } as AdminJob);
const day = [{ start: 480, end: 720 }];

describe("where a dropped card goes (ADM-SCH-33)", () => {
  it("takes the first free time of the day when dropped at the top", () => {
    expect(freeStart(day, [], 0, 20)).toBe(480);
    expect(freeStart(day, [at(480), at(500)], 0, 20)).toBe(520);
  });

  it("takes the first free time after the card above it", () => {
    expect(freeStart(day, [at(480), at(600)], 1, 20)).toBe(500);
    expect(freeStart(day, [at(480), at(600)], 2, 20)).toBe(620);
  });

  it("skips a gap that is too short and snaps to 5 minutes", () => {
    expect(freeStart(day, [at(480, 20), at(510, 20)], 1, 20)).toBe(530);
    expect(freeStart(day, [at(480, 17)], 1, 20)).toBe(500);
  });

  it("keeps the job inside the member's slots", () => {
    const split = [{ start: 480, end: 540 }, { start: 600, end: 660 }];
    expect(freeStart(split, [at(480, 40), at(520, 20)], 2, 20)).toBe(600);
  });

  it("falls back to the earliest free time when nothing is free after the card above", () => {
    expect(freeStart(day, [at(500), at(700)], 2, 30)).toBe(520);
  });

  it("gives null when the job fits nowhere", () => {
    expect(freeStart([{ start: 480, end: 500 }], [], 0, 30)).toBeNull();
    expect(freeStart([], [], 0, 20)).toBeNull();
  });
});

describe("free slots on the card board (ADM-SCH-33)", () => {
  it("lists the free time of each slot around the jobs", () => {
    const split = [{ start: 480, end: 600 }, { start: 660, end: 720 }];
    expect(freeSlots(split, [at(480), at(540, 30), at(660)])).toEqual([
      { start: 500, end: 540 }, { start: 570, end: 600 }, { start: 680, end: 720 }]);
    expect(freeSlots(day, [])).toEqual(day);
    expect(freeSlots(day, [at(480, 238)])).toEqual([]);
  });

  it("checks a start time against the slots and the other jobs", () => {
    expect(fitsAt(day, [at(500)], 520, 20)).toBe(true);
    expect(fitsAt(day, [at(500)], 510, 20)).toBe(false);
    expect(fitsAt(day, [], 710, 20)).toBe(false);
  });

  it("writes minutes as hours and minutes", () => {
    expect(hm(45)).toBe("45 min");
    expect(hm(360)).toBe("6 h");
    expect(hm(200)).toBe("3 h 20 min");
  });
});

describe("board helpers", () => {
  it("finds the time outside the working slots", () => {
    expect(gaps([{ start: 480, end: 600 }], 300, 720)).toEqual([{ start: 300, end: 480 }, { start: 600, end: 720 }]);
  });

  it("matches a vehicle search without spaces or case, and the status picked", () => {
    const job = { registration: "KA 01 AB 1234", parking: "B1-24", status: "Scheduled" } as AdminJob;
    expect(matches(job, "", "ab12")).toBe(true);
    expect(matches(job, "", "b1-2")).toBe(true);
    expect(matches(job, "", "zz")).toBe(false);
    expect(matches(job, "Completed", "")).toBe(false);
  });
});
