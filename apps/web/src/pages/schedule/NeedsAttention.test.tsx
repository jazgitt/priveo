import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ToastProvider } from "../../components";
import { choose, PortalProviders } from "../../test/portal";
import { withSite } from "../../site/testSite";
import { NeedsAttention } from "./NeedsAttention";

const fetchMock = vi.fn();

function json(status: number, body?: unknown) {
  return new Response(body === undefined ? null : JSON.stringify(body), { status });
}

function wrap(ui: ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}><MemoryRouter initialEntries={["/schedule"]}><ToastProvider><PortalProviders>
      {withSite(ui, "s1", "Palm Grove")}
    </PortalProviders></ToastProvider></MemoryRouter></QueryClientProvider>,
  );
}

const car = (over: Record<string, unknown> = {}) => ({
  subscription_id: "sub1", vehicle_id: "veh1", registration: "KA01AB1234", customer_name: "Meena Rao",
  vehicle: "Honda City", plan_name: "Premium", ...over,
});

/** The cars the endpoint lists; the test changes it when a save succeeds. */
let missing: ReturnType<typeof car>[] = [];

beforeEach(() => {
  vi.stubGlobal("fetch", fetchMock);
  missing = [car(), car({ subscription_id: "sub2", vehicle_id: "veh2", registration: "KA02CD5678", customer_name: "Asha Iyer" })];
  fetchMock.mockImplementation(async (path: string, init?: RequestInit) => {
    const url = String(path);
    if (url.startsWith("/v1/admin/scheduling/interior-day-missing")) return json(200, missing);
    if (url.startsWith("/v1/admin/subscriptions/sub1") && init?.method === "PATCH") {
      missing = missing.filter((c) => c.subscription_id !== "sub1");
      return json(200, { updated: true, pending_from: null });
    }
    return json(404, { code: "not_found", message: "no", fields: {}, request_id: "" });
  });
});

afterEach(() => {
  vi.unstubAllGlobals();
  fetchMock.mockReset();
});

const patchCalls = () => fetchMock.mock.calls.filter(([p, init]) =>
  String(p).startsWith("/v1/admin/subscriptions/") && (init as RequestInit | undefined)?.method === "PATCH");

describe("Needs Attention (cars with no preferred Interior day)", () => {
  it("lists the cars with no Interior day, with their text in red", async () => {
    wrap(<NeedsAttention societyId="s1" />);
    const card = await screen.findByRole("button", { name: "Set the Interior day for KA01AB1234" });
    expect(card).toHaveClass("text-destructive");
    expect(within(card).getByText("KA01AB1234")).toBeInTheDocument();
    expect(card).toHaveTextContent("Meena Rao, Premium. No Interior day set.");
    expect(screen.getByRole("button", { name: "Set the Interior day for KA02CD5678" })).toHaveClass("text-destructive");
  });

  it("says so when every car on Interior care has its day", async () => {
    missing = [];
    wrap(<NeedsAttention societyId="s1" />);
    expect(await screen.findByText("Every car on Interior care has its preferred day.")).toBeInTheDocument();
  });

  it("asks for the site first and does not call the endpoint without one", async () => {
    wrap(<NeedsAttention societyId="" />);
    expect(await screen.findByText("Choose a site")).toBeInTheDocument();
    expect(fetchMock.mock.calls.some(([p]) => String(p).startsWith("/v1/admin/scheduling/interior-day-missing"))).toBe(false);
  });

  it("opens the set-day control when a car is clicked, and saves the chosen day", async () => {
    wrap(<NeedsAttention societyId="s1" />);
    await userEvent.click(await screen.findByRole("button", { name: "Set the Interior day for KA01AB1234" }));
    const dialog = await screen.findByRole("dialog");
    expect(within(dialog).getByText("Interior day for KA01AB1234")).toBeInTheDocument();
    const save = within(dialog).getByRole("button", { name: "Save Interior day" });
    expect(save).toBeDisabled();
    await choose("Interior care day", "Monday");
    expect(save).toBeEnabled();
    await userEvent.click(save);
    expect(patchCalls()).toHaveLength(1);
    expect(JSON.parse(String(patchCalls()[0][1]!.body))).toEqual({ interior_day: "Monday" });
    // The confirmation says the day is set and that the next run considers it.
    expect(await screen.findByText("KA01AB1234: Interior day set to Monday. It is considered in the next run.")).toBeInTheDocument();
    // The car leaves the list once the list is read again.
    await screen.findByRole("button", { name: "Set the Interior day for KA02CD5678" });
    expect(screen.queryByRole("button", { name: "Set the Interior day for KA01AB1234" })).not.toBeInTheDocument();
  });

  it("asks for notes with Custom and sends them with the day", async () => {
    wrap(<NeedsAttention societyId="s1" />);
    await userEvent.click(await screen.findByRole("button", { name: "Set the Interior day for KA01AB1234" }));
    const dialog = await screen.findByRole("dialog");
    await choose("Interior care day", "Custom");
    await userEvent.type(within(dialog).getByLabelText(/Interior day notes/), "Alternate weeks with the blue car");
    await userEvent.click(within(dialog).getByRole("button", { name: "Save Interior day" }));
    await screen.findByText(/KA01AB1234: Interior day set to Custom/);
    expect(JSON.parse(String(patchCalls()[0][1]!.body))).toEqual({
      interior_day: "Custom", interior_day_notes: "Alternate weeks with the blue car",
    });
  });
});
