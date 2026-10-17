import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { ToastProvider } from "../../components";
import { choose, confirmWith, PortalProviders } from "../../test/portal";
import { CustomerDetailPage, CustomersPage } from "./CustomersPage";
import type { Vehicle } from "./api";

const fetchMock = vi.fn();
const society = { id: "s1", name: "DLF Meadows", active: true, parking_basements: ["B1", "B2"] };
const plan = { id: "p1", name: "Premium", active: true, monthly_price_rupees: 999, list_price_rupees: 1499, includes_interior: true, inclusions: ["Daily exterior", "Weekly interior"], badge: "Founding member" };
const catalogue = { id: "cat1", make: "Tata", model: "Nexon", variant: "Pure", category: "Compact SUV", active: true };
const customer = { id: "c1", first_name: "Asha", last_name: "Rao", email: "asha@example.com", mobile: "9876543210", flat: "A-12", email_verified: false, password_set: false, onboarding_confirmed: false, vehicles: [] };
const car = (sub: Partial<NonNullable<Vehicle["subscription"]>> = {}): Vehicle => ({
  id: "v1", society_id: "s1", society: "DLF Meadows", registration: "HR01ZZ1234",
  make: "Tata", model: "Nexon", variant: "Pure", category: "Compact SUV",
  parking_basement: "B1", parking_number: "17", photo_url: null, rc_url: null,
  rc_verified: false, payments: [{ id: "pay1", status: "Due", amount_rupees: 999, due_date: "2026-11-01" }],
  subscription: { id: "sub1", status: "Active", plan_id: "p1", plan_name: "Premium", price_rupees: 999,
    cutoff_time: "09:00", interior_day: "Monday", first_service_date: "2026-10-01", pending_plan_id: null,
    pending_from: null, ...sub },
});
let created: Record<string, unknown> | null;
const reply = (body: unknown, status = 200) => new Response(status === 204 ? null : JSON.stringify(body), { status });
const sentTo = (path: string, method: string) => fetchMock.mock.calls.filter(([p, o]) => p === path && (o?.method ?? "GET") === method);
const bodyOf = (path: string, method: string) => JSON.parse(sentTo(path, method).at(-1)![1].body as string);

beforeEach(() => {
  created = null;
  fetchMock.mockImplementation(async (path: string, options?: RequestInit) => {
    const method = options?.method ?? "GET";
    if (path === "/media/file") return reply(null, 204);
    if (path.endsWith("/customer-uploads") && method === "POST") return reply({ id: "u1", upload_url: "/media/file", method: "PUT", headers: {} }, 201);
    if (path.endsWith("/u1/confirm")) return reply({ id: "u1", url: "/photo.jpg" });
    if (path.includes("/directory/societies")) return reply([society]);
    if (path.includes("/directory/plans")) return reply([plan]);
    if (path.includes("/directory/vehicle-catalogue")) return reply([catalogue]);
    if (path.endsWith("/notification-preferences") && method === "GET") return reply({ items: [] });
    if (path.endsWith("/sessions")) return reply([]);
    if (path.endsWith("/changes")) return reply({ skips: [], pauses: [] });
    if (path === "/v1/admin/customers" && method === "POST") { created = JSON.parse(options!.body as string); return reply({ id: "c1", welcome_sent: true }, 201); }
    if (path === "/v1/admin/customers/c1" && method === "GET") return reply(customer);
    if (path.startsWith("/v1/admin/customers?")) return reply([{ id: "c1", name: "Asha Rao", email: customer.email, mobile: customer.mobile, flat: "A-12", email_verified: false, password_set: false, onboarding_confirmed: false, vehicles: [{ id: "v1", registration: "HR01ZZ1234", status: "Activating" }] }]);
    return reply({ saved: true });
  });
  vi.stubGlobal("fetch", fetchMock);
});
afterEach(() => { vi.unstubAllGlobals(); fetchMock.mockReset(); });

