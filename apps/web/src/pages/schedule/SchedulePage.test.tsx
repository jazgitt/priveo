import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { withSite } from "../../site/testSite";
import { createEvent, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { toast } from "sonner";

import { ToastProvider } from "../../components";
import { choose, confirmWith, PortalProviders } from "../../test/portal";
import { CapacityPage } from "../capacity/CapacityPage";
import { jobsCsv, csvCell } from "./JobTable";
import { toIso } from "./api";
import { SchedulePage } from "./SchedulePage";

const fetchMock = vi.fn();

function json(status: number, body?: unknown) {
  return new Response(body === undefined ? null : JSON.stringify(body), { status });
}
const err = (code: string, message: string) => ({ code, message, fields: {}, request_id: "" });

function wrap(ui: ReactNode, path = "/schedule") {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}><MemoryRouter initialEntries={[path]}><ToastProvider><PortalProviders>
      {withSite(ui, "s1", "Palm Grove")}
    </PortalProviders></ToastProvider></MemoryRouter></QueryClientProvider>,
  );
}

const SOC = "s1";
const crew = [
  { id: "c1", name: "Asha", role: "Member", active: true, society_id: SOC, society: "Palm Grove" },
  { id: "c2", name: "Ravi", role: "Member", active: true, society_id: SOC, society: "Palm Grove" },
];

function job(over: Record<string, unknown> = {}) {
  return {
    id: "j1", visit_id: "v1", schedule_id: "sch1", schedule_status: "Draft", date: "2026-11-08",
    vehicle_id: "veh1", registration: "KA01AB1234", vehicle: "Honda City", parking: "B1-24",
    customer_name: "Meena",
    service: "Cleaning-External", status: "Scheduled", duration_minutes: 20, crew_id: "c1",
    crew_name: "Asha", start_minute: 540, start_time: "09:00", end_time: "09:20", finish_by: "10:00",
    late: false, manual: false, reason: "", ...over,
  };
}

function board(status = "Draft", jobs = [job()], availability: unknown[] = []) {
  return {
    schedule: {
      id: "sch1", society_id: SOC, society_name: "Palm Grove", start_date: "2026-11-08",
      end_date: "2026-11-14", status, frozen_at: status === "Frozen" ? "2026-11-07T14:00:00Z" : null,
      freeze_deadline: "2026-11-07T14:30:00Z",
    },
    days: [{ date: "2026-11-08", capacity_minutes: 960, demand_minutes: 60, scheduled_minutes: 20,
             over_capacity: false, availability }],
    crew: [
      { id: "c1", name: "Asha", role: "Member", start_minute: 480, end_minute: 720 },
      { id: "c2", name: "Ravi", role: "Member", start_minute: 480, end_minute: 720 },
    ],
    jobs,
  };
}

interface Opts {
  jobs?: ReturnType<typeof job>[];
  status?: string;
  moveReply?: () => Response;
  /** The reply to a card drag, a group drag or a drop on Unscheduled (POST .../jobs/batch-move). */
  batchReply?: (init?: RequestInit) => Promise<Response> | Response;
  freezeReply?: () => Response;
  unfreezeReply?: () => Response;
  boardReply?: () => Response;
  /** More boards by schedule ID, for the days of other schedules (ADM-SCH-35). */
  boards?: Record<string, ReturnType<typeof board>>;
  needs?: ReturnType<typeof job>[];
  /** Cars on Interior care with no preferred day (the Needs Attention tab). */
  interiorMissing?: Record<string, unknown>[];
  /** The "Freeze by itself" feature (scheduler.auto_freeze), off unless a test switches it on. */
  autoFreeze?: boolean;
}

function server(o: Opts = {}) {
  fetchMock.mockImplementation(async (path: string, init?: RequestInit) => {
    const url = String(path);
    if (url.startsWith("/v1/admin/directory/settings")) return json(200, []);
    if (url.startsWith("/v1/admin/features")) {
      return json(200, [{ key: "scheduler.auto_freeze", label: "Freeze by itself", description: "", group: "Scheduler",
                          audience: "admin", enabled: o.autoFreeze ?? false }]);
    }
    if (url.startsWith("/v1/admin/scheduling/cutoff-requests")) return json(200, []);
    if (url.startsWith("/v1/admin/crew")) return json(200, crew);
    const main = () => board(o.status ?? "Draft", o.jobs ?? [job()]);
    if (url.startsWith("/v1/admin/scheduling/schedules?")) {
      if (o.boardReply && o.boardReply().status === 404) return json(200, []);
      return json(200, [main().schedule, ...Object.values(o.boards ?? {}).map((b) => b.schedule)]);
    }
    if (url.startsWith("/v1/admin/scheduling/board")) {
      const id = new URL(url, "http://x").searchParams.get("schedule_id");
      if (id && o.boards?.[id]) return json(200, o.boards[id]);
      return o.boardReply ? o.boardReply() : json(200, main());
    }
    if (url.startsWith("/v1/admin/scheduling/skipped?")) {
      return json(200, [
        job({ id: "j5", registration: "KA05SK0005", crew_id: null, crew_name: null, start_minute: null,
              start_time: null, status: "Skipped", skip_kind: "Paused",
              skip_reason: "Paused by the customer, 08-Nov-26 to 10-Nov-26" }),
        job({ id: "j6", registration: "KA06SK0006", crew_id: null, crew_name: null, start_minute: null,
              start_time: null, status: "Skipped", skip_kind: "Skipped", skip_reason: "Skipped by operations" }),
      ]);
    }
    if (url.startsWith("/v1/admin/scheduling/interior-day-missing")) return json(200, o.interiorMissing ?? []);
    if (url.startsWith("/v1/admin/scheduling/needs-scheduling")) {
      return json(200, { jobs: o.needs ?? [job({ id: "j9", crew_id: null, crew_name: null, start_minute: null,
                                                 start_time: null, reason: "Capacity is short." })] });
    }
    if (url.startsWith("/v1/admin/scheduling/capacity")) {
      return json(200, [
        { date: "2026-11-08", capacity_minutes: 480, demand_minutes: 600, scheduled_minutes: 400,
          over_capacity: true,
          crew: [{ name: "Asha Rao", role: "Member", minutes: 480, slots: "05:00-13:00" }],
          demand: [{ service: "Cleaning-External", source: "Subscription", jobs: 24, minutes: 480 },
                   { service: "Deep Spa", source: "Add-on", jobs: 1, minutes: 120 }] },
        { date: "2026-11-09", capacity_minutes: 480, demand_minutes: 100, scheduled_minutes: 0,
          over_capacity: false },
      ]);
    }
    if (url.endsWith("/batch-move")) return o.batchReply ? await o.batchReply(init) : json(200, { jobs: [], warnings: [] });
    if (url.endsWith("/move")) return o.moveReply ? o.moveReply() : json(200, job());
    if (url.endsWith("/freeze")) return o.freezeReply ? o.freezeReply() : json(200, board("Frozen").schedule);
    if (url.endsWith("/unfreeze")) {
      return o.unfreezeReply ? o.unfreezeReply() : json(200, board("Draft").schedule);
    }
    if (url.endsWith("/run") && init?.method === "POST") {
      return json(200, { schedules: [{ schedule_id: "sch1", society_id: SOC, status: "Draft",
                                       placed: 3, unscheduled: 1, late: 0 }] });
    }
    return json(404, err("not_found", "no"));
  });
}

function callsTo(suffix: string) {
  return fetchMock.mock.calls.filter((c) => String(c[0]).endsWith(suffix));
}

/** The page for one day; 08-Nov-26 is the first day of the weekly draft. */
async function openDay(date = "2026-11-08", extra = "") {
  wrap(<SchedulePage />, `/schedule?date=${date}${extra}`);
}

const column = (id: string) => screen.findByTestId(`col-${id}`);
const bodyOf = (col: HTMLElement) => col.querySelector<HTMLElement>(".sch-col-body")!;

/**
 * Drags a card with the mouse, as the drag engine reads it: a press on the card, a move past
 * its 5 px threshold, then a release over `target` at `clientY`. jsdom has no layout and no
 * elementFromPoint, so the target is the element under the pointer, and the tests stub the
 * rectangles they need.
 */
function dragTo(card: Element, target: Element, clientY = 0) {
  Object.defineProperty(document, "elementFromPoint", { configurable: true, value: () => target });
  const pointer = (node: Element | Window, type: "pointerDown" | "pointerMove" | "pointerUp", y: number) => {
    const ev = createEvent[type](node, {});
    for (const [key, value] of Object.entries({ pointerId: 1, pointerType: "mouse", isPrimary: true, button: 0, clientX: 0, clientY: y })) {
      Object.defineProperty(ev, key, { value });
    }
    fireEvent(node, ev);
  };
  pointer(card, "pointerDown", 0);
  pointer(window, "pointerMove", 20);
  pointer(window, "pointerMove", clientY);
  pointer(window, "pointerUp", clientY);
}

/** The batch-move calls: a card drag, a multi-select drag and a drop on Unscheduled all send one. */
const batchCalls = () => callsTo("/v1/admin/scheduling/jobs/batch-move");
const batchBody = (i: number) => JSON.parse(String(batchCalls()[i][1].body));

beforeEach(() => {
  vi.stubGlobal("fetch", fetchMock);
  // What the admin chose in one test must not carry into the next.
  localStorage.removeItem("priveo.schedule.card-density");
  localStorage.removeItem("priveo.schedule.days-folded");
  localStorage.removeItem("priveo.schedule.folded-lanes");
  // Toasts are kept at module level, so a toast from one test must not crowd the next test's toast out of view.
  toast.dismiss();
});
afterEach(() => {
  fetchMock.mockReset();
  vi.unstubAllGlobals();
  // Set by dragTo for one drag; jsdom has no such function of its own.
  delete (document as unknown as { elementFromPoint?: unknown }).elementFromPoint;
});

