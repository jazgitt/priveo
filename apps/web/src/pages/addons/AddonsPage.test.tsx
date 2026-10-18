import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { ToastProvider } from "../../components";
import { withSite } from "../../site/testSite";
import { choose, confirmWith, PortalProviders } from "../../test/portal";
import { AddonsPage } from "./AddonsPage";

const fetchMock = vi.fn();
const booking = {
  id: "spa1", service: "Deep Spa", customer_name: "Asha Rao", vehicle: "HR01ZZ1234",
  society: "Meadows", date: "2026-11-15", finish_by: "12:00", status: "Scheduled",
  payment_id: "p1", payment_status: "Due", price_rupees: 1500, standalone: false,
  contact_mobile: "", notes: "", crew_name: "Ravi", start_time: "09:00", change_requested: true,
  requested_date: "2026-11-16", requested_finish_by: "13:00",
};
const asha = { id: "c1", first_name: "Asha", last_name: "Rao", email: "a@x.com", mobile: "9", flat: "1",
  email_verified: true, password_set: true, onboarding_confirmed: true, vehicles: [
    { id: "v1", society: "Meadows", registration: "HR01", make: "Tata", model: "Nexon", variant: "", category: "", parking_basement: "B1", parking_number: "1", photo_url: null, payments: [], subscription: null },
    { id: "v2", society: "Meadows", registration: "HR02", make: "Tata", model: "Nexon", variant: "", category: "", parking_basement: "B1", parking_number: "2", photo_url: null, payments: [],
      subscription: { id: "s2", status: "Inactive", plan_id: "p", plan_name: "", price_rupees: 0, cutoff_time: "", interior_day: null, first_service_date: null, pending_plan_id: null, pending_from: null } }] };

beforeEach(() => {
  vi.stubGlobal("fetch", fetchMock);
  fetchMock.mockImplementation(async (path: string, options?: RequestInit) => {
    if (options?.method === "PATCH" || options?.method === "POST") return new Response(JSON.stringify({ saved: true }));
    const body = path.startsWith("/v1/admin/addons?") ? [booking]
      : path.startsWith("/v1/admin/customers?") ? [{ id: "c1", name: "Asha Rao", email: "a@x.com", mobile: "9", vehicles: [] }]
      : path === "/v1/admin/customers/c1" ? asha : [];
    return new Response(JSON.stringify(body));
  });
});
afterEach(() => { vi.unstubAllGlobals(); fetchMock.mockReset(); });

function page() {
  render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })}>
    <MemoryRouter><ToastProvider><PortalProviders>{withSite(<AddonsPage />)}</PortalProviders></ToastProvider></MemoryRouter>
  </QueryClientProvider>);
}
const patched = (key: string) => fetchMock.mock.calls.some(([path, o]) =>
  path === "/v1/admin/addons/spa1" && o?.method === "PATCH" && key in JSON.parse(o.body));

it("lists bookings with the real assignment and payment, and marks a requested change", async () => {
  page();
  expect(await screen.findByText("Ravi at 09:00")).toBeInTheDocument();
  expect(screen.getByText("Change requested")).toBeInTheDocument();
  expect(screen.getByText("₹1,500")).toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: "Open" }));
  expect(within(screen.getByRole("dialog")).getByRole("link", { name: "Open payment" })).toHaveAttribute("href", "/payments?payment=p1");
});

it("applies or rejects a requested change after asking", async () => {
  page();
  await userEvent.click(await screen.findByRole("button", { name: "Open" }));
  await userEvent.click(screen.getByRole("button", { name: "Reject requested change" }));
  expect(patched("reject_change")).toBe(false);
  await confirmWith("Reject requested change");
  await waitFor(() => expect(patched("reject_change")).toBe(true));
  await userEvent.click(screen.getByRole("button", { name: "Apply requested change" }));
  await confirmWith("Apply requested change");
  await waitFor(() => expect(patched("resolve_change")).toBe(true));
});

