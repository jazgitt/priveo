import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { AuditPage, MAX_EVENTS } from "./AuditPage";

const fetchMock = vi.fn();
const entry = (i: number) => ({
  id: `e${i}`, at: "2026-10-10T05:00:00Z", admin_login_id: null, entity: "plan",
  entity_id: `0000000${i}-aaaa`, action: "update", detail: { price: [100 + i, 200 + i] },
});
const listCalls = () => fetchMock.mock.calls.filter((c) => String(c[0]).startsWith("/v1/admin/directory/audit"));

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false, refetchInterval: 30_000 } } });
  return render(<QueryClientProvider client={qc}><AuditPage /></QueryClientProvider>);
}

beforeEach(() => {
  fetchMock.mockImplementation(async () => new Response(JSON.stringify(Array.from({ length: 120 }, (_, i) => entry(i))), { status: 200 }));
  vi.stubGlobal("fetch", fetchMock);
});
afterEach(() => { fetchMock.mockReset(); vi.unstubAllGlobals(); });

it("loads the last 1000 events once and pages them in the browser", async () => {
  renderPage();
  expect(await screen.findByText("1-50 of 120 · Page 1 of 3")).toBeInTheDocument();
  expect(String(listCalls()[0][0])).toContain(`limit=${MAX_EVENTS}`);
  expect(MAX_EVENTS).toBe(1000);
  expect(screen.getAllByRole("row")).toHaveLength(51); // the header and 50 events
  await userEvent.click(screen.getByRole("button", { name: "Next" }));
  expect(await screen.findByText("51-100 of 120 · Page 2 of 3")).toBeInTheDocument();
  expect(listCalls()).toHaveLength(1); // paging asks the server for nothing
});

it("tells the admin to refresh by hand and never reloads by itself", async () => {
  renderPage();
  expect(await screen.findByRole("note")).toHaveTextContent("does not update by itself");
  expect(screen.getByRole("note")).toHaveTextContent("Press Refresh");
  fireEvent.focus(window);
  window.dispatchEvent(new Event("visibilitychange"));
  window.dispatchEvent(new Event("online"));
  await new Promise((r) => setTimeout(r, 50));
  expect(listCalls()).toHaveLength(1);
  await userEvent.click(screen.getByRole("button", { name: "Refresh" }));
  await waitFor(() => expect(listCalls()).toHaveLength(2));
});

it("asks again for a new filter, from the first page", async () => {
  renderPage();
  await screen.findByText("1-50 of 120 · Page 1 of 3");
  await userEvent.click(screen.getByRole("button", { name: "Next" }));
  fireEvent.change(screen.getByLabelText("Actor ID"), { target: { value: "abc" } });
  await waitFor(() => expect(listCalls()).toHaveLength(2));
  expect(String(listCalls()[1][0])).toContain("actor_id=abc");
  expect(await screen.findByText("1-50 of 120 · Page 1 of 3")).toBeInTheDocument();
});