describe("the card board (ADM-SCH-33)", () => {
  it("shows a column for Unscheduled and each crew member, with job cards, flags and the reason", async () => {
    server({ jobs: [
      job(),
      job({ id: "j2", registration: "KA02ZZ0001", crew_id: "c2", start_minute: 600,
            start_time: "10:00", end_time: "10:20", late: true, manual: true, reason: "Misses the cutoff." }),
      job({ id: "j3", registration: "KA03XX0002", crew_id: null, start_minute: null,
            start_time: null, reason: "No crew member is free." }),
    ] });
    await openDay();
    const asha = await column("c1");
    // Standard: line 1 is zone, car number and cutoff; line 2 is EXT or INT and the service slot (owner review, 8-Nov-26).
    const card1 = within(asha).getByRole("button", { name: "EXT,KA01AB1234,B1-24" });
    expect(card1).toHaveTextContent("09:00-09:20");
    expect(card1).toHaveTextContent("EXT");
    expect(card1).toHaveTextContent("KA01AB123410:00");
    expect(card1.querySelectorAll(".sch-card-line")).toHaveLength(2);
    const card2 = within(await column("c2")).getByRole("button", { name: /KA02ZZ0001/ });
    expect(card2).toHaveClass("late");
    expect(card2).toHaveClass("manual");
    expect(within(card2).getByRole("img", { name: "Late" })).toBeInTheDocument();
    expect(within(card2).getByRole("img", { name: "Placed by hand" })).toBeInTheDocument();
    expect(card2).toHaveAttribute("title", expect.stringContaining("Misses the cutoff."));
    const unscheduled = await column("unscheduled");
    expect(unscheduled).toHaveAccessibleName("Unscheduled (1)");
    expect(within(unscheduled).getByText("No crew member is free.")).toBeInTheDocument();
    // The column header gives the use: 20 of Asha's 240 minutes, and her free slots.
    expect(asha).toHaveTextContent("8%");
    expect(asha).toHaveTextContent("20 min of 4 h used · 3 h 40 min free");
    expect(within(asha).getByLabelText("Free 08:00-09:00")).toHaveTextContent("1 h");
    expect(within(asha).getByLabelText("Free 09:20-12:00")).toHaveTextContent("2 h 40 min");
  });

  it("moves a card to the first free time of another crew member, in one batch move", async () => {
    server();
    await openDay();
    const card = within(await column("c1")).getByRole("button", { name: /KA01AB1234/ });
    dragTo(card, bodyOf(await column("c2")));
    await waitFor(() => expect(batchCalls()).toHaveLength(1));
    expect(batchBody(0)).toEqual({ moves: [{ job_id: "j1", crew_id: "c2", start_minute: 480 }], override: false });
    expect(callsTo("/move")).toHaveLength(0);
    expect(await screen.findByText("Moved.")).toBeInTheDocument();
  });

  it("shows a crew-hours warning in red and keeps the move", async () => {
    server({ batchReply: () => json(200, { jobs: [], warnings: [
      { job_id: "j1", code: "crew_hours", message: "That time is outside the crew member's hours." }] }) });
    await openDay();
    dragTo(within(await column("c1")).getByRole("button", { name: /KA01AB1234/ }), bodyOf(await column("c2")));
    await waitFor(() => expect(batchCalls()).toHaveLength(1));
    // No confirmation: the warning is shown and the card stays in Ravi's column (decision 5).
    expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument();
    expect(await screen.findByTestId("board-warnings")).toHaveClass("text-destructive");
    expect(screen.getByTestId("board-warnings")).toHaveTextContent("That time is outside the crew member's hours.");
  });

  it("shows the move at once, before the server answers, and puts the card back if it is refused", async () => {
    let answer: (r: Response) => void = () => {};
    server({ batchReply: () => new Promise<Response>((res) => { answer = res; }) });
    await openDay();
    const card = within(await column("c1")).getByRole("button", { name: /KA01AB1234/ });
    dragTo(card, bodyOf(await column("c2")));
    // The server has not answered, yet the card is already in Ravi's column.
    expect(await within(await column("c2")).findByRole("button", { name: /KA01AB1234/ })).toBeInTheDocument();
    expect(within(await column("c1")).queryByRole("button", { name: /KA01AB1234/ })).not.toBeInTheDocument();
    await waitFor(() => expect(batchCalls()).toHaveLength(1));
    answer(json(409, err("overlap", "KA09ZZ0009 is in the way at 09:00-09:20.")));
    expect(await within(await column("c1")).findByRole("button", { name: /KA01AB1234/ })).toBeInTheDocument();
    expect(within(await column("c2")).queryByRole("button", { name: /KA01AB1234/ })).not.toBeInTheDocument();
    expect(await screen.findByText(/KA09ZZ0009 is in the way/)).toBeInTheDocument();
  });

  it("moves a picked group together, each card keeping its time from the dragged card (P0-8)", async () => {
    server({ jobs: [
      job(),
      job({ id: "j2", registration: "KA02ZZ0001", start_minute: 600, start_time: "10:00", end_time: "10:20" }),
    ] });
    await openDay();
    const asha = await column("c1");
    await userEvent.click(within(within(asha).getByRole("button", { name: /KA01AB1234/ })).getByRole("checkbox"));
    await userEvent.click(within(within(asha).getByRole("button", { name: /KA02ZZ0001/ })).getByRole("checkbox"));
    dragTo(within(asha).getByRole("button", { name: /KA01AB1234/ }), bodyOf(await column("c2")));
    await waitFor(() => expect(batchCalls()).toHaveLength(1));
    // Ravi's lane is empty: the dragged card goes to 08:00, and the card 60 minutes later on Asha's day goes 60 minutes after it.
    expect(batchBody(0)).toEqual({ moves: [
      { job_id: "j1", crew_id: "c2", start_minute: 480 },
      { job_id: "j2", crew_id: "c2", start_minute: 540 },
    ], override: false });
  });

  it("refuses a picked group that has a card with no time yet, and says why", async () => {
    server({ jobs: [
      job(),
      job({ id: "j3", registration: "KA03XX0002", crew_id: null, crew_name: null, start_minute: null, start_time: null,
            end_time: null, reason: "No crew member is free." }),
    ] });
    await openDay();
    const asha = await column("c1");
    await userEvent.click(within(within(asha).getByRole("button", { name: /KA01AB1234/ })).getByRole("checkbox"));
    const unscheduled = await column("unscheduled");
    await userEvent.click(within(within(unscheduled).getByRole("button", { name: /KA03XX0002/ })).getByRole("checkbox"));
    dragTo(within(asha).getByRole("button", { name: /KA01AB1234/ }), bodyOf(await column("c2")));
    expect(await screen.findByText("Cards with no time yet cannot be moved as a group. Take them out of the selection first.")).toBeInTheDocument();
    expect(batchCalls()).toHaveLength(0);
  });

  it("moves a placed card 5 minutes with Alt and the arrow keys, only into free time", async () => {
    server();
    await openDay();
    const card = within(await column("c1")).getByRole("button", { name: /KA01AB1234/ });
    card.focus();
    await userEvent.keyboard("{Alt>}{ArrowDown}{/Alt}");
    await waitFor(() => expect(callsTo("/move")).toHaveLength(1));
    expect(JSON.parse(callsTo("/move")[0][1].body)).toEqual({ crew_id: "c1", start_minute: 545 });
  });

  it("colours a card by its kind of work and keeps the status as an icon, not a fill", async () => {
    server({ jobs: [
      job(),
      job({ id: "j2", registration: "KA02IN0002", service: "Cleaning-Internal", crew_id: "c2", crew_name: "Ravi",
            start_minute: 600, start_time: "10:00", end_time: "10:20", status: "Completed" }),
      job({ id: "j3", registration: "KA03SP0003", service: "Deep Spa", crew_id: "c2", crew_name: "Ravi",
            start_minute: 700, start_time: "11:40", end_time: "12:00" }),
    ] });
    await openDay();
    const ext = within(await column("c1")).getByRole("button", { name: /KA01AB1234/ });
    const int = within(await column("c2")).getByRole("button", { name: /KA02IN0002/ });
    const spa = within(await column("c2")).getByRole("button", { name: /KA03SP0003/ });
    expect(ext).toHaveClass("t-ext");
    expect(int).toHaveClass("t-int", "done");
    expect(spa).toHaveClass("t-spa");
    expect(int.querySelector(".sch-st.done")).not.toBeNull();
  });

  it("shows more on a card as the detail grows, and remembers it", async () => {
    server();
    await openDay();
    await column("c1");
    const card = () => within(screen.getByTestId("col-c1")).getByRole("button", { name: /KA01AB1234/ });
    expect(card()).not.toHaveTextContent("Meena");
    await userEvent.click(await screen.findByRole("button", { name: "Detail" }));
    expect(card()).toHaveTextContent("Meena");
    expect(localStorage.getItem("priveo.schedule.card-density")).toBe("detailed");
    await userEvent.click(await screen.findByRole("button", { name: "Compact" }));
    expect(card()).toHaveClass("compact");
  });

  it("hides the kind of work the chip does not keep; Show all brings it back dimmed", async () => {
    server({ jobs: [job(), job({ id: "j2", registration: "KA02IN0002", service: "Cleaning-Internal", crew_id: "c2",
                                 crew_name: "Ravi", start_minute: 600, start_time: "10:00", end_time: "10:20" })] });
    await openDay();
    const int = within(await column("c2")).getByRole("button", { name: /KA02IN0002/ });
    expect(screen.getByRole("switch", { name: "Show all" })).toHaveAttribute("aria-checked", "false");
    await userEvent.click(await screen.findByRole("button", { name: "INT" }));
    expect(int).not.toHaveClass("dim");
    expect(screen.queryByRole("button", { name: /KA01AB1234/ })).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("switch", { name: "Show all" }));
    expect(screen.getByRole("button", { name: /KA01AB1234/ })).toHaveClass("dim");
    expect(int).not.toHaveClass("dim");
    await userEvent.click(screen.getByRole("button", { name: "INT" }));
    expect(screen.getByRole("button", { name: /KA01AB1234/ })).not.toHaveClass("dim");
  });

  it("puts a card dropped below another at the first free time after it", async () => {
    server({ jobs: [job(), job({ id: "j2", registration: "KA02ZZ0001", crew_id: "c2", crew_name: "Ravi",
                                 start_minute: 600, start_time: "10:00", end_time: "10:20" })] });
    await openDay();
    const ravi = await column("c2");
    const below = within(ravi).getByRole("button", { name: /KA02ZZ0001/ });
    below.getBoundingClientRect = () => ({ top: 0, height: 40, bottom: 40, left: 0, right: 0, width: 0, x: 0, y: 0, toJSON: () => ({}) });
    dragTo(within(await column("c1")).getByRole("button", { name: /KA01AB1234/ }), bodyOf(ravi), 100);
    await waitFor(() => expect(batchCalls()).toHaveLength(1));
    expect(batchBody(0).moves).toEqual([{ job_id: "j1", crew_id: "c2", start_minute: 620 }]);
  });

  describe("moving a card within its own crew lane (ADM-SCH-33)", () => {
    const rect = (top: number, height: number) => () => ({ top, height, bottom: top + height, left: 0, right: 0, width: 0, x: 0, y: top, toJSON: () => ({}) });
    /** Asha has three cards: 09:00 (moved), 10:20 and 11:00. */
    const lane = () => server({ jobs: [
      job(),
      job({ id: "j2", registration: "KA02ZZ0001", start_minute: 620, start_time: "10:20", end_time: "10:40" }),
      job({ id: "j3", registration: "KA03ZZ0001", start_minute: 660, start_time: "11:00", end_time: "11:20" }),
    ] });
    const moved = () => batchBody(0).moves;

    // Each lane move is one batch: the dragged card, then every card it pushes (all marked By hand on the server).
    it("drops a card between two cards of its lane, and the card below it moves down (P0-5)", async () => {
      lane();
      await openDay();
      const body = bodyOf(await column("c1"));
      within(body).getByRole("button", { name: /KA02ZZ0001/ }).getBoundingClientRect = rect(0, 40);
      within(body).getByRole("button", { name: /KA03ZZ0001/ }).getBoundingClientRect = rect(100, 40);
      dragTo(within(body).getByRole("button", { name: /KA01AB1234/ }), body, 60);
      await waitFor(() => expect(batchCalls()).toHaveLength(1));
      // 09:00 goes after the 10:20 card, which moves up to 10:00 to close the gap; the 11:00 card stays.
      expect(moved()).toEqual([
        { job_id: "j1", crew_id: "c1", start_minute: 620 },
        { job_id: "j2", crew_id: "c1", start_minute: 600 },
      ]);
    });

    it("drops a card above the first card of its lane, and the cards below stay where they are", async () => {
      lane();
      await openDay();
      const body = bodyOf(await column("c1"));
      // The 11:00 card goes to the top of the lane, which starts at 08:00.
      dragTo(within(body).getByRole("button", { name: /KA03ZZ0001/ }), body, -1);
      await waitFor(() => expect(batchCalls()).toHaveLength(1));
      expect(moved()).toEqual([{ job_id: "j3", crew_id: "c1", start_minute: 480 }]);
    });

    it("drops a card below the last card of its lane, and the cards it passes move up", async () => {
      lane();
      await openDay();
      const body = bodyOf(await column("c1"));
      dragTo(within(body).getByRole("button", { name: /KA01AB1234/ }), body, 500);
      await waitFor(() => expect(batchCalls()).toHaveLength(1));
      expect(moved()).toEqual([
        { job_id: "j1", crew_id: "c1", start_minute: 660 },
        { job_id: "j2", crew_id: "c1", start_minute: 600 },
        { job_id: "j3", crew_id: "c1", start_minute: 640 },
      ]);
    });

    it("drops a card into a free slot of its own lane at the pointer's 5 minutes", async () => {
      lane();
      await openDay();
      const body = bodyOf(await column("c1"));
      const slot = within(body).getByLabelText("Free 11:20-12:00");
      slot.getBoundingClientRect = rect(0, 100);
      dragTo(within(body).getByRole("button", { name: /KA01AB1234/ }), slot, 50);
      await waitFor(() => expect(batchCalls()).toHaveLength(1));
      expect(moved()).toEqual([{ job_id: "j1", crew_id: "c1", start_minute: 690 }]);
    });
  });

  describe("card tools, lock, zones and folding (items 6, 7, 9, 10, 15)", () => {
    it("shows a lock on a card placed by hand, and a click locks or unlocks it through the server", async () => {
      serverWith({ "/v1/admin/scheduling/jobs/j1/hand-lock": () => json(200, job({ placed_by_hand: true, hand_locked: true })) },
        { jobs: [job({ placed_by_hand: true, hand_locked: false })] });
      await openDay();
      const body = bodyOf(await column("c1"));
      const lock = within(body).getByRole("button", { name: /Unlocked\. The next scheduler run may move this card/ });
      expect(lock).toHaveAttribute("title", "Unlocked. The next scheduler run may move this card. Click to lock it here.");
      await userEvent.click(lock);
      await waitFor(() => expect(callsTo("/hand-lock")).toHaveLength(1));
      expect(JSON.parse(callsTo("/hand-lock")[0][1].body)).toEqual({ locked: true });
      expect(callsTo("/hand-lock")[0][1].method).toBe("PUT");
    });

    it("shows the locked tip on a locked card, and no lock on a card not placed by hand", async () => {
      server({ jobs: [job({ placed_by_hand: true, hand_locked: true }), job({ id: "j2", registration: "KA02ZZ0001", start_minute: 620, start_time: "10:20", end_time: "10:40" })] });
      await openDay();
      const body = bodyOf(await column("c1"));
      expect(within(body).getByRole("button", { name: /^Locked\. The scheduler keeps this card here on every run/ })).toBeInTheDocument();
      expect(within(body).getAllByRole("button", { name: /^(Locked|Unlocked)\./ })).toHaveLength(1);
    });

    it("takes a card off the day from its delete icon, after a confirmation, and does not open the card", async () => {
      server();
      await openDay();
      const body = bodyOf(await column("c1"));
      await userEvent.click(within(body).getByRole("button", { name: "Take off the day" }));
      expect(screen.queryByRole("dialog")).toBeNull();
      expect(callsTo("/move")).toHaveLength(0);
      await confirmWith("Take off the day");
      await waitFor(() => expect(callsTo("/move")).toHaveLength(1));
      expect(JSON.parse(callsTo("/move")[0][1].body)).toEqual({ crew_id: null, start_minute: null });
    });

    it("shows a short marker for a cross-zone cleaner, with the full reason in its tip", async () => {
      server({ jobs: [job({ cross_zone_reason: "Zone 5 car with a Zone 2 cleaner; no Zone 5 slot is free" })] });
      await openDay();
      const marker = within(await column("c1")).getByText("Outside zone");
      expect(marker).toHaveAttribute("title", "Zone 5 car with a Zone 2 cleaner; no Zone 5 slot is free");
      expect(marker).toHaveAttribute("aria-label", "Zone 5 car with a Zone 2 cleaner; no Zone 5 slot is free");
    });

    it("shows the home zones after the crew name in the lane header, and nothing when there are none", async () => {
      const b = board();
      serverWith({ "/v1/admin/scheduling/board": () => json(200, { ...b, crew: [
        { ...b.crew[0], home_zones: [{ id: "z2", name: "Zone 2" }, { id: "z5", name: "Zone 5" }] }, b.crew[1]] }) });
      await openDay();
      // The header shows the short labels (owner, 8-Nov-26); the full names are in the tip.
      expect((await column("c1")).querySelector(".sch-name-line")).toHaveTextContent("Asha · Z2, Z5");
      expect((await column("c2")).querySelector(".sch-home-zones")).toBeNull();
    });

    it("folds the Unscheduled lane like a crew lane and remembers it", async () => {
      server();
      await openDay();
      await userEvent.click(await screen.findByRole("button", { name: "Fold the Unscheduled lane" }));
      expect(screen.getByRole("region", { name: /Unscheduled \(0\), folded/ })).toBeInTheDocument();
      expect(JSON.parse(localStorage.getItem("priveo.schedule.folded-lanes")!)).toContain("unscheduled");
      await userEvent.click(screen.getByRole("button", { name: "Show the Unscheduled lane" }));
      expect(screen.getByRole("region", { name: "Unscheduled (0)" })).toBeInTheDocument();
    });
  });

  it("starts a card where it is dropped inside a free slot, at any 5 minutes", async () => {
    server();
    await openDay();
    const slot = within(await column("c2")).getByLabelText("Free 08:00-12:00");
    slot.getBoundingClientRect = () => ({ top: 0, height: 100, bottom: 100, left: 0, right: 0, width: 0, x: 0, y: 0, toJSON: () => ({}) });
    // Halfway down the 240 minute slot: 08:00 + half of the 220 minutes a 20 minute job can start in.
    dragTo(within(await column("c1")).getByRole("button", { name: /KA01AB1234/ }), slot, 50);
    await waitFor(() => expect(batchCalls()).toHaveLength(1));
    expect(batchBody(0).moves).toEqual([{ job_id: "j1", crew_id: "c2", start_minute: 590 }]);
  });

  it("a card dropped on a free slot too short for it is not refused: the card below it moves down (P0-5)", async () => {
    server({ jobs: [job(), job({ id: "j2", registration: "KA02ZZ0001", crew_id: "c2", crew_name: "Ravi",
                                 start_minute: 490, start_time: "08:10", end_time: "08:30" })] });
    await openDay();
    const ravi = await column("c2");
    const boxAt = (top: number, height: number) => () => ({ top, height, bottom: top + height, left: 0, right: 0, width: 0, x: 0, y: top, toJSON: () => ({}) });
    const slot = within(ravi).getByLabelText("Free 08:00-08:10");
    slot.getBoundingClientRect = boxAt(0, 10);
    within(ravi).getByRole("button", { name: /KA02ZZ0001/ }).getBoundingClientRect = boxAt(10, 20);
    dragTo(within(await column("c1")).getByRole("button", { name: /KA01AB1234/ }), slot, 5);
    await waitFor(() => expect(batchCalls()).toHaveLength(1));
    expect(batchBody(0).moves).toEqual([
      { job_id: "j1", crew_id: "c2", start_minute: 480 },
      { job_id: "j2", crew_id: "c2", start_minute: 500 },
    ]);
  });

  it("takes a card off its crew member when it is dropped on Unscheduled, with no confirmation (P0-7)", async () => {
    server();
    await openDay();
    dragTo(within(await column("c1")).getByRole("button", { name: /KA01AB1234/ }), bodyOf(await column("unscheduled")));
    await waitFor(() => expect(batchCalls()).toHaveLength(1));
    expect(batchBody(0)).toEqual({ moves: [{ job_id: "j1", crew_id: null, start_minute: null }], override: false });
    expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument();
  });

  it("places a card dragged out of Unscheduled into a crew lane at the drop, with no confirmation (P0-7)", async () => {
    const unplaced = job({ id: "j3", registration: "KA03XX0002", crew_id: null, crew_name: null, start_minute: null,
                           start_time: null, end_time: null, reason: "No crew member is free." });
    server({ jobs: [job(), unplaced] });
    await openDay();
    const body = bodyOf(await column("c1"));
    // Asha's only card sits at 09:00-09:20; the drop is below it, so the card goes after it.
    within(body).getByRole("button", { name: /KA01AB1234/ }).getBoundingClientRect = () => ({ top: 0, height: 40, bottom: 40, left: 0, right: 0, width: 0, x: 0, y: 0, toJSON: () => ({}) });
    dragTo(within(await column("unscheduled")).getByRole("button", { name: /KA03XX0002/ }), body, 60);
    await waitFor(() => expect(batchCalls()).toHaveLength(1));
    expect(batchBody(0).moves).toEqual([{ job_id: "j3", crew_id: "c1", start_minute: 560 }]);
    expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument();
  });

  it("moves and takes a job off from its dialog", async () => {
    server();
    await openDay();
    await userEvent.click(within(await column("c1")).getByRole("button", { name: /KA01AB1234/ }));
    await choose("Crew member", /Ravi/);
    fireEvent.change(screen.getByLabelText("Start time"), { target: { value: "09:40" } });
    await userEvent.click(screen.getByRole("button", { name: "Move here" }));
    await waitFor(() => expect(callsTo("/move")).toHaveLength(1));
    expect(JSON.parse(callsTo("/move")[0][1].body)).toEqual({ crew_id: "c2", start_minute: 580 });
  });

  it("confirms before taking a job off its crew member from the dialog", async () => {
    server();
    await openDay();
    await userEvent.click(within(await column("c1")).getByRole("button", { name: /KA01AB1234/ }));
    await userEvent.click(screen.getByRole("button", { name: "Take off crew member" }));
    expect(callsTo("/move")).toHaveLength(0);
    await confirmWith("Take off crew member");
    await waitFor(() => expect(callsTo("/move")).toHaveLength(1));
    expect(JSON.parse(callsTo("/move")[0][1].body)).toEqual({ crew_id: null, start_minute: null });
  });

  it("moves one service to another date with a reason (S-05)", async () => {
    server();
    await openDay();
    await userEvent.click(within(await column("c1")).getByRole("button", { name: /KA01AB1234/ }));
    await userEvent.click(screen.getByRole("button", { name: "Move to date" }));
    const submit = screen.getByRole("button", { name: "Move service" });
    expect(submit).toBeDisabled();
    fireEvent.change(screen.getByLabelText("New date"), { target: { value: "2099-01-05" } });
    await userEvent.type(screen.getByLabelText("Reason"), "Customer away");
    await userEvent.click(submit);
    await waitFor(() => expect(callsTo("/move-date")).toHaveLength(1));
    expect(JSON.parse(callsTo("/move-date")[0][1].body)).toEqual({ date: "2099-01-05", reason: "Customer away" });
  });

  it("reassigns a crew member's whole day to another (S-09)", async () => {
    server();
    await openDay();
    await userEvent.click(await screen.findByRole("button", { name: "Reassign crew day" }));
    const submit = screen.getByRole("button", { name: "Reassign" });
    expect(submit).toBeDisabled();
    await choose("From crew member", /Asha/);
    await choose("To crew member", /Ravi/);
    await userEvent.type(screen.getByLabelText("Reason"), "Asha is unwell");
    await userEvent.click(submit);
    await waitFor(() => expect(callsTo("/scheduling/reassign")).toHaveLength(1));
    expect(JSON.parse(callsTo("/scheduling/reassign")[0][1].body)).toEqual({
      from_crew_id: "c1", date: "2026-11-08", to_crew_id: "c2", reason: "Asha is unwell" });
  });

  it("shows a frozen-schedule conflict plainly and offers the code prompt", async () => {
    server({
      status: "Frozen",
      moveReply: () => json(409, err("schedule_frozen",
        "This schedule is frozen. Unfreeze it with the code to move work.")),
    });
    await openDay();
    expect(await screen.findByLabelText(/This schedule is frozen. Dropping a card on Unscheduled needs no code/)).toBeInTheDocument();
    await userEvent.click(within(await column("c1")).getByRole("button", { name: /KA01AB1234/ }));
    await userEvent.click(screen.getByRole("button", { name: "Move here" }));
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("This schedule is frozen. Unfreeze it with the code to move work.");
    await userEvent.click(within(alert).getByRole("button", { name: "Unfreeze with code" }));
    expect(screen.getByRole("dialog", { name: "Unfreeze with the code" })).toBeInTheDocument();
  });

  it("hides the cards that do not match the vehicle search; Show all brings them back disabled", async () => {
    server({ jobs: [job(), job({ id: "j2", registration: "KA02ZZ0001", crew_id: "c2", parking: "B2-07" })] });
    await openDay();
    await column("c1");
    await userEvent.type(screen.getByRole("searchbox", { name: "Find a job" }), "zz00");
    expect(screen.queryByRole("button", { name: /KA01AB1234/ })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /KA02ZZ0001/ })).not.toHaveClass("dim");
    await userEvent.click(screen.getByRole("switch", { name: "Show all" }));
    const hidden = screen.getByRole("button", { name: /KA01AB1234/ });
    expect(hidden).toHaveClass("dim");
    expect(hidden).toHaveAttribute("aria-disabled", "true");
    expect(screen.getByRole("button", { name: /KA02ZZ0001/ })).not.toHaveClass("dim");
  });
});

