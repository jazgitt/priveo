import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ToastProvider } from "../../components";
import { choose, confirmWith, PortalProviders } from "../../test/portal";
import { PaymentsPage } from "./PaymentsPage";

const fetchMock = vi.fn();

function json(status: number, body?: unknown) {
  return new Response(body === undefined ? null : JSON.stringify(body), { status });
}

const pay = (over: Record<string, unknown> = {}) => ({
  id: "p1", kind: "Plan", description: "Monthly plan", amount_rupees: 1500, status: "Initiated",
  due_date: "2026-11-07", cycle_start: "2026-11-07", cycle_end: "2026-12-07", vehicle_id: "v1",
  received_on: null, invoice_number: null, customer_name: "Asha Rao", flat: "B-12",
  society: "Lake View", vehicle: "Swift KA01", initiated_at: null, ...over,
});
const customerDetail = { id: "c1", first_name: "Asha", last_name: "Rao", email: "a@x.com", mobile: "9876543210", flat: "B-12",
  email_verified: true, password_set: true, onboarding_confirmed: true,
  vehicles: [{ id: "v9", society: "Lake View", registration: "KA01AB1234", make: "Maruti", model: "Swift", variant: "", category: "",
    parking_basement: "B1", parking_number: "1", photo_url: null, subscription: null, payments: [] }] };

let payments: ReturnType<typeof pay>[] = [];

function route(path: string, init?: RequestInit) {
  const method = init?.method ?? "GET";
  if (path.startsWith("/v1/admin/payment-alerts")) return json(200, []);
  if (path.startsWith("/v1/admin/customers?")) return json(200, [{ id: "c1", name: "Asha Rao", email: "a@x.com", mobile: "9876543210", vehicles: [] }]);
  if (path === "/v1/admin/customers/c1") return json(200, customerDetail);
  if (path.startsWith("/v1/admin/payments/summary")) {
    return json(200, { total: 3, total_rupees: 4500, by_status: {
      Due: { count: 1, rupees: 1500 }, "Over due": { count: 0, rupees: 0 },
      Initiated: { count: 1, rupees: 1500 }, Received: { count: 1, rupees: 1500 } } });
  }
  if (path.startsWith("/v1/admin/payments") && method === "GET") return json(200, payments);
  return json(404, { code: "not_found", message: "no", fields: {}, request_id: "" });
}

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter><ToastProvider><PortalProviders><PaymentsPage /></PortalProviders></ToastProvider></MemoryRouter>
    </QueryClientProvider>,
  );
}

const calls = (needle: string) => fetchMock.mock.calls.filter((c) => String(c[0]).includes(needle));
const lastList = () => String(fetchMock.mock.calls.filter((c) => String(c[0]).startsWith("/v1/admin/payments?")).at(-1)![0]);

/** Picks Asha Rao in a customer search box. */
async function pickCustomer(scope: HTMLElement = document.body) {
  await userEvent.type(within(scope).getByRole("combobox", { name: "Customer" }), "Asha");
  await userEvent.click(await within(scope).findByRole("option", { name: /Asha Rao/ }));
}

beforeEach(() => {
  payments = [pay()];
  fetchMock.mockImplementation(async (p: string, init?: RequestInit) => route(p, init));
  vi.stubGlobal("fetch", fetchMock);
});
afterEach(() => {
  fetchMock.mockReset();
  vi.unstubAllGlobals();
});

