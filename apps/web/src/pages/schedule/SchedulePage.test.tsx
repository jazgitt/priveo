import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createEvent, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ToastProvider } from "../../components";
import { CapacityPage } from "../capacity/CapacityPage";
import { SchedulePage } from "./SchedulePage";

const fetchMock = vi.fn();

function json(status: number, body?: unknown) {
  return new Response(body === undefined ? null : JSON.stringify(body), { status });
}
const err = (code: string, message: string) => ({ code, message, fields: {}, request_id: "" });

function wrap(ui: ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}><ToastProvider>{ui}</ToastProvider></QueryClientProvider>,
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
    vehicle_id: "veh1", registration: "KA01AB1234", vehicle: "Honda City", customer_name: "Meena",
    service: "Cleaning-External", status: "Scheduled", duration_minutes: 20, crew_id: "c1",
    crew_name: "Asha", start_minute: 540, start_time: "09:00", end_time: "09:20", finish_by: "10:00",
    late: false, manual: false, reason: "", ...over,
  };
}

function board(status = "Draft", jobs = [job()]) {
  return {
    schedule: {
      id: "sch1", society_id: SOC, society_name: "Palm Grove", start_date: "2026-11-08",
      end_date: "2026-11-14", status, frozen_at: status === "Frozen" ? "2026-11-07T14:00:00Z" : null,
      freeze_deadline: "2026-11-07T14:30:00Z",
    },
    days: [{ date: "2026-11-08", capacity_minutes: 960, demand_minutes: 60, scheduled_minutes: 20,
             over_capacity: false }],
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
}

function server(o: Opts = {}) {
  fetchMock.mockImplementation(async (path: string, init?: RequestInit) => {
    const url = String(path);
    if (url.startsWith("/v1/admin/crew")) return json(200, crew);
    if (url.startsWith("/v1/admin/scheduling/board")) {
      return o.boardReply ? o.boardReply() : json(200, board(o.status ?? "Draft", o.jobs ?? [job()]));
    }
    if (url.startsWith("/v1/admin/scheduling/needs-scheduling")) {
      return json(200, { jobs: [job({ id: "j9", crew_id: null, crew_name: null, start_minute: null,
                                      start_time: null, reason: "Capacity is short." })] });
    }
    if (url.startsWith("/v1/admin/scheduling/capacity")) {
      return json(200, [
        { date: "2026-11-08", capacity_minutes: 480, demand_minutes: 600, scheduled_minutes: 400,
          over_capacity: true },
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

async function openBoard() {
  wrap(<SchedulePage />);
  const select = await screen.findByLabelText("Society");
  await screen.findByRole("option", { name: "Palm Grove" });
  await userEvent.selectOptions(select, SOC);
  fireEvent.change(screen.getByLabelText("Start date"), { target: { value: "2026-11-08" } });
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
    expect(within(lane1).getByText(/KA01AB1234/)).toBeInTheDocument();
    const lane2 = screen.getByTestId("lane-c2");
    expect(within(lane2).getByText(/\(late\)/)).toBeInTheDocument();
    expect(within(lane2).getByText(/\(hand\)/)).toBeInTheDocument();
    expect(screen.getByText("Draft")).toBeInTheDocument();
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
    Object.defineProperty(dropEvent, "clientY", { value: 120 }); // 40 min after 08:00
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
    await userEvent.selectOptions(screen.getByLabelText("Crew member"), "c2");
    await userEvent.clear(screen.getByLabelText("Start time"));
    await userEvent.type(screen.getByLabelText("Start time"), "09:40");
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
    await userEvent.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Freeze" }));
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
    expect(await screen.findByText(/No schedule has been run for this society/)).toBeInTheDocument();
    expect(await screen.findByText("Capacity is short.")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Run scheduler" }));
    await waitFor(() => expect(callsTo("/run")).toHaveLength(1));
    expect(JSON.parse(callsTo("/run")[0][1].body)).toEqual({
      society_id: SOC, start_date: "2026-11-08", days: 7,
    });
  });
});

describe("capacity page", () => {
  it("shows demand against capacity and marks over capacity dates", async () => {
    server();
    wrap(<CapacityPage />);
    await userEvent.selectOptions(await screen.findByLabelText("Society"), SOC);
    expect(await screen.findByText("Over capacity")).toBeInTheDocument();
    expect(screen.getByText("10 h")).toBeInTheDocument();
    expect(screen.getByText("Asha")).toBeInTheDocument();
  });
});
