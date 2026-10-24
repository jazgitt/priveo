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
  parking_basement: "B1", parking_number: "17", photo_url: null,
  payments: [{ id: "pay1", status: "Due", amount_rupees: 999, due_date: "2026-11-01" }],
  subscription: { id: "sub1", status: "Active", plan_id: "p1", plan_name: "Premium", price_rupees: 999,
    cutoff_time: "09:00", interior_day: "Monday", first_service_date: "2026-10-01", pending_plan_id: null,
    pending_from: null, ...sub },
});
const summary = { total: 120, with_subscription: 90, addons_only: 7,
  by_status: { Active: 60, Activating: 20, Inactive: 10, "No subscription": 30 } };
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
    if (path.endsWith("/crew")) return reply([]);
    if (path.endsWith("/plan-history")) return reply({ current_plan: "Plan", current_price_rupees: 999, changes: [] });
    if (path.endsWith("/parking-changes") && method === "GET") return reply({ base: "B2-14", today: "B2-14", changes: [] });
    if (path === "/v1/admin/customers" && method === "POST") { created = JSON.parse(options!.body as string); return reply({ id: "c1", welcome_sent: true }, 201); }
    if (path === "/v1/admin/customers/c1" && method === "GET") return reply(customer);
    if (path.startsWith("/v1/admin/customers/summary")) return reply(summary);
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
  page("/customers/c1?tab=vehicles");
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
  expect(screen.getByText("Personal details")).toBeInTheDocument();
  await userEvent.click(screen.getByRole("tab", { name: /Vehicles/ }));
  expect((await screen.findAllByRole("button", { name: "Add vehicle" })).length).toBeGreaterThan(0);
});

it("shows imported Spa history without inventing completion or a date", async () => {
  const original = fetchMock.getMockImplementation()!;
  fetchMock.mockImplementation(async (path: string, options?: RequestInit) =>
    path === "/v1/admin/customers/c1" ? reply({ ...customer, imported_history: [{
      id: "old1", date: null, service: "Deep Spa", vehicle: "Unmatched vehicle",
      payment_status: "Received", notes: "Date as given: unclear" }] }) : original(path, options));
  page("/customers/c1");
  await userEvent.click(await screen.findByRole("tab", { name: "Service history" }));
  expect(await screen.findByText(/Date unknown/)).toBeInTheDocument();
  expect(screen.getAllByText(/Completion not recorded/).length).toBeGreaterThan(0);
  expect(screen.getByText("Date as given: unclear")).toBeInTheDocument();
});

