import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { crewWithCards, JobCardButtons } from "./ScheduleActions";
import type { AdminJob } from "./api";

const DATE = "2026-10-18";
const fetchMock = vi.fn();
const downloads: string[] = [];

// A string body: this environment's Response refuses a jsdom Blob, which the fetch would then report as a lost connection.
const pdf = () => new Response("%PDF-1.4", { status: 200, headers: { "Content-Type": "application/pdf" } });

/** A card with only the fields the buttons read. */
function card(id: string, crewId: string | null, crewName: string | null, status = "Scheduled", date = DATE): AdminJob {
  return { id, date, crew_id: crewId, crew_name: crewName, status } as unknown as AdminJob;
}

function renderButtons(jobs: AdminJob[]) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <JobCardButtons scheduleId="sch1" date={DATE} jobs={jobs} />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.stubGlobal("fetch", fetchMock);
  Object.assign(URL, { createObjectURL: vi.fn(() => "blob:cards"), revokeObjectURL: vi.fn() });
  vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(function (this: HTMLAnchorElement) {
    downloads.push(this.download);
  });
  fetchMock.mockImplementation(async () => pdf());
});

afterEach(() => {
  fetchMock.mockReset();
  downloads.length = 0;
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("crewWithCards", () => {
  it("lists the crew with cards on the day, by name, without skipped or unassigned cards", () => {
    const jobs = [
      card("a", "c2", "Meena"),
      card("b", "c1", "Ravi"),
      card("c", "c1", "Ravi"),
      card("d", "c3", "Asha", "Skipped"),
      card("e", null, null),
      card("f", "c4", "Dev", "Scheduled", "2026-10-19"),
    ];
    // Sorted by name: Meena (c2) before Ravi (c1).
    expect(crewWithCards(jobs, DATE)).toEqual([
      { id: "c2", name: "Meena" },
      { id: "c1", name: "Ravi" },
    ]);
  });
});

describe("JobCardButtons", () => {
  it("shows nothing when no crew has cards that day", () => {
    renderButtons([card("e", null, null)]);
    expect(screen.queryByRole("button", { name: /job cards/i })).not.toBeInTheDocument();
  });

  it("the all-crew button asks for the one PDF of the day and saves it", async () => {
    renderButtons([card("a", "c1", "Ravi"), card("b", "c2", "Meena")]);
    fireEvent.click(screen.getByRole("button", { name: /all crew/i }));

    await waitFor(() => expect(downloads).toEqual(["job-cards-2026-10-18.pdf"]));
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock.mock.calls[0][0]).toBe("/v1/admin/scheduling/job-cards/pdf?schedule_id=sch1&date=2026-10-18");
    expect(fetchMock.mock.calls[0][1].headers.Accept).toBe("application/pdf");
  });

  it("the per-crew button asks for one PDF for each crew member, in name order", async () => {
    renderButtons([card("a", "c2", "Meena"), card("b", "c1", "Ravi Kumar")]);
    fireEvent.click(screen.getByRole("button", { name: /one PDF per crew/i }));

    await waitFor(() => expect(downloads).toHaveLength(2));
    // Meena comes before Ravi Kumar by name, so her PDF is asked for first.
    expect(fetchMock.mock.calls.map((call) => call[0])).toEqual([
      "/v1/admin/scheduling/job-cards/crews/c2/pdf?schedule_id=sch1&date=2026-10-18",
      "/v1/admin/scheduling/job-cards/crews/c1/pdf?schedule_id=sch1&date=2026-10-18",
    ]);
    expect(downloads).toEqual(["job-cards-Meena-2026-10-18.pdf", "job-cards-Ravi-Kumar-2026-10-18.pdf"]);
  });
});