describe("search and filters on every view (ADM-SCH-33)", () => {
  const two = () => server({ jobs: [
    job({ customer_name: "Meena Rao" }),
    job({ id: "j2", registration: "KA02ZZ0001", vehicle: "Tata Nexon", customer_name: "Farhan Ali", crew_id: "c2",
          crew_name: "Ravi", parking: "B2-07", start_minute: 600, start_time: "10:00", end_time: "10:20", late: true }),
  ] });

  it("finds a job by customer, crew member or vehicle model, and by several words together", async () => {
    two();
    await openDay();
    await column("c1");
    await userEvent.click(screen.getByRole("switch", { name: "Show all" }));
    const find = screen.getByRole("searchbox", { name: "Find a job" });
    const card1 = screen.getByRole("button", { name: /KA01AB1234/ });
    const card2 = screen.getByRole("button", { name: /KA02ZZ0001/ });
    await userEvent.type(find, "farhan");
    expect(card1).toHaveClass("dim");
    expect(card2).not.toHaveClass("dim");
    await userEvent.clear(find);
    await userEvent.type(find, "ravi nexon");
    expect(card1).toHaveClass("dim");
    expect(card2).not.toHaveClass("dim");
    await userEvent.clear(find);
    await userEvent.type(find, "asha civic");
    expect(card1).toHaveClass("dim");
    expect(card2).toHaveClass("dim");
  });

  it("keeps only late jobs bright when Late is pressed", async () => {
    two();
    await openDay();
    await column("c1");
    await userEvent.click(screen.getByRole("button", { name: "Late" }));
    await userEvent.click(screen.getByRole("switch", { name: "Show all" }));
    expect(screen.getByRole("button", { name: /KA01AB1234/ })).toHaveClass("dim");
    expect(screen.getByRole("button", { name: /KA02ZZ0001/ })).not.toHaveClass("dim");
  });

  it("shows only the crew members chosen in the picker", async () => {
    two();
    await openDay();
    await column("c1");
    await userEvent.click(screen.getByRole("button", { name: /Crew shown: All crew/ }));
    await userEvent.click(await screen.findByRole("menuitemcheckbox", { name: "Ravi" }));
    await waitFor(() => expect(screen.queryByTestId("col-c1")).not.toBeInTheDocument());
    expect(screen.getByTestId("col-c2")).toBeInTheDocument();
    expect(screen.getByTestId("col-unscheduled")).toBeInTheDocument();
  });
});

