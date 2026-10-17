import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { withSite } from "../../site/testSite";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { AddonsPage } from "./AddonsPage";

const fetchMock = vi.fn();
beforeEach(() => {
  vi.stubGlobal("fetch", fetchMock);
  fetchMock.mockImplementation(async (path: string, options?: RequestInit) => {
    const body = path.startsWith("/v1/admin/addons?") ? [{
      id: "spa1", service: "Deep Spa", customer_name: "Asha Rao", vehicle: "HR01ZZ1234",
      society: "Meadows", date: "2026-11-15", finish_by: "12:00", status: "Scheduled",
      payment_id: "p1", payment_status: "Due", price_rupees: 1500, standalone: false,
      crew_name: "Ravi", start_time: "09:00", change_requested: true,
      requested_date: "2026-11-16", requested_finish_by: "13:00",
    }] : path.includes("directory/societies") ? [{ id: "s1", name: "Meadows" }] : [];
    if (options?.method === "PATCH") return new Response(JSON.stringify({ saved: true }));
    return new Response(JSON.stringify(body));
  });
});
afterEach(() => { vi.unstubAllGlobals(); fetchMock.mockReset(); });
function page() {
  render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
    <MemoryRouter>{withSite(<AddonsPage />)}</MemoryRouter>
  </QueryClientProvider>);
}
it("shows the real assignment and unpaid payment, and resolves a pending change", async () => {
  page();
  expect(await screen.findByText("Ravi at 09:00")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Open payment" })).toHaveAttribute("href", "/payments?payment=p1");
  await userEvent.click(screen.getByRole("button", { name: "Reject requested change" }));
  await waitFor(() => expect(fetchMock.mock.calls.some(([path, options]) =>
    path === "/v1/admin/addons/spa1" && options?.method === "PATCH" &&
    JSON.parse(options.body).reject_change === true)).toBe(true));
});
it("filters by the chosen site and cancels only the selected booking", async () => {
  page(); await screen.findByText("Ravi at 09:00");
  await waitFor(() => expect(fetchMock.mock.calls.some(([path]) => path.includes("society_id=s1"))).toBe(true));
  await userEvent.click(screen.getByRole("button", { name: "Cancel booking" }));
  await waitFor(() => expect(fetchMock.mock.calls.some(([path, options]) =>
    path === "/v1/admin/addons/spa1" && options?.method === "PATCH" &&
    JSON.parse(options.body).status === "Cancelled")).toBe(true));
});
