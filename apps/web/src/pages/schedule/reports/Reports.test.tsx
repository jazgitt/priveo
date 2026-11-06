import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { collectSections } from ".";
import * as daily from "./DailySection";
import * as exceptions from "./ExceptionsSection";
import { weekStartOf } from "./shared";
import * as weekly from "./WeeklySection";

const json = (status: number, body?: unknown) => new Response(body === undefined ? null : JSON.stringify(body), { status });
const fetchMock = vi.fn();
// 11-Nov-26 is a Wednesday: its week starts on Sunday 08-Nov-26.
const DATE = "2026-11-11";

function show(module: { section: { component: React.ComponentType<{ societyId: string; date: string }> } }) {
  const Part = module.section.component;
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}><Part societyId="s1" date={DATE} /></QueryClientProvider>);
}
const reply = (body: unknown, status = 200) => fetchMock.mockImplementation(async () => json(status, body));

beforeEach(() => vi.stubGlobal("fetch", fetchMock));
afterEach(() => { fetchMock.mockReset(); vi.unstubAllGlobals(); });

describe("reports folder", () => {
  it("holds the three sections in order", () => {
    const sections = collectSections({
      "./DailySection.tsx": daily, "./WeeklySection.tsx": weekly, "./ExceptionsSection.tsx": exceptions,
    });
    expect(sections.map((s) => s.id)).toEqual(["daily", "weekly", "exceptions"]);
  });

  it("the week starts on Sunday", () => {
    expect(weekStartOf(DATE)).toBe("2026-11-08");
    expect(weekStartOf("2026-11-08")).toBe("2026-11-08");
    expect(weekStartOf("2026-11-14")).toBe("2026-11-08");
  });
});

describe("DailySection", () => {
  it("loads the chosen day and lists each cleaner's jobs", async () => {
    reply({ society_id: "s1", date: DATE, cleaners: [{
      cleaner_id: "c1", name: "Raj", break_window: { start_time: "09:30", end_time: "10:00" }, free_slots: null,
      jobs: [{ job_id: "j1", registration: "MH12AB1234", zone: "Zone 1", type: "Exterior", start_time: "06:00",
        end_time: "06:20", cutoff: "09:00", exceptions: [{ code: "key_unavailable", detail: "" }], cross_zone_reason: null }],
    }] });
    show(daily);
    expect(await screen.findByText("MH12AB1234")).toBeInTheDocument();
    expect(fetchMock.mock.calls[0][0]).toBe(`/v1/admin/scheduling/reports/daily?society_id=s1&date=${DATE}`);
    expect(screen.getByText(/Break 09:30 to 10:00/)).toBeInTheDocument();
    expect(screen.getByText("Key unavailable")).toBeInTheDocument();
  });

  it("shows an empty state with the date as dd-Mon-yy", async () => {
    reply({ society_id: "s1", date: DATE, cleaners: [] });
    show(daily);
    expect(await screen.findByText("No jobs planned")).toBeInTheDocument();
    expect(screen.getByText("No cleaner has a job on 11-Nov-26.")).toBeInTheDocument();
  });

  it("shows an error with a retry", async () => {
    reply({ code: "boom", message: "No." }, 500);
    show(daily);
    expect(await screen.findByRole("alert")).toHaveTextContent(/could not be loaded/i);
  });
});

describe("ExceptionsSection", () => {
  it("asks for the week and lists only the kinds that have rows", async () => {
    reply({ society_id: "s1", start_date: "2026-11-08", end_date: "2026-11-14", kinds: [
      { kind: "unassigned_exteriors", label: "Unassigned Exteriors", rows: [
        { date: "2026-11-10", job_id: "j1", registration: "MH12AB1234", cleaner_name: "", code: "no_cleaner", detail: "No one free." }] },
      { kind: "cross_zone", label: "Cross-zone jobs", rows: [] },
    ] });
    show(exceptions);
    expect(await screen.findByText("Unassigned Exteriors")).toBeInTheDocument();
    expect(fetchMock.mock.calls[0][0]).toBe("/v1/admin/scheduling/reports/exceptions?society_id=s1&start_date=2026-11-08&end_date=2026-11-14");
    expect(screen.queryByText(/Cross-zone jobs/)).not.toBeInTheDocument();
    expect(screen.getByText("10-Nov-26")).toBeInTheDocument();
    expect(screen.getByText("No cleaner")).toBeInTheDocument();
  });

  it("shows an empty state when every kind is empty", async () => {
    reply({ society_id: "s1", start_date: "2026-11-08", end_date: "2026-11-14", kinds: [{ kind: "cross_zone", label: "Cross-zone jobs", rows: [] }] });
    show(exceptions);
    expect(await screen.findByText("No exceptions")).toBeInTheDocument();
    expect(screen.getByText("Nothing to report for 08-Nov-26 to 14-Nov-26.")).toBeInTheDocument();
  });
});

describe("WeeklySection", () => {
  it("shows the values and tables the endpoint returns, with dates as dd-Mon-yy", async () => {
    reply({ society_id: "s1", start_date: "2026-11-08", exteriors_completed: 40, exteriors_mandatory: 42,
      interiors: [{ original_service_week: "2026-11-01", overdue_days: 1, completed_on: "2026-11-09" }] });
    show(weekly);
    expect(await screen.findByText("Exteriors completed")).toBeInTheDocument();
    expect(screen.getByText("40")).toBeInTheDocument();
    expect(screen.getByText("01-Nov-26")).toBeInTheDocument();
    expect(screen.getByText("09-Nov-26")).toBeInTheDocument();
    expect(fetchMock.mock.calls[0][0]).toBe("/v1/admin/scheduling/reports/weekly?society_id=s1&week_start=2026-11-08");
  });

  it("shows an empty state when the week has nothing", async () => {
    reply({ society_id: "s1", exteriors_completed: 0, interiors: [] });
    show(weekly);
    expect(await screen.findByText("Nothing this week")).toBeInTheDocument();
  });

  it("says so when the endpoint is not there yet", async () => {
    reply({ code: "not_found", message: "Not found." }, 404);
    show(weekly);
    expect(await screen.findByText("Not available yet")).toBeInTheDocument();
  });
});