it.each([true, false])("creates a customer with subscription=%s and a photo", async (subscribed) => {
  page(); await userEvent.click(screen.getByRole("button", { name: "Create customer" }));
  for (const [label, value] of [["First name", "Asha"], ["Last name", "Rao"], ["Email", "asha@example.com"], ["Mobile number", "9876543210"]]) await userEvent.type(screen.getByLabelText(label), value);
  await userEvent.click(screen.getByRole("button", { name: "Continue" }));
  await choose("Society", "DLF Meadows"); await userEvent.click(screen.getByRole("button", { name: "Continue" }));
  await choose("Make", "Tata"); await choose("Model", "Nexon"); await choose("Variant", "Pure");
  await userEvent.type(screen.getByLabelText("Registration"), "hr01zz1234");
  expect(screen.getByRole("button", { name: "Continue" })).toBeEnabled();
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
  await choose("New plan", /Exterior/);
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
  await waitFor(() => expect(bodyOf("/v1/admin/customers/c1", "PATCH")).toEqual({ first_name: "Ash", last_name: "Rao", mobile: "9876543210", flat: "A-12", address_line1: "", address_line2: "" }));

  await userEvent.click(screen.getAllByRole("button", { name: "Update email" })[0]);
  const email = await screen.findByRole("dialog");
  await userEvent.clear(within(email).getByLabelText("New email")); await userEvent.type(within(email).getByLabelText("New email"), "new@example.com");
  await userEvent.click(within(email).getByRole("button", { name: "Update email" }));
  await waitFor(() => expect(bodyOf("/v1/admin/customers/c1/email", "PATCH")).toEqual({ email: "new@example.com" }));

  await userEvent.click(await screen.findByRole("button", { name: "Clear password" }));
  expect(sentTo("/v1/admin/customers/c1/reset-password", "POST")).toHaveLength(0);
  await confirmWith("Clear password");
  await waitFor(() => expect(sentTo("/v1/admin/customers/c1/reset-password", "POST")).toHaveLength(1));

  await userEvent.click(await screen.findByRole("switch", { name: "Payments" }));
  await waitFor(() => expect(bodyOf("/v1/admin/customers/c1/notification-preferences", "PUT")).toEqual({ items: [{ event: "payment_due", enabled: false }] }));

  await userEvent.click(screen.getAllByRole("button", { name: "Sign out session" })[0]);
  await confirmWith("Sign out session");
  await waitFor(() => expect(sentTo("/v1/admin/customers/c1/sessions/t1/logout", "POST")).toHaveLength(1));
  await userEvent.click(screen.getAllByRole("button", { name: "Sign out all sessions" })[0]);
  await confirmWith("Sign out all sessions");
  await waitFor(() => expect(sentTo("/v1/admin/customers/c1/sessions/logout", "POST")).toHaveLength(1));
});

it("shows the summary numbers, filters by status tab and counts the pages", async () => {
  page();
  expect(await screen.findByText("Total customers")).toBeInTheDocument();
  const tiles = screen.getByRole("region", { name: "Customer summary" });
  expect(await within(tiles).findByRole("button", { name: "Total customers: 120" })).toBeInTheDocument();
  expect(within(tiles).getByRole("button", { name: "With a subscription: 90" })).toBeInTheDocument();
  expect(within(tiles).getByRole("button", { name: "Add-ons only: 7" })).toBeInTheDocument();
  expect(await screen.findByText(/1-1 of 120 · Page 1 of 3/)).toBeInTheDocument();
  await userEvent.click(screen.getByRole("tab", { name: /^Active\s*\d/ }));
  await waitFor(() => expect(fetchMock.mock.calls.some((c) => String(c[0]).includes("&status=Active&limit=50&offset=0"))).toBe(true));
  expect(await screen.findByText(/of 60 · Page 1 of 2/)).toBeInTheDocument();
  await userEvent.click(screen.getByRole("tab", { name: /No subscription/ }));
  await waitFor(() => expect(fetchMock.mock.calls.some((c) => String(c[0]).includes("status=No%20subscription"))).toBe(true));
});

it("opens a customer from any cell of the row", async () => {
  page();
  await userEvent.click(await screen.findByText("asha@example.com"));
  expect(await screen.findByRole("heading", { name: "Asha Rao" })).toBeInTheDocument();
});

it("shows account details first, with onboarding wording, and keeps the chosen tab", async () => {
  page("/customers/c1");
  expect(await screen.findByText("First name")).toBeInTheDocument();
  expect(screen.getByText("9876543210")).toBeInTheDocument();
  expect(screen.getByText("App onboarding")).toBeInTheDocument();
  expect(screen.queryByText("App sign-in")).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Account actions" })).not.toBeInTheDocument();
  expect(screen.getByRole("tab", { name: "Account details" })).toHaveAttribute("aria-selected", "true");
  expect(screen.queryByRole("tab", { name: "Account" })).not.toBeInTheDocument();
  await userEvent.click(screen.getByRole("tab", { name: /Vehicles/ }));
  expect(screen.getByRole("tab", { name: /Vehicles/ })).toHaveAttribute("aria-selected", "true");
});

it("cannot deactivate a vehicle while its subscription runs", async () => {
  detail([car({ status: "Active" })]);
  expect(await screen.findByRole("button", { name: "Deactivate" })).toBeDisabled();
});

