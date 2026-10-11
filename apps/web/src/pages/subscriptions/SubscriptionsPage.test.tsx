import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ToastProvider } from "../../components";
import { allowedMoves } from "./api";
import { SubscriptionsPage } from "./SubscriptionsPage";

const fetchMock = vi.fn();

function json(status: number, body?: unknown) {
  return new Response(body === undefined ? null : JSON.stringify(body), { status });
}
const err = (status: number, message: string) =>
  json(status, { code: "x", message, fields: {}, request_id: "" });

const row = {
  subscription_id: "s1", vehicle_id: "v1", customer_name: "Asha Rao", flat: "B-12",
  society: "Lake View", vehicle: "Swift KA01", plan_name: "Daily", status: "Activating",
  first_service_date: null, renewal_date: null,
};

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <ToastProvider><SubscriptionsPage /></ToastProvider>
    </QueryClientProvider>,
  );
}

beforeEach(() => vi.stubGlobal("fetch", fetchMock));
afterEach(() => {
  fetchMock.mockReset();
  vi.unstubAllGlobals();
});

describe("subscriptions", () => {
  it("allows only the moves the API accepts", () => {
    expect(allowedMoves("Active")).toEqual(["Inactive"]);
    expect(allowedMoves("Inactive")).toEqual(["Activating"]);
    expect(allowedMoves("Activating")).toEqual(["Inactive", "Active"]);
  });

  it("lists subscriptions and activates one with a first service date", async () => {
    fetchMock.mockImplementation(async (p: string, init?: RequestInit) => {
      if (p.startsWith("/v1/admin/subscriptions?") || p === "/v1/admin/subscriptions") {
        return json(200, [row]);
      }
      if (p.endsWith("/events")) return json(200, []);
      if (p.endsWith("/status") && init?.method === "PUT") {
        return json(200, { subscription_id: "s1", status: "Active" });
      }
      return err(404, "no");
    });
    renderPage();
    expect(await screen.findByText("Asha Rao, B-12")).toBeInTheDocument();
    await userEvent.click(screen.getAllByRole("button", { name: "Change status" })[0]);
    const dialog = await screen.findByRole("dialog");
    await userEvent.selectOptions(within(dialog).getByLabelText("New status"), "Active");
    await userEvent.type(within(dialog).getByLabelText("First service date"), "2026-11-10");
    await userEvent.click(within(dialog).getByRole("button", { name: "Save" }));
    await waitFor(() => {
      const put = fetchMock.mock.calls.find((c) => c[1]?.method === "PUT")!;
      expect(put[0]).toBe("/v1/admin/subscriptions/s1/status");
      expect(JSON.parse(put[1].body)).toEqual({
        status: "Active", reason: "", first_service_date: "2026-11-10",
      });
    });
  });

  it("explains a missing list endpoint and still offers the ID form", async () => {
    fetchMock.mockImplementation(async () => err(404, "Not found."));
    renderPage();
    expect(await screen.findByText(/not available from the server/)).toBeInTheDocument();
    expect(screen.getByLabelText("Subscription ID")).toBeInTheDocument();
  });

  it("requires a reason for Inactive and shows the API error", async () => {
    fetchMock.mockImplementation(async (p: string, init?: RequestInit) => {
      if (p.endsWith("/status") && init?.method === "PUT") {
        return err(409, "A subscription cannot go from Inactive to Inactive.");
      }
      return err(404, "Not found.");
    });
    renderPage();
    await userEvent.type(await screen.findByLabelText("Subscription ID"), "s9");
    await userEvent.click(screen.getAllByRole("button", { name: "Change status" })[0]);
    const dialog = await screen.findByRole("dialog");
    await userEvent.selectOptions(within(dialog).getByLabelText("New status"), "Inactive");
    const save = within(dialog).getByRole("button", { name: "Save" });
    expect(save).toBeDisabled();
    await userEvent.type(within(dialog).getByLabelText("Reason"), "Moved away");
    await userEvent.click(save);
    expect(await within(dialog).findByText(/cannot go from Inactive/)).toBeInTheDocument();
  });

  it("skips a day on behalf of the customer", async () => {
    fetchMock.mockImplementation(async (p: string, init?: RequestInit) => {
      if (p === "/v1/admin/vehicles/v1/changes") {
        return json(200, { vehicle_id: "v1", skips: [], pauses: [], renewal_date: null });
      }
      if (p === "/v1/admin/vehicles/v1/skips" && init?.method === "POST") return json(201, {});
      return err(404, "Not found.");
    });
    renderPage();
    await userEvent.type(await screen.findByLabelText("Vehicle ID"), "v1");
    await userEvent.click(screen.getByRole("button", { name: "Show" }));
    await userEvent.type(await screen.findByLabelText("Skip date"), "2026-11-12");
    await userEvent.click(screen.getByRole("button", { name: "Skip this day" }));
    await waitFor(() => {
      const post = fetchMock.mock.calls.find((c) => c[1]?.method === "POST")!;
      expect(JSON.parse(post[1].body)).toEqual({ date: "2026-11-12" });
    });
  });
});
