import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { ToastProvider } from "../../components";
import { withSite } from "../../site/testSite";
import { choose, PortalProviders } from "../../test/portal";
import { currentMonth } from "./monthRange";
import { OperationsPage } from "./OperationsPage";

const fetchMock = vi.fn();
beforeEach(() => {
  vi.stubGlobal("fetch", fetchMock);
  fetchMock.mockImplementation(async (path: string) => new Response(JSON.stringify(
    path.includes("/job-status-report") ? {
      dates: ["2026-11-14", "2026-11-15"],
      rows: [{ vehicle_id: "v1", registration: "HR01ZZ1234", customer_name: "Asha Rao",
        cells: { "2026-11-14": "Both", "2026-11-15": "EXT" } },
      { vehicle_id: "v2", registration: "HR26AB9999", customer_name: "Vikram Shah",
        cells: { "2026-11-15": "INT" } }],
    } : [])));
});
afterEach(() => { vi.unstubAllGlobals(); fetchMock.mockReset(); });

it("shows the Reports tab as a vehicle by date grid of completed services", async () => {
  render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
    <MemoryRouter><ToastProvider><PortalProviders>{withSite(<OperationsPage />)}</PortalProviders></ToastProvider></MemoryRouter>
  </QueryClientProvider>);
  await userEvent.click(await screen.findByRole("tab", { name: "Completed" }));
  const table = await screen.findByRole("table", { name: "Job completion by day" });
  expect(table).toHaveTextContent("HR01ZZ1234");
  expect(table).toHaveTextContent("Asha Rao");
  expect(table).not.toHaveTextContent("Type");
  expect(table).toHaveTextContent("Both");
  expect(table).toHaveTextContent("EXT");
  expect(fetchMock.mock.calls.some(([p]) => String(p).includes("/operations/jobs?queue=reports"))).toBe(false);
});

it("filters the grid by customer or vehicle search and by service done", async () => {
  render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
    <MemoryRouter><ToastProvider><PortalProviders>{withSite(<OperationsPage />)}</PortalProviders></ToastProvider></MemoryRouter>
  </QueryClientProvider>);
  await userEvent.click(await screen.findByRole("tab", { name: "Completed" }));
  const table = await screen.findByRole("table", { name: "Job completion by day" });
  expect(table).toHaveTextContent("Vikram Shah");
  await userEvent.type(screen.getByLabelText("Search"), "asha");
  expect(table).not.toHaveTextContent("Vikram Shah");
  expect(table).toHaveTextContent("Asha Rao");
  await userEvent.clear(screen.getByLabelText("Search"));
  await userEvent.type(screen.getByLabelText("Search"), "hr26");
  expect(table).toHaveTextContent("HR26AB9999");
  expect(table).not.toHaveTextContent("Asha Rao");
  await userEvent.clear(screen.getByLabelText("Search"));
  await choose("Service done", "Interior done");
  expect(table).toHaveTextContent("Vikram Shah");
  expect(table).toHaveTextContent("Asha Rao");
  await choose("Service done", "Exterior and Interior both done");
  expect(table).not.toHaveTextContent("Vikram Shah");
});

it("pages the grid 20 vehicles at a time", async () => {
  fetchMock.mockImplementation(async (path: string) => new Response(JSON.stringify(path.includes("/job-status-report") ? {
    dates: ["2026-11-14"],
    rows: Array.from({ length: 45 }, (_, i) => ({ vehicle_id: `v${i}`, registration: `HR01AA${String(i).padStart(4, "0")}`,
      customer_name: `Customer ${i}`, cells: { "2026-11-14": "EXT" } })),
  } : [])));
  render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
    <MemoryRouter><ToastProvider><PortalProviders>{withSite(<OperationsPage />)}</PortalProviders></ToastProvider></MemoryRouter>
  </QueryClientProvider>);
  await userEvent.click(await screen.findByRole("tab", { name: "Completed" }));
  const table = await screen.findByRole("table", { name: "Job completion by day" });
  expect(screen.getByText(/1-20 of 45/)).toBeInTheDocument();
  expect(table.querySelectorAll("tbody tr")).toHaveLength(20);
  await userEvent.click(screen.getByRole("button", { name: "Next" }));
  await userEvent.click(screen.getByRole("button", { name: "Next" }));
  expect(screen.getByText(/41-45 of 45/)).toBeInTheDocument();
  expect(table.querySelectorAll("tbody tr")).toHaveLength(5);
  await userEvent.type(screen.getByLabelText("Search"), "Customer 7");
  expect(screen.getByText(/1-1 of 1/)).toBeInTheDocument();
});

it("opens on the first to the last day of the current month", async () => {
  const { from, to } = currentMonth();
  render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
    <MemoryRouter><ToastProvider><PortalProviders>{withSite(<OperationsPage />)}</PortalProviders></ToastProvider></MemoryRouter>
  </QueryClientProvider>);
  await userEvent.click(await screen.findByRole("tab", { name: "Completed" }));
  await screen.findByRole("table", { name: "Job completion by day" });
  expect(screen.getByLabelText("From date")).toHaveValue(from);
  expect(screen.getByLabelText("To date")).toHaveValue(to);
  expect(fetchMock.mock.calls.some(([p]) => String(p).includes(`date_from=${from}&date_to=${to}`))).toBe(true);
  expect(currentMonth(new Date(2026, 1, 10))).toEqual({ from: "2026-02-01", to: "2026-02-28" });
});