describe("focus view and the board in its own tab (ADM-SCH-33)", () => {
  it("opens the board alone in a full-screen dialog, where a card still opens, and Escape goes back", async () => {
    server();
    await openDay();
    await column("c1");
    await userEvent.click(screen.getByRole("button", { name: /Focus/ }));
    const focus = await screen.findByRole("dialog", { name: "Schedule board, focus view" });
    // Only the board: no tabs. The top bar keeps the Run button, as on the page (item 8).
    expect(within(focus).queryByRole("tablist")).not.toBeInTheDocument();
    expect(within(focus).getByRole("button", { name: "Run" })).toBeInTheDocument();
    expect(within(focus).getByRole("button", { name: "Freeze" })).toBeInTheDocument();
    const card = await within(focus).findByRole("button", { name: /KA01AB1234/ });
    await userEvent.click(card);
    // The job dialog stacks over the focus view.
    expect(await screen.findByRole("dialog", { name: /KA01AB1234/ })).toBeInTheDocument();
    await userEvent.keyboard("{Escape}");
    await waitFor(() => expect(screen.queryByRole("dialog", { name: /KA01AB1234/ })).not.toBeInTheDocument());
    expect(screen.getByRole("dialog", { name: "Schedule board, focus view" })).toBeInTheDocument();
    await userEvent.keyboard("{Escape}");
    await waitFor(() => expect(screen.queryByRole("dialog", { name: "Schedule board, focus view" })).not.toBeInTheDocument());
  });

  it("opens the focus view with the F key, but not while typing", async () => {
    server();
    await openDay();
    await column("c1");
    await userEvent.type(screen.getByRole("searchbox", { name: "Find a job" }), "f");
    expect(screen.queryByRole("dialog", { name: "Schedule board, focus view" })).not.toBeInTheDocument();
    await userEvent.click(document.body);
    await userEvent.keyboard("f");
    expect(await screen.findByRole("dialog", { name: "Schedule board, focus view" })).toBeInTheDocument();
  });

  it("links to the board alone in a new tab, keeping the day and the view", async () => {
    server();
    await openDay("2026-11-08", "&view=table");
    const link = await screen.findByRole("link", { name: /New tab/ });
    expect(link).toHaveAttribute("target", "_blank");
    expect(link).toHaveAttribute("rel", expect.stringContaining("noopener"));
    expect(link.getAttribute("href")).toBe("/schedule/board?date=2026-11-08&view=table");
  });

  it("shows only the board when it is the page of its own tab", async () => {
    server();
    wrap(<SchedulePage mode="solo" />, "/schedule/board?date=2026-11-08");
    expect(await within(await screen.findByTestId("col-c1")).findByRole("button", { name: /KA01AB1234/ })).toBeInTheDocument();
    expect(screen.queryByRole("tablist")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Run" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Focus/ })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Next day" })).toBeInTheDocument();
    // The strip of days starts folded here, to leave the room to the board, and never changes what the page remembers.
    expect(screen.queryByRole("group", { name: "Days" })).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Show days" }));
    expect(await screen.findByRole("group", { name: "Days" })).toBeInTheDocument();
    expect(localStorage.getItem("priveo.schedule.days-folded")).toBeNull();
  });
});

