import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { AdminJob, CrewDayAvailability, SchedulingCrew } from "./api";
import { REM_PER_MINUTE, Timeline } from "./Timeline";

const crew: SchedulingCrew[] = [{ id: "c1", name: "Asha", role: "Cleaner", start_minute: 540, end_minute: 1080 }];
const availability: CrewDayAvailability[] = [{ crew_id: "c1", status: "Working", windows: [{ start: 540, end: 1080 }], reason: "" }];

/** A placed job on crew c1. Only the fields the timeline and its block read. */
function job(id: string, start: number, duration: number): AdminJob {
  const hh = (m: number) => `${String(Math.floor(m / 60)).padStart(2, "0")}:${String(m % 60).padStart(2, "0")}`;
  return {
    id, visit_id: id, schedule_id: "s", schedule_status: "Draft", date: "2026-11-09", vehicle_id: "v", registration: `KA${id}`,
    vehicle: "Honda City", parking: "B1-1", zone: "Zone 2", customer_name: "Meera", service: "Cleaning-External",
    status: "Scheduled", duration_minutes: duration, crew_id: "c1", crew_name: "Asha", start_minute: start,
    start_time: hh(start), end_time: hh(start + duration), finish_by: null, late: false, manual: false, reason: "",
  } as unknown as AdminJob;
}

const jobs = [job("1", 540, 30), job("2", 780, 60)];

function renderTimeline() {
  return render(<Timeline crew={crew} jobs={jobs} availability={availability} focus="" search="" density="standard" />);
}

describe("Timeline scale (ux9, items 11 and 12)", () => {
  it("the ruler and every row share one track width, so they use the same scale", () => {
    const { container } = renderTimeline();
    const tracks = Array.from(container.querySelectorAll<HTMLElement>(".sch-tl-track"));
    expect(tracks.length).toBeGreaterThan(1);
    const widths = new Set(tracks.map((t) => t.style.width));
    expect(widths.size).toBe(1);
  });

  it.each(["compact", "standard", "detailed"] as const)("a block is as long as its duration on the shared scale (%s layout)", (density) => {
    const { container } = render(<Timeline crew={crew} jobs={jobs} availability={availability} focus="" search="" density={density} />);
    const track = container.querySelector<HTMLElement>(".sch-tl-track")!;
    const trackRem = parseFloat(track.style.width);
    // Span is 09:00 to 18:00, 540 minutes.
    expect(trackRem).toBeCloseTo(540 * REM_PER_MINUTE, 6);
    const block = screen.getByLabelText(/^09:00-09:30 /);
    const blockRem = (parseFloat(block.style.width) / 100) * trackRem;
    expect(blockRem).toBeCloseTo(30 * REM_PER_MINUTE, 6);
  });
});
