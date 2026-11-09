import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { withSite } from "../../site/testSite";
import { toIso } from "../schedule/api";
import { CapacityPage } from "./CapacityPage";

const fetchMock = vi.fn();
const day = (date: string, capacity: number, demand: number, over: boolean) => ({
  date, capacity_minutes: capacity, demand_minutes: demand, scheduled_minutes: demand, over_capacity: over, crew: [], demand: [],
});
// The server orders the list: Exteriors by cutoff, then Interiors by cutoff, then the other services by cutoff.
const due = [
  { group: "EXT", service: "Cleaning-External", service_label: "Exterior", vehicle_id: "v-2", registration: "TEST-B", vehicle: "Car B", cutoff: "08:00", source: "Subscription" },
  { group: "EXT", service: "Cleaning-External", service_label: "Exterior", vehicle_id: "v-1", registration: "TEST-A", vehicle: "Car A", cutoff: "10:00", source: "Subscription" },
  { group: "INT", service: "Cleaning-Internal", service_label: "Interior", vehicle_id: "v-3", registration: "TEST-C", vehicle: "Car C", cutoff: "09:00", source: "Subscription" },
  { group: "Other", service: "Deep Spa", service_label: "Deep Spa", vehicle_id: "v-4", registration: "TEST-D", vehicle: "Car D", cutoff: null, source: "Add-on" },
];

beforeEach(() => {
  fetchMock.mockImplementation(async (path: string) => {
    if (path.startsWith("/v1/admin/scheduling/capacity")) {
      return new Response(JSON.stringify([day("2026-10-25", 600, 300, false), day("2026-10-26", 300, 600, true)]), { status: 200 });
    }
    if (path.startsWith("/v1/admin/scheduling/demand")) {
      return new Response(JSON.stringify(due), { status: 200 });
    }
    return new Response(JSON.stringify([]), { status: 200 });
  });
  vi.stubGlobal("fetch", fetchMock);
});
afterEach(() => { fetchMock.mockReset(); vi.unstubAllGlobals(); });

const renderPage = () => {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(<QueryClientProvider client={qc}>{withSite(<CapacityPage />)}</QueryClientProvider>);
};

it("is called Capacity Utilisation, shows summary tiles and no crew list", async () => {
  renderPage();
  expect(screen.getByRole("heading", { name: "Capacity Utilisation" })).toBeInTheDocument();
  const tiles = await screen.findByRole("region", { name: "Capacity summary" });
  expect(await within(tiles).findByText("Days shown")).toBeInTheDocument();
  expect(within(tiles).getByText("Days over capacity").nextElementSibling).toHaveTextContent("1");
  expect(within(tiles).getByText("Overall use").nextElementSibling).toHaveTextContent("100%");
  expect(within(tiles).getByText(/Busiest day 200%/)).toBeInTheDocument();
  expect(screen.queryByText("Crew")).not.toBeInTheDocument();
  expect(screen.queryByText(/Trainees add no capacity/)).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Tiles" })).not.toBeInTheDocument();
  expect(fetchMock.mock.calls.some((c) => String(c[0]).startsWith("/v1/admin/crew"))).toBe(false);
});

it("starts the default range on today, not the next Sunday (P3-2.1)", async () => {
  renderPage();
  await screen.findByRole("region", { name: "Capacity summary" });
  const capacityCall = fetchMock.mock.calls.map((c) => String(c[0])).find((p) => p.startsWith("/v1/admin/scheduling/capacity"));
  expect(capacityCall).toBeDefined();
  expect(capacityCall).toContain(`start_date=${toIso(new Date())}`);
  expect(capacityCall).toContain("days=7");
});

it("opens the Demand tab from a demand figure and lists the day's jobs in the server order (P3-2.2)", async () => {
  renderPage();
  await screen.findByRole("region", { name: "Capacity summary" });
  await userEvent.click(screen.getByRole("button", { name: /Show jobs due on .* 25-Oct-26/ }));

  expect(screen.getByRole("tab", { name: "Demand" })).toHaveAttribute("aria-selected", "true");
  const demandCall = fetchMock.mock.calls.map((c) => String(c[0])).find((p) => p.startsWith("/v1/admin/scheduling/demand"));
  expect(demandCall).toContain("date=2026-10-25");
  expect(demandCall).toContain("society_id=");
  expect(demandCall).not.toContain("service=");

  await screen.findByText("TEST-B");
  const rows = screen.getAllByRole("row").slice(1);
  const text = rows.map((r) => r.textContent ?? "");
  const order = ["TEST-B", "TEST-A", "TEST-C", "TEST-D"].map((reg) => text.findIndex((t) => t.includes(reg)));
  expect(order.every((i) => i >= 0)).toBe(true);
  expect([...order].sort((a, b) => a - b)).toEqual(order);
  expect(text[2]).toContain("Interior");
});

it("searches the Demand list by registration and keeps each job's place in the day's order", async () => {
  renderPage();
  await screen.findByRole("region", { name: "Capacity summary" });
  await userEvent.click(screen.getByRole("button", { name: /Show jobs due on .* 25-Oct-26/ }));
  await screen.findByText("TEST-C");
  await userEvent.type(screen.getByRole("searchbox"), "TEST-C");

  const rows = screen.getAllByRole("row").slice(1);
  expect(rows).toHaveLength(1);
  expect(rows[0]).toHaveTextContent("TEST-C");
  expect(rows[0].textContent?.startsWith("3")).toBe(true);
});

it("sends the service filter to the server when one is chosen", async () => {
  renderPage();
  await screen.findByRole("region", { name: "Capacity summary" });
  await userEvent.click(screen.getByRole("button", { name: /Show jobs due on .* 25-Oct-26/ }));
  await screen.findByText("TEST-B");
  const demandCalls = () => fetchMock.mock.calls.map((c) => String(c[0])).filter((p) => p.startsWith("/v1/admin/scheduling/demand"));
  expect(demandCalls().some((p) => p.includes("service="))).toBe(false);
  await userEvent.click(screen.getByRole("combobox", { name: "Service" }));
  await userEvent.click(await screen.findByRole("option", { name: "Interior" }));
  await vi.waitFor(() => expect(demandCalls().some((p) => p.includes("service=Cleaning-Internal"))).toBe(true));
});
