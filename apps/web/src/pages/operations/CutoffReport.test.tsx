import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { ToastProvider } from "../../components";
import { withSite } from "../../site/testSite";
import { PortalProviders } from "../../test/portal";
import { OperationsPage } from "./OperationsPage";

const fetchMock = vi.fn();
beforeEach(() => {
  vi.stubGlobal("fetch", fetchMock);
  fetchMock.mockImplementation(async (path: string) => new Response(JSON.stringify(
    path.includes("/cutoff-report") ? {
      as_of: "2026-11-15",
      rows: [{ vehicle_id: "v1", customer_name: "Asha Rao", model: "Hyundai Creta", registration: "HR01ZZ1234",
        exterior_cutoff: "08:30", interior_preferred_day: "Sunday" },
      { vehicle_id: "v2", customer_name: "Vikram Shah", model: "Tata Nexon", registration: "HR26AB9999",
        exterior_cutoff: "", interior_preferred_day: "" }],
    } : [])));
});
afterEach(() => { vi.unstubAllGlobals(); fetchMock.mockReset(); });

it("shows the Cutoff reports tab as a table of cutoff and Interior day per vehicle", async () => {
  render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
    <MemoryRouter><ToastProvider><PortalProviders>{withSite(<OperationsPage />)}</PortalProviders></ToastProvider></MemoryRouter>
  </QueryClientProvider>);
  await userEvent.click(await screen.findByRole("tab", { name: "Cutoff reports" }));
  const table = await screen.findByRole("table", { name: "Cutoff report" });
  expect(table).toHaveTextContent("Ext cutoff time");
  expect(table).toHaveTextContent("INT preferred day");
  expect(table).toHaveTextContent("Asha RaoHyundai CretaHR01ZZ123408:30Sunday");
  expect(table).toHaveTextContent("Vikram ShahTata NexonHR26AB9999--");
  await userEvent.type(screen.getByRole("searchbox"), "vikram");
  expect(table).not.toHaveTextContent("Asha Rao");
});
