import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ToastProvider } from "../../components";
import { AuditPage } from "../audit/AuditPage";
import { SettingsPage } from "../settings/SettingsPage";
import { ReferencePage } from "./ReferencePage";

const fetchMock = vi.fn();

function json(status: number, body?: unknown) {
  return new Response(body === undefined ? null : JSON.stringify(body), { status });
}
const err = (status: number, code: string, message: string, fields: Record<string, string> = {}) =>
  json(status, { code, message, fields, request_id: "" });

const society = (over: Record<string, unknown> = {}) => ({
  id: "s1", name: "Lake View", sector: "S4", city: "Pune", active: true,
  parking_basements: ["B1", "B2"], cars_serviced: 12, active_subscriptions: 3, active_crew: 1,
  ...over,
});

let handlers: Record<string, (init?: RequestInit) => Response> = {};

function renderUi(ui: React.ReactElement) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}><ToastProvider>{ui}</ToastProvider></QueryClientProvider>,
  );
}

const calls = (needle: string) => fetchMock.mock.calls.filter((c) => String(c[0]).includes(needle));

beforeEach(() => {
  handlers = {};
  fetchMock.mockImplementation(async (p: string, init?: RequestInit) => {
    const key = `${init?.method ?? "GET"} ${p}`;
    for (const [k, h] of Object.entries(handlers)) if (key.startsWith(k)) return h(init);
    return err(404, "not_found", "No handler.");
  });
  vi.stubGlobal("fetch", fetchMock);
});
afterEach(() => {
  fetchMock.mockReset();
  vi.unstubAllGlobals();
});

describe("reference data", () => {
  it("lists societies and shows the in-use block plainly", async () => {
    handlers["GET /v1/admin/directory/societies"] = () => json(200, [society()]);
    handlers["POST /v1/admin/directory/societies/s1/deactivate"] = () => err(
      409, "in_use", "This society has active subscriptions or active crew. Deactivate those first.",
      { active_subscriptions: "3", active_crew: "1" });
    renderUi(<ReferencePage />);
    expect(await screen.findByText("Lake View")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Deactivate Lake View" }));
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("Deactivate those first.");
    expect(alert).toHaveTextContent("Active subscriptions: 3. Active crew: 1.");
  });

  it("creates a society and shows a field error from the API", async () => {
    handlers["GET /v1/admin/directory/societies"] = () => json(200, []);
    handlers["POST /v1/admin/directory/societies"] = () => err(
      409, "duplicate", "This society already exists.", { name: "This society already exists." });
    renderUi(<ReferencePage />);
    await userEvent.click(await screen.findByRole("button", { name: "Add a society" }));
    const dialog = screen.getByRole("dialog");
    await userEvent.type(within(dialog).getByLabelText("Name"), "Lake View");
    await userEvent.type(within(dialog).getByLabelText("Parking basements"), "B1, B2");
    await userEvent.click(within(dialog).getByRole("button", { name: "Save" }));
    expect(await within(dialog).findByText("This society already exists.")).toBeInTheDocument();
    const post = calls("/societies").find((c) => c[1]?.method === "POST")!;
    expect(JSON.parse(post[1].body)).toMatchObject({ name: "Lake View", parking_basements: ["B1", "B2"] });
  });

  it("reorders reasons by sending every id", async () => {
    handlers["GET /v1/admin/directory/reasons"] = () => json(200, [
      { id: "r1", key: "a", label: "Car locked", sort_order: 0, active: true },
      { id: "r2", key: "b", label: "No access", sort_order: 1, active: false },
    ]);
    handlers["PUT /v1/admin/directory/reasons/order"] = () => json(200, []);
    renderUi(<ReferencePage />);
    await userEvent.click(screen.getByRole("tab", { name: "Could not complete reasons" }));
    await userEvent.click(await screen.findByRole("button", { name: "Move Car locked down" }));
    await waitFor(() => expect(calls("/reasons/order")).toHaveLength(1));
    expect(JSON.parse(calls("/reasons/order")[0][1].body)).toEqual({ ids: ["r2", "r1"] });
  });

  it("saves a service's proof minimums", async () => {
    handlers["GET /v1/admin/directory/services"] = () => json(200, [
      { name: "Deep Spa", duration_minutes: 120, min_photos: 2, min_videos: 1 }]);
    handlers["PATCH /v1/admin/directory/services/Deep%20Spa"] = () => json(200, {});
    renderUi(<ReferencePage />);
    await userEvent.click(screen.getByRole("tab", { name: "Services" }));
    const photos = await screen.findByLabelText("Minimum photos, Deep Spa");
    await userEvent.clear(photos);
    await userEvent.type(photos, "4");
    await userEvent.click(screen.getByRole("button", { name: "Save Deep Spa" }));
    await waitFor(() => expect(calls("/services/Deep")).toHaveLength(1));
    expect(JSON.parse(calls("/services/Deep")[0][1].body)).toEqual(
      { duration_minutes: 120, min_photos: 4, min_videos: 1 });
  });
});

describe("settings", () => {
  const setting = (over: Record<string, unknown>) => ({
    key: "billing.cycle_days", label: "Billing cycle in days", group: "billing", kind: "int",
    value: 30, is_default: true, updated_at: null, updated_by: null, ...over,
  });

  it("saves one key and shows its validation message", async () => {
    handlers["GET /v1/admin/directory/settings"] = () => json(200, [
      setting({}), setting({ key: "support.hours", label: "Support hours", group: "support",
                              kind: "text", value: "6 AM to 10 PM" })]);
    handlers["PUT /v1/admin/directory/settings/billing.cycle_days"] = () => err(
      422, "validation_failed", "Please check the details.", { value: "Enter 1 to 366." });
    renderUi(<SettingsPage />);
    const input = await screen.findByLabelText("Billing cycle in days");
    expect(screen.getAllByText("Default").length).toBe(2);
    await userEvent.clear(input);
    await userEvent.type(input, "999");
    await userEvent.click(screen.getByRole("button", { name: "Save Billing cycle in days" }));
    expect(await screen.findByText("Enter 1 to 366.")).toBeInTheDocument();
    const put = calls("billing.cycle_days")[0];
    expect(JSON.parse(put[1].body)).toEqual({ value: 999 });
  });
});

describe("audit", () => {
  it("filters by entity and shows old and new values", async () => {
    handlers["GET /v1/admin/directory/audit"] = () => json(200, [{
      id: "a1", at: "2026-10-11T10:00:00Z", admin_login_id: "u1", entity: "plan",
      entity_id: "p1", action: "update", detail: { monthly_price_rupees: [1500, 1800] },
    }]);
    renderUi(<AuditPage />);
    expect(await screen.findByText("1500")).toBeInTheDocument();
    expect(screen.getByText("1800")).toBeInTheDocument();
    await userEvent.selectOptions(screen.getByLabelText("Entity"), "plan");
    await waitFor(() => {
      const last = String(fetchMock.mock.calls.at(-1)![0]);
      expect(last).toContain("entity=plan");
      expect(last).toContain("limit=100");
    });
  });
});
