import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createMemoryRouter, MemoryRouter, RouterProvider } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { AlertBell } from "../../components/AlertBell";
import { ToastProvider } from "../../components";
import { routes as alertRoutes } from "../alerts";
import { routes as complaintRoutes } from "../complaints";
import { routes as dashboardRoutes } from "../dashboard";
import { routes as feedbackRoutes } from "../feedback";
import { choose, confirmWith, PortalProviders } from "../../test/portal";

type Handler = (method: string, body: unknown) => unknown;
let handlers: Record<string, Handler> = {};
const calls: { url: string; method: string; body: unknown }[] = [];

function install() {
  vi.stubGlobal("fetch", vi.fn(async (url: string, init?: RequestInit) => {
    const method = init?.method ?? "GET";
    const body = init?.body ? JSON.parse(String(init.body)) : undefined;
    calls.push({ url, method, body });
    const key = Object.keys(handlers).find((k) => url.split("?")[0] === k || url === k);
    if (!key) return new Response(JSON.stringify({ code: "nf", message: "no" }), { status: 404 });
    const out = handlers[key](method, body);
    return out === undefined ? new Response(null, { status: 204 })
      : new Response(JSON.stringify(out), { status: 200 });
  }));
}

function renderAt(path: string, extra?: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const router = createMemoryRouter(
    [...dashboardRoutes, ...alertRoutes, ...complaintRoutes, ...feedbackRoutes]
      .map((r) => ({ ...r, element: <PortalProviders>{r.element}</PortalProviders> })),
    { initialEntries: [path] },
  );
  return render(
    <QueryClientProvider client={qc}>
      <ToastProvider>
        {extra ? <MemoryRouter><PortalProviders>{extra}</PortalProviders></MemoryRouter> : <RouterProvider router={router} />}
      </ToastProvider>
    </QueryClientProvider>,
  );
}

const supportAlert = {
  id: "s1", kind: "complaint", title: "New complaint", body: "C-0001 raised",
  ref_type: "complaint", ref_id: "c1", created_at: "2026-10-10T10:00:00Z", read: false,
};
const payAlert = {
  id: "p1", kind: "Payment initiated", message: "Asha paid", payment_id: "pay1",
  created_at: "2026-10-11T10:00:00Z", read: false,
};
const complaint = {
  id: "c1", number: 1, display_id: "#C-0001", category: "Cleaning quality",
  description: "Streaks on the glass", status: "Raised", visit_id: null,
  created_at: "2026-10-10T05:00:00Z", updated_at: "2026-10-10T05:00:00Z", latest_note: null,
  customer_name: "Asha", society: "Green Park", flat: "B-12", overdue: true,
};

beforeEach(() => {
  calls.length = 0;
  handlers = {
    "/v1/admin/alerts": () => ({ unread_count: 1, items: [supportAlert] }),
    "/v1/admin/payment-alerts": () => [payAlert],
  };
  install();
});
afterEach(() => vi.unstubAllGlobals());

it("shows complaint vehicle/photos and the linked visit proof", async () => {
  handlers["/v1/admin/complaints/c1"] = () => ({ ...complaint, vehicle: "HR01ZZ1234 · Creta",
    visit_id: "visit1", photo_keys: ["photo1"], photo_urls: ["/signed-complaint.jpg"], updates: [] });
  handlers["/v1/admin/complaints/c1/visit"] = () => ({ status: "Completed", date: "2026-10-09",
    jobs: [{ id: "j1", service: "Cleaning-External", crew_name: "Ravi",
      checklist: [{ key: "body", label: "Body clean", checked_at: "2026-10-09T07:00:00Z" }],
      proof: [{ id: "proof1", kind: "photo", url: "/signed-proof.jpg" }] }] });
  renderAt("/complaints/c1");
  expect(await screen.findByText("HR01ZZ1234 · Creta")).toBeInTheDocument();
  expect(screen.getByRole("img", { name: "Complaint photo 1" })).toHaveAttribute("src", "/signed-complaint.jpg");
  expect(await screen.findByRole("img", { name: "Linked visit proof" })).toHaveAttribute("src", "/signed-proof.jpg");
  expect(screen.getByText(/Body clean/)).toBeInTheDocument();
});

describe("alerts", () => {
  it("merges both sources, tagged, and marks one read on its own endpoint", async () => {
    handlers["/v1/admin/payment-alerts/p1/read"] = () => undefined;
    renderAt("/alerts");
    expect(await screen.findByText("Asha paid")).toBeInTheDocument();
    expect(screen.getByText("C-0001 raised")).toBeInTheDocument();
    expect(screen.getByText("Payment")).toBeInTheDocument();
    expect(screen.getByText("Support")).toBeInTheDocument();
    expect(screen.getByText("2 unread")).toBeInTheDocument();
    const buttons = screen.getAllByRole("button", { name: "Mark read" });
    await userEvent.click(buttons[0]);
    await waitFor(() => expect(calls.some((c) =>
      c.url === "/v1/admin/payment-alerts/p1/read" && c.method === "POST")).toBe(true));
  });

  it("reads all on both sources", async () => {
    handlers["/v1/admin/alerts/read-all"] = () => undefined;
    handlers["/v1/admin/payment-alerts/p1/read"] = () => undefined;
    renderAt("/alerts");
    await screen.findByText("Asha paid");
    await userEvent.click(screen.getByRole("button", { name: "Mark all read" }));
    await waitFor(() => expect(calls.some((c) =>
      c.url === "/v1/admin/payment-alerts/p1/read")).toBe(true));
    expect(calls.some((c) => c.url === "/v1/admin/alerts/read-all")).toBe(true);
  });

  it("shows the unread count on the bell", async () => {
    renderAt("/", <AlertBell />);
    const bell = await screen.findByRole("button", { name: "Alerts, 2 unread" });
    await userEvent.click(bell);
    expect(within(screen.getByRole("region", { name: "Latest alerts" }))
      .getByText("New complaint")).toBeInTheDocument();
  });
});