describe("lanes: fold, hide off crew, pan (ADM-SCH-33)", () => {
  it("folds a crew member's lane to a thin strip, still takes a dropped card, and remembers it", async () => {
    server();
    await openDay();
    await column("c1");
    await userEvent.click(screen.getByRole("button", { name: "Fold Ravi's lane" }));
    const strip = screen.getByRole("region", { name: "Ravi, folded" });
    expect(strip).toHaveTextContent("Ravi");
    expect(strip.querySelector(".sch-col-body")).toBeNull();
    expect(JSON.parse(localStorage.getItem("priveo.schedule.folded-lanes")!)).toEqual(["c2"]);
    // A card dropped on the strip goes to Ravi's first free time.
    dragTo(within(await column("c1")).getByRole("button", { name: /KA01AB1234/ }), strip);
    await waitFor(() => expect(batchCalls()).toHaveLength(1));
    expect(batchBody(0).moves).toEqual([{ job_id: "j1", crew_id: "c2", start_minute: 480 }]);
    await userEvent.click(screen.getByRole("button", { name: "Show Ravi's lane" }));
    expect(screen.getByRole("region", { name: "Ravi" })).toBeInTheDocument();
    expect(JSON.parse(localStorage.getItem("priveo.schedule.folded-lanes")!)).toEqual([]);
  });

  it("hides the crew members who are off today from the crew picker", async () => {
    server({ boardReply: () => json(200, board("Draft", [job()], [
      { crew_id: "c1", status: "Working", windows: [{ start: 480, end: 720 }], reason: "" },
      { crew_id: "c2", status: "Off", windows: [], reason: "Sick on this date." },
    ])) });
    await openDay();
    await column("c2");
    await userEvent.click(screen.getByRole("button", { name: /Crew shown: All crew/ }));
    await userEvent.click(await screen.findByRole("menuitemcheckbox", { name: "Hide crew who are off today" }));
    await waitFor(() => expect(screen.queryByTestId("col-c2")).not.toBeInTheDocument());
    expect(screen.getByTestId("col-c1")).toBeInTheDocument();
    await userEvent.keyboard("{Escape}");
    expect(await screen.findByRole("button", { name: /Crew shown: Working crew/ })).toBeInTheDocument();
  });

  it("pans the board sideways when its background or a column heading is dragged", async () => {
    server();
    await openDay();
    await column("c1");
    const board = screen.getByRole("group", { name: "Day board" });
    board.scrollLeft = 100;
    fireEvent.pointerDown(board, { button: 0, clientX: 300, pointerId: 1 });
    fireEvent.pointerMove(board, { clientX: 250, pointerId: 1 });
    expect(board.scrollLeft).toBe(150);
    expect(board).toHaveClass("panning");
    fireEvent.pointerUp(board, { pointerId: 1 });
    expect(board).not.toHaveClass("panning");
    // A press on a card does not pan: it is a drag of the card.
    const card = screen.getByRole("button", { name: /KA01AB1234/ });
    fireEvent.pointerDown(card, { button: 0, clientX: 300, pointerId: 1 });
    expect(board).not.toHaveClass("panning");
  });

  it("scrolls the board sideways with the wheel over a heading, not over a lane", async () => {
    server();
    await openDay();
    await column("c1");
    const board = screen.getByRole("group", { name: "Day board" });
    board.scrollLeft = 0;
    fireEvent.wheel(within(screen.getByTestId("col-c1")).getByText("1", { selector: ".sch-count" }), { deltaY: 120 });
    expect(board.scrollLeft).toBe(120);
    fireEvent.wheel(bodyOf(screen.getByTestId("col-c1")), { deltaY: 80 });
    expect(board.scrollLeft).toBe(120);
  });
});

describe("the table view (ADM-SCH-33)", () => {
  const three = () => server({ jobs: [
    job({ customer_name: "Meena Rao" }),
    job({ id: "j2", registration: "KA02ZZ0001", vehicle: "Tata Nexon", customer_name: "Farhan Ali", crew_id: "c2",
          crew_name: "Ravi", parking: "B2-07", start_minute: 600, start_time: "10:00", end_time: "10:20", late: true }),
    job({ id: "j3", registration: "KA03UN0003", customer_name: "Zoya", crew_id: null, crew_name: null,
          start_minute: null, start_time: null, end_time: null, reason: "No crew member is free." }),
  ] });
  const rowsOf = () => within(screen.getByRole("region", { name: "Jobs of the day" })).getAllByRole("row").slice(1);

  it("lists every job with its crew member and card details, unassigned first", async () => {
    three();
    await openDay("2026-11-08", "&view=table");
    const region = await screen.findByRole("region", { name: "Jobs of the day" });
    expect(screen.getByRole("button", { name: /Table/ })).toHaveAttribute("aria-pressed", "true");
    const heads = within(region).getAllByRole("columnheader").map((h) => h.textContent?.trim());
    expect(heads).toEqual(["Time", "Crew", "Vehicle", "Customer", "Parking", "Service", "Min", "Finish by", "Status", "Notes"]);
    const rows = rowsOf();
    expect(rows).toHaveLength(3);
    expect(rows[0]).toHaveTextContent("Unassigned");
    expect(rows[0]).toHaveTextContent("KA03UN0003");
    expect(rows[1]).toHaveTextContent("Asha");
    expect(rows[1]).toHaveTextContent("Honda City");
    expect(rows[1]).toHaveTextContent("Meena Rao");
    expect(rows[1]).toHaveTextContent("B1-24");
    expect(rows[1]).toHaveTextContent("09:00-09:20");
    expect(rows[2]).toHaveTextContent("Ravi");
    expect(rows[2]).toHaveTextContent("Late");
    expect(screen.getByRole("status", { name: "" })).toHaveTextContent("3 jobs");
  });

  it("sorts by a column and reverses it on a second click", async () => {
    three();
    await openDay("2026-11-08", "&view=table");
    await screen.findByRole("region", { name: "Jobs of the day" });
    await userEvent.click(screen.getByRole("button", { name: "Customer" }));
    expect(rowsOf().map((r) => r.getAttribute("aria-label"))).toEqual(["KA02ZZ0001, Ravi", "KA01AB1234, Asha", "KA03UN0003, Unassigned"]);
    await userEvent.click(screen.getByRole("button", { name: "Customer" }));
    expect(rowsOf().map((r) => r.getAttribute("aria-label"))).toEqual(["KA03UN0003, Unassigned", "KA01AB1234, Asha", "KA02ZZ0001, Ravi"]);
    expect(screen.getByRole("columnheader", { name: "Customer" })).toHaveAttribute("aria-sort", "descending");
  });

  it("lists only what the search and the chips keep, and says how many are hidden", async () => {
    three();
    await openDay("2026-11-08", "&view=table");
    await screen.findByRole("region", { name: "Jobs of the day" });
    await userEvent.type(screen.getByRole("searchbox", { name: "Find a job" }), "zoya");
    expect(rowsOf()).toHaveLength(1);
    expect(screen.getByRole("status", { name: "" })).toHaveTextContent("1 of 3 jobs");
    await userEvent.clear(screen.getByRole("searchbox", { name: "Find a job" }));
    await userEvent.click(screen.getByRole("button", { name: "Late" }));
    expect(rowsOf()).toHaveLength(1);
    expect(rowsOf()[0]).toHaveTextContent("KA02ZZ0001");
  });

  it("opens the job dialog from a row, where it can be moved", async () => {
    three();
    await openDay("2026-11-08", "&view=table");
    await screen.findByRole("region", { name: "Jobs of the day" });
    await userEvent.click(screen.getByRole("row", { name: "KA03UN0003, Unassigned" }));
    expect(await screen.findByRole("dialog", { name: /KA03UN0003/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Move here" })).toBeInTheDocument();
  });

  it("makes a CSV of the rows shown, with formula-looking text defused", () => {
    const csv = jobsCsv([
      job({ customer_name: "=HYPERLINK(\"x\")", reason: "Late, sorry" }) as never,
    ]);
    const [head, row] = csv.split("\r\n");
    expect(head).toBe("Time,Crew,Registration,Vehicle,Customer,Parking,Service,Duration (min),Finish by,Status,Late,By hand,Reason");
    expect(row).toContain("09:00-09:20,Asha,KA01AB1234,Honda City,\"'=HYPERLINK(\"\"x\"\")\",B1-24");
    expect(row).toContain('"Late, sorry"');
    expect(csvCell("+1")).toBe("'+1");
    expect(csvCell(null)).toBe("");
  });
});

describe("the timeline view (ADM-SCH-33)", () => {
  it("shows compact rows on an hour ruler for the day's hours, with details on hover and nothing to drag", async () => {
    server();
    await openDay("2026-11-08", "&view=timeline");
    const chart = await screen.findByRole("group", { name: "Day timeline" });
    expect(screen.getByRole("button", { name: /Timeline/ })).toHaveAttribute("aria-pressed", "true");
    // The crew work 08:00 to 12:00, so the ruler runs 08:00 to 12:00 with a label each hour.
    const hours = [...chart.querySelectorAll(".sch-tl-hour")].map((h) => h.textContent);
    expect(hours).toEqual(["08:00", "09:00", "10:00", "11:00", ""]);
    const row = screen.getByTestId("row-c1");
    expect(row).toHaveTextContent("Asha");
    expect(row).toHaveTextContent("20/240");
    const block = within(row).getByLabelText(/09:00-09:20 EXT,KA01AB1234,B1-24, Scheduled/);
    // 09:00 is a quarter of the way through 08:00-12:00; 20 minutes is a twelfth of it.
    expect(block.style.left).toBe("25%");
    expect(parseFloat(block.style.width)).toBeCloseTo(8.333, 2);
    expect(block).not.toHaveAttribute("draggable");
    expect(screen.queryByRole("group", { name: "Day board" })).not.toBeInTheDocument();

    await userEvent.hover(block);
    // The job tip is the timeline's own tooltip; the (i) hint has a tooltip of its own now.
    const tip = document.getElementById("sch-tl-tip") as HTMLElement;
    expect(tip).toHaveTextContent("Honda City");
    expect(tip).toHaveTextContent("Meena");
    expect(tip).toHaveTextContent("Finish by10:00");
    await userEvent.unhover(block);
    expect(document.getElementById("sch-tl-tip")).toBeNull();
  });

  it("switches between Cards and Timeline", async () => {
    server();
    await openDay();
    expect(await screen.findByRole("group", { name: "Day board" })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /Timeline/ }));
    expect(await screen.findByRole("group", { name: "Day timeline" })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /Cards/ }));
    expect(await screen.findByRole("group", { name: "Day board" })).toBeInTheDocument();
  });
});

