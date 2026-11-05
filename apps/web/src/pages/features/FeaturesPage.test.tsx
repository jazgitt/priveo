import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { ToastProvider } from "../../components";
import { PortalProviders } from "../../test/portal";
import { FeaturesPage } from "./FeaturesPage";

const fetchMock = vi.fn();
const feature = (key: string, label: string, group: string, enabled = true, audience = "customer") => ({
  key, label, group, description: "A thing.", audience, enabled,
});

beforeEach(() => {
  fetchMock.mockImplementation(async () => new Response(JSON.stringify([
    feature("customer.deep_spa", "Deep Spa", "Customer: services"),
    feature("customer.help", "Help and FAQ", "Customer: support", false),
    feature("crew.notifications", "Crew notifications", "Crew", true, "crew"),
    feature("common.push", "Push registration", "Both", false, "both")]), { status: 200 }));
  vi.stubGlobal("fetch", fetchMock);
});
afterEach(() => { fetchMock.mockReset(); vi.unstubAllGlobals(); });

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}><MemoryRouter><ToastProvider><PortalProviders><FeaturesPage /></PortalProviders></ToastProvider></MemoryRouter></QueryClientProvider>);
}
const puts = () => fetchMock.mock.calls.filter((c) => c[1]?.method === "PUT");

it("groups features and shows each switch's state", async () => {
  renderPage();
  expect(await screen.findByText("Customer: services")).toBeInTheDocument();
  expect(screen.getByRole("switch", { name: "Deep Spa" })).toBeChecked();
  expect(screen.getByRole("switch", { name: "Help and FAQ" })).not.toBeChecked();
});

it("asks before turning a feature off, and saves only when confirmed", async () => {
  renderPage();
  await userEvent.click(await screen.findByRole("switch", { name: "Deep Spa" }));
  await userEvent.click(await screen.findByRole("button", { name: "Cancel" }));
  expect(puts()).toHaveLength(0);
  await userEvent.click(screen.getByRole("switch", { name: "Deep Spa" }));
  await userEvent.click(await screen.findByRole("button", { name: "Turn off" }));
  await waitFor(() => expect(puts()).toHaveLength(1));
  expect(String(puts()[0][0])).toBe("/v1/admin/features/customer.deep_spa");
  expect(JSON.parse(puts()[0][1].body)).toEqual({ enabled: false });
});

it("turns a feature on without asking", async () => {
  renderPage();
  await userEvent.click(await screen.findByRole("switch", { name: "Help and FAQ" }));
  await waitFor(() => expect(puts()).toHaveLength(1));
  expect(JSON.parse(puts()[0][1].body)).toEqual({ enabled: true });
});

it("shows Feature Plugs as tabs by audience with counts, one audience at a time", async () => {
  renderPage();
  expect(await screen.findByRole("heading", { name: "Feature Plugs" })).toBeInTheDocument();
  expect(await screen.findByRole("tab", { name: /Customers/ })).toHaveTextContent("2, 1 off");
  expect(screen.getByRole("tab", { name: /Crew/ })).toHaveTextContent("1");
  expect(screen.getByRole("tab", { name: /Both apps/ })).toHaveTextContent("1, 1 off");
  expect(screen.queryByRole("switch", { name: "Crew notifications" })).not.toBeInTheDocument();
  await userEvent.click(screen.getByRole("tab", { name: /Crew/ }));
  expect(await screen.findByRole("switch", { name: "Crew notifications" })).toBeChecked();
  expect(screen.queryByRole("switch", { name: "Deep Spa" })).not.toBeInTheDocument();
  await userEvent.click(screen.getByRole("tab", { name: /Both apps/ }));
  expect(await screen.findByRole("switch", { name: "Push registration" })).not.toBeChecked();
});
