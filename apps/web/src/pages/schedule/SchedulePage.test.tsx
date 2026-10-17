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
      return json(200, { jobs: [job({ id: "j9", crew_id: null, crew_name: null, start_minute: null,
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

/** The page for the week from 08-Nov-26, as a finished run links to it. */
async function openBoard(days = "2026-11-08") {
  wrap(<SchedulePage />, `/schedule?start=2026-11-08&days=${days}`);
}

beforeEach(() => vi.stubGlobal("fetch", fetchMock));
afterEach(() => {
  fetchMock.mockReset();
  vi.unstubAllGlobals();
});

describe("schedule board", () => {
  it("shows crew lanes, job cards, flags and the unscheduled reason", async () => {
    server({ jobs: [
      job(),
      job({ id: "j2", registration: "KA02ZZ0001", crew_id: "c2", start_minute: 600,
            start_time: "10:00", late: true, manual: true, reason: "Misses the cutoff." }),
      job({ id: "j3", registration: "KA03XX0002", crew_id: null, start_minute: null,
            start_time: null, reason: "No crew member is free." }),
    ] });
    await openBoard();
    const lane1 = await screen.findByTestId("lane-c1");
    // Each job shows the service code, the vehicle number and the parking place.
    const card1 = within(lane1).getByRole("button", { name: "EXT,KA01AB1234,B1-24" });
    expect(card1).toHaveTextContent("EXTKA01AB1234B1-24");
    const lane2 = screen.getByTestId("lane-c2");
    const card2 = within(lane2).getByRole("button", { name: /KA02ZZ0001/ });
    expect(card2).toHaveClass("late");
    expect(card2).toHaveClass("manual");
    expect(card2).toHaveAttribute("title", expect.stringContaining("Misses the cutoff."));
    expect(screen.getAllByText("Draft").length).toBeGreaterThan(0);
    expect(screen.getByText("No crew member is free.")).toBeInTheDocument();
    expect(screen.getByText("Unscheduled on this day (1)")).toBeInTheDocument();
  });

  it("moves a job by dropping it on another crew lane", async () => {
    server();
    await openBoard();
    const card = (await screen.findByTestId("lane-c1")).querySelector("[draggable]")!;
    const track = screen.getByTestId("lane-c2").querySelector(".sch-track")!;
    fireEvent.dragStart(card, { dataTransfer: { setData: vi.fn() } });
    // jsdom has no DragEvent, so the point is set on a plain event.
    const dropEvent = createEvent.drop(track);
    Object.defineProperty(dropEvent, "clientX", { value: 880 }); // 520 = 40 min after 08:00, from 05:00 at 4 px a minute
    fireEvent(track, dropEvent);
    await waitFor(() => expect(callsTo("/move")).toHaveLength(1));
    const [path, init] = callsTo("/move")[0];
    expect(path).toBe("/v1/admin/scheduling/jobs/j1/move");
    expect(JSON.parse(init.body)).toEqual({ crew_id: "c2", start_minute: 520 });
  });

  it("moves and takes a job off from its dialog", async () => {
    server();
    await openBoard();
    await userEvent.click(await within(await screen.findByTestId("lane-c1")).findByRole("button"));
    await choose("Crew member", /Ravi/);
    fireEvent.change(screen.getByLabelText("Start time"), { target: { value: "09:40" } });
    await userEvent.click(screen.getByRole("button", { name: "Move here" }));
    await waitFor(() => expect(callsTo("/move")).toHaveLength(1));
    expect(JSON.parse(callsTo("/move")[0][1].body)).toEqual({ crew_id: "c2", start_minute: 580 });
  });

  it("shows a frozen-schedule conflict plainly and offers the code prompt", async () => {
    server({
      moveReply: () => json(409, err("schedule_frozen",
        "This schedule is frozen. Unfreeze it with the code to move work.")),
    });
    await openBoard();
    await userEvent.click(await within(await screen.findByTestId("lane-c1")).findByRole("button"));
    await userEvent.click(screen.getByRole("button", { name: "Move here" }));
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("This schedule is frozen. Unfreeze it with the code to move work.");
    await userEvent.click(within(alert).getByRole("button", { name: "Unfreeze with code" }));
    expect(screen.getByRole("dialog", { name: "Unfreeze with the code" })).toBeInTheDocument();
  });

  it("freezes a draft after a confirmation", async () => {
    server();
    await openBoard();
    await userEvent.click(await screen.findByRole("button", { name: "Freeze" }));
    expect(callsTo("/freeze")).toHaveLength(0);
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
    await openBoard();
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

  it("runs the scheduler with the chosen period and lists needs scheduling", async () => {
    server({ boardReply: () => json(404, err("not_found", "No schedule has been run for that week.")) });
    await openBoard();
    await userEvent.click(screen.getByRole("tab", { name: "Board" }));
    expect(await screen.findByText(/No schedule has been run for this society/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("tab", { name: /^Needs scheduling/ }));
    expect(await screen.findByText("Capacity is short.")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("tab", { name: "Run" }));
    await userEvent.click(screen.getByRole("button", { name: "Run scheduler" }));
    await waitFor(() => expect(callsTo("/run")).toHaveLength(1));
    expect(JSON.parse(callsTo("/run")[0][1].body)).toEqual({
      society_id: SOC, start_date: "2026-11-08", days: 7,
    });
  });
});

describe("board as a gantt chart", () => {
  it("has a time ruler from 05:00 to 22:00 with a tick every 30 minutes, and a row for each crew member", async () => {
    server();
    await openBoard();
    const chart = await screen.findByRole("group", { name: "Day plan" });
    const ruler = chart.querySelector(".sch-g-ruler")!;
    expect(ruler.querySelectorAll("span")).toHaveLength(35); // 05:00, 05:30 ... 22:00
    expect(within(ruler as HTMLElement).getByText("05:00")).toBeInTheDocument();
    expect(within(ruler as HTMLElement).getByText("22:00")).toBeInTheDocument();
    expect(ruler.querySelectorAll("span.half")).toHaveLength(17);
    expect(screen.getByTestId("lane-c1")).toBeInTheDocument();
    expect(screen.getByTestId("lane-c2")).toBeInTheDocument();
    // 09:00 is 240 minutes after 05:00, at 4 px a minute, 80 px wide for 20 minutes.
    const card = within(screen.getByTestId("lane-c1")).getByRole("button");
    expect(card).toHaveStyle({ left: "960px", width: "78px" });
  });
});

describe("job status on the board (ADM-SCH-34)", () => {
  it("fills completed jobs green and missed ones red, counts each status and picks one out", async () => {
    server({ jobs: [
      job({ id: "j1", registration: "KA01AA0001", status: "Completed" }),
      job({ id: "j2", registration: "KA01AA0002", status: "Could not complete", start_minute: 600, start_time: "10:00", end_time: "10:20" }),
      job({ id: "j3", registration: "KA01AA0003", status: "Scheduled", start_minute: 660, start_time: "11:00", end_time: "11:20" }),
    ] });
    await openBoard();
    const lane = await screen.findByTestId("lane-c1");
    const card = (reg: string) => within(lane).getByRole("button", { name: new RegExp(reg) });
    expect(card("KA01AA0001")).toHaveClass("done");
    expect(card("KA01AA0002")).toHaveClass("failed");
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
  it("leaves a skipped job out of the unscheduled list and shows a finished job without move controls", async () => {
    server({ jobs: [
      job({ id: "j1", status: "Completed" }),
      job({ id: "j5", registration: "KA05SK0005", crew_id: null, crew_name: null, start_minute: null,
            start_time: null, status: "Skipped" }),
    ] });
    await openBoard();
    const card = within(await screen.findByTestId("lane-c1")).getByRole("button");
    expect(card).toHaveAttribute("draggable", "false");
    expect(screen.getByText("Unscheduled on this day (0)")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Place KA05SK0005" })).not.toBeInTheDocument();

    await userEvent.click(card);
    const dialog = screen.getByRole("dialog");
    expect(within(dialog).getByText("This job is Completed, so it can no longer be placed or moved.")).toBeInTheDocument();
    expect(within(dialog).queryByLabelText("Start time")).not.toBeInTheDocument();
    await userEvent.click(within(dialog).getByRole("button", { name: "Close" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(callsTo("/move")).toHaveLength(0);
  });

  it("keeps skipped jobs off the board and lists them with why on their own tab (ADM-SCH-36)", async () => {
    server({ jobs: [
      job(),
      job({ id: "j5", registration: "KA05SK0005", crew_id: "c2", status: "Skipped" }),
    ] });
    await openBoard();
    expect(within(await screen.findByTestId("lane-c2")).queryByRole("button")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "All jobs 1" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /^Skipped/ })).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "1 skipped or paused, not shown" }));
    expect(screen.getByRole("tab", { name: "Skipped and paused" })).toHaveAttribute("aria-selected", "true");
    expect(await screen.findByText("Paused by the customer, 08-Nov-26 to 10-Nov-26")).toBeInTheDocument();
    expect(screen.getByText("Skipped by operations")).toBeInTheDocument();
    const [path] = fetchMock.mock.calls.find((c) => String(c[0]).startsWith("/v1/admin/scheduling/skipped?"))!;
    expect(String(path)).toContain("date_from=2026-11-08");
    expect(String(path)).toContain("date_to=2026-11-14");

    await choose("Show", "Paused only");
    expect(screen.queryByText("Skipped by operations")).not.toBeInTheDocument();
    expect(screen.getByText("Paused by the customer, 08-Nov-26 to 10-Nov-26")).toBeInTheDocument();
  });
});

describe("every day of every schedule on the board (ADM-SCH-35)", () => {
  function nextDay() {
    const b = board("Frozen", [job({ id: "j7", date: "2026-11-15", registration: "KA07AA0007", status: "Completed",
                                     schedule_id: "sch2" })]);
    b.schedule = { ...b.schedule, id: "sch2", start_date: "2026-11-15", end_date: "2026-11-15" };
    b.days = [{ ...b.days[0], date: "2026-11-15" }];
    return b;
  }

  it("lists the days of all schedules and shows each chosen day as its own chart", async () => {
    server({ boards: { sch2: nextDay() } });
    await openBoard();
    const days = await screen.findByRole("group", { name: "Days" });
    // Seven days of the weekly draft, then the one-day frozen schedule.
    expect(within(days).getAllByRole("button")).toHaveLength(8);
    const later = within(days).getByRole("button", { name: /15-Nov-26/ });
    expect(later).toHaveAttribute("aria-pressed", "false");
    expect(screen.getAllByRole("group", { name: "Day plan" })).toHaveLength(1);

    await userEvent.click(later);
    expect(later).toHaveAttribute("aria-pressed", "true");
    await waitFor(() => expect(screen.getAllByRole("group", { name: "Day plan" })).toHaveLength(2));
    expect(screen.getByRole("region", { name: /15-Nov-26/ })).toHaveTextContent("KA07AA0007");
    // One count for all chosen days, and a freeze row for each schedule.
    expect(screen.getByRole("button", { name: "All jobs 2" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Freeze" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Unfreeze" })).toBeInTheDocument();

    // Clicking a chosen day takes it off again.
    await userEvent.click(within(days).getByRole("button", { name: /08-Nov-26/ }));
    await waitFor(() => expect(screen.getAllByRole("group", { name: "Day plan" })).toHaveLength(1));
    expect(screen.queryByRole("button", { name: "Freeze" })).not.toBeInTheDocument();
  });
});

describe("schedule tabs and unavailable crew time", () => {
  const avail = [
    { crew_id: "c1", status: "Partial", windows: [{ start: 480, end: 600 }],
      reason: "Late start from 08:00. Works 08:00-10:00." },
    { crew_id: "c2", status: "Off", windows: [], reason: "Sick on this date." },
  ];

  it("shows the sections as tabs, the board first once a schedule exists", async () => {
    server();
    await openBoard();
    const tabs = await screen.findByRole("tablist", { name: "Schedule sections" });
    expect(within(tabs).getAllByRole("tab").map((x) => x.textContent)).toEqual([
      "Run", "Board", "Needs scheduling", "Cutoff requests", "Draft improvements"]);
    expect(await screen.findByRole("tab", { name: "Board" })).toHaveAttribute("aria-selected", "true");
    expect(screen.queryByText("Run the scheduler, Palm Grove")).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("tab", { name: "Run" }));
    expect(screen.getByText("Run the scheduler, Palm Grove")).toBeInTheDocument();
  });

  it("greys out the time a crew member cannot work and explains it on hover", async () => {
    server({ boardReply: () => json(200, board("Draft", [job()], avail)) });
    await openBoard();
    const asha = await screen.findByTestId("lane-c1");
    expect(within(asha).getAllByTestId("grey")).toHaveLength(2); // before 08:00 and after 10:00
    const ravi = screen.getByTestId("lane-c2");
    expect(ravi).toHaveClass("closed");
    expect(within(ravi).getByTestId("grey")).toHaveTextContent("Sick on this date.");
    const tip = within(ravi).getByRole("tooltip");
    expect(tip).toHaveTextContent("Sick on this date.");
    expect(tip).toHaveTextContent("Cannot take work this day.");
    expect(within(asha).getByRole("tooltip")).toHaveTextContent("Booked");
  });

  it("does not move a job onto time the crew member cannot work", async () => {
    server({ boardReply: () => json(200, board("Draft", [job()], avail)) });
    await openBoard();
    const card = (await screen.findByTestId("lane-c1")).querySelector("[draggable]")!;
    const track = screen.getByTestId("lane-c2").querySelector(".sch-track")!;
    fireEvent.dragStart(card, { dataTransfer: { setData: vi.fn() } });
    const dropEvent = createEvent.drop(track);
    Object.defineProperty(dropEvent, "clientX", { value: 880 });
    fireEvent(track, dropEvent);
    expect(await screen.findByRole("alert")).toHaveTextContent("Ravi cannot take work there");
    expect(callsTo("/move")).toHaveLength(0);
  });
});

describe("capacity page", () => {
  it("shows demand against capacity and marks over capacity dates", async () => {
    server();
    wrap(<CapacityPage />);
    expect(await screen.findByText("Over capacity")).toBeInTheDocument();
    expect(screen.getByText("10 h")).toBeInTheDocument();
    expect(screen.getByText("Asha")).toBeInTheDocument();
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
    await openBoard();
    await userEvent.click(await screen.findByRole("button", { name: "Run scheduler" }));
    expect(await screen.findByRole("button", { name: "Running…" })).toBeDisabled();
    expect(screen.getByText(/You can leave this page/)).toBeInTheDocument();
    expect(screen.getAllByRole("status").some((s) => s.textContent?.includes("The scheduler is placing the jobs"))).toBe(true);
    finish(json(200, { schedules: [{ schedule_id: "sch1", society_id: SOC, status: "Draft", placed: 3, unscheduled: 1, late: 0 }] }));
    expect((await screen.findAllByText("3 placed, 1 unscheduled, 0 late.")).length).toBeGreaterThan(0);
  });

  it("does not change the default period unless asked", async () => {
    server();
    await openBoard();
    await userEvent.click(await screen.findByRole("tab", { name: "Run" }));
    await choose("Period", "Daily");
    expect(fetchMock.mock.calls.some(([p, i]) => String(p).includes("settings/schedule.period") && i?.method === "PUT")).toBe(false);
    await userEvent.click(screen.getByRole("button", { name: "Make daily the default" }));
    await waitFor(() => expect(fetchMock.mock.calls.some(([p, i]) => String(p).includes("settings/schedule.period") && i?.method === "PUT")).toBe(true));
  });

  it("confirms before taking a job off its crew member", async () => {
    server();
    await openBoard();
    await userEvent.click(await within(await screen.findByTestId("lane-c1")).findByRole("button"));
    await userEvent.click(screen.getByRole("button", { name: "Take off crew member" }));
    expect(callsTo("/move")).toHaveLength(0);
    await confirmWith("Take off crew member");
    await waitFor(() => expect(callsTo("/move")).toHaveLength(1));
    expect(JSON.parse(callsTo("/move")[0][1].body)).toEqual({ crew_id: null, start_minute: null });
  });

  it("applies or rejects a cutoff request after a confirmation", async () => {
    serverWith({
      "/v1/admin/scheduling/cutoff-requests/r1/handle": () => json(200, {}),
      "/v1/admin/scheduling/cutoff-requests": () => json(200, [{ id: "r1", registration: "HR01", customer_name: "Asha", date: "2026-11-09",
        cutoff_time: "08:00", old_cutoff: "10:00", crew_name: "Raj", start_time: "07:00" }]),
    });
    await openBoard();
    await userEvent.click(await screen.findByRole("tab", { name: "Cutoff requests" }));
    await userEvent.click(await screen.findByRole("button", { name: "Apply and schedule" }));
    await confirmWith("Apply and schedule");
    await waitFor(() => expect(callsTo("/r1/handle")).toHaveLength(1));
    expect(JSON.parse(callsTo("/r1/handle")[0][1].body)).toEqual({ apply: true });
    await userEvent.click(screen.getByRole("button", { name: "Reject" }));
    await confirmWith("Reject");
    await waitFor(() => expect(callsTo("/r1/handle")).toHaveLength(2));
    expect(JSON.parse(callsTo("/r1/handle")[1][1].body)).toEqual({ apply: false });
  });

  it("swaps two jobs and applies the chosen improvements with the preview fingerprint", async () => {
    serverWith({
      "/v1/admin/scheduling/jobs/swap": () => json(200, {}),
      "/v1/admin/scheduling/schedules/sch1/suggestions/apply": () => json(200, {}),
      "/v1/admin/scheduling/schedules/sch1/suggestions": () => json(200, { fingerprint: "version1",
        items: [{ job_id: "j1", crew_id: "c2", start_minute: 425, date: "2026-11-08", service: "Cleaning-External" }] }),
    }, { jobs: [job(), job({ id: "j2", registration: "KA02ZZ0001", crew_id: "c2", crew_name: "Ravi" })] });
    await openBoard();
    await userEvent.click(await screen.findByRole("tab", { name: "Draft improvements" }));
    await choose("First job", /KA01AB1234/);
    await choose("Second job", /KA02ZZ0001/);
    await userEvent.click(screen.getByRole("button", { name: "Swap crew and times" }));
    await confirmWith("Swap crew and times");
    await waitFor(() => expect(callsTo("/jobs/swap")).toHaveLength(1));
    expect(JSON.parse(callsTo("/jobs/swap")[0][1].body)).toEqual({ first_job_id: "j1", second_job_id: "j2" });

    await userEvent.click(screen.getByRole("button", { name: "Preview improvements" }));
    const choice = await screen.findByRole("checkbox", { name: "Apply for KA01AB1234" });
    expect(screen.getByRole("button", { name: "Apply selected improvements" })).toBeDisabled();
    await userEvent.click(choice);
    await userEvent.click(screen.getByRole("button", { name: "Apply selected improvements" }));
    await confirmWith("Apply selected improvements");
    await waitFor(() => expect(callsTo("/suggestions/apply")).toHaveLength(1));
    expect(JSON.parse(callsTo("/suggestions/apply")[0][1].body)).toEqual({ fingerprint: "version1", job_ids: ["j1"] });
  });

  it("disables the draft actions on a frozen schedule", async () => {
    server({ status: "Frozen" });
    await openBoard();
    await userEvent.click(await screen.findByRole("tab", { name: "Draft improvements" }));
    expect(await screen.findByText("Unfreeze this schedule to swap work or apply improvements.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Preview improvements" })).toBeDisabled();
  });

  it("lists add-ons waiting for a scheduling period under Needs scheduling", async () => {
    serverWith({ "/v1/admin/scheduling/needs-scheduling": () => json(200, { jobs: [],
      pending_addons: [{ id: "b1", registration: "HR03", date: "2026-11-21", finish_by: "12:00" }] }) });
    await openBoard();
    await userEvent.click(await screen.findByRole("tab", { name: /^Needs scheduling/ }));
    expect(await screen.findByText("Add-ons awaiting a scheduling period")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Manage booking" })).toHaveAttribute("href", "/addons");
  });
});