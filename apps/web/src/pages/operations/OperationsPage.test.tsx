import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { ToastProvider } from "../../components";
import { OperationsPage } from "./OperationsPage";

const fetchMock = vi.fn();
let service: string;
beforeEach(() => {
  service = "Cleaning-Internal";
  vi.stubGlobal("fetch", fetchMock);
  fetchMock.mockImplementation(async (path: string) => {
    const body = path.includes("/operations/jobs?") ? [{ id: "j1", visit_id: "v1", date: "2026-11-15",
      customer_id: "c1", customer_name: "Asha", society: "Meadows", registration: "HR01ZZ1234",
      service, status: "Could not complete", note: "Car unavailable", reason: "Other", resolved_at: null,
      covered_on: service === "Cleaning-External" ? "2026-11-16" : null,
    }] : path.includes("/reasons") ? [{ key: "other", label: "Other" }] : path.includes("directory/societies") ? [{ id: "s1", name: "Meadows" }] : {};
    return new Response(JSON.stringify(body));
  });
});
afterEach(() => { vi.unstubAllGlobals(); fetchMock.mockReset(); });
function page() {
  render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><MemoryRouter><ToastProvider><OperationsPage /></ToastProvider></MemoryRouter></QueryClientProvider>);
}
it("resolves missed Interior work through the next-day-only action", async () => {
  page(); await screen.findByText("Other Car unavailable");
  await userEvent.type(screen.getByLabelText("Outcome note"), "Customer confirmed availability");
  await userEvent.click(screen.getByRole("button", { name: "Reschedule for next day" }));
  await waitFor(() => expect(fetchMock.mock.calls.some(([path, options]) => path === "/v1/admin/operations/jobs/j1/resolve" &&
    JSON.parse(options.body).action === "Reschedule" && JSON.parse(options.body).note === "Customer confirmed availability")).toBe(true));
});
it("keeps Exterior coverage automatic and shows the skip extension", async () => {
  service = "Cleaning-External"; page();
  expect(await screen.findByText(/Covered by the next day/)).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Reschedule for next day" })).not.toBeInTheDocument();
  expect(screen.getByText(/Skipping adds one day/)).toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: "Skip job by operations" }));
  await waitFor(() => expect(fetchMock.mock.calls.some(([path, options]) => path.endsWith("/j1/resolve") && JSON.parse(options.body).action === "Skip")).toBe(true));
});
it("filters the server queue by society and failure reason", async () => {
  page(); await screen.findByText("Other Car unavailable");
  await userEvent.selectOptions(screen.getByLabelText("Society"), "s1");
  await userEvent.selectOptions(screen.getByLabelText("Failure reason"), "other");
  await waitFor(() => expect(fetchMock.mock.calls.some(([path]) => path.includes("society_id=s1") && path.includes("reason_key=other"))).toBe(true));
});