it("deactivates after confirming, shows deactivated vehicles on request and reactivates one", async () => {
  detail([car({ status: "Inactive" }), { ...car(), id: "v2", registration: "HR02AB0002", active: false }]);
  expect(screen.queryByText("HR02AB0002")).not.toBeInTheDocument();
  await userEvent.click(await screen.findByRole("button", { name: "Deactivate" }));
  expect(sentTo("/v1/admin/vehicles/v1", "PATCH")).toHaveLength(0);
  await confirmWith("Deactivate vehicle");
  await waitFor(() => expect(bodyOf("/v1/admin/vehicles/v1", "PATCH")).toEqual({ active: false }));

  await userEvent.click(screen.getByRole("switch", { name: "Show deactivated vehicles" }));
  await userEvent.click(await screen.findByRole("radio", { name: "HR02AB0002" }));
  expect(screen.getByText("Deactivated")).toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: "Reactivate vehicle" }));
  await waitFor(() => expect(sentTo("/v1/admin/vehicles/v2", "PATCH")).toHaveLength(1));
  expect(bodyOf("/v1/admin/vehicles/v2", "PATCH")).toEqual({ active: true });
});

it("says why a photo is refused instead of sending it", async () => {
  page(); await userEvent.click(screen.getByRole("button", { name: "Create customer" }));
  for (const [label, value] of [["First name", "Asha"], ["Last name", "Rao"], ["Email", "asha@example.com"], ["Mobile number", "9876543210"]]) await userEvent.type(screen.getByLabelText(label), value);
  await userEvent.click(screen.getByRole("button", { name: "Continue" }));
  await choose("Society", "DLF Meadows"); await userEvent.click(screen.getByRole("button", { name: "Continue" }));
  await userEvent.upload(screen.getByLabelText("Vehicle photo"), new File(["x"], "notes.txt", { type: "text/plain" }), { applyAccept: false });
  expect(await screen.findByText("Choose a JPG, PNG, HEIC or WebP photo.")).toBeInTheDocument();
  expect(sentTo("/v1/admin/customer-uploads", "POST")).toHaveLength(0);
});

it("shows no vehicle tiles for a single vehicle", async () => {
  detail([car()]);
  await screen.findByRole("button", { name: "Edit car and parking" });
  expect(screen.queryByRole("radiogroup", { name: "Choose a vehicle" })).not.toBeInTheDocument();
});

it("chooses between several vehicles with tiles, one selected at a time", async () => {
  detail([car(), { ...car(), id: "v2", registration: "HR02AB0002", parking_number: "88", subscription: null, payments: [] }]);
  const group = await screen.findByRole("radiogroup", { name: "Choose a vehicle" });
  const first = within(group).getByRole("radio", { name: "HR01ZZ1234" });
  const second = within(group).getByRole("radio", { name: "HR02AB0002" });
  expect(first).toHaveAttribute("aria-checked", "true");
  expect(second).toHaveAttribute("aria-checked", "false");
  expect(screen.getByText("B1-17")).toBeInTheDocument();
  await userEvent.click(second);
  expect(second).toHaveAttribute("aria-checked", "true");
  expect(first).toHaveAttribute("aria-checked", "false");
  expect(screen.getByText("B1-88")).toBeInTheDocument();
  expect(screen.queryByText("B1-17")).not.toBeInTheDocument();
});

it("has no RC document anywhere on the vehicle", async () => {
  detail([car()]);
  await userEvent.click(await screen.findByRole("button", { name: "Edit car and parking" }));
  expect(screen.queryByText(/RC/)).not.toBeInTheDocument();
  expect(document.body.textContent).not.toMatch(/RC document/);
  expect(screen.getByLabelText(/Vehicle photo/)).toBeInTheDocument();
});