describe("payments page", () => {
  it("pages payments and goes back to the first page when a filter changes", async () => {
    fetchMock.mockImplementation(async (path: string, init?: RequestInit) => {
      if (path.startsWith("/v1/admin/payments?")) {
        const offset = new URL(path, "https://test").searchParams.get("offset");
        return json(200, offset === "50" ? [pay({ id: "last", customer_name: "Second page" })]
          : Array.from({ length: 50 }, (_, i) => pay({ id: `p${i}`, customer_name: `First ${i}` })));
      }
      return route(path, init);
    });
    renderPage();
    await screen.findByText("First 0");
    await userEvent.click(screen.getByRole("button", { name: "Next" }));
    expect(await screen.findByText("Second page")).toBeInTheDocument();
    await choose("Status", "Due");
    await waitFor(() => expect(lastList()).toContain("offset=0"));
    expect(calls("offset=50").length).toBeGreaterThan(0);
  });

  it("lists payments and sends the filters, the customer and vehicle by search", async () => {
    renderPage();
    expect(await screen.findByText("Asha Rao")).toBeInTheDocument();
    expect(within(screen.getByRole("table")).getByText("₹1,500")).toBeInTheDocument();
    await choose("Status", "Over due");
    await choose("Type", "Add-on");
    await pickCustomer();
    await choose("Vehicle", /KA01AB1234/);
    fireEvent.change(screen.getByLabelText("Due after"), { target: { value: "2026-11-01" } });
    await waitFor(() => {
      const last = lastList();
      expect(last).toContain("status=Over+due");
      expect(last).toContain("kind=Add-on");
      expect(last).toContain("customer_id=c1");
      expect(last).toContain("vehicle_id=v9");
      expect(last).toContain("due_after=2026-11-01");
    });
    await userEvent.click(screen.getByRole("button", { name: "Clear" }));
    await waitFor(() => expect(lastList()).not.toContain("status="));
  });

  it("confirms an Initiated payment after asking", async () => {
    fetchMock.mockImplementation(async (p: string, init?: RequestInit) =>
      p.endsWith("/confirm") ? json(200, pay({ status: "Received", received_on: "2026-11-08" })) : route(p, init));
    renderPage();
    await userEvent.click(await screen.findByRole("button", { name: "Open" }));
    await userEvent.click(screen.getByRole("button", { name: "Confirm received" }));
    expect(calls("/confirm")).toHaveLength(0);
    await confirmWith("Confirm received");
    expect(await screen.findByRole("button", { name: "Issue invoice" })).toBeInTheDocument();
    expect(calls("/v1/admin/payments/p1/confirm")[0][1].method).toBe("POST");
  });

  it("offers reject only for Initiated or Received", async () => {
    payments = [pay({ status: "Due" })];
    renderPage();
    await userEvent.click(await screen.findByRole("button", { name: "Open" }));
    expect(screen.getByRole("button", { name: "Confirm received" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Reject/ })).toBeNull();
  });

  it("sets a status with the chosen value after asking", async () => {
    fetchMock.mockImplementation(async (p: string, init?: RequestInit) =>
      p.endsWith("/status") ? json(200, pay({ status: "Over due" })) : route(p, init));
    renderPage();
    await userEvent.click(await screen.findByRole("button", { name: "Open" }));
    await choose("Set status", "Over due");
    await userEvent.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Save status" }));
    await confirmWith("Save status");
    await waitFor(() => expect(calls("/status")).toHaveLength(1));
    const [, init] = calls("/status")[0];
    expect(init.method).toBe("PUT");
    expect(JSON.parse(init.body)).toEqual({ status: "Over due" });
  });

  it("shows the error message from the API", async () => {
    fetchMock.mockImplementation(async (p: string, init?: RequestInit) =>
      p.endsWith("/reject")
        ? json(409, { code: "conflict", message: "Already moved.", fields: {}, request_id: "r" })
        : route(p, init));
    renderPage();
    await userEvent.click(await screen.findByRole("button", { name: "Open" }));
    await userEvent.click(screen.getByRole("button", { name: /Reject/ }));
    await confirmWith("Reject");
    expect(await screen.findByText("Already moved.")).toBeInTheDocument();
  });

  it("issues an invoice for a Received payment after asking", async () => {
    payments = [pay({ status: "Received", received_on: "2026-11-08" })];
    fetchMock.mockImplementation(async (p: string, init?: RequestInit) =>
      p.endsWith("/invoice")
        ? json(200, { number: "PRV10264321", issued_on: "2026-11-08", amount_rupees: 1500,
                      description: "Monthly plan", customer_name: "Asha Rao", vehicle: "Swift",
                      gst_included: true, seller_name: "Priveo", seller_address: "Pune", seller_gstin: "G1" })
        : route(p, init));
    renderPage();
    await userEvent.click(await screen.findByRole("button", { name: "Open" }));
    await userEvent.click(screen.getByRole("button", { name: "Issue invoice" }));
    await confirmWith("Issue invoice");
    expect(await screen.findByText("Invoice PRV10264321")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Open invoice PDF" })).toHaveAttribute("href", `/v1/admin/payments/${payments[0].id}/invoice.pdf`);
    expect(screen.getByRole("link", { name: "Open invoice PDF" })).toHaveAttribute("target", "_blank");
  });

  it("records a payment for a vehicle found by customer search", async () => {
    fetchMock.mockImplementation(async (p: string, init?: RequestInit) =>
      p === "/v1/admin/payments" && init?.method === "POST"
        ? json(404, { code: "not_found", message: "That vehicle was not found.", fields: { vehicle_id: "unknown" }, request_id: "" })
        : route(p, init));
    renderPage();
    await userEvent.click(await screen.findByRole("button", { name: "Record a payment" }));
    const dialog = screen.getByRole("dialog");
    expect(within(dialog).getByRole("button", { name: "Record" })).toBeDisabled();
    await pickCustomer(dialog);
    await choose("Vehicle", /KA01AB1234/);
    await userEvent.type(within(dialog).getByLabelText("Amount (₹, GST included)"), "1500");
    fireEvent.change(within(dialog).getByLabelText("Due date"), { target: { value: "2026-11-07" } });
    await userEvent.click(within(dialog).getByRole("button", { name: "Record" }));
    expect((await screen.findAllByText(/That vehicle was not found/)).length).toBeGreaterThan(0);
    const post = calls("/v1/admin/payments").find((c) => c[1]?.method === "POST")!;
    expect(JSON.parse(post[1].body)).toMatchObject({ vehicle_id: "v9", amount_rupees: 1500, due_date: "2026-11-07" });
  });
});

describe("payment summary tiles", () => {
  it("counts payments and rupees by status, and filters the list from a tile", async () => {
    renderPage();
    const tiles = await screen.findByRole("region", { name: "Payment summary" });
    expect(await within(tiles).findByRole("button", { name: "All payments: 3" })).toBeInTheDocument();
    expect(within(tiles).getByText("₹4,500")).toBeInTheDocument();
    await userEvent.click(within(tiles).getByRole("button", { name: "Initiated: 1" }));
    await waitFor(() => expect(lastList()).toContain("status=Initiated"));
    expect(within(tiles).getByRole("button", { name: "Initiated: 1" })).toHaveAttribute("aria-pressed", "true");
    await userEvent.click(within(tiles).getByRole("button", { name: "All payments: 3" }));
    await waitFor(() => expect(lastList()).not.toContain("status="));
  });
});
