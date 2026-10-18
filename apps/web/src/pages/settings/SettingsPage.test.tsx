import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { ToastProvider } from "../../components";
import { PortalProviders } from "../../test/portal";
import { SettingsPage } from "./SettingsPage";

const fetchMock = vi.fn();
const setting = (key: string, label: string, group: string) => ({
  key, label, group, kind: "text", value: "x", is_default: true, updated_at: null, updated_by: null,
});

beforeEach(() => {
  fetchMock.mockImplementation(async (path: string) => {
    if (path === "/v1/admin/directory/settings") {
      return new Response(JSON.stringify([
        setting("support.phone", "Support phone", "support"),
        setting("payment.upi", "UPI ID", "payment"),
        setting("billing.cycle_days", "Cycle days", "billing")]), { status: 200 });
    }
    if (path === "/v1/admin/scheduling/automatic-planning") return new Response(JSON.stringify({ enabled: false, time_ist: "20:00" }), { status: 200 });
    if (path.includes("alert-email")) return new Response(JSON.stringify({ email: "a@b.in", enabled: true }), { status: 200 });
    return new Response(JSON.stringify({}), { status: 200 });
  });
  vi.stubGlobal("fetch", fetchMock);
});
afterEach(() => { fetchMock.mockReset(); vi.unstubAllGlobals(); });

it("shows every section as a tab, one at a time", async () => {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(<QueryClientProvider client={qc}><MemoryRouter><ToastProvider><PortalProviders><SettingsPage /></PortalProviders></ToastProvider></MemoryRouter></QueryClientProvider>);
  const tabs = await screen.findByRole("tablist", { name: "Settings sections" });
  await screen.findByRole("tab", { name: "Support" });
  expect((await screen.findAllByRole("tab")).map((t) => t.textContent)).toEqual(
    ["Support", "Payment", "Billing", "Alert emails", "Automatic planning"]);
  expect(tabs).toBeInTheDocument();
  expect(await screen.findByLabelText("Support phone")).toBeInTheDocument();
  expect(screen.queryByLabelText("UPI ID")).not.toBeInTheDocument();
  await userEvent.click(screen.getByRole("tab", { name: "Payment" }));
  expect(await screen.findByLabelText("UPI ID")).toBeInTheDocument();
  expect(screen.queryByLabelText("Support phone")).not.toBeInTheDocument();
  await userEvent.click(screen.getByRole("tab", { name: "Automatic planning" }));
  expect(await screen.findByText("Automatic schedule planning")).toBeInTheDocument();
  await userEvent.click(screen.getByRole("tab", { name: "Alert emails" }));
  expect(await screen.findByLabelText("Alert email address")).toBeInTheDocument();
});
