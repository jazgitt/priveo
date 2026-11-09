import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { announceBoardChange, BOARD_CHANNEL_NAME, resetBoardSenderForTests, useBoardSync } from "./sync";

/** A stand-in for BroadcastChannel: a message posted on one channel reaches every other open channel of the same name. */
class FakeChannel {
  static all: FakeChannel[] = [];
  onmessage: ((event: { data: unknown }) => void) | null = null;
  closed = false;
  constructor(readonly name: string) {
    FakeChannel.all.push(this);
  }
  postMessage(data: unknown) {
    for (const c of FakeChannel.all) {
      if (c !== this && c.name === this.name && !c.closed) c.onmessage?.({ data });
    }
  }
  close() {
    this.closed = true;
  }
}

let qc: QueryClient;
const wrapper = ({ children }: { children: ReactNode }) => <QueryClientProvider client={qc}>{children}</QueryClientProvider>;

beforeEach(() => {
  FakeChannel.all = [];
  vi.stubGlobal("BroadcastChannel", FakeChannel);
  resetBoardSenderForTests();
  qc = new QueryClient();
});

afterEach(() => {
  resetBoardSenderForTests();
  vi.unstubAllGlobals();
});

describe("same-browser board sync (P0-9)", () => {
  it("a change announced by one tab refreshes the board queries of another tab", () => {
    const invalidate = vi.spyOn(qc, "invalidateQueries").mockResolvedValue(undefined);
    renderHook(() => useBoardSync(), { wrapper });

    // This tab saves a move and tells the others.
    announceBoardChange();

    expect(invalidate).toHaveBeenCalledWith({ queryKey: ["board"] });
  });

  it("ignores messages that are not board changes", () => {
    const invalidate = vi.spyOn(qc, "invalidateQueries").mockResolvedValue(undefined);
    renderHook(() => useBoardSync(), { wrapper });
    const other = new FakeChannel(BOARD_CHANNEL_NAME);
    other.postMessage({ kind: "something-else" });
    other.postMessage("hello");
    expect(invalidate).not.toHaveBeenCalled();
  });

  it("stops listening when the hook unmounts", () => {
    const invalidate = vi.spyOn(qc, "invalidateQueries").mockResolvedValue(undefined);
    const { unmount } = renderHook(() => useBoardSync(), { wrapper });
    unmount();
    announceBoardChange();
    expect(invalidate).not.toHaveBeenCalled();
  });

  it("does nothing in a browser without BroadcastChannel", () => {
    vi.stubGlobal("BroadcastChannel", undefined);
    resetBoardSenderForTests();
    expect(() => announceBoardChange()).not.toThrow();
    const invalidate = vi.spyOn(qc, "invalidateQueries").mockResolvedValue(undefined);
    expect(() => renderHook(() => useBoardSync(), { wrapper })).not.toThrow();
    expect(invalidate).not.toHaveBeenCalled();
  });
});
