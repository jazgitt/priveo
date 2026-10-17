import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { ToastProvider } from "../../components";
import { withSite } from "../../site/testSite";
import { choose, confirmWith, PortalProviders } from "../../test/portal";
import { OperationsPage } from "./OperationsPage";

const fetchMock = vi.fn();
let service: string;
let status: string;
beforeEach(() => {
  service = "Cleaning-Internal";
  status = "Could not complete";
  vi.stubGlobal("fetch", fetchMock);
  fetchMock.mockImplementation(async (path: string) => {
    const body = path.includes("/operations/jobs?") ? [{ id: "j1", visit_id: "v1", date: "2026-11-15",
      customer_id: "c1", customer_name: "Asha", society: "Meadows", registration: "HR01ZZ1234", vehicle: "Nexon",
      service, status, note: "Car unavailable", reason: "Other", resolved_at: null, crew_name: "Ravi",
      covered_on: service === "Cleaning-External" ? "2026-11-16" : null,
    }] : path.includes("/reasons") ? [{ key: "other", label: "Other" }] : {};
    return new Response(JSON.stringify(body));
  });
});
afterEach(() => { vi.unstubAllGlobals(); fetchMock.mockReset(); });
function page() {
  render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })}>
    <MemoryRouter><ToastProvider><PortalProviders>{withSite(<OperationsPage />)}</PortalProviders></ToastProvider></MemoryRouter>
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
  await userEvent.click(screen.getByRole("tab", { name: "Resolution history" }));
  await waitFor(() => expect(fetchMock.mock.calls.some(([path]) => path.includes("queue=history"))).toBe(true));
});
