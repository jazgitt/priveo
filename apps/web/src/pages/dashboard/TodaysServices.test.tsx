import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { choose } from "../../test/portal";
import { TodaysServices, type DaySummary } from "./TodaysServices";

const fetchMock = vi.fn();
const state = (count: number, items: DaySummary["pending"]["items"] = []) => ({ count, items, more: 0 });
const summary = (over: Partial<DaySummary> = {}): DaySummary => ({
  date: "2026-11-15", total: 4, pending: state(1), completed: state(1),
  missed: state(1, [{ id: "v1", registration: "HR01ZZ1234", crew: "Ravi", reason: "Car locked", time: "07:00" }]),
  partially_completed: state(1), skipped: state(0), rescheduled: state(0), cancelled: state(0), ...over,
});
let response: () => Response;
beforeEach(() => {
  vi.stubGlobal("fetch", fetchMock);
  response = () => new Response(JSON.stringify(summary()));
  fetchMock.mockImplementation(async (path: string) =>
    path.includes("/v1/admin/crew") ? new Response(JSON.stringify([{ id: "c1", name: "Ravi", role: "Member", active: true, society_id: "s1", society: "Meadows" }]))
      : response());
});
afterEach(() => { vi.unstubAllGlobals(); fetchMock.mockReset(); });
function page() {
  render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
    <MemoryRouter><TodaysServices /></MemoryRouter></QueryClientProvider>);
}
const summaryCalls = () => fetchMock.mock.calls.map(([p]) => String(p)).filter((p) => p.includes("day-summary"));

it("shows a tile for each state that links to the page that handles it", async () => {
  page();
  const missed = await screen.findByRole("link", { name: "Missed: 1" });
  expect(missed.getAttribute("href")).toBe("/operations?queue=missed&date_from=2026-11-15&date_to=2026-11-15");
  expect(screen.getByRole("link", { name: "Pending: 1" }).getAttribute("href")).toBe("/schedule?date=2026-11-15");
  expect(screen.getByRole("link", { name: "Partially completed: 1" }).getAttribute("href")).toContain("/operations?queue=missed");
  expect(screen.getByText(/Car locked/)).toBeTruthy();
});

it("sends the date, crew and vehicle filters", async () => {
  page();
  await screen.findByRole("link", { name: "Missed: 1" });
  await choose("Crew", "Ravi");
  await userEvent.type(screen.getByLabelText("Vehicle"), "HR01ZZ1234");
  await waitFor(() => expect(summaryCalls().some((p) => p.includes("crew_id=c1") && p.includes("registration=HR01ZZ1234"))).toBe(true));
});

it("says so when the day has no services", async () => {
  response = () => new Response(JSON.stringify(summary({ total: 0 })));
  page();
  expect(await screen.findByText("No services on this day.")).toBeTruthy();
});

it("shows an error with a retry", async () => {
  response = () => new Response(JSON.stringify({ message: "Boom" }), { status: 500 });
  page();
  expect(await screen.findByRole("alert")).toBeTruthy();
});