it("creates a customer without a vehicle photo, sending no photo", async () => {
  page(); await userEvent.click(screen.getByRole("button", { name: "Create customer" }));
  for (const [label, value] of [["First name", "Asha"], ["Last name", "Rao"], ["Email", "asha@example.com"], ["Mobile number", "9876543210"]]) await userEvent.type(screen.getByLabelText(label), value);
  await userEvent.click(screen.getByRole("button", { name: "Continue" }));
  await choose("Society", "DLF Meadows"); await userEvent.click(screen.getByRole("button", { name: "Continue" }));
  await choose("Make", "Tata"); await choose("Model", "Nexon"); await choose("Variant", "Pure");
  await userEvent.type(screen.getByLabelText("Registration"), "hr01zz1234");
  expect(screen.getByText("(optional)")).toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: "Continue" }));
  await choose("Basement", "B2"); await userEvent.type(screen.getByLabelText("Parking number"), "17");
  await userEvent.click(screen.getByRole("button", { name: "Continue" }));
  await userEvent.click(screen.getByRole("switch", { name: "Create a subscription" }));
  await userEvent.click(screen.getByRole("button", { name: "Continue" }));
  await userEvent.click(screen.getByRole("button", { name: "Continue" }));
  await userEvent.click(screen.getByRole("button", { name: "Create" }));
  await waitFor(() => expect(created).not.toBeNull());
  expect((created as unknown as { vehicle: Record<string, unknown> }).vehicle.photo_upload_id).toBeNull();
}, 30000);

it("fills empty address lines from the society and saves them with the society", async () => {
  const original = fetchMock.getMockImplementation()!;
  fetchMock.mockImplementation(async (path: string, o?: RequestInit) =>
    path.includes("/directory/societies") ? reply([{ ...society, sector: "Sector 9", city: "Gurugram" }])
      : path === "/v1/admin/customers/c1" && (o?.method ?? "GET") === "GET" ? reply({ ...customer, society_id: "s1" })
      : original(path, o));
  page("/customers/c1");
  await userEvent.click(await screen.findByRole("button", { name: "Edit details" }));
  const dialog = screen.getByRole("dialog");
  await waitFor(() => expect(within(dialog).getByLabelText(/Address line 1/)).toHaveValue("DLF Meadows"));
  expect(within(dialog).getByLabelText(/Address line 2/)).toHaveValue("Sector 9, Gurugram");
  await userEvent.clear(within(dialog).getByLabelText(/Address line 2/));
  await userEvent.type(within(dialog).getByLabelText(/Address line 2/), "Tower 4");
  await userEvent.click(within(dialog).getByRole("button", { name: "Save customer" }));
  await waitFor(() => expect(bodyOf("/v1/admin/customers/c1", "PATCH")).toMatchObject({
    address_line1: "DLF Meadows", address_line2: "Tower 4", society_id: "s1" }));
});

it("filters from a summary tile with a chip to clear it, and switches to tiles", async () => {
  page();
  const tiles = await screen.findByRole("region", { name: "Customer summary" });
  await userEvent.click(await within(tiles).findByRole("button", { name: "Add-ons only: 7" }));
  await waitFor(() => expect(fetchMock.mock.calls.some((c) => String(c[0]).includes("&scope=addons_only&limit=50&offset=0"))).toBe(true));
  expect(await screen.findByText(/of 7 · Page 1 of 1/)).toBeInTheDocument();
  expect(within(tiles).getByRole("button", { name: "Add-ons only: 7" })).toHaveAttribute("aria-pressed", "true");
  await userEvent.click(screen.getByRole("button", { name: /Clear this filter/ }));
  expect(screen.queryByRole("button", { name: /Clear this filter/ })).not.toBeInTheDocument();
  await userEvent.click(within(tiles).getByRole("button", { name: "Active: 60" }));
  await waitFor(() => expect(fetchMock.mock.calls.some((c) => String(c[0]).includes("&status=Active&limit=50&offset=0"))).toBe(true));

  await userEvent.click(screen.getByRole("button", { name: "Tiles" }));
  expect(screen.queryByRole("table")).not.toBeInTheDocument();
  expect(await screen.findByText("Asha Rao")).toBeInTheDocument();
  expect(localStorage.getItem("priveo.view.customers")).toBe("tiles");
  await userEvent.click(screen.getByRole("button", { name: "Open Asha Rao" }));
  expect(await screen.findByRole("heading", { name: "Asha Rao" })).toBeInTheDocument();
  localStorage.removeItem("priveo.view.customers");
});

