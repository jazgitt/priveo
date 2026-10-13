import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, afterEach, expect, it, vi } from "vitest";
import { ToastProvider } from "../../components";
import { CustomerDetailPage, CustomersPage } from "./CustomersPage";
import type { Vehicle } from "./api";

const fetchMock = vi.fn();
const society = { id: "s1", name: "DLF Meadows", active: true, parking_basements: ["B1", "B2"] };
const plan = { id: "p1", name: "Premium", active: true, monthly_price_rupees: 999, list_price_rupees: 1499, includes_interior: true, inclusions: ["Daily exterior", "Weekly interior"], badge: "Founding member" };
const catalogue = { id: "cat1", make: "Tata", model: "Nexon", variant: "Pure", category: "Compact SUV", active: true };
const customer = { id: "c1", first_name: "Asha", last_name: "Rao", email: "asha@example.com", mobile: "9876543210", flat: "A-12", email_verified: false, password_set: false, onboarding_confirmed: false, vehicles: [] };
let created: Record<string, unknown> | null;
const reply = (body: unknown, status = 200) => new Response(status === 204 ? null : JSON.stringify(body), { status });
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
    if (path.endsWith("/notification-preferences")) return reply({ items: [] });
    if (path.endsWith("/sessions")) return reply([]);
    if (path === "/v1/admin/customers" && method === "POST") { created = JSON.parse(options!.body as string); return reply({ id: "c1", welcome_sent: true }, 201); }
    if (path === "/v1/admin/customers/c1") return reply(customer);
    if (path.startsWith("/v1/admin/customers?")) return reply([{ id: "c1", name: "Asha Rao", email: customer.email, mobile: customer.mobile }]);
    return reply({ saved: true });
  });
  vi.stubGlobal("fetch", fetchMock);
});
afterEach(() => { vi.unstubAllGlobals(); fetchMock.mockReset(); });
function page() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(<QueryClientProvider client={client}><MemoryRouter initialEntries={["/customers"]}><ToastProvider><Routes>
    <Route path="/customers" element={<CustomersPage />} /><Route path="/customers/:id" element={<CustomerDetailPage />} />
  </Routes></ToastProvider></MemoryRouter></QueryClientProvider>);
}

it("pages customer search and resets the offset when the search changes", async () => {
  const original = fetchMock.getMockImplementation()!;
  fetchMock.mockImplementation(async (path: string, options?: RequestInit) => {
    if (path.startsWith("/v1/admin/customers?")) {
      const query = new URL(path, "https://test").searchParams;
      return reply(query.get("offset") === "50" ? [{ id: "second", name: "Second page", email: "second@example.com", mobile: "1" }]
        : Array.from({ length: 50 }, (_, i) => ({ id: `row${i}`, name: `First ${i}`, email: "first@example.com", mobile: "1" })));
    }
    return original(path, options);
  });
  page();
  await screen.findByRole("link", { name: "First 0" });
  await userEvent.click(screen.getByRole("button", { name: "Next" }));
  expect(await screen.findByRole("link", { name: "Second page" })).toBeInTheDocument();
  await userEvent.type(screen.getByLabelText("Search by name, mobile, registration or society"), "new");
  await waitFor(() => expect(fetchMock.mock.calls.some(c => String(c[0]).includes("q=new&limit=50&offset=0"))).toBe(true));
});

it("shows imported Spa history without inventing completion or a date", async () => {
  const original = fetchMock.getMockImplementation()!;
  fetchMock.mockImplementation(async (path: string, options?: RequestInit) =>
    path === "/v1/admin/customers/c1" ? reply({ ...customer, imported_history: [{
      id: "old1", date: null, service: "Deep Spa", vehicle: "Unmatched vehicle",
      payment_status: "Received", notes: "Date as given: unclear" }] }) : original(path, options));
  page();
  await userEvent.click(await screen.findByRole("link", { name: "Asha Rao" }));
  expect(await screen.findByText(/Date unknown/)).toBeInTheDocument();
  expect(screen.getByText(/Completion not recorded/)).toBeInTheDocument();
  expect(screen.getByText("Date as given: unclear")).toBeInTheDocument();
});

it("searches customers through the server and opens their onboarding state", async () => {
  page(); await userEvent.type(screen.getByLabelText("Search by name, mobile, registration or society"), "Asha Rao");
  await waitFor(() => expect(fetchMock.mock.calls.some(c => String(c[0]).includes("q=Asha%20Rao"))).toBe(true));
  await userEvent.click(await screen.findByRole("link", { name: "Asha Rao" }));
  expect(await screen.findByText(/Email not verified/)).toHaveTextContent("Review pending");
  expect(screen.getByRole("button", { name: "Add vehicle" })).toBeInTheDocument();
});

