import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ToastProvider } from "../../components";
import { withSite } from "../../site/testSite";
import { choose, confirmWith, PortalProviders } from "../../test/portal";
import { allowedMoves } from "./api";
import { SubscriptionsPage } from "./SubscriptionsPage";

const fetchMock = vi.fn();

function json(status: number, body?: unknown) {
  return new Response(body === undefined ? null : JSON.stringify(body), { status });
}
const err = (status: number, message: string) => json(status, { code: "x", message, fields: {}, request_id: "" });

const row = (over: Record<string, unknown> = {}) => ({
  subscription_id: "s1", vehicle_id: "v1", customer_name: "Asha Rao", flat: "B-12",
  society: "Lake View", vehicle: "Swift KA01", plan_name: "Daily", status: "Activating",
  first_service_date: null, renewal_date: null, ...over,
});
let rows = [row()];

function server(extra: (p: string, init?: RequestInit) => Response | undefined = () => undefined) {
  fetchMock.mockImplementation(async (p: string, init?: RequestInit) => {
    const hit = extra(p, init);
    if (hit) return hit;
    if (p.startsWith("/v1/admin/subscriptions?")) return json(200, rows);
    if (p.endsWith("/events")) return json(200, [{ from_status: "Inactive", to_status: "Activating", by: "Admin", reason: "Came back", at: "2026-10-01T05:00:00Z" }]);
    if (p === "/v1/admin/vehicles/v1/changes") {
      return json(200, { vehicle_id: "v1", renewal_date: null,
        skips: [{ id: "k1", kind: "skip", status: "Scheduled", start_date: "2026-11-03", end_date: "2026-11-03", days: 1, actor: "customer" }],
        pauses: [{ id: "q1", kind: "pause", status: "Scheduled", start_date: "2026-11-10", end_date: "2026-11-12", days: 3, actor: "admin" }] });
    }
    if (init?.method && init.method !== "GET") return json(200, {});
    return err(404, "Not found.");
  });
}

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}><MemoryRouter><ToastProvider><PortalProviders>
      {withSite(<SubscriptionsPage />)}
    </PortalProviders></ToastProvider></MemoryRouter></QueryClientProvider>,
  );
}
const sent = (method: string, path: string) => fetchMock.mock.calls.filter((c) => c[0] === path && c[1]?.method === method);

beforeEach(() => { rows = [row()]; vi.stubGlobal("fetch", fetchMock); });
afterEach(() => { fetchMock.mockReset(); vi.unstubAllGlobals(); });

describe("subscriptions", () => {
  it("allows only the moves the API accepts", () => {
    expect(allowedMoves("Active")).toEqual(["Inactive"]);
    expect(allowedMoves("Inactive")).toEqual(["Activating"]);
    expect(allowedMoves("Activating")).toEqual(["Inactive", "Active"]);
  });

  it("lists the site's subscriptions, filters by status on the server and searches in the page", async () => {
    rows = [row(), row({ subscription_id: "s2", vehicle_id: "v2", customer_name: "Ravi Kumar", vehicle: "Creta HR01" })];
    server();
    renderPage();
    expect(await screen.findByText("Asha Rao")).toBeInTheDocument();
    await waitFor(() => expect(fetchMock.mock.calls.some((c) => String(c[0]).includes("society_id=s1"))).toBe(true));
    await userEvent.type(screen.getByLabelText("Search subscriptions"), "creta");
    expect(screen.queryByText("Asha Rao")).not.toBeInTheDocument();
    expect(screen.getByText("Ravi Kumar")).toBeInTheDocument();
    await choose("Status", "Inactive");
    await waitFor(() => expect(fetchMock.mock.calls.some((c) => String(c[0]).includes("status=Inactive"))).toBe(true));
  });

  it("activates with a first service date and shows the history", async () => {
    server();
    renderPage();
    await userEvent.click(await screen.findByRole("button", { name: "Manage" }));
    const panel = await screen.findByRole("dialog");
    expect(await within(panel).findByText("Came back")).toBeInTheDocument();
    await choose("New status", "Active");
    const activate = within(panel).getByRole("button", { name: "Activate" });
    expect(activate).toBeDisabled();
    fireEvent.change(within(panel).getByLabelText("First service date"), { target: { value: "2026-11-10" } });
    await userEvent.click(activate);
    await waitFor(() => expect(JSON.parse(sent("PUT", "/v1/admin/subscriptions/s1/status")[0][1].body)).toEqual({
      status: "Active", reason: "", first_service_date: "2026-11-10",
    }));
  });

  it("requires a reason for Inactive and shows the API error", async () => {
    rows = [row({ status: "Active" })];
    server((p, init) => (p.endsWith("/status") && init?.method === "PUT" ? err(409, "A subscription cannot go from Active to Inactive.") : undefined));
    renderPage();
    await userEvent.click(await screen.findByRole("button", { name: "Manage" }));
    const panel = await screen.findByRole("dialog");
    const save = within(panel).getByRole("button", { name: "Make inactive" });
    expect(save).toBeDisabled();
    await userEvent.type(within(panel).getByLabelText("Reason"), "Moved away");
    await userEvent.click(save);
    expect(await screen.findByText(/cannot go from Active/)).toBeInTheDocument();
  });

  it("skips and pauses for the customer, and confirms before removing one", async () => {
    server();
    renderPage();
    await userEvent.click(await screen.findByRole("button", { name: "Manage" }));
    const panel = await screen.findByRole("dialog");
    fireEvent.change(await within(panel).findByLabelText("Skip date"), { target: { value: "2026-11-12" } });
    await userEvent.click(within(panel).getByRole("button", { name: "Skip this day" }));
    await waitFor(() => expect(JSON.parse(sent("POST", "/v1/admin/vehicles/v1/skips")[0][1].body)).toEqual({ date: "2026-11-12" }));
    fireEvent.change(within(panel).getByLabelText("Pause from"), { target: { value: "2026-11-20" } });
    fireEvent.change(within(panel).getByLabelText("Pause to"), { target: { value: "2026-11-22" } });
    await userEvent.click(within(panel).getByRole("button", { name: "Pause" }));
    await waitFor(() => expect(JSON.parse(sent("POST", "/v1/admin/vehicles/v1/pauses")[0][1].body)).toEqual({ from_date: "2026-11-20", to_date: "2026-11-22" }));
    await userEvent.click(within(panel).getByRole("button", { name: "Remove skip" }));
    await confirmWith("Remove skip");
    await waitFor(() => expect(sent("DELETE", "/v1/admin/vehicles/v1/skips/k1")).toHaveLength(1));
    await userEvent.click(within(panel).getByRole("button", { name: "End pause" }));
    await confirmWith("End pause");
    await waitFor(() => expect(sent("DELETE", "/v1/admin/vehicles/v1/pauses/q1")).toHaveLength(1));
  });

  it("shows a list error with a retry", async () => {
    fetchMock.mockImplementation(async () => err(500, "The server failed."));
    renderPage();
    expect(await screen.findByText("The server failed.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Try again" })).toBeInTheDocument();
  });
});