it("shows the crew who serve a vehicle, read only (ADM-CUS-28)", async () => {
  detail([car()], (path) => (path.endsWith("/v1/admin/vehicles/v1/crew")
    ? reply([{ id: "w1", name: "Ravi", role: "Member", services: ["Cleaning-External", "Cleaning-Internal"], next_date: "2026-11-03", jobs: 8 }]) : undefined));
  expect(await screen.findByText("Crew serving this vehicle")).toBeInTheDocument();
  expect(await screen.findByText("Ravi")).toBeInTheDocument();
  expect(screen.getByText(/Cleaning-External, Cleaning-Internal/)).toBeInTheDocument();
  expect(sentTo("/v1/admin/vehicles/v1/crew", "GET")).toHaveLength(1);
  expect(fetchMock.mock.calls.filter(([p, o]) => /\/crew/.test(String(p)) && (o?.method ?? "GET") !== "GET")).toHaveLength(0);
});

it("says so when no crew is scheduled for a vehicle", async () => {
  detail([car()]);
  expect(await screen.findByText("No crew is scheduled for this vehicle yet.")).toBeInTheDocument();
});

it("shows a vehicle's parking changes and saves a temporary one (S-07)", async () => {
  detail([car()], (path, o) => (path.endsWith("/v1/admin/vehicles/v1/parking-changes") && (o?.method ?? "GET") === "GET"
    ? reply({ base: "B2-14", today: "B1-24", changes: [
      { id: "p1", basement: "B1", number: "24", from_date: "2026-11-03", to_date: "2026-11-05", kind: "Temporary", note: "Water logging", state: "Current" },
      { id: "p2", basement: "B3", number: "7", from_date: "2026-12-01", to_date: null, kind: "Permanent", note: "", state: "Upcoming" },
      { id: "p3", basement: "B4", number: "1", from_date: "2026-10-01", to_date: "2026-10-02", kind: "Temporary", note: "", state: "Ended" },
    ] }) : undefined));
  expect(await screen.findByText(/Today the crew go to/)).toBeInTheDocument();
  expect(screen.getByText("B1-24", { selector: "strong" })).toBeInTheDocument();
  expect(screen.getByText(/Water logging/)).toBeInTheDocument();
  expect(screen.getAllByRole("button", { name: "Cancel" })).toHaveLength(2); // not the ended one

  await userEvent.click(screen.getByRole("button", { name: "Change parking" }));
  const dialog = within(screen.getByRole("dialog"));
  expect(dialog.getByRole("button", { name: "Save change" })).toBeDisabled();
  await userEvent.type(dialog.getByLabelText("Parking number"), "9");
  fireEvent.change(dialog.getByLabelText("First day"), { target: { value: "2026-11-10" } });
  fireEvent.change(dialog.getByLabelText("Last day"), { target: { value: "2026-11-09" } });
  expect(dialog.getByText("The change must end on or after its first day.")).toBeInTheDocument();
  expect(dialog.getByRole("button", { name: "Save change" })).toBeDisabled();
  fireEvent.change(dialog.getByLabelText("Last day"), { target: { value: "2026-11-12" } });
  await userEvent.click(dialog.getByRole("button", { name: "Save change" }));
  await waitFor(() => expect(bodyOf("/v1/admin/vehicles/v1/parking-changes", "POST")).toEqual({
    basement: "B1", number: "9", from_date: "2026-11-10", to_date: "2026-11-12", note: "" }));
});

