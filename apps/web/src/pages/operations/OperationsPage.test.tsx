import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { ToastProvider } from "../../components";
import { withSite } from "../../site/testSite";
import { choose, confirmWith, PortalProviders } from "../../test/portal";
import { currentMonth } from "./monthRange";
import { OperationsPage } from "./OperationsPage";

const fetchMock = vi.fn();
let service: string;
let status: string;
let partial = false;
beforeEach(() => {
  service = "Cleaning-Internal";
  status = "Could not complete";
  partial = false;
  vi.stubGlobal("fetch", fetchMock);
  fetchMock.mockImplementation(async (path: string) => {
    const body = path.includes("/operations/jobs?") ? [{ id: "j1", visit_id: "v1", date: "2026-11-15",
      customer_id: "c1", customer_name: "Asha", society: "Meadows", registration: "HR01ZZ1234", vehicle: "Nexon",
      service, status, note: "Car unavailable", reason: "Other", resolved_at: null, crew_name: "Ravi",
      covered_on: service === "Cleaning-External" ? "2026-11-16" : null,
      ...(partial ? { partial: true, visit_outcome: "Partially Completed", planned_services: ["Cleaning-External", "Cleaning-Internal"],
        delivered_services: ["Cleaning-External"], outcome_summary: "Exterior done. Interior not done today: Other.",
        reported_by: "Ravi", reported_at: "2026-11-15T05:00:00Z" } : {}),
    }] : path.includes("/completion-options") ? { statuses: ["Completed", "Could not complete", "Deferred"],
      reasons: [{ key: "other", label: "Other", defers: false }, { key: "car_locked", label: "Car is locked", defers: true }] }
      : path.includes("/reasons") ? [{ key: "other", label: "Other" }] : {};
    return new Response(JSON.stringify(body));
  });
});
afterEach(() => { vi.unstubAllGlobals(); fetchMock.mockReset(); });
function page(entry = "/operations?queue=missed") {
  render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })}>
    <MemoryRouter initialEntries={[entry]}><ToastProvider><PortalProviders>{withSite(<OperationsPage />)}</PortalProviders></ToastProvider></MemoryRouter>
  </QueryClientProvider>);
}
const resolved = (action: string) => fetchMock.mock.calls.some(([path, options]) =>
  path === "/v1/admin/operations/jobs/j1/resolve" && JSON.parse(options.body).action === action);

it("resolves missed Interior work through the next-day-only action, after asking", async () => {
  page();
  expect(await screen.findByText("Car unavailable")).toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: "Open" }));
  await userEvent.type(screen.getByLabelText("Outcome note"), "Customer confirmed availability");
  await userEvent.click(screen.getByRole("button", { name: "Reschedule for next day" }));
  expect(resolved("Reschedule")).toBe(false);
  await confirmWith("Reschedule");
  await waitFor(() => expect(fetchMock.mock.calls.some(([path, options]) => path === "/v1/admin/operations/jobs/j1/resolve" &&
    JSON.parse(options.body).action === "Reschedule" && JSON.parse(options.body).note === "Customer confirmed availability")).toBe(true));
});

it("keeps Exterior coverage automatic and shows the skip extension", async () => {
  service = "Cleaning-External";
  page();
  await userEvent.click(await screen.findByRole("button", { name: "Open" }));
  expect(screen.getByText(/Covered by the next day/)).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Reschedule for next day" })).not.toBeInTheDocument();
  expect(screen.getByText(/Skipping adds one day/)).toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: "Skip job by operations" }));
  await confirmWith("Skip job");
  await waitFor(() => expect(resolved("Skip")).toBe(true));
});

it("skips the rest of a scheduled visit after asking", async () => {
  status = "Scheduled";
  page();
  await userEvent.click(await screen.findByRole("button", { name: "Open" }));
  await userEvent.click(screen.getByRole("button", { name: "Skip remaining jobs on this visit" }));
  await confirmWith("Skip remaining jobs");
  await waitFor(() => expect(fetchMock.mock.calls.some(([path]) => path === "/v1/admin/operations/visits/v1/skip")).toBe(true));
});

it("filters the server queue by the chosen site, queue and failure reason", async () => {
  page();
  await screen.findByText("Car unavailable");
  await choose("Failure reason", "Other");
  await waitFor(() => expect(fetchMock.mock.calls.some(([path]) => path.includes("society_id=s1") && path.includes("reason_key=other"))).toBe(true));
  await userEvent.click(screen.getByRole("switch", { name: "Only Interior/Spa jobs awaiting an outcome" }));
  await waitFor(() => expect(fetchMock.mock.calls.some(([path]) => path.includes("unresolved=true"))).toBe(true));
  await userEvent.click(screen.getByRole("tab", { name: "Scheduled work" }));
  await waitFor(() => expect(fetchMock.mock.calls.some(([path]) => path.includes("queue=scheduled"))).toBe(true));
});

it("skips selected visits in bulk with a reason, after asking (S-12)", async () => {
  page();
  await screen.findByText("Car unavailable");
  expect(screen.getByRole("button", { name: "Skip selected (0)" })).toBeDisabled();
  await userEvent.click(screen.getByRole("checkbox", { name: /Select HR01ZZ1234/ }));
  await userEvent.click(screen.getByRole("button", { name: "Skip selected (1)" }));
  const submit = screen.getByRole("button", { name: "Skip visits" });
  expect(submit).toBeDisabled();
  await choose("Reason", "Other");
  await userEvent.click(submit);
  await confirmWith("Skip visits");
  await waitFor(() => expect(fetchMock.mock.calls.some(([path, options]) => path === "/v1/admin/operations/bulk-skip" &&
    JSON.parse(options.body).visit_ids[0] === "v1" && JSON.parse(options.body).reason === "Other")).toBe(true));
});

