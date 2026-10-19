import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("sonner", () => ({ toast: { loading: vi.fn(() => "t"), success: vi.fn(), error: vi.fn() } }));
vi.mock("@/analytics/analytics", () => ({ track: vi.fn() }));

import { track } from "@/analytics/analytics";
import { ApiError } from "@/api/client";
import { useAppMutation } from "./mutation";

const wrapper = ({ children }: { children: ReactNode }) => (
  <QueryClientProvider client={new QueryClient()}>{children}</QueryClientProvider>
);

beforeEach(() => vi.mocked(track).mockClear());

describe("useAppMutation analytics", () => {
  it("sends the event name when it worked", async () => {
    const { result } = renderHook(() => useAppMutation<void>({
      event: "setting saved", mutationFn: async () => undefined, success: "Saved.",
    }), { wrapper });
    await act(async () => { await result.current.mutateAsync(); });
    expect(track).toHaveBeenCalledWith("setting saved");
  });

  it("sends only status and code when it failed, never the message", async () => {
    const { result } = renderHook(() => useAppMutation<void>({
      event: "setting saved",
      mutationFn: async () => { throw new ApiError(409, "conflict", "Aarav Mehta already exists"); },
      success: "Saved.",
    }), { wrapper });
    await act(async () => { await result.current.mutateAsync().catch(() => undefined); });
    expect(track).toHaveBeenCalledWith("setting saved failed", { status: 409, code: "conflict" });
    expect(JSON.stringify(vi.mocked(track).mock.calls)).not.toContain("Aarav");
  });

  it("sends nothing without an event", async () => {
    const { result } = renderHook(() => useAppMutation<void>({
      mutationFn: async () => undefined, success: "Saved.",
    }), { wrapper });
    await act(async () => { await result.current.mutateAsync(); });
    expect(track).not.toHaveBeenCalled();
  });
});
