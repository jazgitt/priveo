import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { EnvBanner } from "./EnvBanner";

const fetchMock = vi.fn();

function answer(body: unknown, status = 200) {
  fetchMock.mockResolvedValue(new Response(JSON.stringify(body), { status }));
}

beforeEach(() => vi.stubGlobal("fetch", fetchMock));
afterEach(() => {
  fetchMock.mockReset();
  vi.unstubAllGlobals();
});

describe("EnvBanner", () => {
  it("shows a banner on the test server", async () => {
    answer({ min_app_version: "0.1.0", environment: "test" });
    render(<EnvBanner />);
    expect(await screen.findByRole("status")).toHaveTextContent("TEST portal");
  });

  it.each(["prod", "dev"])("shows nothing on %s", async (environment) => {
    answer({ min_app_version: "0.1.0", environment });
    render(<EnvBanner />);
    await waitFor(() => expect(fetchMock).toHaveBeenCalled());
    expect(screen.queryByRole("status")).toBeNull();
  });

  it("shows nothing when the config cannot be read", async () => {
    answer({ code: "boom", message: "x", fields: {}, request_id: "" }, 500);
    render(<EnvBanner />);
    await waitFor(() => expect(fetchMock).toHaveBeenCalled());
    expect(screen.queryByRole("status")).toBeNull();
  });
});