it("sets the status of one scheduled job with a reason and a remark (P1-3)", async () => {
  status = "Scheduled";
  page();
  await userEvent.click(await screen.findByRole("tab", { name: "Scheduled work" }));
  await userEvent.click(await screen.findByRole("button", { name: "Set status for HR01ZZ1234 Cleaning-Internal" }));
  const save = screen.getByRole("button", { name: "Save status" });
  expect(save).toBeDisabled();
  await choose("Completion status", "Could not complete");
  await choose("Reason", "Other");
  expect(save).toBeDisabled();
  await userEvent.type(screen.getByLabelText("Remark"), "Car away");
  await userEvent.click(save);
  await waitFor(() => expect(fetchMock.mock.calls.some(([path, options]) => path === "/v1/admin/operations/jobs/j1/completion" &&
    JSON.parse(options.body).status === "Could not complete" && JSON.parse(options.body).reason_key === "other" &&
    JSON.parse(options.body).note === "Car away")).toBe(true));
});

it("offers only the deferring reasons for Deferred (P1-3)", async () => {
  status = "Scheduled";
  page();
  await userEvent.click(await screen.findByRole("tab", { name: "Scheduled work" }));
  await userEvent.click(await screen.findByRole("button", { name: "Set status for HR01ZZ1234 Cleaning-Internal" }));
  await choose("Completion status", "Deferred");
  await userEvent.click(screen.getByRole("combobox", { name: "Reason" }));
  expect(await screen.findByRole("option", { name: "Car is locked" })).toBeInTheDocument();
  expect(screen.queryByRole("option", { name: "Other" })).not.toBeInTheDocument();
});

it("sets one status for the picked scheduled jobs in bulk (P1-3)", async () => {
  status = "Scheduled";
  page();
  await userEvent.click(await screen.findByRole("tab", { name: "Scheduled work" }));
  expect(screen.getByRole("button", { name: "Set status (0)" })).toBeDisabled();
  await userEvent.click(await screen.findByRole("checkbox", { name: /Select HR01ZZ1234/ }));
  await userEvent.click(screen.getByRole("button", { name: "Set status (1)" }));
  await choose("Completion status", "Completed");
  await userEvent.click(screen.getByRole("button", { name: "Save status" }));
  await waitFor(() => expect(fetchMock.mock.calls.some(([path, options]) => path === "/v1/admin/operations/bulk-completion" &&
    JSON.parse(options.body).job_ids[0] === "j1" && JSON.parse(options.body).status === "Completed")).toBe(true));
});

it("lists a partially completed visit for follow-up with planned and delivered services", async () => {
  partial = true;
  page();
  expect(await screen.findByText("Partially Completed")).toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: "Open" }));
  expect(screen.getByText(/Planned Cleaning-External, Cleaning-Internal\. Delivered Cleaning-External\./)).toBeInTheDocument();
  expect(screen.getByText(/Exterior done\. Interior not done today: Other\./)).toBeInTheDocument();
  expect(screen.getByText("Recorded by")).toBeInTheDocument();
});

it("pages Scheduled work 20 jobs at a time", async () => {
  fetchMock.mockImplementation(async (path: string) => new Response(JSON.stringify(path.includes("/operations/jobs?")
    ? Array.from({ length: 45 }, (_, i) => ({ id: `j${i}`, visit_id: `v${i}`, date: "2026-11-15", customer_id: "c1",
      customer_name: "Asha", society: "Meadows", registration: `HR01AA${String(i).padStart(4, "0")}`, vehicle: "Nexon",
      service: "Cleaning-Internal", status: "Scheduled", note: "", reason: "", resolved_at: null, crew_name: "Ravi" }))
    : path.includes("/reasons") ? [] : {})));
  page();
  await userEvent.click(await screen.findByRole("tab", { name: "Scheduled work" }));
  expect(await screen.findByText(/1-20 of 45/)).toBeInTheDocument();
  expect(screen.getAllByRole("button", { name: "Open" })).toHaveLength(20);
  await userEvent.click(screen.getByRole("button", { name: "Next" }));
  expect(screen.getByText(/21-40 of 45/)).toBeInTheDocument();
});

it("opens every queue on the current month and drops the Reason column from Scheduled work", async () => {
  const { from, to } = currentMonth();
  page();
  await screen.findByText("Car unavailable");
  expect(screen.getByLabelText("From date")).toHaveValue(from);
  expect(screen.getByLabelText("To date")).toHaveValue(to);
  expect(fetchMock.mock.calls.some(([p]) => String(p).includes(`/operations/jobs?queue=missed`) && String(p).includes(`date_from=${from}`) && String(p).includes(`date_to=${to}`))).toBe(true);
  expect(screen.getByRole("columnheader", { name: "Reason" })).toBeInTheDocument();
  await userEvent.click(screen.getByRole("tab", { name: "Scheduled work" }));
  await waitFor(() => expect(screen.queryByRole("columnheader", { name: "Reason" })).not.toBeInTheDocument());
  expect(screen.queryByLabelText("Failure reason")).not.toBeInTheDocument();
  expect(screen.getByLabelText("From date")).toHaveValue(from);
});

it("offers the tabs Scheduled work, Missed jobs, Completed and Cutoff reports, in that order, and opens on Scheduled work", async () => {
  page("/operations");
  await screen.findByRole("tab", { name: "Scheduled work" });
  expect(screen.getAllByRole("tab").map((t) => t.textContent)).toEqual(["Scheduled work", "Missed jobs", "Completed", "Cutoff reports"]);
  expect(screen.getByRole("tab", { name: "Scheduled work" })).toHaveAttribute("aria-selected", "true");
});
