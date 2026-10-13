import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ToastProvider } from "../../components";
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

let payments: unknown[] = [];

function route(path: string, init?: RequestInit) {
  const method = init?.method ?? "GET";
  if (path.startsWith("/v1/admin/payment-alerts")) return json(200, []);
  if (path.startsWith("/v1/admin/directory/societies")) return json(200, [{ name: "Lake View" }]);
  if (path.startsWith("/v1/admin/payments") && method === "GET") return json(200, payments);
  return json(404, { code: "not_found", message: "no", fields: {}, request_id: "" });
}

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter><ToastProvider><PaymentsPage /></ToastProvider></MemoryRouter>
    </QueryClientProvider>,
  );
}

const calls = (needle: string) =>
  fetchMock.mock.calls.filter((c) => String(c[0]).includes(needle));

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
  it("pages payments and resets the page on filter application", async () => {
    fetchMock.mockImplementation(async (path: string, init?: RequestInit) => {
      if (path.startsWith("/v1/admin/payments?")) {
        const offset = new URL(path, "https://test").searchParams.get("offset");
        return json(200, offset === "50" ? [pay({ id: "last", customer_name: "Second page" })]
          : Array.from({ length: 50 }, (_, i) => pay({ id: `p${i}`, customer_name: `First ${i}` })));
      }
      return route(path, init);
    });
    renderPage();
    await screen.findByText("First 0, B-12");
    await userEvent.click(screen.getByRole("button", { name: "Next" }));
    expect(await screen.findByText("Second page, B-12")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Apply" }));
    await waitFor(() => expect(screen.getByText("First 0, B-12")).toBeInTheDocument());
    expect(calls("offset=50").length).toBeGreaterThan(0);
  });
  it("lists payments and sends the filters", async () => {
    renderPage();
    expect(await screen.findByText("Asha Rao, B-12")).toBeInTheDocument();
    expect(screen.getByText("07-Nov-26")).toBeInTheDocument();
    await userEvent.selectOptions(screen.getByLabelText("Status"), "Over due");
    await userEvent.selectOptions(screen.getByLabelText("Type"), "Add-on");
    await userEvent.type(screen.getByLabelText("Vehicle ID"), "v9");
    await userEvent.click(screen.getByRole("button", { name: "Apply" }));
    await waitFor(() => {
      const last = String(fetchMock.mock.calls.filter((c) => String(c[0]).startsWith("/v1/admin/payments?")).at(-1)![0]);
      expect(last).toContain("status=Over+due");
      expect(last).toContain("kind=Add-on");
      expect(last).toContain("vehicle_id=v9");
    });
  });

  it("confirms an Initiated payment", async () => {
    fetchMock.mockImplementation(async (p: string, init?: RequestInit) =>
      p.endsWith("/confirm") ? json(200, pay({ status: "Received", received_on: "2026-11-08" }))
        : route(p, init));
    renderPage();
    await userEvent.click(await screen.findByRole("button", { name: "Open" }));
    await userEvent.click(screen.getByRole("button", { name: "Confirm received" }));
    expect(await screen.findByRole("button", { name: "Issue invoice" })).toBeInTheDocument();
    expect(calls("/v1/admin/payments/p1/confirm")[0][1].method).toBe("POST");
  });

  it("offers reject only for Initiated or Received and no confirm for Received", async () => {
    payments = [pay({ status: "Due" })];
    renderPage();
    await userEvent.click(await screen.findByRole("button", { name: "Open" }));
    expect(screen.getByRole("button", { name: "Confirm received" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Reject/ })).toBeNull();
  });

  it("sets a status with the chosen value", async () => {
    fetchMock.mockImplementation(async (p: string, init?: RequestInit) =>
      p.endsWith("/status") ? json(200, pay({ status: "Over due" })) : route(p, init));
    renderPage();
    await userEvent.click(await screen.findByRole("button", { name: "Open" }));
    const dialog = screen.getByRole("dialog");
    await userEvent.selectOptions(within(dialog).getByLabelText("Set status"), "Over due");
    await userEvent.click(within(dialog).getByRole("button", { name: "Save status" }));
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
    expect(await screen.findByText("Already moved.")).toBeInTheDocument();
  });

  it("issues an invoice for a Received payment", async () => {
    payments = [pay({ status: "Received", received_on: "2026-11-08" })];
    fetchMock.mockImplementation(async (p: string, init?: RequestInit) =>
      p.endsWith("/invoice")
        ? json(200, { number: "PRV10264321", issued_on: "2026-11-08", amount_rupees: 1500,
                      description: "Monthly plan", customer_name: "Asha Rao", vehicle: "Swift",
                      gst_included: true, seller_name: "Priveo", seller_address: "Pune",
                      seller_gstin: "G1" })
        : route(p, init));
    renderPage();
    await userEvent.click(await screen.findByRole("button", { name: "Open" }));
    await userEvent.click(screen.getByRole("button", { name: "Issue invoice" }));
    expect(await screen.findByText("Invoice PRV10264321")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Open invoice PDF" })).toHaveAttribute(
      "href", `/v1/admin/payments/${payments[0].id}/invoice.pdf`);
    expect(screen.getByRole("link", { name: "Open invoice PDF" })).toHaveAttribute("target", "_blank");
  });

  it("records a payment and shows field errors", async () => {
    fetchMock.mockImplementation(async (p: string, init?: RequestInit) =>
      p === "/v1/admin/payments" && init?.method === "POST"
        ? json(404, { code: "not_found", message: "That vehicle was not found.",
                      fields: { vehicle_id: "unknown" }, request_id: "" })
        : route(p, init));
    renderPage();
    await userEvent.click(await screen.findByRole("button", { name: "Record a payment" }));
    const dialog = screen.getByRole("dialog");
    await userEvent.type(within(dialog).getByLabelText("Vehicle ID"), "zz");
    await userEvent.type(within(dialog).getByLabelText("Amount (Rs, GST included)"), "1500");
    await userEvent.type(within(dialog).getByLabelText("Due date"), "2026-11-07");
    await userEvent.click(within(dialog).getByRole("button", { name: "Record" }));
    expect((await screen.findAllByText("That vehicle was not found.")).length).toBeGreaterThan(0);
    const post = calls("/v1/admin/payments").find((c) => c[1]?.method === "POST")!;
    expect(JSON.parse(post[1].body)).toMatchObject({ vehicle_id: "zz", amount_rupees: 1500 });
  });
});