it("saves a new date and cancels only the chosen booking after asking", async () => {
  page();
  await userEvent.click(await screen.findByRole("button", { name: "Open" }));
  const dialog = screen.getByRole("dialog");
  fireEvent.change(within(dialog).getByLabelText("Service date"), { target: { value: "2026-11-22" } });
  await userEvent.click(within(dialog).getByRole("button", { name: "Save date and time" }));
  await waitFor(() => expect(fetchMock.mock.calls.some(([p, o]) => p === "/v1/admin/addons/spa1" && o?.method === "PATCH"
    && JSON.stringify(JSON.parse(o.body)) === JSON.stringify({ date: "2026-11-22", finish_by: "12:00" }))).toBe(true));
  await userEvent.click(within(dialog).getByRole("button", { name: "Cancel booking" }));
  await confirmWith("Cancel booking");
  await waitFor(() => expect(fetchMock.mock.calls.some(([p, o]) => p === "/v1/admin/addons/spa1" && o?.method === "PATCH"
    && JSON.parse(o.body).status === "Cancelled")).toBe(true));
});

it("sends the site and the filters to the API", async () => {
  page();
  await screen.findByText("Ravi at 09:00");
  await choose("Status filter", "Scheduled");
  fireEvent.change(screen.getByLabelText("From date"), { target: { value: "2026-10-19" } });
  fireEvent.change(screen.getByLabelText("To date"), { target: { value: "2026-10-21" } });
  await choose("Add-on filter", "Deep Spa");
  await waitFor(() => expect(fetchMock.mock.calls.some(([p]) =>
    String(p).includes("status=Scheduled&society_id=s1&date_from=2026-10-19&date_to=2026-10-21&service=Deep+Spa"))).toBe(true));
});

it("requests an add-on for a standalone or Active vehicle found by search", async () => {
  page();
  await userEvent.click(await screen.findByRole("button", { name: "Request add-on" }));
  const dialog = screen.getByRole("dialog");
  await userEvent.type(within(dialog).getByRole("combobox", { name: "Customer" }), "Asha");
  await userEvent.click(await within(dialog).findByRole("option", { name: /Asha Rao/ }));
  await userEvent.click(within(dialog).getByRole("combobox", { name: "Vehicle" }));
  expect(await screen.findByRole("option", { name: /HR01/ })).toBeInTheDocument();
  expect(screen.queryByRole("option", { name: /HR02/ })).not.toBeInTheDocument();
  await userEvent.click(screen.getByRole("option", { name: /HR01/ }));
  fireEvent.change(within(dialog).getByLabelText("Proposed date"), { target: { value: "2026-10-20" } });
  await choose("Finish by", "13:00");
  await userEvent.click(within(dialog).getByRole("button", { name: "Request add-on" }));
  await waitFor(() => expect(fetchMock.mock.calls.some(([p, o]) => p === "/v1/admin/addons" && o?.method === "POST"
    && JSON.stringify(JSON.parse(o.body)) === JSON.stringify({ vehicle_id: "v1", service: "Deep Spa", date: "2026-10-20", finish_by: "13:00" }))).toBe(true));
});

it("lets the admin choose which add-on to request when the catalogue has several", async () => {
  const base = fetchMock.getMockImplementation()!;
  fetchMock.mockImplementation(async (path: string, options?: RequestInit) =>
    path.endsWith("/directory/addons") && options?.method !== "POST"
      ? new Response(JSON.stringify([
        { id: "a1", code: "ADN-0001", name: "Deep Spa", service: "Deep Spa", active: true },
        { id: "a2", code: "ADN-0002", name: "Interior shine", service: "Cleaning-Internal", active: true },
        { id: "a3", code: "ADN-0003", name: "Retired", service: "Deep Spa", active: false }]))
      : base(path, options));
  page();
  await userEvent.click(await screen.findByRole("button", { name: "Request add-on" }));
  const dialog = screen.getByRole("dialog");
  await within(dialog).findByRole("combobox", { name: "Add-on" });
  await choose("Add-on", "Interior shine");
  await userEvent.type(within(dialog).getByRole("combobox", { name: "Customer" }), "Asha");
  await userEvent.click(await within(dialog).findByRole("option", { name: /Asha Rao/ }));
  await userEvent.click(within(dialog).getByRole("combobox", { name: "Vehicle" }));
  await userEvent.click(await screen.findByRole("option", { name: /HR01/ }));
  fireEvent.change(within(dialog).getByLabelText("Proposed date"), { target: { value: "2026-10-20" } });
  await userEvent.click(within(dialog).getByRole("button", { name: "Request add-on" }));
  await waitFor(() => expect(fetchMock.mock.calls.some(([p, o]) => p === "/v1/admin/addons" && o?.method === "POST"
    && JSON.stringify(JSON.parse(o.body)) === JSON.stringify({
      vehicle_id: "v1", service: "Cleaning-Internal", addon: "ADN-0002", date: "2026-10-20", finish_by: "12:00" }))).toBe(true));
});
