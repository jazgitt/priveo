import { describe, expect, it } from "vitest";

import { slotTime } from "./CardBoard";
import {
  breached, cardLines, clashMessage, clashOf, freeStart, matches, parkingPlace, stepOf, typeClass,
} from "./Board";
import type { AdminJob } from "./api";

const base = {
  id: "j1", registration: "KA01AB1234", vehicle: "Honda City", parking: "Zone 3 · B1-24", zone: "Zone 3",
  customer_name: "Meena", crew_name: "Asha", service: "Cleaning-External", status: "Scheduled",
  duration_minutes: 20, start_minute: 540, start_time: "09:00", end_time: "09:20", finish_by: "10:00",
  late: false, manual: false, reason: "", crew_id: "c1",
} as AdminJob;

/** The text of each line, one string per line of the card. */
const lines = (job: AdminJob, density: "compact" | "standard" | "detailed") =>
  cardLines(job, density).map((line) => line.map((p) => p.text).join(" | "));

describe("card lines by layout (owner review, 8-Nov-26)", () => {
  it("detailed: zone, make and model and cutoff; EXT and slot; car number and customer", () => {
    expect(lines(base, "detailed")).toEqual([
      "Zone 3 | Honda City | Cutoff 10:00",
      "EXT | 09:00-09:20",
      "KA01AB1234 | Meena",
    ]);
  });

  it("standard: zone, car number and cutoff; EXT and slot", () => {
    expect(lines(base, "standard")).toEqual(["Zone 3 | KA01AB1234 | Cutoff 10:00", "EXT | 09:00-09:20"]);
  });

  it("compact: zone, EXT or INT and cutoff on one line", () => {
    expect(lines(base, "compact")).toEqual(["Zone 3 | EXT | Cutoff 10:00"]);
  });

  it("drops a piece that is missing rather than showing a blank", () => {
    const bare = { ...base, zone: "", finish_by: null, customer_name: "" } as unknown as AdminJob;
    expect(lines(bare, "detailed")).toEqual(["Honda City", "EXT | 09:00-09:20", "KA01AB1234"]);
  });

  it("shows the duration in place of the slot for a job with no time yet", () => {
    const unplaced = { ...base, start_time: null, end_time: null, crew_id: null, start_minute: null } as AdminJob;
    expect(lines(unplaced, "standard")[1]).toBe("EXT | 20 min");
  });

  it("gives the same kind of piece the same kind on every size", () => {
    const kinds = (d: "compact" | "standard" | "detailed") => cardLines(base, d).flat().map((p) => p.kind);
    expect(kinds("compact")).toContain("zone");
    expect(kinds("standard")).toContain("zone");
    expect(kinds("detailed")).toContain("zone");
    expect(kinds("standard")).toContain("reg");
    expect(kinds("detailed")).toContain("reg");
  });
});

describe("the zone search (ADM-SCH-33)", () => {
  it("finds a job by its zone", () => {
    expect(matches(base, "", "z3")).toBe(true);
    expect(matches(base, "", "zone 3")).toBe(true);
    expect(matches(base, "", "zone 9")).toBe(false);
  });
});

describe("a card placed by hand against a rule (SCHS-22)", () => {
  it("is wine only when a breach is stored for it", () => {
    expect(breached({ ...base, hand_breaches: ["That time is outside the crew member's hours."] } as AdminJob)).toBe(true);
    expect(breached({ ...base, hand_breaches: [] } as AdminJob)).toBe(false);
    expect(breached(base)).toBe(false);
  });

  it("keeps the kind of work's colour when nothing is breached", () => {
    expect(typeClass(base)).toBe("t-ext");
  });

  it("takes the parking place without the zone in front", () => {
    expect(parkingPlace(base)).toBe("B1-24");
    expect(parkingPlace({ ...base, parking: "B1-24" } as AdminJob)).toBe("B1-24");
  });
});

describe("a drop that overlaps a job is refused (ADM-SCH-33)", () => {
  const other = { ...base, id: "j2", registration: "KA02ZZ0001", start_minute: 540, start_time: "09:00", end_time: "09:20", duration_minutes: 20 } as AdminJob;

  it("finds the job in the way", () => {
    expect(clashOf([other], 550, 20)?.registration).toBe("KA02ZZ0001");
    expect(clashOf([other], 560, 20)).toBeNull();
  });

  it("names that job and suggests a time that is free", () => {
    const day = [{ start: 480, end: 720 }];
    const msg = clashMessage({ ...base, registration: "KA01AB1234" } as AdminJob, other, "Asha", freeStart(day, [other], 0, 20, 5));
    expect(msg).toBe("KA01AB1234 cannot go there: KA02ZZ0001 (09:00-09:20) is in the way for Asha. Try 08:00 instead.");
  });

  it("asks for another time when no time is free", () => {
    expect(clashMessage(base, other, "Asha", null)).toContain("Please try another time.");
  });
});

describe("15-minute snapping on the detailed layout", () => {
  it("steps by 15 minutes on the detailed layout and 5 minutes otherwise", () => {
    expect(stepOf("detailed")).toBe(15);
    expect(stepOf("standard")).toBe(5);
    expect(stepOf("compact")).toBe(5);
  });

  it("starts a card on a 15-minute multiple when it takes the first free time", () => {
    // A job at 05:30 to 06:00 can go to 05:15, 05:30 or 06:15 (owner, 8-Nov-26).
    expect(freeStart([{ start: 300, end: 720 }], [], 0, 30, 15)).toBe(300);
    expect(freeStart([{ start: 303, end: 720 }], [], 0, 30, 15)).toBe(315);
    expect(freeStart([{ start: 300, end: 720 }], [{ ...base, start_minute: 330, duration_minutes: 30 } as AdminJob], 1, 30, 15)).toBe(360);
  });

  it("snaps a slot drop to 15 minutes and never past the slot end", () => {
    const el = { dataset: { start: "315", end: "375" }, getBoundingClientRect: () => ({ top: 0, height: 100 }) } as unknown as HTMLElement;
    // A 30-minute job in 05:15 to 06:15: the start is 05:15, 05:30 or 05:45, never later than 05:45.
    expect(slotTime(el, 0, 30, 15)).toBe(315);
    expect(slotTime(el, 100, 30, 15)).toBe(345);
    expect(slotTime(el, 100, 30, 15) + 30).toBeLessThanOrEqual(375);
  });
});
