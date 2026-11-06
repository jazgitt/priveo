import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ToastProvider } from "../../../components";
import { choose } from "../../../test/portal";
import type { Crew } from "../api";
import { collectSections } from ".";
import * as module from "./HomeZoneSection";

const crew: Crew = {
  id: "c1", name: "Raj Kumar", mobile: "9000000001", society_id: "s1", society: "Lake View",
  role: "Member", active: true, locked: false, working_hours: [],
  paired_member_id: null, paired_member: "", exceptions: [],
};
const zones = [{ id: "z1", name: "Zone 1" }, { id: "z2", name: "Zone 2" }];
const json = (status: number, body?: unknown) => new Response(JSON.stringify(body), { status });
const fetchMock = vi.fn();

function show(data: object) {
  fetchMock.mockImplementation(async (_p: string, init?: RequestInit) => {
    if (init?.method === "PUT") return json(200, { home_zone_id: null, follows_member: null, editable: true, zones, ...JSON.parse(String(init.body)) });
    return json(200, { home_zone_id: null, follows_member: null, editable: true, zones, ...data });
  });
  const Part = module.section.component;
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}><ToastProvider><Part crew={crew} /></ToastProvider></QueryClientProvider>);
}
const puts = () => fetchMock.mock.calls.filter(([, i]) => i?.method === "PUT");

beforeEach(() => vi.stubGlobal("fetch", fetchMock));
afterEach(() => { fetchMock.mockReset(); vi.unstubAllGlobals(); });

describe("HomeZoneSection", () => {
  it("is a section file the Scheduling panel finds by itself", () => {
    expect(collectSections({ "./HomeZoneSection.tsx": module }).map((s) => s.id)).toContain("home-zone");
  });

  it("picks a zone of the society and saves its id", async () => {
    show({});
    await screen.findByRole("combobox", { name: "Home zone" });
    await choose("Home zone", "Zone 2");
    await userEvent.click(screen.getByRole("button", { name: "Save" }));
    await waitFor(() => expect(puts()).toHaveLength(1));
    expect(puts()[0][0]).toBe("/v1/admin/crew/c1/home-zone");
    expect(JSON.parse(puts()[0][1].body)).toEqual({ home_zone_id: "z2" });
  });

  it("saves null for no home zone", async () => {
    show({ home_zone_id: "z1" });
    await screen.findByRole("combobox", { name: "Home zone" });
    await choose("Home zone", "No home zone");
    await userEvent.click(screen.getByRole("button", { name: "Save" }));
    await waitFor(() => expect(puts()).toHaveLength(1));
    expect(JSON.parse(puts()[0][1].body)).toEqual({ home_zone_id: null });
  });

  it("shows a Trainee the Member's zone and does not allow an edit", async () => {
    show({ home_zone_id: "z1", follows_member: "Asha", editable: false });
    expect(await screen.findByText(/follows Asha's home zone/i)).toBeInTheDocument();
    expect(screen.getByRole("combobox", { name: "Home zone" })).toBeDisabled();
    expect(screen.queryByRole("button", { name: "Save" })).not.toBeInTheDocument();
  });
});
