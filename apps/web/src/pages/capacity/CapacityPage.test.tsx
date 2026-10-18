import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { withSite } from "../../site/testSite";
import { CapacityPage } from "./CapacityPage";

const fetchMock = vi.fn();
const day = (date: string, capacity: number, demand: number, over: boolean) => ({
  date, capacity_minutes: capacity, demand_minutes: demand, scheduled_minutes: demand, over_capacity: over, crew: [], demand: [],
});

beforeEach(() => {
  fetchMock.mockImplementation(async (path: string) => {
    if (path.startsWith("/v1/admin/scheduling/capacity")) {
      return new Response(JSON.stringify([day("2026-10-25", 600, 300, false), day("2026-10-26", 300, 600, true)]), { status: 200 });
    }
    return new Response(JSON.stringify([]), { status: 200 });
  });
  vi.stubGlobal("fetch", fetchMock);
});
afterEach(() => { fetchMock.mockReset(); vi.unstubAllGlobals(); });

it("is called Capacity Utilisation, shows summary tiles and no crew list", async () => {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(<QueryClientProvider client={qc}>{withSite(<CapacityPage />)}</QueryClientProvider>);
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
