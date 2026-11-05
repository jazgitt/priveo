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

async function typeSearch(value: string) {
  const box = screen.getByLabelText("Search");
  await userEvent.clear(box);
  if (value) await userEvent.type(box, value);
  return box;
}

it("does not ask while typing, and the button waits for 3 characters [ADM-SET-09]", async () => {
  renderPage();
  await screen.findByText("1-50 of 120 · Page 1 of 3");
  const before = listCalls().length;
  expect(screen.queryByLabelText("Actor ID")).not.toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Search" })).toBeDisabled();
  await typeSearch("ab");
  expect(screen.getByText("Type at least 3 characters")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Search" })).toBeDisabled();
  await userEvent.type(screen.getByLabelText("Search"), "c");
  expect(screen.getByRole("button", { name: "Search" })).toBeEnabled();
  await new Promise((r) => setTimeout(r, 50));
  expect(listCalls()).toHaveLength(before);
});

it("asks with q when the Search button is pressed, from the first page [ADM-SET-09]", async () => {
  renderPage();
  await screen.findByText("1-50 of 120 · Page 1 of 3");
  await userEvent.click(screen.getByRole("button", { name: "Next" }));
  await screen.findByText("51-100 of 120 · Page 2 of 3");
  await typeSearch("  gold  ");
  await userEvent.click(screen.getByRole("button", { name: "Search" }));
  await waitFor(() => expect(lastUrl().searchParams.get("q")).toBe("gold"));
  expect(lastUrl().searchParams.get("offset")).toBe("0");
  expect(lastUrl().searchParams.get("society_id")).toBe("s1");
  expect(lastUrl().searchParams.has("actor_id")).toBe(false);
  expect(await screen.findByText("1-50 of 120 · Page 1 of 3")).toBeInTheDocument();
});

it("asks with q when Enter is pressed [ADM-SET-09]", async () => {
  renderPage();
  await screen.findByText("1-50 of 120 · Page 1 of 3");
  await typeSearch("plan{Enter}");
  await waitFor(() => expect(lastUrl().searchParams.get("q")).toBe("plan"));
});

it("does not ask on Enter under 3 characters [ADM-SET-09]", async () => {
  renderPage();
  await screen.findByText("1-50 of 120 · Page 1 of 3");
  const before = listCalls().length;
  await typeSearch("ab{Enter}");
  await new Promise((r) => setTimeout(r, 50));
  expect(listCalls()).toHaveLength(before);
});

it("keeps the search with the other filters and with paging [ADM-SET-09]", async () => {
  renderPage();
  await screen.findByText("1-50 of 120 · Page 1 of 3");
  fireEvent.change(screen.getByLabelText("From date"), { target: { value: "2026-10-01" } });
  await waitFor(() => expect(lastUrl().searchParams.get("date_from")).toBe("2026-10-01"));
  await typeSearch("gold{Enter}");
  await waitFor(() => expect(lastUrl().searchParams.get("q")).toBe("gold"));
  expect(lastUrl().searchParams.get("date_from")).toBe("2026-10-01");
  await userEvent.click(screen.getByRole("button", { name: "Next" }));
  await waitFor(() => expect(lastUrl().searchParams.get("offset")).toBe("50"));
  expect(lastUrl().searchParams.get("q")).toBe("gold");
});

it("Clear drops the search and loads again [ADM-SET-09]", async () => {
  renderPage();
  await screen.findByText("1-50 of 120 · Page 1 of 3");
  await typeSearch("gold{Enter}");
  await waitFor(() => expect(lastUrl().searchParams.get("q")).toBe("gold"));
  await userEvent.click(screen.getByRole("button", { name: "Clear" }));
  await waitFor(() => expect(lastUrl().searchParams.has("q")).toBe(false));
  expect(screen.getByLabelText("Search")).toHaveValue("");
  expect(lastUrl().searchParams.get("offset")).toBe("0");
});

it("says so when a search finds nothing [ADM-SET-09]", async () => {
  fetchMock.mockImplementation(async () => new Response(JSON.stringify({ items: [], total: 0, limit: 50, offset: 0 }), { status: 200 }));
  renderPage();
  await screen.findByText("No changes recorded for this site or for all sites");
  await typeSearch("zzz{Enter}");
  expect(await screen.findByText('No changes match "zzz"')).toBeInTheDocument();
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
