import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { ReactElement } from "react";
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";

import { batchMoveJobs, type AdminJob, type CrewDayAvailability, type SchedulingCrew } from "./api";
import { REM_PER_MINUTE, Timeline } from "./Timeline";

vi.mock("./api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("./api")>()),
  batchMoveJobs: vi.fn(async () => ({ jobs: [], warnings: [] })),
}));

const KEY = ["board", "id", "s1"];
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

// jsdom has no PointerEvent. The drag engine reads pointerId and pointerType from it, so a small stand-in is used.
beforeAll(() => {
  class PointerEventShim extends MouseEvent {
    readonly pointerId: number;
    readonly pointerType: string;
    constructor(type: string, init: MouseEventInit & { pointerId?: number; pointerType?: string } = {}) {
      super(type, init);
      this.pointerId = init.pointerId ?? 1;
      this.pointerType = init.pointerType ?? "mouse";
    }
  }
  const scope = (document.defaultView ?? globalThis) as unknown as { PointerEvent?: unknown };
  if (typeof scope.PointerEvent === "undefined") scope.PointerEvent = PointerEventShim;
});

let qc: QueryClient;

/** Renders with a query client, which the drag engine needs to save a drop. */
function renderWith(ui: ReactElement) {
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

function renderTimeline() {
  return renderWith(<Timeline crew={crew} jobs={jobs} availability={availability} focus="" search="" density="standard" boardKey={KEY} />);
}

beforeEach(() => {
  qc = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  vi.mocked(batchMoveJobs).mockClear();
});

afterEach(() => {
  delete (document as { elementFromPoint?: unknown }).elementFromPoint;
});

describe("Timeline scale (ux9, items 11 and 12)", () => {
  it("a 09:00 block starts under the 09:00 tick on the ruler", () => {
    renderTimeline();
    const tick = screen.getByText("09:00");
    const block = screen.getByLabelText(/^09:00-09:30 /);
    expect(block.style.left).not.toBe("");
    expect(block.style.left).toBe(tick.style.left);
  });

  it("the ruler and every row share one track width, so they use the same scale", () => {
    const { container } = renderTimeline();
    const tracks = Array.from(container.querySelectorAll<HTMLElement>(".sch-tl-track"));
    expect(tracks.length).toBeGreaterThan(1);
    const widths = new Set(tracks.map((t) => t.style.width));
    expect(widths.size).toBe(1);
  });

  it.each(["compact", "standard", "detailed"] as const)("a block is as long as its duration on the shared scale (%s layout)", (density) => {
    const { container } = renderWith(<Timeline crew={crew} jobs={jobs} availability={availability} focus="" search="" density={density} boardKey={KEY} />);
    const track = container.querySelector<HTMLElement>(".sch-tl-track")!;
    const trackRem = parseFloat(track.style.width);
    // Span is 09:00 to 18:00, 540 minutes.
    expect(trackRem).toBeCloseTo(540 * REM_PER_MINUTE, 6);
    const block = screen.getByLabelText(/^09:00-09:30 /);
    const blockRem = (parseFloat(block.style.width) / 100) * trackRem;
    expect(blockRem).toBeCloseTo(30 * REM_PER_MINUTE, 6);
  });
});

describe("Timeline drag (P0-6)", () => {
  const crewTwo: SchedulingCrew[] = [...crew, { id: "c2", name: "Ravi", role: "Cleaner", start_minute: 540, end_minute: 1080 }];
  const availTwo: CrewDayAvailability[] = [...availability, { crew_id: "c2", status: "Working", windows: [{ start: 540, end: 1080 }], reason: "" }];

  /** The pointer at x. The engine reads clientX, clientY, pointerId, pointerType and button. */
  const at = (clientX: number) => ({ clientX, clientY: 10, pointerId: 1, pointerType: "mouse", button: 0 });

  /** A rect with its left edge at `left`. The track starts at 100px; 1 minute is 0.8rem, 12.8px at the 16px default. */
  const place = (el: HTMLElement, left: number) => {
    vi.spyOn(el, "getBoundingClientRect").mockReturnValue({
      left, top: 0, right: left + 100, bottom: 20, width: 100, height: 20, x: left, y: 0, toJSON: () => ({}),
    } as DOMRect);
  };

  const trackOf = (crewId: string) => screen.getByTestId(`row-${crewId}`).querySelector<HTMLElement>(".sch-tl-track")!;

  /**
   * Presses the block at grabX, moves it, and drops it at dropX over the row's track.
   * The block's left edge is at 100px, so the grab point is dropX minus the drop's block left.
   */
  function drag(block: HTMLElement, grabX: number, dropX: number, dropOn: HTMLElement) {
    fireEvent.pointerDown(block, at(grabX));
    fireEvent.pointerMove(window, at(grabX + 20));
    document.elementFromPoint = (() => dropOn) as typeof document.elementFromPoint;
    fireEvent.pointerMove(window, at(dropX));
    fireEvent.pointerUp(window, at(dropX));
  }

  it("a block dragged to a new 5-minute snap time issues one batchMove call with that start_minute", async () => {
    renderWith(<Timeline crew={crew} jobs={jobs} availability={availability} focus="" search="" density="standard" boardKey={KEY} />);
    const block = screen.getByLabelText(/^09:00-09:30 /);
    place(block, 100);
    place(trackOf("c1"), 100);

    // The grab point is 10px into the block. The block's left edge lands 63 minutes after 09:00, which snaps to 605 (09:05).
    drag(block, 110, 100 + 63 * 12.8 + 10, trackOf("c1"));

    await waitFor(() => expect(batchMoveJobs).toHaveBeenCalledTimes(1));
    expect(batchMoveJobs).toHaveBeenCalledWith([{ job_id: "1", crew_id: "c1", start_minute: 605 }], false);
  });

  it("a block dragged to another crew row changes crew", async () => {
    renderWith(<Timeline crew={crewTwo} jobs={jobs} availability={availTwo} focus="" search="" density="standard" boardKey={KEY} />);
    const block = screen.getByLabelText(/^09:00-09:30 /);
    place(block, 100);
    place(trackOf("c1"), 100);
    place(trackOf("c2"), 100);

    // Dropped at the same time on Ravi's row: the block keeps 09:00 and moves to crew c2.
    drag(block, 110, 110, trackOf("c2"));

    await waitFor(() => expect(batchMoveJobs).toHaveBeenCalledTimes(1));
    expect(batchMoveJobs).toHaveBeenCalledWith([{ job_id: "1", crew_id: "c2", start_minute: 540 }], false);
  });

  it("a block that is not Scheduled does not drag", () => {
    const done = [{ ...job("1", 540, 30), status: "Completed" } as AdminJob];
    renderWith(<Timeline crew={crew} jobs={done} availability={availability} focus="" search="" density="standard" boardKey={KEY} />);
    const block = screen.getByLabelText(/^09:00-09:30 /);
    place(block, 100);
    place(trackOf("c1"), 100);

    drag(block, 110, 916, trackOf("c1"));

    expect(batchMoveJobs).not.toHaveBeenCalled();
  });
});
