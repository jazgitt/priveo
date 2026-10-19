import { render } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const auth = vi.hoisted(() => ({ value: { status: "loading", user: null } as {
  status: string; user: { user_id: string; role: string; display_name: string } | null } }));
vi.mock("../auth/AuthContext", () => ({ useAuth: () => auth.value }));
vi.mock("./analytics", () => ({ identifyUser: vi.fn(), resetUser: vi.fn() }));

import { AnalyticsBridge } from "./AnalyticsBridge";
import { identifyUser, resetUser } from "./analytics";

beforeEach(() => {
  vi.mocked(identifyUser).mockClear();
  vi.mocked(resetUser).mockClear();
});

describe("AnalyticsBridge", () => {
  it("does nothing while loading", () => {
    auth.value = { status: "loading", user: null };
    render(<AnalyticsBridge />);
    expect(identifyUser).not.toHaveBeenCalled();
    expect(resetUser).not.toHaveBeenCalled();
  });

  it("identifies by id and role only, never the name", () => {
    auth.value = { status: "signedIn", user: { user_id: "u1", role: "admin", display_name: "Priveo Admin" } };
    render(<AnalyticsBridge />);
    expect(identifyUser).toHaveBeenCalledWith("u1", "admin");
    expect(JSON.stringify(vi.mocked(identifyUser).mock.calls)).not.toContain("Priveo Admin");
  });

  it("resets when signed out", () => {
    auth.value = { status: "signedOut", user: null };
    render(<AnalyticsBridge />);
    expect(resetUser).toHaveBeenCalledTimes(1);
  });
});