function page(path = "/customers") {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  render(<QueryClientProvider client={client}><MemoryRouter initialEntries={[path]}><ToastProvider><PortalProviders><Routes>
    <Route path="/customers" element={<CustomersPage />} /><Route path="/customers/:id" element={<CustomerDetailPage />} />
  </Routes></PortalProviders></ToastProvider></MemoryRouter></QueryClientProvider>);
}
/** The detail page of a customer with the given vehicles. */
function detail(vehicles: Vehicle[], extra: (path: string, o?: RequestInit) => Response | undefined = () => undefined) {
  const original = fetchMock.getMockImplementation()!;
  fetchMock.mockImplementation(async (path: string, o?: RequestInit) =>
    extra(path, o) ?? (path === "/v1/admin/customers/c1" && (o?.method ?? "GET") === "GET" ? reply({ ...customer, vehicles }) : original(path, o)));
  page("/customers/c1");
}

it("lists vehicles and sign-in state, pages the search and resets the offset when it changes", async () => {
  const original = fetchMock.getMockImplementation()!;
  fetchMock.mockImplementation(async (path: string, options?: RequestInit) => {
    if (path.startsWith("/v1/admin/customers?")) {
      const query = new URL(path, "https://test").searchParams;
      return reply(query.get("offset") === "50" ? [{ id: "second", name: "Second page", email: "second@example.com", mobile: "1", vehicles: [] }]
        : Array.from({ length: 50 }, (_, i) => ({ id: `row${i}`, name: `First ${i}`, email: "first@example.com", mobile: "1",
          email_verified: true, password_set: true, onboarding_confirmed: i === 0, vehicles: [{ id: `v${i}`, registration: `HR01AA${i}`, status: "Active" }] })));
    }
    return original(path, options);
  });
  page();
  const first = (await screen.findByRole("link", { name: "First 0" })).closest("tr")!;
  expect(within(first).getByText("HR01AA0")).toBeInTheDocument();
  expect(within(first).getByText("Active")).toBeInTheDocument();
  expect(within(first).getByText("Confirmed")).toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: "Next" }));
  expect(await screen.findByRole("link", { name: "Second page" })).toBeInTheDocument();
  await userEvent.type(screen.getByLabelText("Search by name, mobile, registration or society"), "new");
  await waitFor(() => expect(fetchMock.mock.calls.some(c => String(c[0]).includes("q=new&limit=50&offset=0"))).toBe(true));
});

it("waits for typing to stop before searching", async () => {
  page();
  await screen.findByRole("link", { name: "Asha Rao" });
  await userEvent.type(screen.getByLabelText("Search by name, mobile, registration or society"), "Asha Rao");
  await waitFor(() => expect(fetchMock.mock.calls.some(c => String(c[0]).includes("q=Asha%20Rao"))).toBe(true));
  expect(fetchMock.mock.calls.some(c => String(c[0]).includes("q=As&"))).toBe(false);
});

it("says when nothing matches", async () => {
  const original = fetchMock.getMockImplementation()!;
  fetchMock.mockImplementation(async (path: string, o?: RequestInit) => (path.startsWith("/v1/admin/customers?q=zz") ? reply([]) : original(path, o)));
  page();
  await userEvent.type(screen.getByLabelText("Search by name, mobile, registration or society"), "zz");
  expect(await screen.findByText("No customers found")).toBeInTheDocument();
});

it("opens a customer from the row and shows their onboarding state", async () => {
  page();
  await userEvent.click(await screen.findByRole("link", { name: "Asha Rao" }));
  expect(await screen.findByRole("heading", { name: "Asha Rao" })).toBeInTheDocument();
  expect(screen.getByText(/Email not verified/)).toHaveTextContent("Review pending");
  expect(screen.getAllByRole("button", { name: "Add vehicle" }).length).toBeGreaterThan(0);
});

