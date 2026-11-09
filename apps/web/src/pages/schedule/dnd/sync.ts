// Same-browser sync for the scheduler (P0-9, decision 9). Tabs of one browser
// tell each other when a board changed, and each tab re-reads its board.
// Cross-device sync is not part of this build.
import { useEffect } from "react";
import { useQueryClient, type QueryKey } from "@tanstack/react-query";

export const BOARD_CHANNEL_NAME = "priveo-schedule-board";

/** The message one tab sends after a change is saved. */
export interface BoardChangeMessage {
  kind: "board-changed";
  at: number;
}

/** The queries a change refreshes in every open tab. */
export const BOARD_KEYS: QueryKey[] = [["board"]];

function isBoardChange(data: unknown): data is BoardChangeMessage {
  return typeof data === "object" && data !== null && (data as { kind?: unknown }).kind === "board-changed";
}

let sender: BroadcastChannel | null = null;

/** Tells the other tabs of this browser that the board changed. A browser without BroadcastChannel does nothing. */
export function announceBoardChange(): void {
  if (typeof globalThis.BroadcastChannel === "undefined") return;
  try {
    sender ??= new globalThis.BroadcastChannel(BOARD_CHANNEL_NAME);
    const message: BoardChangeMessage = { kind: "board-changed", at: Date.now() };
    sender.postMessage(message);
  } catch {
    // A tab that cannot post simply does not tell the others; its own board is already right.
  }
}

/** Calls `onChange` when another tab of this browser announces a change. Returns the stop function. */
export function listenForBoardChanges(onChange: (message: BoardChangeMessage) => void): () => void {
  if (typeof globalThis.BroadcastChannel === "undefined") return () => {};
  let channel: BroadcastChannel;
  try {
    channel = new globalThis.BroadcastChannel(BOARD_CHANNEL_NAME);
  } catch {
    return () => {};
  }
  channel.onmessage = (event: MessageEvent) => {
    if (isBoardChange(event.data)) onChange(event.data);
  };
  return () => channel.close();
}

/**
 * Re-reads the board queries when another tab of this browser saves a change,
 * so the change shows here within about a second. Mounted by the drag engine
 * provider, which every editable board is wrapped in.
 */
export function useBoardSync(keys: QueryKey[] = BOARD_KEYS): void {
  const qc = useQueryClient();
  useEffect(() => listenForBoardChanges(() => {
    for (const queryKey of keys) void qc.invalidateQueries({ queryKey });
  }), [qc, keys]);
}

/** Test-only: forgets the sending channel so a test can install its own BroadcastChannel. */
export function resetBoardSenderForTests(): void {
  sender?.close();
  sender = null;
}
