import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { AppRoutes } from "./App";
import { AuthProvider } from "./auth/AuthContext";
import { ToastProvider } from "./components";
import { NAV } from "./nav";

const fetchMock = vi.fn();
const profile = { user_id: "u1", role: "admin", display_name: "Priveo Papa" };

function json(status: number, body?: unknown) {
  return new Response(body === undefined ? null : JSON.stringify(body), { status });
}

const unauthorized = {
  code: "unauthorized", message: "Please sign in.", fields: {}, request_id: "",
};

function renderAt(path: string) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[path]}>
        <ToastProvider>
          <AuthProvider>
            <AppRoutes />
          </AuthProvider>
        </ToastProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => vi.stubGlobal("fetch", fetchMock));
afterEach(() => {
  fetchMock.mockReset();
  vi.unstubAllGlobals();
});

describe("portal shell", () => {
  it("sends a signed-out visitor to the sign-in page", async () => {
    fetchMock.mockResolvedValue(json(401, unauthorized));
    renderAt("/customers");
    expect(await screen.findByRole("heading", { name: "Priveo" })).toBeInTheDocument();
    expect(screen.getByLabelText("User ID")).toBeInTheDocument();
  });

  it("shows the navigation and the page when signed in", async () => {
    fetchMock.mockResolvedValue(json(200, profile));
    renderAt("/payments");
    const nav = await screen.findByRole("navigation", { name: "Admin areas" });
    for (const item of NAV) {
      expect(within(nav).getByRole("link", { name: item.label })).toBeInTheDocument();
    }
    expect(screen.getByRole("heading", { name: "Payments" })).toBeInTheDocument();
    expect(screen.getByText("Priveo Papa")).toBeInTheDocument();
  });

  it("signs in and lands on the page that was asked for", async () => {
    fetchMock.mockImplementation(async (path: string) => {
      if (path === "/v1/web/me") return json(401, unauthorized);
      if (path === "/v1/web/login") return json(200, profile);
      return json(404, { code: "not_found", message: "no", fields: {}, request_id: "" });
    });
    renderAt("/crew");
    await userEvent.type(await screen.findByLabelText("User ID"), "priveopapa");
    await userEvent.type(screen.getByLabelText("Password"), "secret-pw1");
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));
    expect(await screen.findByRole("heading", { name: "Crew" })).toBeInTheDocument();
    const login = fetchMock.mock.calls.find((c) => c[0] === "/v1/web/login")!;
    expect(JSON.parse(login[1].body)).toEqual({ login_id: "priveopapa", password: "secret-pw1" });
  });

  it("shows the API's message for a wrong password", async () => {
    fetchMock.mockImplementation(async (path: string) => {
      if (path === "/v1/web/me") return json(401, unauthorized);
      return json(401, {
        code: "invalid_credentials", message: "The ID or password is not correct.",
        fields: {}, request_id: "",
      });
    });
    renderAt("/");
    await userEvent.type(await screen.findByLabelText("User ID"), "priveopapa");
    await userEvent.type(screen.getByLabelText("Password"), "wrong");
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("The ID or password is not correct.");
  });

  it("signs out and returns to sign-in", async () => {
    fetchMock.mockImplementation(async (path: string) => {
      if (path === "/v1/web/me") return json(200, profile);
      if (path === "/v1/web/logout") return json(204);
      return json(404);
    });
    renderAt("/");
    await userEvent.click(await screen.findByRole("button", { name: "Sign out" }));
    expect(await screen.findByLabelText("User ID")).toBeInTheDocument();
  });
});