it("shows imported Spa history without inventing completion or a date", async () => {
  const original = fetchMock.getMockImplementation()!;
  fetchMock.mockImplementation(async (path: string, options?: RequestInit) =>
    path === "/v1/admin/customers/c1" ? reply({ ...customer, imported_history: [{
      id: "old1", date: null, service: "Deep Spa", vehicle: "Unmatched vehicle",
      payment_status: "Received", notes: "Date as given: unclear" }] }) : original(path, options));
  page("/customers/c1");
  expect(await screen.findByText(/Date unknown/)).toBeInTheDocument();
  expect(screen.getAllByText(/Completion not recorded/).length).toBeGreaterThan(0);
  expect(screen.getByText("Date as given: unclear")).toBeInTheDocument();
});

it.each([true, false])("creates a customer with subscription=%s and a required photo", async (subscribed) => {
  page(); await userEvent.click(screen.getByRole("button", { name: "Create customer" }));
  for (const [label, value] of [["First name", "Asha"], ["Last name", "Rao"], ["Email", "asha@example.com"], ["Mobile number", "9876543210"]]) await userEvent.type(screen.getByLabelText(label), value);
  await userEvent.click(screen.getByRole("button", { name: "Continue" }));
  await choose("Society", "DLF Meadows"); await userEvent.click(screen.getByRole("button", { name: "Continue" }));
  await choose("Make", "Tata"); await choose("Model", "Nexon"); await choose("Variant", "Pure");
  await userEvent.type(screen.getByLabelText("Registration"), "hr01zz1234");
  expect(screen.getByRole("button", { name: "Continue" })).toBeDisabled();
  await userEvent.upload(screen.getByLabelText("Vehicle photo"), new File(["photo"], "car.jpg", { type: "image/jpeg" }));
  await waitFor(() => expect(screen.getByRole("button", { name: "Continue" })).toBeEnabled());
  await userEvent.click(screen.getByRole("button", { name: "Continue" }));
  await choose("Basement", "B2"); await userEvent.type(screen.getByLabelText("Parking number"), "17");
  await userEvent.click(screen.getByRole("button", { name: "Continue" }));
  if (subscribed) await choose("Plan", /Premium/);
  else await userEvent.click(screen.getByRole("switch", { name: "Create a subscription" }));
  await userEvent.click(screen.getByRole("button", { name: "Continue" }));
  if (subscribed) await choose("Interior care day", "Monday");
  await userEvent.click(screen.getByRole("button", { name: "Continue" }));
  if (subscribed) await choose("First payment status", "Received");
  await userEvent.click(screen.getByRole("button", { name: "Create" }));
  await waitFor(() => expect(created).not.toBeNull());
  expect(created).toMatchObject({ email: "asha@example.com", vehicle: { photo_upload_id: "u1", registration: "HR01ZZ1234", society_id: "s1", ...(subscribed ? { first_payment_status: "Received", interior_day: "Monday" } : { plan_id: null, cutoff_time: null, interior_day: null }) } });
  expect(await screen.findByRole("heading", { name: "Asha Rao" })).toBeInTheDocument();
}, 30000);

it("shows prices with the rupee sign and the subscription in a grid", async () => {
  detail([car()]);
  expect(await screen.findByText(/₹999\/month/)).toBeInTheDocument();
  expect(screen.getByText("₹999")).toBeInTheDocument();
  expect(document.body.textContent).not.toMatch(/Â|â‚¹/);
});

it("changes to an exterior-only plan without submitting the old interior day", async () => {
  const original = fetchMock.getMockImplementation()!;
  fetchMock.mockImplementation(async (path: string, options?: RequestInit) =>
    path.includes("/directory/plans") ? reply([plan, { ...plan, id: "p2", name: "Exterior", includes_interior: false }]) : original(path, options));
  detail([car()]);
  await userEvent.click(await screen.findByRole("button", { name: "Schedule settings" }));
  await choose("Plan at next renewal", /Exterior/);
  expect(screen.queryByRole("combobox", { name: "Interior care day" })).not.toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: "Save settings" }));
  await waitFor(() => expect(bodyOf("/v1/admin/subscriptions/sub1", "PATCH")).toEqual({ plan_id: "p2", cutoff_time: "09:00" }));
});