it("cancels a parking change", async () => {
  detail([car()], (path, o) => (path.endsWith("/v1/admin/vehicles/v1/parking-changes") && (o?.method ?? "GET") === "GET"
    ? reply({ base: "B2-14", today: "B2-14", changes: [
      { id: "p2", basement: "B3", number: "7", from_date: "2026-12-01", to_date: null, kind: "Permanent", note: "", state: "Upcoming" }] }) : undefined));
  await userEvent.click(await screen.findByRole("button", { name: "Cancel" }));
  await waitFor(() => expect(sentTo("/v1/admin/vehicles/v1/parking-changes/p2", "DELETE")).toHaveLength(1));
});

it("sends a permanent parking change without an end date", async () => {
  detail([car()]);
  await userEvent.click(await screen.findByRole("button", { name: "Change parking" }));
  const dialog = within(screen.getByRole("dialog"));
  await userEvent.type(dialog.getByLabelText("Parking number"), "5");
  await userEvent.click(dialog.getByRole("combobox", { name: "Applies" }));
  await userEvent.click(await screen.findByRole("option", { name: "Permanently, from a date" }));
  expect(dialog.queryByLabelText("Last day")).not.toBeInTheDocument();
  fireEvent.change(dialog.getByLabelText("First day"), { target: { value: "2026-11-10" } });
  await userEvent.click(dialog.getByRole("button", { name: "Save change" }));
  await waitFor(() => expect(bodyOf("/v1/admin/vehicles/v1/parking-changes", "POST")).toMatchObject({ to_date: null, number: "5" }));
});

it("shows the plan history and cancels a scheduled change (ADM-SUB-08)", async () => {
  detail([car()], (path) => (path.endsWith("/plan-history")
    ? reply({ current_plan: "Premium", current_price_rupees: 999, changes: [
      { id: "c1", from_plan: "Premium", from_price_rupees: 999, to_plan: "Exterior", to_price_rupees: 699, effective_from: "2026-12-01", status: "Scheduled", chosen: true },
      { id: "c0", from_plan: "Basic", from_price_rupees: 500, to_plan: "Premium", to_price_rupees: 999, effective_from: "2026-10-01", status: "Applied", chosen: false },
    ] }) : undefined));
  expect(await screen.findByText("Plan history")).toBeInTheDocument();
  expect(screen.getByText("Scheduled")).toBeInTheDocument();
  expect(screen.getByText("Applied")).toBeInTheDocument();
  expect(screen.getAllByRole("button", { name: "Cancel change" })).toHaveLength(1);
  await userEvent.click(screen.getByRole("button", { name: "Cancel change" }));
  await waitFor(() => expect(sentTo("/v1/admin/subscriptions/sub1/plan-change", "DELETE")).toHaveLength(1));
});

it("sends the chosen start date with a plan change, and only then", async () => {
  const original = fetchMock.getMockImplementation()!;
  fetchMock.mockImplementation(async (path: string, options?: RequestInit) =>
    path.includes("/directory/plans") ? reply([plan, { ...plan, id: "p2", name: "Exterior", includes_interior: false }]) : original(path, options));
  detail([car()]);
  await userEvent.click(await screen.findByRole("button", { name: "Schedule settings" }));
  const dialog = within(screen.getByRole("dialog"));
  expect(dialog.queryByLabelText("Plan starts on (optional)")).not.toBeInTheDocument();
  await choose("New plan", /Exterior/);
  fireEvent.change(dialog.getByLabelText("Plan starts on (optional)"), { target: { value: "2026-12-01" } });
  await userEvent.click(dialog.getByRole("button", { name: "Save settings" }));
  await waitFor(() => expect(bodyOf("/v1/admin/subscriptions/sub1", "PATCH")).toMatchObject({ effective_from: "2026-12-01" }));
});
