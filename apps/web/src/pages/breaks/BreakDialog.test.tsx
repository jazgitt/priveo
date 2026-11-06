import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ConfirmProvider } from "../../blocks/confirm";
import { ToastProvider } from "../../components";
import { confirmWith } from "../../test/portal";
import { BreakDialog, cueDates } from "./BreakDialog";
import { BreakPanel, ruleInForce } from "./BreakPanel";

const TODAY = "2026-11-10";
const json = (status: number, body?: unknown) => new Response(JSON.stringify(body), { status });
const fetchMock = vi.fn();
const rule = (o: object) => ({
  id: "r1", society_id: "s1", crew_id: null, start_date: "2026-11-12", end_date: "2026-11-14",
  start_minute: null, end_minute: null, enabled: false, ...o,
});
const posts = () => fetchMock.mock.calls.filter(([, i]) => i?.method === "POST");

function wrap(ui: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}><ToastProvider><ConfirmProvider>{ui}</ConfirmProvider></ToastProvider></QueryClientProvider>);
}
const site = { start: 570, end: 600 };

beforeEach(() => vi.stubGlobal("fetch", fetchMock));
afterEach(() => { fetchMock.mockReset(); vi.unstubAllGlobals(); });

describe("cueDates", () => {
  it("Today and Tomorrow fill the dates, Date range keeps what was typed", () => {
    const typed = { from: "2026-12-01", to: "2026-12-05" };
    expect(cueDates("today", TODAY, typed)).toEqual({ from: TODAY, to: TODAY });
    expect(cueDates("tomorrow", TODAY, typed)).toEqual({ from: "2026-11-11", to: "2026-11-11" });
    expect(cueDates("range", TODAY, typed)).toEqual(typed);
  });
});

describe("BreakDialog", () => {
  beforeEach(() => fetchMock.mockImplementation(async () => json(201, rule({}))));
  const open = (crewId?: string) => wrap(
    <BreakDialog open onOpenChange={() => {}} societyId="s1" crewId={crewId} siteBreak={site} today={TODAY} invalidate={[["x"]]} />);

  it("starts on Today and Tomorrow moves the dates", async () => {
    open();
    expect(screen.getByLabelText("From date")).toHaveValue(TODAY);
    await userEvent.click(screen.getByRole("button", { name: "Tomorrow" }));
    expect(screen.getByLabelText("From date")).toHaveValue("2026-11-11");
    expect(screen.getByLabelText("To date")).toHaveValue("2026-11-11");
    expect(screen.getByLabelText("From date")).toBeDisabled();
  });

  it("saves a Date range for one cleaner; times equal to the site break follow the site", async () => {
    open("c1");
    await userEvent.click(screen.getByRole("button", { name: "Date range" }));
    fireEvent.change(screen.getByLabelText("From date"), { target: { value: "2026-11-12" } });
    fireEvent.change(screen.getByLabelText("To date"), { target: { value: "2026-11-14" } });
    await userEvent.click(screen.getByRole("button", { name: "Save break" }));
    await waitFor(() => expect(posts()).toHaveLength(1));
    expect(posts()[0][0]).toBe("/v1/admin/scheduling/break-rules");
    expect(JSON.parse(posts()[0][1].body)).toEqual({
      society_id: "s1", crew_id: "c1", start_date: "2026-11-12", end_date: "2026-11-14",
      start_minute: null, end_minute: null, enabled: true });
  });

  it("saves new times as minutes", async () => {
    open();
    fireEvent.change(screen.getByLabelText("Break starts"), { target: { value: "10:00" } });
    fireEvent.change(screen.getByLabelText("Break ends"), { target: { value: "10:30" } });
    await userEvent.click(screen.getByRole("button", { name: "Save break" }));
    await waitFor(() => expect(posts()).toHaveLength(1));
    expect(JSON.parse(posts()[0][1].body)).toMatchObject({ crew_id: null, start_minute: 600, end_minute: 630, enabled: true });
  });

  it("No break saves a switched-off rule without times", async () => {
    open();
    await userEvent.click(screen.getByRole("switch", { name: "No break on these dates" }));
    expect(screen.queryByLabelText("Break starts")).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Save break" }));
    await waitFor(() => expect(posts()).toHaveLength(1));
    expect(JSON.parse(posts()[0][1].body)).toMatchObject({ enabled: false, start_minute: null, end_minute: null });
  });

  it("refuses an end date before the start date", async () => {
    open();
    await userEvent.click(screen.getByRole("button", { name: "Date range" }));
    fireEvent.change(screen.getByLabelText("To date"), { target: { value: "2026-11-01" } });
    expect(await screen.findByRole("alert")).toHaveTextContent(/cannot be before/i);
    expect(screen.getByRole("button", { name: "Save break" })).toBeDisabled();
  });
});

describe("ruleInForce", () => {
  const r = (id: string, o: object) => rule({ id, ...o });
  it("a date for the cleaner beats a date for the site, which beats the cleaner's own rule", () => {
    const site_ = r("site", {});
    const crew = r("crew", { crew_id: "c1", start_date: null, end_date: null });
    const both = r("both", { crew_id: "c1" });
    expect(ruleInForce([site_, crew, both], "2026-11-13")?.id).toBe("both");
    expect(ruleInForce([site_, crew], "2026-11-13")?.id).toBe("site");
    expect(ruleInForce([site_, crew], "2026-11-20")?.id).toBe("crew");
    expect(ruleInForce([site_], "2026-11-20")).toBeNull();
  });
});

describe("BreakPanel", () => {
  const settings = [
    { key: "site.break_enabled", value: "true" }, { key: "site.break_start_minute", value: "570" },
    { key: "site.break_end_minute", value: "600" },
  ];
  beforeEach(() => fetchMock.mockImplementation(async (p: string, init?: RequestInit) => {
    if (init?.method === "DELETE") return new Response(null, { status: 204 });
    if (p.includes("site-settings")) return json(200, settings);
    return json(200, { scheduling_crew_id: "sc1", society_id: "s1", rules: [rule({}), rule({ id: "r2", crew_id: "sc1", enabled: true, start_minute: 600, end_minute: 630 })] });
  }));

  it("lists the rules and marks the one in force", async () => {
    wrap(<BreakPanel societyId="s1" crewMemberId="c1" today="2026-11-13" />);
    expect(await screen.findByText(/site break: 09:30 to 10:00/i)).toBeInTheDocument();
    expect(screen.getByText("No break")).toBeInTheDocument();
    expect(screen.getByText("10:00 to 10:30")).toBeInTheDocument();
    // Both cover 13-Nov-26; the cleaner's date rule is the most specific.
    const marks = screen.getAllByText("In force today");
    expect(marks).toHaveLength(1);
    expect(marks[0].closest("li")).toHaveTextContent("This cleaner");
  });

  it("asks before it deletes", async () => {
    wrap(<BreakPanel societyId="s1" crewMemberId="c1" today="2026-11-13" />);
    await screen.findByText("No break");
    await userEvent.click(screen.getAllByRole("button", { name: /Delete break rule/ })[0]);
    expect(fetchMock.mock.calls.some(([, i]) => i?.method === "DELETE")).toBe(false);
    await confirmWith("Delete rule");
    await waitFor(() => expect(fetchMock.mock.calls.some(([p, i]) => i?.method === "DELETE" && p === "/v1/admin/scheduling/break-rules/r1")).toBe(true));
  });
});