it("offers only the valid status change and asks for the date and the reason", async () => {
  detail([car({ status: "Activating", first_service_date: null })]);
  expect(await screen.findByRole("button", { name: "Activate" })).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Reactivate" })).not.toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: "Activate" }));
  const dialog = screen.getByRole("dialog");
  expect(within(dialog).getByRole("button", { name: "Activate" })).toBeDisabled();
  fireEvent.change(within(dialog).getByLabelText("First service date"), { target: { value: "2026-11-02" } });
  await userEvent.click(within(dialog).getByRole("button", { name: "Activate" }));
  await waitFor(() => expect(bodyOf("/v1/admin/subscriptions/sub1/status", "PUT")).toEqual({ status: "Active", reason: "", first_service_date: "2026-11-02" }));

  await userEvent.click(await screen.findByRole("button", { name: "Make inactive" }));
  const inactive = screen.getByRole("dialog");
  expect(within(inactive).getByRole("button", { name: "Make inactive" })).toBeDisabled();
  await userEvent.type(within(inactive).getByLabelText("Reason"), "Moved out");
  await userEvent.click(within(inactive).getByRole("button", { name: "Make inactive" }));
  await waitFor(() => expect(bodyOf("/v1/admin/subscriptions/sub1/status", "PUT")).toEqual({ status: "Inactive", reason: "Moved out" }));
});

it("reactivates an inactive subscription", async () => {
  detail([car({ status: "Inactive" })]);
  await userEvent.click(await screen.findByRole("button", { name: "Reactivate" }));
  await userEvent.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Reactivate" }));
  await waitFor(() => expect(bodyOf("/v1/admin/subscriptions/sub1/status", "PUT")).toMatchObject({ status: "Activating" }));
});

it("skips and pauses with their own dates, and confirms un-skip and end pause", async () => {
  detail([car()], (path) => (path.endsWith("/v1/admin/vehicles/v1/changes")
    ? reply({ skips: [{ id: "k1", start_date: "2026-11-03" }], pauses: [{ id: "q1", start_date: "2026-11-10", end_date: "2026-11-12" }] }) : undefined));
  await userEvent.click(await screen.findByRole("button", { name: "Skip a date" }));
  fireEvent.change(within(screen.getByRole("dialog")).getByLabelText("Service date"), { target: { value: "2026-11-05" } });
  await userEvent.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Skip date" }));
  await waitFor(() => expect(bodyOf("/v1/admin/vehicles/v1/skips", "POST")).toEqual({ date: "2026-11-05" }));

  await userEvent.click(await screen.findByRole("button", { name: "Pause" }));
  const pause = screen.getByRole("dialog");
  fireEvent.change(within(pause).getByLabelText("First day"), { target: { value: "2026-11-20" } });
  fireEvent.change(within(pause).getByLabelText("Last day"), { target: { value: "2026-11-18" } });
  expect(within(pause).getByText("The pause must end on or after its first day.")).toBeInTheDocument();
  fireEvent.change(within(pause).getByLabelText("Last day"), { target: { value: "2026-11-25" } });
  await userEvent.click(within(pause).getByRole("button", { name: "Pause" }));
  await waitFor(() => expect(bodyOf("/v1/admin/vehicles/v1/pauses", "POST")).toEqual({ from_date: "2026-11-20", to_date: "2026-11-25" }));

  await userEvent.click(await screen.findByRole("button", { name: "Un-skip" }));
  expect(sentTo("/v1/admin/vehicles/v1/skips/k1", "DELETE")).toHaveLength(0);
  await confirmWith("Un-skip");
  await waitFor(() => expect(sentTo("/v1/admin/vehicles/v1/skips/k1", "DELETE")).toHaveLength(1));
  await userEvent.click(screen.getByRole("button", { name: "End pause" }));
  await confirmWith("End pause");
  await waitFor(() => expect(sentTo("/v1/admin/vehicles/v1/pauses/q1", "DELETE")).toHaveLength(1));
});

