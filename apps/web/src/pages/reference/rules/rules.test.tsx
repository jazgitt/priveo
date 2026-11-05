import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ToastProvider } from "../../../components";
import { withSite } from "../../../site/testSite";
import { PortalProviders } from "../../../test/portal";
import { CrewDetailPage } from "../../crew/CrewDetailPage";
import { collectSections as collectCrew } from "../../crew/rules";
import { collectSections as collectReports } from "../../schedule/reports";
import { SchedulePage } from "../../schedule/SchedulePage";
import { ReferencePage } from "../ReferencePage";
import { collectSections } from ".";

// The section lists the three pages read. Each test sets what the folder would hold.
const folders = vi.hoisted(() => ({
  rules: [] as unknown[], crew: [] as unknown[], reports: [] as unknown[],
}));
vi.mock("./index", async (orig) => ({ ...(await orig<object>()), get RULES_SECTIONS() { return folders.rules; } }));
vi.mock("../../crew/rules", async (orig) => ({ ...(await orig<object>()), get CREW_RULES_SECTIONS() { return folders.crew; } }));
vi.mock("../../schedule/reports", async (orig) => ({ ...(await orig<object>()), get REPORT_SECTIONS() { return folders.reports; } }));

const fetchMock = vi.fn();
const json = (status: number, body?: unknown) => new Response(body === undefined ? null : JSON.stringify(body), { status });

const raj = {
  id: "c1", name: "Raj Kumar", mobile: "9000000001", society_id: "s1", society: "Lake View",
  role: "Member", active: true, locked: false, working_hours: [],
  paired_member_id: null, paired_member: "", exceptions: [],
};

function wrap(ui: React.ReactElement, path: string) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}><MemoryRouter initialEntries={[path]}><ToastProvider><PortalProviders>
      <Routes>
        <Route path="/crew/:id" element={ui} />
        <Route path="*" element={withSite(ui, "s1", "Palm Grove")} />
      </Routes>
    </PortalProviders></ToastProvider></MemoryRouter></QueryClientProvider>,
  );
}

beforeEach(() => {
  folders.rules = []; folders.crew = []; folders.reports = [];
  fetchMock.mockImplementation(async (p: string) => {
    if (p.startsWith("/v1/admin/crew/c1")) return json(200, raj);
    return json(200, []);
  });
  vi.stubGlobal("fetch", fetchMock);
});
afterEach(() => {
  fetchMock.mockReset();
  vi.unstubAllGlobals();
});

const Fake = (name: string) => () => <p>{name} body</p>;

describe("collecting sections from a folder", () => {
  it("returns nothing for an empty folder and ignores files without a section", () => {
    expect(collectSections({})).toEqual([]);
    expect(collectSections({ "./OtherSection.tsx": {} })).toEqual([]);
  });

  it("orders sections by order, then id, for all three folders", () => {
    const mk = (id: string, order: number) => ({ section: { id, title: id, order, component: Fake(id) } });
    const mods = { "./a": mk("b", 2), "./b": mk("c", 1), "./c": mk("a", 2) };
    expect(collectSections(mods).map((s) => s.id)).toEqual(["c", "a", "b"]);
    expect(collectCrew(mods).map((s) => s.id)).toEqual(["c", "a", "b"]);
    expect(collectReports(mods).map((s) => s.id)).toEqual(["c", "a", "b"]);
  });
});

describe("Scheduling rules tab (Site Setup)", () => {
  it("shows an empty state when the folder has no section files", async () => {
    wrap(<ReferencePage />, "/reference");
    await userEvent.click(await screen.findByRole("tab", { name: "Scheduling rules" }));
    expect(await screen.findByText("No scheduling rules yet")).toBeInTheDocument();
  });

  it("shows a section file added to the folder with no other edit", async () => {
    folders.rules = collectSections({ "./XSection.tsx": { section: { id: "x", title: "Freeze rules", order: 1, component: Fake("freeze") } } });
    wrap(<ReferencePage />, "/reference");
    await userEvent.click(await screen.findByRole("tab", { name: "Scheduling rules" }));
    expect(await screen.findByRole("heading", { name: "Freeze rules" })).toBeInTheDocument();
    expect(screen.getByText("freeze body")).toBeInTheDocument();
    expect(screen.queryByText("No scheduling rules yet")).not.toBeInTheDocument();
  });
});

describe("Scheduling panel (crew detail)", () => {
  it("shows an empty state when the folder has no section files", async () => {
    wrap(<CrewDetailPage />, "/crew/c1?tab=scheduling");
    expect(await screen.findByText("No scheduling rules yet")).toBeInTheDocument();
  });

  it("mounts each section file with the crew member", async () => {
    folders.crew = collectCrew({ "./TimesSection.tsx": { section: {
      id: "times", title: "Times", order: 1, component: ({ crew }) => <p>times for {crew.name}</p> } } });
    wrap(<CrewDetailPage />, "/crew/c1?tab=scheduling");
    expect(await screen.findByRole("heading", { name: "Times" })).toBeInTheDocument();
    expect(screen.getByText("times for Raj Kumar")).toBeInTheDocument();
  });
});

describe("Reports tab (Schedule)", () => {
  it("is hidden when the folder has no report sections", async () => {
    wrap(<SchedulePage />, "/schedule?date=2026-11-08");
    expect(await screen.findByRole("tab", { name: "Board" })).toBeInTheDocument();
    expect(screen.queryByRole("tab", { name: "Reports" })).not.toBeInTheDocument();
  });

  it("appears, with its sections, once a report section file exists", async () => {
    folders.reports = collectReports({ "./DailySection.tsx": { section: {
      id: "daily", title: "Daily report", order: 1, component: ({ date }) => <p>report for {date}</p> } } });
    wrap(<SchedulePage />, "/schedule?date=2026-11-08&tab=reports");
    expect(await screen.findByRole("tab", { name: "Reports" })).toBeInTheDocument();
    expect(await screen.findByRole("heading", { name: "Daily report" })).toBeInTheDocument();
    expect(screen.getByText("report for 2026-11-08")).toBeInTheDocument();
  });
});
