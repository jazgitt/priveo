import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { ToastProvider } from "../../components";
import { PortalProviders } from "../../test/portal";
import { FeaturesPage } from "./FeaturesPage";

const fetchMock = vi.fn();
const feature = (key: string, label: string, group: string, enabled = true) => ({
  key, label, group, description: "A thing.", audience: "customer", enabled,
});

beforeEach(() => {
  fetchMock.mockImplementation(async () => new Response(JSON.stringify([
    feature("customer.deep_spa", "Deep Spa", "Customer: services"),
    feature("customer.help", "Help and FAQ", "Customer: support", false)]), { status: 200 }));
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