it("edits car and parking in a dialog", async () => {
  detail([car()]);
  await userEvent.click(await screen.findByRole("button", { name: "Edit car and parking" }));
  const dialog = screen.getByRole("dialog");
  await choose("Basement", "B2");
  await userEvent.clear(within(dialog).getByLabelText("Parking number"));
  await userEvent.type(within(dialog).getByLabelText("Parking number"), "42");
  await userEvent.click(within(dialog).getByRole("button", { name: "Save car details" }));
  await waitFor(() => expect(bodyOf("/v1/admin/vehicles/v1", "PATCH")).toEqual({ registration: "HR01ZZ1234", parking_basement: "B2", parking_number: "42" }));
});

it("edits details, corrects the email, and confirms password, notification and session changes", async () => {
  const original = fetchMock.getMockImplementation()!;
  fetchMock.mockImplementation(async (path: string, o?: RequestInit) => {
    const method = o?.method ?? "GET";
    if (path === "/v1/admin/customers/c1/sessions") return reply([
      { id: "t1", device_name: "Phone", platform: "Android", app_version: "1", last_active: "2026-10-13T10:00:00Z", channel: "mobile" },
      { id: "t2", device_name: "Tablet", platform: "iOS", app_version: "1", last_active: "2026-10-12T10:00:00Z", channel: "mobile" }]);
    if (path === "/v1/admin/customers/c1/notification-preferences" && method === "GET") return reply({ items: [{ event: "payment_due", label: "Payments", enabled: true }] });
    return original(path, o);
  });
  page("/customers/c1");
  await userEvent.click(await screen.findByRole("button", { name: "Edit details" }));
  const edit = screen.getByRole("dialog");
  await userEvent.clear(within(edit).getByLabelText("First name")); await userEvent.type(within(edit).getByLabelText("First name"), "Ash");
  await userEvent.click(within(edit).getByRole("button", { name: "Save customer" }));
  await waitFor(() => expect(bodyOf("/v1/admin/customers/c1", "PATCH")).toEqual({ first_name: "Ash", last_name: "Rao", mobile: "9876543210", flat: "A-12" }));

  await userEvent.click(screen.getByRole("button", { name: "Account actions" }));
  await userEvent.click(await screen.findByRole("menuitem", { name: "Correct email" }));
  const email = await screen.findByRole("dialog");
  await userEvent.clear(within(email).getByLabelText("Correct email")); await userEvent.type(within(email).getByLabelText("Correct email"), "new@example.com");
  await userEvent.click(within(email).getByRole("button", { name: "Correct email" }));
  await waitFor(() => expect(bodyOf("/v1/admin/customers/c1/email", "PATCH")).toEqual({ email: "new@example.com" }));

  await userEvent.click(screen.getByRole("button", { name: "Account actions" }));
  await userEvent.click(await screen.findByRole("menuitem", { name: "Clear password" }));
  expect(sentTo("/v1/admin/customers/c1/reset-password", "POST")).toHaveLength(0);
  await confirmWith("Clear password");
  await waitFor(() => expect(sentTo("/v1/admin/customers/c1/reset-password", "POST")).toHaveLength(1));

  await userEvent.click(screen.getByRole("switch", { name: "Payments" }));
  await waitFor(() => expect(bodyOf("/v1/admin/customers/c1/notification-preferences", "PUT")).toEqual({ items: [{ event: "payment_due", enabled: false }] }));

  await userEvent.click(screen.getAllByRole("button", { name: "Sign out session" })[0]);
  await confirmWith("Sign out session");
  await waitFor(() => expect(sentTo("/v1/admin/customers/c1/sessions/t1/logout", "POST")).toHaveLength(1));
  await userEvent.click(screen.getByRole("button", { name: "Sign out all sessions" }));
  await confirmWith("Sign out all sessions");
  await waitFor(() => expect(sentTo("/v1/admin/customers/c1/sessions/logout", "POST")).toHaveLength(1));
});
