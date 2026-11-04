import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { ConfirmProvider } from "@/blocks/confirm";
import { NAV } from "../../nav";
import { ScheduledJobsPage, type CronJob } from "./ScheduledJobsPage";

const job = (over: Partial<CronJob>): CronJob => ({
  job: "payments-daily", label: "Daily payments", purpose: "Makes the payments.",
  schedule_utc: "Daily at 20:30 UTC", schedule_ist: "Daily at 02:00 IST (next day)",
  scheduled_on_vercel: true, enabled: true, status: "Success",
  last_run: { id: "r1", trigger: "vercel", started_at: "2026-11-05T20:30:00Z", finished_at: null, status: "Success",
    duration_ms: 120, what_it_did: "Made 3 payments, marked 0 over due, made 0 subscriptions Inactive.", error: "" },
  purpose_achieved: true, purpose_achieved_text: "Every late payment is marked Over due.", ...over,
});
const jobs = [
  job({}),
  job({ job: "freeze-due", label: "Freeze schedules", enabled: false, status: "Disabled", last_run: null,
    purpose_achieved: null, purpose_achieved_text: "Off" }),
];
const fetchMock = vi.fn();

beforeEach(() => {
  fetchMock.mockImplementation(async (path: string, init?: RequestInit) => {
    if (init?.method === "PUT") return new Response(JSON.stringify({ ...jobs[0], enabled: JSON.parse(init.body as string).enabled }), { status: 200 });
    if (path.includes("/runs")) return new Response(JSON.stringify([
      { id: "a", trigger: "vercel", started_at: "2026-11-05T20:30:00Z", finished_at: null, status: "Failed", duration_ms: 9, what_it_did: "The job failed.", error: "RuntimeError: boom" },
    ]), { status: 200 });
    return new Response(JSON.stringify(jobs), { status: 200 });
  });
  vi.stubGlobal("fetch", fetchMock);
});
afterEach(() => { fetchMock.mockReset(); vi.unstubAllGlobals(); });

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}><ConfirmProvider><ScheduledJobsPage /></ConfirmProvider></QueryClientProvider>);
}
const puts = () => fetchMock.mock.calls.filter((c) => c[1]?.method === "PUT");

it("lists each job with schedule, last run in IST, status and what it did", async () => {
  renderPage();
  expect(await screen.findByText("Daily payments")).toBeInTheDocument();
  for (const h of ["Job", "Purpose", "Schedule (IST)", "State", "Last run (IST)", "Status", "What it did", "Purpose achieved"]) {
    expect(screen.getByRole("columnheader", { name: h })).toBeInTheDocument();
  }
  expect(screen.getByText("06-Nov-26 02:00")).toBeInTheDocument();
  expect(screen.getByText("Made 3 payments, marked 0 over due, made 0 subscriptions Inactive.")).toBeInTheDocument();
  expect(screen.getByText("Disabled")).toBeInTheDocument();
  expect(screen.getByRole("switch", { name: "Freeze schedules on or off" })).not.toBeChecked();
});

it("switches a job on at once and asks before switching it off", async () => {
  renderPage();
  await userEvent.click(await screen.findByRole("switch", { name: "Freeze schedules on or off" }));
  await waitFor(() => expect(puts()).toHaveLength(1));
  expect(puts()[0][0]).toBe("/v1/admin/operations/cron/freeze-due");
  expect(JSON.parse(puts()[0][1].body)).toEqual({ enabled: true });

  await userEvent.click(screen.getByRole("switch", { name: "Daily payments on or off" }));
  const dialog = await screen.findByRole("alertdialog");
  expect(dialog).toHaveTextContent("New payments will not be made");
  expect(puts()).toHaveLength(1); // nothing sent before the answer
  await userEvent.click(within(dialog).getByRole("button", { name: "Cancel" }));
  expect(puts()).toHaveLength(1);

  await userEvent.click(screen.getByRole("switch", { name: "Daily payments on or off" }));
  await userEvent.click(within(await screen.findByRole("alertdialog")).getByRole("button", { name: "Switch off" }));
  await waitFor(() => expect(puts()).toHaveLength(2));
  expect(puts()[1][0]).toBe("/v1/admin/operations/cron/payments-daily");
  expect(JSON.parse(puts()[1][1].body)).toEqual({ enabled: false });
});

it("opens the last 20 runs of a job in a sheet", async () => {
  renderPage();
  await userEvent.click(await screen.findByText("Daily payments"));
  expect(await screen.findByText("RuntimeError: boom")).toBeInTheDocument();
  expect(fetchMock.mock.calls.some((c) => String(c[0]).endsWith("/payments-daily/runs?limit=20"))).toBe(true);
});

it("is in the All sites group of the navigation", () => {
  const item = NAV.find((n) => n.path === "/scheduled-jobs");
  expect(item?.group).toBe("master");
  expect(item?.label).toBe("Scheduled jobs");
});
