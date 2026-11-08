import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ToastProvider } from "../../../components";
import { withSite } from "../../../site/testSite";
import { collectSections } from ".";
import * as module from "./GeneralSection";

const rows = [
  { key: "site.first_job_minute", label: "Earliest first job (minutes after midnight)", kind: "int",
    default_value: "330", site_value: null, value: "330", minimum: 0, maximum: 1439 },
  { key: "site.break_enabled", label: "Crew break on", kind: "bool",
    default_value: "true", site_value: "false", value: "false", minimum: null, maximum: null },
  { key: "site.weekday_cutoff_hard", label: "Customer cutoff is strict on weekdays", kind: "bool",
    default_value: "true", site_value: null, value: "true", minimum: null, maximum: null },
];
const json = (status: number, body?: unknown) => new Response(JSON.stringify(body), { status });
const fetchMock = vi.fn();

function show(putResponse?: Response) {
  fetchMock.mockImplementation(async (_p: string, init?: RequestInit) => {
    if (init?.method === "PUT") return putResponse ?? json(200, rows[0]);
    return json(200, rows);
  });
  const Part = module.section.component;
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}><ToastProvider>{withSite(<Part />)}</ToastProvider></QueryClientProvider>);
}
const puts = () => fetchMock.mock.calls.filter(([, i]) => i?.method === "PUT");

beforeEach(() => vi.stubGlobal("fetch", fetchMock));
afterEach(() => { fetchMock.mockReset(); vi.unstubAllGlobals(); });

describe("GeneralSection", () => {
  it("is a section file the Scheduler Rules tab finds by itself", () => {
    expect(collectSections({ "./GeneralSection.tsx": module }).map((s) => s.id)).toContain(module.section.id);
  });

  it("shows the default, the site value and the range of each key", async () => {
    show();
    expect(await screen.findByLabelText("Earliest first job (minutes after midnight)")).toHaveValue("05:30");
    expect(screen.getByText(/Default 05:30\. This site uses the default\. Range 00:00 to 23:59\./)).toBeInTheDocument();
    expect(screen.getByText(/Default On\. This site: Off\./)).toBeInTheDocument();
  });

  it("names the three cutoffs Customer cutoff, Freeze and 9 PM rule", async () => {
    show();
    await screen.findByLabelText("Earliest first job (minutes after midnight)");
    for (const n of ["Customer cutoff", "Freeze", "9 PM rule"]) expect(screen.getByText(n)).toBeInTheDocument();
  });

  it("saves an edited time in minutes for the chosen site", async () => {
    show();
    fireEvent.change(await screen.findByLabelText("Earliest first job (minutes after midnight)"), { target: { value: "05:45" } });
    await userEvent.click(screen.getByRole("button", { name: "Save Earliest first job (minutes after midnight)" }));
    await waitFor(() => expect(puts()).toHaveLength(1));
    expect(puts()[0][0]).toBe("/v1/admin/scheduling/site-settings/site.first_job_minute");
    expect(JSON.parse(puts()[0][1].body)).toEqual({ society_id: "s1", value: "345" });
  });

  it("shows the message when the value is refused", async () => {
    show(json(422, { code: "validation_failed", message: "Bad.", fields: { value: "Interior cannot start before the first job." } }));
    fireEvent.change(await screen.findByLabelText("Earliest first job (minutes after midnight)"), { target: { value: "09:00" } });
    await userEvent.click(screen.getByRole("button", { name: "Save Earliest first job (minutes after midnight)" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Interior cannot start before the first job.");
  });

  it("saves a switch as true or false", async () => {
    show();
    await userEvent.click(await screen.findByRole("switch", { name: "Crew break on" }));
    await userEvent.click(screen.getByRole("button", { name: "Save Crew break on" }));
    await waitFor(() => expect(puts()).toHaveLength(1));
    expect(JSON.parse(puts()[0][1].body).value).toBe("true");
  });
});