describe("dashboard", () => {
  it("shows the four counts", async () => {
    handlers["/v1/admin/scheduling/needs-scheduling"] = () => ({
      jobs: [{ id: "j1", date: "2026-10-12", registration: "MH12AB1234", vehicle: "Swift",
        customer_name: "Asha", service: "Cleaning-External", reason: "" }],
    });
    handlers["/v1/admin/payments"] = () => [];
    handlers["/v1/admin/complaints"] = () => [complaint];
    renderAt("/");
    expect(await screen.findByText("MH12AB1234")).toBeInTheDocument();
    expect(screen.getByText("12-Oct-26")).toBeInTheDocument();
    expect(screen.getByText("No payment is waiting for confirmation.")).toBeInTheDocument();
    expect(await screen.findByText("#C-0001")).toBeInTheDocument();
    expect(screen.getByLabelText("Unread alerts count")).toHaveTextContent("2");
    expect(screen.getByLabelText("Needs scheduling count")).toHaveTextContent("1");
    expect(screen.getByLabelText("Payments to confirm count")).toHaveTextContent("0");
    expect(screen.getByLabelText("Complaints overdue count")).toHaveTextContent("1");
  });
});

describe("complaints", () => {
  it("marks overdue rows and filters by status on the server", async () => {
    handlers["/v1/admin/complaints"] = () => [complaint];
    renderAt("/complaints");
    expect(await screen.findByText("Overdue")).toBeInTheDocument();
    await choose("Status", "Resolved");
    await waitFor(() => expect(calls.some((c) =>
      c.url === "/v1/admin/complaints?status=Resolved")).toBe(true));
  });

  it("sets the status and adds a note on the detail page", async () => {
    const detail = { ...complaint, photo_keys: [], updates: [
      { id: "u1", author_role: "customer", note: "Please check", status: null,
        created_at: "2026-10-10T05:00:00Z" }] };
    handlers["/v1/admin/complaints/c1"] = () => detail;
    handlers["/v1/admin/complaints/c1/status"] = (_m, b) => ({ ...detail, status: (b as { status: string }).status });
    handlers["/v1/admin/complaints/c1/notes"] = () => detail;
    renderAt("/complaints/c1");
    expect(await screen.findByText("Please check")).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText("Note for the customer"), "Supervisor booked");
    await userEvent.click(screen.getByRole("button", { name: "Add note" }));
    await waitFor(() => expect(calls.some((c) =>
      c.url.endsWith("/notes") && (c.body as { note: string }).note === "Supervisor booked")).toBe(true));
    await choose("Set status", "In progress");
    await userEvent.click(screen.getByRole("button", { name: "Change status" }));
    await confirmWith("Change status");
    await waitFor(() => expect(calls.some((c) =>
      c.url.endsWith("/status") && (c.body as { status: string }).status === "In progress")).toBe(true));
  });
});

describe("feedback", () => {
  it("shows ratings tag counts and check-in averages", async () => {
    handlers["/v1/admin/feedback"] = () => [];
    handlers["/v1/admin/support/options"] = () => [];
    handlers["/v1/admin/ratings"] = () => ({
      count: 2, average: 4.5, tag_counts: {},
      items: [
        { visit_id: "v1", rating: 5, tags: ["Polite"], comment: "", testimonial_permission: true,
          created_at: "2026-10-10T05:00:00Z", society: "Green Park" },
        { visit_id: "v2", rating: 4, tags: ["Polite", "On time"], comment: "", testimonial_permission: false,
          created_at: "2026-10-10T05:00:00Z", society: "Green Park" },
      ],
    });
    handlers["/v1/admin/checkins"] = () => ({
      category_averages: {},
      items: [{ id: "k1", customer_name: "Asha", society: "Green Park", vehicle_label: "Swift",
        cycle_start: "2026-10-01", answers: [{ category: "Cleanliness", rating: 4 }],
        comment: "", created_at: "2026-10-10T05:00:00Z" }],
    });
    renderAt("/feedback");
    await userEvent.click(await screen.findByRole("tab", { name: "Ratings" }));
    expect(await screen.findByLabelText("Polite: 2")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("tab", { name: "Check-ins" }));
    expect(await screen.findByLabelText("Cleanliness: 4.00")).toBeInTheDocument();
  });

  it("adds and deactivates a category", async () => {
    handlers["/v1/admin/feedback"] = () => [];
    const opt = { id: "o1", kind: "feedback_category", name: "Timing", description: "",
      sort_order: 1, active: true };
    handlers["/v1/admin/support/options"] = (m) => (m === "POST" ? { ...opt, id: "o2" } : [opt]);
    handlers["/v1/admin/support/options/o1"] = () => ({ ...opt, active: false });
    renderAt("/feedback");
    await userEvent.click(await screen.findByRole("tab", { name: "Categories and tags" }));
    expect(await screen.findByText("Timing")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Deactivate" }));
    await confirmWith("Deactivate");
    await waitFor(() => expect(calls.some((c) =>
      c.method === "PATCH" && (c.body as { active: boolean }).active === false)).toBe(true));
    await userEvent.type(screen.getByLabelText("New name"), "Safety");
    await userEvent.click(screen.getByRole("button", { name: "Add" }));
    await waitFor(() => expect(calls.some((c) =>
      c.method === "POST" && (c.body as { name: string }).name === "Safety")).toBe(true));
  });
});
