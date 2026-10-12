import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, afterEach, expect, it, vi } from "vitest";
import { ToastProvider } from "../../components";
import { CustomerDetailPage, CustomersPage } from "./CustomersPage";

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

it("searches customers through the server and opens their onboarding state", async () => {
  page(); await userEvent.type(screen.getByLabelText("Search by name, mobile, registration or society"), "Asha Rao");
  await waitFor(() => expect(fetchMock.mock.calls.some(c => String(c[0]).includes("q=Asha%20Rao"))).toBe(true));
  await userEvent.click(await screen.findByRole("link", { name: "Asha Rao" }));
  expect(await screen.findByText(/Email not verified/)).toHaveTextContent("Review pending");
  expect(screen.getByRole("button", { name: "Add vehicle" })).toBeInTheDocument();
});

it("requires a photo and creates a complete customer with the chosen first payment status", async () => {
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
  await userEvent.click(screen.getByRole("button", { name: "Continue" })); await userEvent.selectOptions(screen.getByLabelText("Plan"), "p1");
  await userEvent.click(screen.getByRole("button", { name: "Continue" })); await userEvent.selectOptions(screen.getByLabelText("Interior care day"), "Monday");
  await userEvent.click(screen.getByRole("button", { name: "Continue" })); await userEvent.selectOptions(screen.getByLabelText("First payment status"), "Received"); await userEvent.click(screen.getByRole("button", { name: "Create" }));
  await waitFor(() => expect(created).not.toBeNull());
  expect(created).toMatchObject({ email: "asha@example.com", vehicle: { photo_upload_id: "u1", registration: "HR01ZZ1234", society_id: "s1", first_payment_status: "Received", interior_day: "Monday" } });
  expect(await screen.findByRole("heading", { name: "Asha Rao" })).toBeInTheDocument();
});