describe("the chosen day leads the page (ADM-SCH-35)", () => {
  function nextDay() {
    const b = board("Frozen", [job({ id: "j7", date: "2026-11-15", registration: "KA07AA0007", status: "Completed",
                                     schedule_id: "sch2" })]);
    b.schedule = { ...b.schedule, id: "sch2", start_date: "2026-11-15", end_date: "2026-11-15" };
    b.days = [{ ...b.days[0], date: "2026-11-15" }];
    return b;
  }

  it("shows the days with their schedule status and moves the whole page to the day chosen", async () => {
    server({ boards: { sch2: nextDay() } });
    await openDay();
    const days = await screen.findByRole("group", { name: "Days" });
    const first = await within(days).findByRole("button", { name: /^Sun 08-Nov-26, Draft/ });
    expect(first).toHaveAttribute("aria-pressed", "true");
    const later = within(days).getByRole("button", { name: /^Sun 15-Nov-26, Frozen/ });
    expect(later).toHaveAttribute("aria-pressed", "false");
    expect(screen.getByTitle(/Part of the schedule for Sun 08-Nov-26 to Sat 14-Nov-26/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Freeze" })).toBeInTheDocument();

    await userEvent.click(later);
    expect(later).toHaveAttribute("aria-pressed", "true");
    expect(first).toHaveAttribute("aria-pressed", "false");
    expect(await screen.findByRole("button", { name: /KA07AA0007/ })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /KA01AB1234/ })).not.toBeInTheDocument();
    expect(screen.getByTitle("A schedule for this day only.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Unfreeze" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Freeze" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /^All jobs/ })).not.toBeInTheDocument();
  });

  it("folds the day strip away to give the board room, and remembers it", async () => {
    localStorage.removeItem("priveo.schedule.days-folded");
    server();
    await openDay();
    expect(await screen.findByRole("group", { name: "Days" })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Hide days" }));
    expect(screen.queryByRole("group", { name: "Days" })).not.toBeInTheDocument();
    // The arrows and the date field stay, so the day can still be changed.
    expect(screen.getByRole("button", { name: "Next day" })).toBeInTheDocument();
    expect(localStorage.getItem("priveo.schedule.days-folded")).toBe("1");
    await userEvent.click(screen.getByRole("button", { name: "Show days" }));
    expect(await screen.findByRole("group", { name: "Days" })).toBeInTheDocument();
    expect(localStorage.getItem("priveo.schedule.days-folded")).toBe("0");
  });

  it("steps a day with the arrows and says when a day has no schedule", async () => {
    server();
    await openDay("2026-11-14");
    expect(await screen.findByRole("button", { name: "Freeze" })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Next day" }));
    expect(await screen.findByText("No schedule covers this day yet. Run the scheduler to make a draft.")).toBeInTheDocument();
    expect(screen.getByText("No schedule for Sun 15-Nov-26")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Previous day" }));
    expect(await screen.findByRole("button", { name: "Freeze" })).toBeInTheDocument();
  });

  it("the Today button moves the whole page to today (item 11)", async () => {
    server();
    await openDay("2026-11-14");
    await screen.findByRole("button", { name: "Freeze" });
    await userEvent.click(screen.getByRole("button", { name: "Today" }));
    expect(screen.getByLabelText("Day")).toHaveValue(toIso(new Date()));
  });

  it("runs the scheduler for the chosen day only (daily runs only, ADM-SCH-09)", async () => {
    server({ boardReply: () => json(404, err("not_found", "No schedule has been run for that day.")) });
    await openDay("2026-11-11");
    // No schedule covers the day, so the board offers to run the scheduler.
    await userEvent.click(await screen.findByRole("button", { name: "Run the scheduler" }));
    expect(await screen.findByText("Run the scheduler, Palm Grove")).toBeInTheDocument();
    expect(screen.getByText("Wed 11-Nov-26")).toBeInTheDocument();
    expect(screen.queryByLabelText("Start date")).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Run scheduler" }));
    await waitFor(() => expect(callsTo("/run")).toHaveLength(1));
    expect(JSON.parse(callsTo("/run")[0][1].body)).toEqual({ society_id: SOC, start_date: "2026-11-11", days: 1 });
  });

  it("marks days that need the admin, and has no Needs scheduling tab (the Board's Unscheduled column shows those jobs)", async () => {
    server({ needs: [
      job({ id: "j9", crew_id: null, crew_name: null, start_minute: null, start_time: null, reason: "Capacity is short." }),
      job({ id: "j10", date: "2026-11-09", registration: "KA10NN0010", crew_id: null, crew_name: null,
            start_minute: null, start_time: null, reason: "No crew member fits." }),
    ] });
    await openDay();
    const days = await screen.findByRole("group", { name: "Days" });
    // The label says ", today" in front of the flag on the day it is run; the check holds on any day.
    expect(await within(days).findByRole("button", { name: /^Mon 09-Nov-26, Draft, (today, )?Needs Attention/ })).toBeInTheDocument();
    const tabs = await screen.findByRole("tablist", { name: "Schedule sections" });
    expect(within(tabs).queryByRole("tab", { name: /Needs scheduling/ })).not.toBeInTheDocument();
  });
});

describe("freezing", () => {
  it("freezes a draft after a confirmation that names all its days", async () => {
    server();
    await openDay();
    await userEvent.click(await screen.findByRole("button", { name: "Freeze" }));
    expect(callsTo("/freeze")).toHaveLength(0);
    expect(await screen.findByText(/every day from Sun 08-Nov-26 to Sat 14-Nov-26/)).toBeInTheDocument();
    await confirmWith("Freeze");
    await waitFor(() => expect(callsTo("/freeze")).toHaveLength(1));
    expect(callsTo("/freeze")[0][0]).toBe("/v1/admin/scheduling/schedules/sch1/freeze");
  });

  it("unfreezes with the code and shows a wrong code inside the prompt", async () => {
    let tries = 0;
    server({
      status: "Frozen",
      unfreezeReply: () => (++tries === 1
        ? json(403, err("wrong_code", "That code is not right."))
        : json(200, board("Draft").schedule)),
    });
    await openDay();
    await userEvent.click(await screen.findByRole("button", { name: "Unfreeze" }));
    const dialog = screen.getByRole("dialog");
    await userEvent.type(within(dialog).getByLabelText("Code"), "nope");
    await userEvent.click(within(dialog).getByRole("button", { name: "Unfreeze" }));
    expect(await within(dialog).findByText("That code is not right.")).toBeInTheDocument();
    await userEvent.clear(within(dialog).getByLabelText("Code"));
    await userEvent.type(within(dialog).getByLabelText("Code"), "unfreeze");
    await userEvent.click(within(dialog).getByRole("button", { name: "Unfreeze" }));
    await waitFor(() => expect(callsTo("/unfreeze")).toHaveLength(2));
    expect(JSON.parse(callsTo("/unfreeze")[1][1].body)).toEqual({ code: "unfreeze" });
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
  });
});

describe("job status on the board (ADM-SCH-34)", () => {
  it("fills completed cards green and missed ones red, counts each status and picks one out", async () => {
    server({ jobs: [
      job({ id: "j1", registration: "KA01AA0001", status: "Completed" }),
      job({ id: "j2", registration: "KA01AA0002", status: "Could not complete", start_minute: 600, start_time: "10:00", end_time: "10:20" }),
      job({ id: "j3", registration: "KA01AA0003", status: "Scheduled", start_minute: 660, start_time: "11:00", end_time: "11:20" }),
    ] });
    await openDay();
    const asha = await column("c1");
    const card = (reg: string) => within(asha).getByRole("button", { name: new RegExp(reg) });
    expect(card("KA01AA0001")).toHaveClass("done");
    expect(card("KA01AA0002")).toHaveClass("failed");
    expect(card("KA01AA0002")).toHaveTextContent("Could not complete");
    expect(card("KA01AA0003")).not.toHaveClass("done");
    expect(card("KA01AA0003")).not.toHaveClass("failed");

    const chips = screen.getByRole("group", { name: "Job status" });
    expect(within(chips).queryByRole("button", { name: /^(All jobs|Scheduled)/ })).not.toBeInTheDocument();
    await userEvent.click(within(chips).getByRole("button", { name: "Could not complete 1" }));
    await userEvent.click(screen.getByRole("switch", { name: "Show all" }));
    expect(card("KA01AA0002")).not.toHaveClass("dim");
    expect(card("KA01AA0001")).toHaveClass("dim");
    await userEvent.click(within(chips).getByRole("button", { name: "Could not complete 1" }));
    expect(card("KA01AA0001")).not.toHaveClass("dim");
  });
});

describe("skipped and finished jobs cannot be placed or moved", () => {
  it("leaves a skipped job off the board and shows a finished job without move controls", async () => {
    server({ jobs: [
      job({ id: "j1", status: "Completed" }),
      job({ id: "j5", registration: "KA05SK0005", crew_id: null, crew_name: null, start_minute: null,
            start_time: null, status: "Skipped" }),
    ] });
    await openDay();
    const card = within(await column("c1")).getByRole("button", { name: /KA01AB1234/ });
    expect(card).toHaveAttribute("draggable", "false");
    const unscheduled = await column("unscheduled");
    expect(unscheduled).toHaveAccessibleName("Unscheduled (0)");
    expect(within(unscheduled).getByText("Every job of this day has a crew member.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /KA05SK0005/ })).not.toBeInTheDocument();

    await userEvent.click(card);
    const dialog = screen.getByRole("dialog");
    expect(within(dialog).getByText("This job is Completed, so it can no longer be placed or moved.")).toBeInTheDocument();
    expect(within(dialog).queryByLabelText("Start time")).not.toBeInTheDocument();
    // The dialog's own X is also named Close; the footer button is the last one.
    await userEvent.click(within(dialog).getAllByRole("button", { name: "Close" }).at(-1)!);
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(callsTo("/move")).toHaveLength(0);
  });

  it("counts skipped jobs and lists them with why for the chosen day on their own tab (ADM-SCH-36)", async () => {
    server({ jobs: [
      job(),
      job({ id: "j5", registration: "KA05SK0005", crew_id: "c2", status: "Skipped" }),
    ] });
    await openDay();
    expect(within(await column("c2")).queryByRole("button", { name: /KA05SK0005/ })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /^All jobs/ })).not.toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Skipped and paused (1)" })).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "1 skipped or paused, not shown" }));
    expect(screen.getByRole("tab", { name: "Skipped and paused (1)" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByText("Skipped and paused on Sun 08-Nov-26")).toBeInTheDocument();
    expect(await screen.findByText("Paused by the customer, 08-Nov-26 to 10-Nov-26")).toBeInTheDocument();
    expect(screen.getByText("Skipped by operations")).toBeInTheDocument();
    const [path] = fetchMock.mock.calls.find((c) => String(c[0]).startsWith("/v1/admin/scheduling/skipped?"))!;
    expect(String(path)).toContain("date_from=2026-11-08");
    expect(String(path)).toContain("date_to=2026-11-08");

    await choose("Show", "Paused only");
    expect(screen.queryByText("Skipped by operations")).not.toBeInTheDocument();
    expect(screen.getByText("Paused by the customer, 08-Nov-26 to 10-Nov-26")).toBeInTheDocument();
  });
});

// The run plays its music (ux9, item 4), and jsdom has no media element to play it: stub play and pause.
HTMLMediaElement.prototype.play = () => Promise.resolve();
HTMLMediaElement.prototype.pause = () => {};

describe("schedule tabs and unavailable crew time", () => {
  const avail = [
    { crew_id: "c1", status: "Partial", windows: [{ start: 480, end: 600 }],
      reason: "Late start from 08:00. Works 08:00-10:00." },
    { crew_id: "c2", status: "Off", windows: [], reason: "Sick on this date." },
  ];

  it("shows the sections as tabs with the chosen day's counts, the board first once a schedule exists", async () => {
    server({ interiorMissing: [{ subscription_id: "sub1", vehicle_id: "veh1", registration: "KA07IN0007",
      customer_name: "Meena", vehicle: "Honda City", plan_name: "Premium" }] });
    await openDay();
    const tabs = await screen.findByRole("tablist", { name: "Schedule sections" });
    await waitFor(() => expect(within(tabs).getAllByRole("tab").map((x) => x.textContent)).toEqual([
      "Board", "Needs Attention (1)", "Skipped and paused", "Cutoff requests", "Crew queue", "Draft improvements", "Rules", "Reports"]));
    expect(screen.getByRole("tab", { name: "Board" })).toHaveAttribute("aria-selected", "true");
    expect(screen.queryByText("Run the scheduler, Palm Grove")).not.toBeInTheDocument();
    // Run is a button in the top bar and opens a dialog.
    await userEvent.click(screen.getByRole("button", { name: "Run" }));
    expect(screen.getByText("Run the scheduler, Palm Grove")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Run again" })).toBeInTheDocument();
  });

  it("greys out a crew member who cannot work, explains it on hover and refuses a drop there", async () => {
    server({ boardReply: () => json(200, board("Draft", [job()], avail)) });
    await openDay();
    const ravi = await column("c2");
    expect(ravi).toHaveClass("closed");
    expect(ravi).toHaveTextContent("Sick on this date.");
    const tip = within(ravi).getByRole("tooltip");
    expect(tip).toHaveTextContent("Sick on this date.");
    expect(tip).toHaveTextContent("Cannot take work this day.");
    expect(within(await column("c1")).getByRole("tooltip")).toHaveTextContent("Booked");
    // Members who cannot work come last.
    const cols = within(screen.getByRole("group", { name: "Day board" })).getAllByRole("region");
    expect(cols.map((c) => c.getAttribute("aria-label"))).toEqual(["Unscheduled (0)", "Asha", "Ravi"]);

    dragTo(within(await column("c1")).getByRole("button", { name: /KA01AB1234/ }), bodyOf(ravi));
    expect(await screen.findByText("Ravi cannot take work this day. Sick on this date.")).toBeInTheDocument();
    expect(batchCalls()).toHaveLength(0);
  });

  it("greys out the time a crew member cannot work on the timeline", async () => {
    server({ boardReply: () => json(200, board("Draft", [job()], avail)) });
    await openDay("2026-11-08", "&view=timeline");
    // The ruler runs 08:00 to 12:00: Asha cannot work after 10:00, Ravi not at all.
    expect(within(await screen.findByTestId("row-c1")).getAllByTestId("grey")).toHaveLength(1);
    const ravi = screen.getByTestId("row-c2");
    expect(ravi).toHaveClass("closed");
    expect(ravi).toHaveTextContent("Off");
    expect(within(ravi).getByTestId("grey")).toHaveAttribute("title", "Sick on this date.");
  });
});

describe("capacity page", () => {
  it("shows demand against capacity and marks over capacity dates", async () => {
    server();
    wrap(<CapacityPage />);
    expect(await screen.findByText("Over capacity")).toBeInTheDocument();
    expect(screen.getAllByText("10 h").length).toBeGreaterThan(0);
    // The crew list moved to the Crew page; this page has the summary tiles instead.
    expect(screen.queryByText("Asha")).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Capacity Utilisation" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Capacity summary" })).toBeInTheDocument();
  });

  it("gives the breakup of crew hours and demand in a tooltip", async () => {
    server();
    wrap(<CapacityPage />);
    const [crew] = await screen.findAllByLabelText(/^Crew available 8 h/);
    const tip = within(crew).getByRole("tooltip");
    expect(tip).toHaveTextContent("Asha Rao (Member)");
    expect(tip).toHaveTextContent("05:00-13:00");
    const demand = screen.getByLabelText(/^Demand 10 h/);
    const lines = within(demand).getByRole("tooltip");
    expect(lines).toHaveTextContent("Cleaning-External");
    expect(lines).toHaveTextContent("24 jobs");
    expect(lines).toHaveTextContent("Deep Spa (add-on)");
    expect(lines).toHaveTextContent("1 job");
  });
});

/** server(), plus replies for the given paths. */
function serverWith(extra: Record<string, (init?: RequestInit) => Response>, o: Opts = {}) {
  server(o);
  const base = fetchMock.getMockImplementation()!;
  fetchMock.mockImplementation(async (path: string, init?: RequestInit) => {
    const hit = Object.keys(extra).find((k) => String(path).startsWith(k));
    return hit ? extra[hit](init) : base(path, init);
  });
}

describe("long runs, confirmations and the action tabs", () => {
  it("shows that the scheduler is running, then reports the result with a link to the board", async () => {
    let finish: (r: Response) => void = () => {};
    serverWith({ "/v1/admin/scheduling/run": () => new Promise<Response>((res) => { finish = res; }) as unknown as Response },
      { boardReply: () => json(404, err("not_found", "No schedule has been run for that week.")) });
    await openDay();
    await userEvent.click(await screen.findByRole("button", { name: "Run the scheduler" }));
    await userEvent.click(await screen.findByRole("button", { name: "Run scheduler" }));
    // The dialog closes at once; the bar button shows the run and the task tray follows it.
    expect(await screen.findByRole("button", { name: "Running…" })).toBeDisabled();
    finish(json(200, { schedules: [{ schedule_id: "sch1", society_id: SOC, status: "Draft", placed: 3, unscheduled: 1, late: 0 }] }));
    expect((await screen.findAllByText("3 placed, 1 unscheduled, 0 late.")).length).toBeGreaterThan(0);
  });

  it("offers no weekly or monthly run, and changes no default period (ADM-SCH-09)", async () => {
    server();
    await openDay();
    await userEvent.click(await screen.findByRole("button", { name: "Run" }));
    expect(screen.getByText("Day to schedule")).toBeInTheDocument();
    expect(screen.queryByText("Period")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /the default$/ })).not.toBeInTheDocument();
    expect(fetchMock.mock.calls.some(([p, i]) => String(p).includes("settings/schedule.period") && i?.method === "PUT")).toBe(false);
  });

  it("shows the chosen day's cutoff requests, links to other days and applies or rejects after a confirmation", async () => {
    serverWith({
      "/v1/admin/scheduling/cutoff-requests/r1/handle": () => json(200, {}),
      "/v1/admin/scheduling/cutoff-requests": () => json(200, [{ id: "r1", registration: "HR01", customer_name: "Asha", date: "2026-11-09",
        cutoff_time: "08:00", old_cutoff: "10:00", crew_name: "Raj", start_time: "07:00" }]),
    });
    await openDay();
    await userEvent.click(await screen.findByRole("tab", { name: "Cutoff requests" }));
    expect(await screen.findByText("No pending cutoff requests for this day.")).toBeInTheDocument();
    expect(screen.getByText("1 more request on other days:")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Mon 09-Nov-26 (1)" }));
    expect(screen.getByRole("tab", { name: "Cutoff requests (1)" })).toHaveAttribute("aria-selected", "true");
    await userEvent.click(await screen.findByRole("button", { name: "Apply and schedule" }));
    await confirmWith("Apply and schedule");
    await waitFor(() => expect(callsTo("/r1/handle")).toHaveLength(1));
    expect(JSON.parse(callsTo("/r1/handle")[0][1].body)).toEqual({ apply: true });
    await userEvent.click(screen.getByRole("button", { name: "Reject" }));
    await confirmWith("Reject");
    await waitFor(() => expect(callsTo("/r1/handle")).toHaveLength(2));
    expect(JSON.parse(callsTo("/r1/handle")[1][1].body)).toEqual({ apply: false });
  });

  it("swaps two jobs of the day and applies the chosen improvements with the preview fingerprint", async () => {
    serverWith({
      "/v1/admin/scheduling/jobs/swap": () => json(200, {}),
      "/v1/admin/scheduling/schedules/sch1/suggestions/apply": () => json(200, {}),
      "/v1/admin/scheduling/schedules/sch1/suggestions": () => json(200, { fingerprint: "version1",
        items: [{ job_id: "j1", crew_id: "c2", start_minute: 425, date: "2026-11-08", service: "Cleaning-External" },
                { job_id: "j8", crew_id: "c2", start_minute: 500, date: "2026-11-09", service: "Cleaning-External" }] }),
    }, { jobs: [job(), job({ id: "j2", registration: "KA02ZZ0001", crew_id: "c2", crew_name: "Ravi" }),
                job({ id: "j8", registration: "KA08OT0008", date: "2026-11-09" })] });
    await openDay();
    await userEvent.click(await screen.findByRole("tab", { name: "Draft improvements" }));
    await userEvent.click(screen.getByRole("combobox", { name: "First job" }));
    expect(screen.queryByRole("option", { name: /KA08OT0008/ })).not.toBeInTheDocument();
    await userEvent.click(await screen.findByRole("option", { name: /KA01AB1234/ }));
    await choose("Second job", /KA02ZZ0001/);
    await userEvent.click(screen.getByRole("button", { name: "Swap crew and times" }));
    await confirmWith("Swap crew and times");
    await waitFor(() => expect(callsTo("/jobs/swap")).toHaveLength(1));
    expect(JSON.parse(callsTo("/jobs/swap")[0][1].body)).toEqual({ first_job_id: "j1", second_job_id: "j2" });

    await userEvent.click(screen.getByRole("button", { name: "Preview improvements" }));
    const choice = await screen.findByRole("checkbox", { name: "Apply for KA01AB1234" });
    // The suggestion for another day is not offered here.
    expect(screen.queryByRole("checkbox", { name: "Apply for KA08OT0008" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Apply selected improvements" })).toBeDisabled();
    await userEvent.click(choice);
    await userEvent.click(screen.getByRole("button", { name: "Apply selected improvements" }));
    await confirmWith("Apply selected improvements");
    await waitFor(() => expect(callsTo("/suggestions/apply")).toHaveLength(1));
    expect(JSON.parse(callsTo("/suggestions/apply")[0][1].body)).toEqual({ fingerprint: "version1", job_ids: ["j1"] });
  });

  it("disables the draft actions on a frozen schedule", async () => {
    server({ status: "Frozen" });
    await openDay();
    await userEvent.click(await screen.findByRole("tab", { name: "Draft improvements" }));
    expect(await screen.findByText("This day's schedule is frozen. Unfreeze it to swap work or apply improvements.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Preview improvements" })).toBeDisabled();
  });

  it("lists add-ons waiting for a scheduling period on their day under the Board", async () => {
    serverWith({ "/v1/admin/scheduling/needs-scheduling": () => json(200, { jobs: [],
      pending_addons: [{ id: "b1", registration: "HR03", date: "2026-11-21", finish_by: "12:00" }] }) });
    await openDay("2026-11-21");
    expect(await screen.findByText("Add-ons awaiting a scheduling period")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Manage booking" })).toHaveAttribute("href", "/addons");
  });
});

describe("freeze by itself and the run (ADM-SCH-25, ADM-SCH-32)", () => {
  it("shows no freeze time for a draft while Freeze by itself is off", async () => {
    server();
    await openDay();
    expect(await screen.findByRole("button", { name: "Freeze" })).toBeInTheDocument();
    await waitFor(() => expect(fetchMock.mock.calls.some(([p]) => String(p).startsWith("/v1/admin/features"))).toBe(true));
    expect(screen.queryByText(/Freezes by itself/)).not.toBeInTheDocument();
  });

  it("shows the freeze time for a draft once Freeze by itself is on", async () => {
    server({ autoFreeze: true });
    await openDay();
    expect(await screen.findByText(/Freezes by itself at/)).toBeInTheDocument();
  });

  it("keeps the card detail switch on the timeline and the table, not only the cards", async () => {
    server();
    await openDay("2026-11-08", "&view=timeline");
    expect(await screen.findByRole("button", { name: "Standard", pressed: true })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /Table/ }));
    expect(await screen.findByRole("button", { name: "Standard", pressed: true })).toBeInTheDocument();
  });

  it("shows the lines of a detailed card: zone, model and cutoff; EXT and slot; car number and customer", async () => {
    localStorage.setItem("priveo.schedule.card-density", "detailed");
    server({ jobs: [job({ zone: "Zone 3", parking: "Zone 3 · B1-24", vehicle: "Honda City", model: "City", finish_by: "10:00" })] });
    await openDay();
    const card = within(await column("c1")).getByRole("button", { name: /KA01AB1234/ });
    const lines = [...card.querySelectorAll(".sch-card-line")];
    expect(lines).toHaveLength(3);
    expect(lines[0]).toHaveTextContent("Z3City10:00");
    expect(card).not.toHaveTextContent("Honda");
    expect(lines[1]).toHaveTextContent("EXT09:00-09:20");
    expect(lines[2]).toHaveTextContent("KA01AB1234Meena");
    expect(card).not.toHaveTextContent("B1-24");
  });

  it("shows a compact card as zone, EXT or INT and cutoff on one line", async () => {
    localStorage.setItem("priveo.schedule.card-density", "compact");
    server({ jobs: [job({ zone: "Zone 3" })] });
    await openDay();
    const card = within(await column("c1")).getByRole("button", { name: /KA01AB1234/ });
    const lines = [...card.querySelectorAll(".sch-card-line")];
    expect(lines).toHaveLength(1);
    expect(lines[0]).toHaveTextContent("Z3EXT10:00");
  });

  it("marks a card placed by hand against a rule as wine", async () => {
    server({ jobs: [job({ hand_breaches: ["That time is outside the crew member's hours."] })] });
    await openDay();
    expect(within(await column("c1")).getByRole("button", { name: /KA01AB1234/ })).toHaveClass("wine");
  });

  it("moves a detailed card in 15-minute steps with Alt and the arrow keys", async () => {
    localStorage.setItem("priveo.schedule.card-density", "detailed");
    server();
    await openDay();
    within(await column("c1")).getByRole("button", { name: /KA01AB1234/ }).focus();
    await userEvent.keyboard("{Alt>}{ArrowDown}{/Alt}");
    await waitFor(() => expect(callsTo("/move")).toHaveLength(1));
    expect(JSON.parse(callsTo("/move")[0][1].body)).toEqual({ crew_id: "c1", start_minute: 555 });
  });

  it("opens the card detail in the card's colour, with a zone and no Cancel button", async () => {
    server({ jobs: [job({ zone: "Zone 3" })] });
    await openDay();
    await userEvent.click(within(await column("c1")).getByRole("button", { name: /KA01AB1234/ }));
    const dialog = await screen.findByRole("dialog");
    expect(dialog).toHaveClass("sch-detail", "t-ext");
    expect(dialog).toHaveAttribute("style", expect.stringContaining("var(--type-bg)"));
    expect(dialog).toHaveTextContent("Zone");
    expect(within(dialog).queryByRole("button", { name: "Cancel" })).toBeNull();
  });

  it("shows the preferred Interior day in the card detail of an Interior card only", async () => {
    server({ jobs: [job({ service: "Cleaning-Internal", interior_day: "Tuesday" })] });
    await openDay();
    await userEvent.click(within(await column("c1")).getByRole("button", { name: /KA01AB1234/ }));
    const dialog = await screen.findByRole("dialog");
    expect(within(dialog).getByText("Preferred Interior day")).toBeInTheDocument();
    expect(within(dialog).getByText("Tuesday")).toBeInTheDocument();
  });

  it("refuses a drop that overlaps another job, naming the job in the way, and puts the card back", async () => {
    server({ batchReply: () => json(409, err("overlap", "KA02ZZ0001 is in the way at 10:00-10:20. Please try another time.")) });
    await openDay();
    dragTo(within(await column("c1")).getByRole("button", { name: /KA01AB1234/ }), bodyOf(await column("c2")));
    expect(await screen.findByText(/KA02ZZ0001 is in the way/)).toBeInTheDocument();
    expect(await within(await column("c1")).findByRole("button", { name: /KA01AB1234/ })).toBeInTheDocument();
    expect(within(await column("c2")).queryByRole("button", { name: /KA01AB1234/ })).not.toBeInTheDocument();
  });

  it("gives a detailed card taken off its crew member its reason as line four", async () => {
    localStorage.setItem("priveo.schedule.card-density", "detailed");
    server({ jobs: [job({ id: "j9", crew_id: null, crew_name: null, start_minute: null, start_time: null, zone: "Zone 1",
                          reason: "Capacity is short." })] });
    await openDay();
    const card = within(await column("unscheduled")).getByRole("button", { name: /KA01AB1234/ });
    expect(card).toHaveTextContent("Capacity is short.");
    expect(card.querySelector(".sch-zone")).toHaveTextContent("Z1");
  });

  it("shows the zone and the customer on a timeline block when detailed", async () => {
    localStorage.setItem("priveo.schedule.card-density", "detailed");
    server({ jobs: [job({ zone: "Zone 3", vehicle: "Honda City", model: "City" })] });
    await openDay("2026-11-08", "&view=timeline");
    const block = await screen.findByLabelText(/KA01AB1234/);
    expect(block).toHaveTextContent("Z3");
    expect(block).toHaveTextContent("City");
    expect(block).not.toHaveTextContent("Honda");
    expect(block).toHaveTextContent("Meena");
  });

  it("celebrates a finished run with its result", async () => {
    server({ boardReply: () => json(404, err("not_found", "No schedule has been run for that week.")) });
    await openDay("2026-11-11");
    await userEvent.click(await screen.findByRole("button", { name: "Run the scheduler" }));
    await userEvent.click(screen.getByRole("button", { name: "Run scheduler" }));
    expect(await screen.findByText("Schedule done")).toBeInTheDocument();
    expect(screen.getByText("Schedule done").parentElement).toHaveTextContent("3 placed, 1 unscheduled, 0 late.");
  });
});
