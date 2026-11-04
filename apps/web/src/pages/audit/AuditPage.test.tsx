import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { SiteContext, type Site } from "../../site/SiteContext";
import { AuditPage, PAGE_SIZE } from "./AuditPage";

const fetchMock = vi.fn();
const entry = (i: number) => ({
  id: `e${i}`, at: "2026-10-10T05:00:00Z", admin_login_id: null, entity: "plan",
  entity_id: `0000000${i}-aaaa`, action: "update", detail: { price: [100 + i, 200 + i] },
});
const TOTAL = 120;
const listCalls = () => fetchMock.mock.calls.filter((c) => String(c[0]).startsWith("/v1/admin/directory/audit"));
const lastUrl = () => new URL(String(listCalls().at(-1)![0]), "http://x");

const site = (id: string, name: string): Site => ({ id, name, sites: [{ id: "s1", name: "Lake View" }, { id: "s2", name: "Park" }], select: () => {} });

function Page({ s }: { s: Site }) {
  return <SiteContext.Provider value={s}><AuditPage /></SiteContext.Provider>;
}

function renderPage(s = site("s1", "Lake View")) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false, refetchInterval: 30_000 } } });
  const ui = (x: Site) => <QueryClientProvider client={qc}><Page s={x} /></QueryClientProvider>;
  const out = render(ui(s));
  return { ...out, setSite: (x: Site) => out.rerender(ui(x)) };
}

beforeEach(() => {
  // The server pages: it answers with the rows of the asked page and the total.
  fetchMock.mockImplementation(async (path: string) => {
    const u = new URL(path, "http://x");
    const offset = Number(u.searchParams.get("offset") ?? 0);
    const limit = Number(u.searchParams.get("limit") ?? 50);
    const items = Array.from({ length: Math.max(0, Math.min(limit, TOTAL - offset)) }, (_, i) => entry(offset + i));
    return new Response(JSON.stringify({ items, total: TOTAL, limit, offset }), { status: 200 });
  });
  vi.stubGlobal("fetch", fetchMock);
});
afterEach(() => { fetchMock.mockReset(); vi.unstubAllGlobals(); });

it("is called Audit trail and asks for the chosen site only", async () => {
  renderPage();
  expect(await screen.findByRole("heading", { name: "Audit trail" })).toBeInTheDocument();
  await screen.findByText("1-50 of 120 · Page 1 of 3");
  expect(lastUrl().searchParams.get("society_id")).toBe("s1");
});

it("shows 50 events a page and asks the server for each page", async () => {
  renderPage();
  expect(await screen.findByText("1-50 of 120 · Page 1 of 3")).toBeInTheDocument();
  expect(PAGE_SIZE).toBe(50);
  expect(lastUrl().searchParams.get("limit")).toBe("50");
  expect(lastUrl().searchParams.get("offset")).toBe("0");
  expect(screen.getAllByRole("row")).toHaveLength(51); // the header and 50 events
  expect(screen.getByRole("button", { name: "Previous" })).toBeDisabled();
  await userEvent.click(screen.getByRole("button", { name: "Next" }));
  expect(await screen.findByText("51-100 of 120 · Page 2 of 3")).toBeInTheDocument();
  expect(lastUrl().searchParams.get("offset")).toBe("50");
  await userEvent.click(screen.getByRole("button", { name: "Next" }));
  expect(await screen.findByText("101-120 of 120 · Page 3 of 3")).toBeInTheDocument();
  expect(screen.getAllByRole("row")).toHaveLength(21); // the header and 20 events
  expect(screen.getByRole("button", { name: "Next" })).toBeDisabled();
  await userEvent.click(screen.getByRole("button", { name: "Previous" }));
  expect(await screen.findByText("51-100 of 120 · Page 2 of 3")).toBeInTheDocument();
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

it("Refresh from a later page goes back to the first page", async () => {
  renderPage();
  await screen.findByText("1-50 of 120 · Page 1 of 3");
  await userEvent.click(screen.getByRole("button", { name: "Next" }));
  await screen.findByText("51-100 of 120 · Page 2 of 3");
  await userEvent.click(screen.getByRole("button", { name: "Refresh" }));
  expect(await screen.findByText("1-50 of 120 · Page 1 of 3")).toBeInTheDocument();
  expect(lastUrl().searchParams.get("offset")).toBe("0");
});

it("asks again for a new filter, from the first page", async () => {
  renderPage();
  await screen.findByText("1-50 of 120 · Page 1 of 3");
  await userEvent.click(screen.getByRole("button", { name: "Next" }));
  await screen.findByText("51-100 of 120 · Page 2 of 3");
  fireEvent.change(screen.getByLabelText("Actor ID"), { target: { value: "abc" } });
  await waitFor(() => expect(lastUrl().searchParams.get("actor_id")).toBe("abc"));
  expect(lastUrl().searchParams.get("offset")).toBe("0");
  expect(lastUrl().searchParams.get("society_id")).toBe("s1");
  expect(await screen.findByText("1-50 of 120 · Page 1 of 3")).toBeInTheDocument();
});

it("goes back to the first page when the site changes", async () => {
  const { setSite } = renderPage();
  await screen.findByText("1-50 of 120 · Page 1 of 3");
  await userEvent.click(screen.getByRole("button", { name: "Next" }));
  await screen.findByText("51-100 of 120 · Page 2 of 3");
  setSite(site("s2", "Park"));
  await waitFor(() => expect(lastUrl().searchParams.get("society_id")).toBe("s2"));
  expect(lastUrl().searchParams.get("offset")).toBe("0");
  expect(await screen.findByText("1-50 of 120 · Page 1 of 3")).toBeInTheDocument();
});

it("says so when the site has no changes", async () => {
  fetchMock.mockImplementation(async () => new Response(JSON.stringify({ items: [], total: 0, limit: 50, offset: 0 }), { status: 200 }));
  renderPage();
  expect(await screen.findByText("No changes recorded for this site or for all sites")).toBeInTheDocument();
});

it("labels a change that applies to all sites", async () => {
  const rows = [
    { ...entry(1), id: "own", society_id: "s1" },
    { ...entry(2), id: "global", entity: "setting", entity_id: "billing.cycle_days", society_id: null },
  ];
  fetchMock.mockImplementation(async () => new Response(JSON.stringify({ items: rows, total: 2, limit: 50, offset: 0 }), { status: 200 }));
  renderPage();
  expect(await screen.findByText("All sites")).toBeInTheDocument();
  expect(screen.getAllByText("All sites")).toHaveLength(1); // the site's own row names the site instead
  expect(screen.getAllByRole("cell", { name: "Lake View" })).toHaveLength(1);
});
