import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { withSite } from "../../site/testSite";
import { createEvent, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ToastProvider } from "../../components";
import { choose, confirmWith, PortalProviders } from "../../test/portal";
import { CapacityPage } from "../capacity/CapacityPage";
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
  freezeReply?: () => Response;
  unfreezeReply?: () => Response;
  boardReply?: () => Response;
  /** More boards by schedule ID, for the days of other schedules (ADM-SCH-35). */
  boards?: Record<string, ReturnType<typeof board>>;
  needs?: ReturnType<typeof job>[];
}

function server(o: Opts = {}) {
  fetchMock.mockImplementation(async (path: string, init?: RequestInit) => {
    const url = String(path);
    if (url.startsWith("/v1/admin/directory/settings")) return json(200, []);
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
const bodyOf = (col: HTMLElement) => col.querySelector(".sch-col-body")!;

/** Drags a card onto a column body, at a pointer height (jsdom has no DragEvent). */
function dragTo(card: Element, target: Element, clientY = 0) {
  fireEvent.dragStart(card, { dataTransfer: { setData: vi.fn() } });
  const dropEvent = createEvent.drop(target);
  Object.defineProperty(dropEvent, "clientY", { value: clientY });
  fireEvent(target, dropEvent);
}

beforeEach(() => vi.stubGlobal("fetch", fetchMock));
afterEach(() => {
  fetchMock.mockReset();
  vi.unstubAllGlobals();
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
    // Each card shows the time, the service code, the vehicle number and the parking place.
    const card1 = within(asha).getByRole("button", { name: "EXT,KA01AB1234,B1-24" });
    expect(card1).toHaveTextContent("09:00-09:20");
    expect(card1).toHaveTextContent("EXT");
    expect(card1).toHaveTextContent("B1-24");
    expect(card1).toHaveTextContent("by 10:00");
    const card2 = within(await column("c2")).getByRole("button", { name: /KA02ZZ0001/ });
    expect(card2).toHaveClass("late");
    expect(card2).toHaveClass("manual");
    expect(card2).toHaveTextContent("Late");
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

  it("moves a card to the first free time of another crew member", async () => {
    server();
    await openDay();
    const card = within(await column("c1")).getByRole("button", { name: /KA01AB1234/ });
    dragTo(card, bodyOf(await column("c2")));
    await waitFor(() => expect(callsTo("/move")).toHaveLength(1));
    const [path, init] = callsTo("/move")[0];
    expect(path).toBe("/v1/admin/scheduling/jobs/j1/move");
    expect(JSON.parse(init.body)).toEqual({ crew_id: "c2", start_minute: 480 });
    expect(await screen.findByText("KA01AB1234 moved to Ravi at 08:00.")).toBeInTheDocument();
  });

  it("puts a card dropped below another at the first free time after it", async () => {
    server({ jobs: [job(), job({ id: "j2", registration: "KA02ZZ0001", crew_id: "c2", crew_name: "Ravi",
                                 start_minute: 600, start_time: "10:00", end_time: "10:20" })] });
    await openDay();
    const ravi = await column("c2");
    const below = within(ravi).getByRole("button", { name: /KA02ZZ0001/ });
    below.getBoundingClientRect = () => ({ top: 0, height: 40, bottom: 40, left: 0, right: 0, width: 0, x: 0, y: 0, toJSON: () => ({}) });
    dragTo(within(await column("c1")).getByRole("button", { name: /KA01AB1234/ }), bodyOf(ravi), 100);
    await waitFor(() => expect(callsTo("/move")).toHaveLength(1));
    expect(JSON.parse(callsTo("/move")[0][1].body)).toEqual({ crew_id: "c2", start_minute: 620 });
  });

  it("starts a card where it is dropped inside a free slot, at any 5 minutes", async () => {
    server();
    await openDay();
    const slot = within(await column("c2")).getByLabelText("Free 08:00-12:00");
    slot.getBoundingClientRect = () => ({ top: 0, height: 100, bottom: 100, left: 0, right: 0, width: 0, x: 0, y: 0, toJSON: () => ({}) });
    // Halfway down the 240 minute slot: 08:00 + half of the 220 minutes a 20 minute job can start in.
    dragTo(within(await column("c1")).getByRole("button", { name: /KA01AB1234/ }), slot, 50);
    await waitFor(() => expect(callsTo("/move")).toHaveLength(1));
    expect(JSON.parse(callsTo("/move")[0][1].body)).toEqual({ crew_id: "c2", start_minute: 590 });
  });

  it("refuses a free slot too short for the card", async () => {
    server({ jobs: [job(), job({ id: "j2", registration: "KA02ZZ0001", crew_id: "c2", crew_name: "Ravi",
                                 start_minute: 490, start_time: "08:10", end_time: "08:30" })] });
    await openDay();
    const slot = within(await column("c2")).getByLabelText("Free 08:00-08:10");
    dragTo(within(await column("c1")).getByRole("button", { name: /KA01AB1234/ }), slot);
    expect(await screen.findByRole("alert")).toHaveTextContent("Only 10 min is free there; KA01AB1234 needs 20 min.");
    expect(callsTo("/move")).toHaveLength(0);
  });

  it("takes a card off its crew member when it is dropped on Unscheduled, after a confirmation", async () => {
    server();
    await openDay();
    dragTo(within(await column("c1")).getByRole("button", { name: /KA01AB1234/ }), bodyOf(await column("unscheduled")));
    expect(callsTo("/move")).toHaveLength(0);
    await confirmWith("Take off crew member");
    await waitFor(() => expect(callsTo("/move")).toHaveLength(1));
    expect(JSON.parse(callsTo("/move")[0][1].body)).toEqual({ crew_id: null, start_minute: null });
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
    expect(await screen.findByText(/This schedule is frozen. Dropping a card on Unscheduled needs no code/)).toBeInTheDocument();
    await userEvent.click(within(await column("c1")).getByRole("button", { name: /KA01AB1234/ }));
    await userEvent.click(screen.getByRole("button", { name: "Move here" }));
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("This schedule is frozen. Unfreeze it with the code to move work.");
    await userEvent.click(within(alert).getByRole("button", { name: "Unfreeze with code" }));
    expect(screen.getByRole("dialog", { name: "Unfreeze with the code" })).toBeInTheDocument();
  });

  it("dims the cards that do not match the vehicle search", async () => {
    server({ jobs: [job(), job({ id: "j2", registration: "KA02ZZ0001", crew_id: "c2", parking: "B2-07" })] });
    await openDay();
    await column("c1");
    await userEvent.type(screen.getByRole("searchbox", { name: "Find a vehicle" }), "zz00");
    expect(screen.getByRole("button", { name: /KA01AB1234/ })).toHaveClass("dim");
    expect(screen.getByRole("button", { name: /KA02ZZ0001/ })).not.toHaveClass("dim");
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
    const tip = screen.getByRole("tooltip");
    expect(tip).toHaveTextContent("Honda City");
    expect(tip).toHaveTextContent("Meena");
    expect(tip).toHaveTextContent("Finish by10:00");
    await userEvent.unhover(block);
    expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
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
    expect(screen.getByText(/Part of the schedule for Sun 08-Nov-26 to Sat 14-Nov-26/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Freeze" })).toBeInTheDocument();

    await userEvent.click(later);
    expect(later).toHaveAttribute("aria-pressed", "true");
    expect(first).toHaveAttribute("aria-pressed", "false");
    expect(await screen.findByRole("button", { name: /KA07AA0007/ })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /KA01AB1234/ })).not.toBeInTheDocument();
    expect(screen.getByText("A schedule for this day only.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Unfreeze" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Freeze" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "All jobs 1" })).toBeInTheDocument();
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

  it("runs the scheduler for the period that contains the chosen day", async () => {
    server({ boardReply: () => json(404, err("not_found", "No schedule has been run for that week.")) });
    await openDay("2026-11-11");
    // No schedule covers the day, so the page opens on Run.
    expect(await screen.findByText("Run the scheduler, Palm Grove")).toBeInTheDocument();
    expect(screen.getByText("Sun 08-Nov-26 to Sat 14-Nov-26")).toBeInTheDocument();
    expect(screen.queryByLabelText("Start date")).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Run scheduler" }));
    await waitFor(() => expect(callsTo("/run")).toHaveLength(1));
    expect(JSON.parse(callsTo("/run")[0][1].body)).toEqual({ society_id: SOC, start_date: "2026-11-08", days: 7 });
  });

  it("marks days that need the admin and lists needs scheduling for the chosen day only", async () => {
    server({ needs: [
      job({ id: "j9", crew_id: null, crew_name: null, start_minute: null, start_time: null, reason: "Capacity is short." }),
      job({ id: "j10", date: "2026-11-09", registration: "KA10NN0010", crew_id: null, crew_name: null,
            start_minute: null, start_time: null, reason: "No crew member fits." }),
    ] });
    await openDay();
    const days = await screen.findByRole("group", { name: "Days" });
    expect(await within(days).findByRole("button", { name: /^Mon 09-Nov-26, Draft, needs you/ })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("tab", { name: "Needs scheduling (1)" }));
    expect(await screen.findByText("Capacity is short.")).toBeInTheDocument();
    expect(screen.queryByText("KA10NN0010")).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Mon 09-Nov-26 (1)" }));
    expect(await screen.findByText("KA10NN0010")).toBeInTheDocument();
    expect(screen.queryByText("Capacity is short.")).not.toBeInTheDocument();
    expect(within(days).getByRole("button", { name: /^Mon 09-Nov-26/ })).toHaveAttribute("aria-pressed", "true");
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
    expect(within(chips).getByRole("button", { name: "All jobs 3" })).toHaveAttribute("aria-pressed", "true");
    await userEvent.click(within(chips).getByRole("button", { name: "Could not complete 1" }));
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
    expect(screen.getByRole("button", { name: "All jobs 1" })).toBeInTheDocument();
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

describe("schedule tabs and unavailable crew time", () => {
  const avail = [
    { crew_id: "c1", status: "Partial", windows: [{ start: 480, end: 600 }],
      reason: "Late start from 08:00. Works 08:00-10:00." },
    { crew_id: "c2", status: "Off", windows: [], reason: "Sick on this date." },
  ];

  it("shows the sections as tabs with the chosen day's counts, the board first once a schedule exists", async () => {
    server();
    await openDay();
    const tabs = await screen.findByRole("tablist", { name: "Schedule sections" });
    await waitFor(() => expect(within(tabs).getAllByRole("tab").map((x) => x.textContent)).toEqual([
      "Run", "Board", "Needs scheduling (1)", "Skipped and paused", "Cutoff requests", "Crew queue", "Draft improvements"]));
    expect(screen.getByRole("tab", { name: "Board" })).toHaveAttribute("aria-selected", "true");
    expect(screen.queryByText("Run the scheduler, Palm Grove")).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("tab", { name: "Run" }));
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
    expect(await screen.findByRole("alert")).toHaveTextContent("Ravi cannot take work this day. Sick on this date.");
    expect(callsTo("/move")).toHaveLength(0);
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
    await userEvent.click(await screen.findByRole("button", { name: "Run scheduler" }));
    expect(await screen.findByRole("button", { name: "Running…" })).toBeDisabled();
    expect(screen.getByText(/You can leave this page/)).toBeInTheDocument();
    expect(screen.getAllByRole("status").some((s) => s.textContent?.includes("The scheduler is placing the jobs"))).toBe(true);
    finish(json(200, { schedules: [{ schedule_id: "sch1", society_id: SOC, status: "Draft", placed: 3, unscheduled: 1, late: 0 }] }));
    expect((await screen.findAllByText("3 placed, 1 unscheduled, 0 late.")).length).toBeGreaterThan(0);
  });

  it("does not change the default period unless asked", async () => {
    server();
    await openDay();
    await userEvent.click(await screen.findByRole("tab", { name: "Run" }));
    await choose("Period", "Daily");
    expect(screen.getByText("Period to schedule").nextSibling).toHaveTextContent(/^Sun 08-Nov-26$/);
    expect(fetchMock.mock.calls.some(([p, i]) => String(p).includes("settings/schedule.period") && i?.method === "PUT")).toBe(false);
    await userEvent.click(screen.getByRole("button", { name: "Make daily the default" }));
    await waitFor(() => expect(fetchMock.mock.calls.some(([p, i]) => String(p).includes("settings/schedule.period") && i?.method === "PUT")).toBe(true));
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

  it("lists add-ons waiting for a scheduling period on their day under Needs scheduling", async () => {
    serverWith({ "/v1/admin/scheduling/needs-scheduling": () => json(200, { jobs: [],
      pending_addons: [{ id: "b1", registration: "HR03", date: "2026-11-21", finish_by: "12:00" }] }) });
    await openDay("2026-11-21", "&tab=needs");
    expect(await screen.findByText("Add-ons awaiting a scheduling period")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Manage booking" })).toHaveAttribute("href", "/addons");
  });
});