it.each([true, false])("creates a customer with subscription=%s and a required photo", async (subscribed) => {
  page(); await userEvent.click(screen.getByRole("button", { name: "Create customer" }));
  for (const [label, value] of [["First name", "Asha"], ["Last name", "Rao"], ["Email", "asha@example.com"], ["Mobile number", "9876543210"]]) await userEvent.type(screen.getByLabelText(label), value);
  await userEvent.click(screen.getByRole("button", { name: "Continue" }));
  await userEvent.selectOptions(screen.getByLabelText("Society"), "s1"); await userEvent.click(screen.getByRole("button", { name: "Continue" }));
  await userEvent.selectOptions(screen.getByLabelText("Make"), "Tata"); await userEvent.selectOptions(screen.getByLabelText("Model"), "Nexon"); await userEvent.selectOptions(screen.getByLabelText("Variant"), "cat1");
  await userEvent.type(screen.getByLabelText("Registration"), "hr01zz1234");
  expect(screen.getByRole("button", { name: "Continue" })).toBeDisabled();
  await userEvent.upload(screen.getByLabelText("Vehicle photo (required)"), new File(["photo"], "car.jpg", { type: "image/jpeg" }));
  await waitFor(() => expect(screen.getByRole("button", { name: "Continue" })).toBeEnabled());
  await userEvent.click(screen.getByRole("button", { name: "Continue" })); await userEvent.selectOptions(screen.getByLabelText("Basement"), "B2"); await userEvent.type(screen.getByLabelText("Parking number"), "17");
  await userEvent.click(screen.getByRole("button", { name: "Continue" })); if (subscribed) await userEvent.selectOptions(screen.getByLabelText("Plan"), "p1");
  else await userEvent.click(screen.getByLabelText("Create a subscription"));
  await userEvent.click(screen.getByRole("button", { name: "Continue" })); if (subscribed) await userEvent.selectOptions(screen.getByLabelText("Interior care day"), "Monday");
  await userEvent.click(screen.getByRole("button", { name: "Continue" })); if (subscribed) await userEvent.selectOptions(screen.getByLabelText("First payment status"), "Received"); await userEvent.click(screen.getByRole("button", { name: "Create" }));
  await waitFor(() => expect(created).not.toBeNull());
  expect(created).toMatchObject({ email: "asha@example.com", vehicle: { photo_upload_id: "u1", registration: "HR01ZZ1234", society_id: "s1", ...(subscribed ? { first_payment_status: "Received", interior_day: "Monday" } : { plan_id: null, cutoff_time: null, interior_day: null }) } });
  expect(await screen.findByRole("heading", { name: "Asha Rao" })).toBeInTheDocument();
});

it("changes to an exterior-only plan without submitting the old interior day", async () => {
  const car: Vehicle = { id: "v1", society: "DLF Meadows", registration: "HR01ZZ1234",
    make: "Tata", model: "Nexon", variant: "Pure", category: "Compact SUV",
    parking_basement: "B1", parking_number: "17", photo_url: null, rc_url: null,
    rc_verified: false, payments: [], subscription: { id: "sub1", status: "Active",
      plan_id: "p1", plan_name: "Premium", price_rupees: 999, cutoff_time: "09:00",
      interior_day: "Monday", first_service_date: "2026-10-01", pending_plan_id: null,
      pending_from: null } };
  const original = fetchMock.getMockImplementation()!;
  let saved: Record<string, unknown> | null = null;
  fetchMock.mockImplementation(async (path: string, options?: RequestInit) => {
    if (path.includes("/directory/plans")) return reply([plan, { ...plan, id: "p2", name: "Exterior", includes_interior: false }]);
    if (path === "/v1/admin/customers/c1") return reply({ ...customer, vehicles: [car] });
    if (path === "/v1/admin/vehicles/v1/changes") return reply({ skips: [], pauses: [] });
    if (path === "/v1/admin/subscriptions/sub1" && options?.method === "PATCH") {
      saved = JSON.parse(options.body as string); return reply({ saved: true });
    }
    return original(path, options);
  });
  page();
  await userEvent.click(await screen.findByRole("link", { name: "Asha Rao" }));
  await userEvent.click(await screen.findByText("Subscription and schedule settings"));
  await userEvent.selectOptions(screen.getByLabelText("Plan at next renewal"), "p2");
  await userEvent.click(screen.getByRole("button", { name: "Save settings" }));
  await waitFor(() => expect(saved).toEqual({ plan_id: "p2", cutoff_time: "09:00" }));
});
