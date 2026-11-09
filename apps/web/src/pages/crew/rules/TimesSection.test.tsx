import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ToastProvider } from "../../../components";
import type { Crew } from "../api";
import { collectSections } from ".";
import * as module from "./TimesSection";

const crew: Crew = {
  id: "c1", name: "Raj Kumar", mobile: "9000000001", society_id: "s1", society: "Lake View", home_zones: [],
  role: "Member", active: true, locked: false, working_hours: [],
  paired_member_id: null, paired_member: "", exceptions: [],
};
const site = { site_reporting_minute: 300, site_first_job_minute: 330 };
const json = (status: number, body?: unknown) => new Response(JSON.stringify(body), { status });
const fetchMock = vi.fn();

function show(times: object) {
  fetchMock.mockImplementation(async (_p: string, init?: RequestInit) => {
    if (init?.method === "PUT") return json(200, { ...site, ...JSON.parse(String(init.body)) });
    return json(200, { reporting_minute: null, first_job_minute: null, ...site, ...times });
  });
  const Part = module.section.component;
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}><ToastProvider><Part crew={crew} /></ToastProvider></QueryClientProvider>);
}
const puts = () => fetchMock.mock.calls.filter(([, i]) => i?.method === "PUT");

beforeEach(() => vi.stubGlobal("fetch", fetchMock));
afterEach(() => { fetchMock.mockReset(); vi.unstubAllGlobals(); });

describe("TimesSection", () => {
  it("is a section file the Scheduling panel finds by itself", () => {
    expect(collectSections({ "./TimesSection.tsx": module }).map((s) => s.id)).toContain(module.section.id);
  });

  it("shows the site defaults in grey when the cleaner has no override", async () => {
    show({});
    const first = await screen.findByLabelText("First job time");
    expect(first).toHaveValue("05:30");
    expect(first).toHaveClass("text-muted-foreground");
    expect(screen.getByLabelText("Reporting time")).toHaveValue("05:00");
    expect(screen.getByText(/site default 05:30/i)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Clear first job time" })).not.toBeInTheDocument();
  });

  it("shows an override in the normal colour", async () => {
    show({ first_job_minute: 345 });
    const first = await screen.findByLabelText("First job time");
    expect(first).toHaveValue("05:45");
    expect(first).not.toHaveClass("text-muted-foreground");
  });

  it("saves an edit as an override in minutes", async () => {
    show({});
    const first = await screen.findByLabelText("First job time");
    fireEvent.change(first, { target: { value: "05:45" } });
    await userEvent.click(screen.getByRole("button", { name: "Save" }));
    await waitFor(() => expect(puts()).toHaveLength(1));
    expect(puts()[0][0]).toBe("/v1/admin/crew/c1/times");
    expect(JSON.parse(puts()[0][1].body)).toEqual({ reporting_minute: null, first_job_minute: 345 });
  });

  it("Clear returns the field to the site default and saves null", async () => {
    show({ first_job_minute: 345 });
    await screen.findByLabelText("First job time");
    await userEvent.click(screen.getByRole("button", { name: "Clear first job time" }));
    expect(screen.getByLabelText("First job time")).toHaveValue("05:30");
    await userEvent.click(screen.getByRole("button", { name: "Save" }));
    await waitFor(() => expect(puts()).toHaveLength(1));
    expect(JSON.parse(puts()[0][1].body)).toEqual({ reporting_minute: null, first_job_minute: null });
  });

  it("refuses a first job time before the reporting time", async () => {
    show({});
    const reporting = await screen.findByLabelText("Reporting time");
    fireEvent.change(reporting, { target: { value: "06:00" } });
    expect(await screen.findByRole("alert")).toHaveTextContent(/not .*before the reporting time/i);
    expect(screen.getByRole("button", { name: "Save" })).toBeDisabled();
    expect(puts()).toHaveLength(0);
  });
});
