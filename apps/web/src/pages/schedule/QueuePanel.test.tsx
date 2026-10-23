import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ToastProvider } from "../../components";
import { PortalProviders } from "../../test/portal";
import { QueuePanel, queueOf } from "./QueuePanel";
import type { AdminJob, SchedulingCrew } from "./api";

const fetchMock = vi.fn();
beforeEach(() => vi.stubGlobal("fetch", fetchMock));
afterEach(() => { fetchMock.mockReset(); vi.unstubAllGlobals(); });

const crew: SchedulingCrew[] = [{ id: "c1", name: "Asha", role: "Member", start_minute: 480, end_minute: 720 }];

function job(id: string, registration: string, sequence: number, over: Partial<AdminJob> = {}): AdminJob {
  return {
    id, visit_id: "v" + id, schedule_id: "s", schedule_status: "Frozen", date: "2026-11-08", vehicle_id: "x",
    registration, vehicle: "Honda", customer_name: "Meena", service: "Cleaning-External", status: "Scheduled",
    duration_minutes: 20, crew_id: "c1", crew_name: "Asha", start_minute: 540 + sequence, start_time: "09:00",
    end_time: "09:20", finish_by: null, late: false, manual: false, reason: "", sequence, queue_unlocked: false, ...over,
  };
}
const jobs = [job("j2", "KA02", 2), job("j1", "KA01", 1), job("j3", "KA03", 3)];

function mount(refresh = vi.fn()) {
  fetchMock.mockImplementation(async () => new Response(JSON.stringify({ message: "ok", ordered_job_ids: [] }), { status: 200 }));
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  render(
    <QueryClientProvider client={qc}><MemoryRouter><ToastProvider><PortalProviders>
      <QueuePanel crew={crew} jobs={jobs} date="2026-11-08" refresh={refresh} />
    </PortalProviders></ToastProvider></MemoryRouter></QueryClientProvider>,
  );
  return refresh;
}

describe("the crew queue (S-13, C-04, B-06)", () => {
  it("lists each crew member's day in sequence order with locks", () => {
    expect(queueOf(jobs, "c1").map((j) => j.id)).toEqual(["j1", "j2", "j3"]);
    mount();
    const items = screen.getAllByRole("listitem");
    expect(items).toHaveLength(3);
    expect(items[0]).toHaveTextContent("KA01");
    expect(items[1]).toHaveTextContent("Locked");
    expect(items[0]).not.toHaveTextContent("Locked");
    expect(screen.getByRole("button", { name: "Move KA01 up" })).toBeDisabled();
  });

  it("needs a reason to move a job, then sends the new order and says it is audited", async () => {
    const refresh = mount();
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "Move KA02 up" }));
    const save = screen.getByRole("button", { name: "Save new order" });
    expect(save).toBeDisabled();
    await user.type(screen.getByLabelText("Reason"), "  ");
    expect(save).toBeDisabled();
    await user.type(screen.getByLabelText("Reason"), "Customer is waiting");
    await user.click(save);
    await waitFor(() => expect(fetchMock).toHaveBeenCalled());
    const [path, init] = fetchMock.mock.calls[0];
    expect(path).toBe("/v1/admin/scheduling/queue/reorder");
    expect(JSON.parse(init.body)).toEqual({
      crew_id: "c1", date: "2026-11-08", ordered_job_ids: ["j2", "j1", "j3"], reason: "Customer is waiting",
    });
    expect(await screen.findByText(/audit log and Asha was told/)).toBeInTheDocument();
    expect(refresh).toHaveBeenCalled();
  });

  it("unlocks a locked job only with a reason", async () => {
    mount();
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "Unlock KA03" }));
    const submit = screen.getByRole("button", { name: "Unlock job" });
    expect(submit).toBeDisabled();
    await user.type(screen.getByLabelText("Reason"), "Owner asked");
    await user.click(submit);
    await waitFor(() => expect(fetchMock).toHaveBeenCalled());
    const [path, init] = fetchMock.mock.calls[0];
    expect(path).toBe("/v1/admin/scheduling/jobs/j3/unlock");
    expect(JSON.parse(init.body)).toEqual({ reason: "Owner asked" });
    expect(await screen.findByText(/KA03 unlocked. The change is in the audit log/)).toBeInTheDocument();
  });
});
