import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { api, ApiError, readCookie, setUnauthorizedListener } from "./client";

function reply(status: number, body?: unknown): Response {
  return new Response(body === undefined ? null : JSON.stringify(body), { status });
}

const fetchMock = vi.fn();

beforeEach(() => {
  vi.stubGlobal("fetch", fetchMock);
  document.cookie = "priveo_csrf=tok123; path=/";
});

afterEach(() => {
  fetchMock.mockReset();
  vi.unstubAllGlobals();
  setUnauthorizedListener(null);
  document.cookie = "priveo_csrf=; path=/; max-age=0";
});

describe("readCookie", () => {
  it("finds a cookie by name", () => {
    expect(readCookie("b", "a=1; b=two%20words; c=3")).toBe("two words");
    expect(readCookie("z", "a=1")).toBeNull();
  });
});

describe("api", () => {
  it("sends credentials and no CSRF header on a read", async () => {
    fetchMock.mockResolvedValue(reply(200, { ok: true }));
    await expect(api("/v1/web/me")).resolves.toEqual({ ok: true });
    const [path, init] = fetchMock.mock.calls[0];
    expect(path).toBe("/v1/web/me");
    expect(init.credentials).toBe("same-origin");
    expect(init.headers["X-CSRF-Token"]).toBeUndefined();
  });

  it("adds the CSRF header on a change", async () => {
    fetchMock.mockResolvedValue(reply(204));
    await api("/v1/admin/sessions/logout-all", { method: "POST" });
    expect(fetchMock.mock.calls[0][1].headers["X-CSRF-Token"]).toBe("tok123");
  });

  it("sends a JSON body", async () => {
    fetchMock.mockResolvedValue(reply(200, {}));
    await api("/x", { method: "POST", body: { a: 1 } });
    const init = fetchMock.mock.calls[0][1];
    expect(init.headers["Content-Type"]).toBe("application/json");
    expect(init.body).toBe('{"a":1}');
  });

  it("turns the error envelope into an ApiError", async () => {
    fetchMock.mockResolvedValue(reply(422, {
      code: "validation_failed", message: "Please check the details.",
      fields: { password: "Too short" }, request_id: "r1",
    }));
    const err = await api("/x").catch((e) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err).toMatchObject({
      status: 422, code: "validation_failed", fields: { password: "Too short" }, requestId: "r1",
    });
  });

  it("handles a reply that is not the envelope", async () => {
    fetchMock.mockResolvedValue(new Response("<html>bad gateway</html>", { status: 502 }));
    const err = await api("/x").catch((e) => e);
    expect(err).toMatchObject({ status: 502, code: "http_error" });
  });

  it("reports a network failure", async () => {
    fetchMock.mockRejectedValue(new TypeError("failed"));
    await expect(api("/x")).rejects.toMatchObject({ code: "network_error" });
  });

  it("tells the listener about a 401, unless quiet", async () => {
    const listener = vi.fn();
    setUnauthorizedListener(listener);
    const body = { code: "unauthorized", message: "Please sign in.", fields: {}, request_id: "" };
    fetchMock.mockResolvedValue(reply(401, body));
    await api("/x").catch(() => undefined);
    expect(listener).toHaveBeenCalledTimes(1);
    fetchMock.mockResolvedValue(reply(401, body));
    await api("/x", { quiet401: true }).catch(() => undefined);
    expect(listener).toHaveBeenCalledTimes(1);
  });
});
