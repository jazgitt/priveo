// The Founder-only Mani Bond API (services/api/app/mani/schemas.py). Only the Founder
// can call it: any other admin gets 403, and the portal then hides every Mani page.
// The server enforces this; hiding is only so that nobody sees a page that cannot work.

import { useQuery } from "@tanstack/react-query";

import { api, ApiError, notifyUnauthorized, readCookie } from "./client";

export const MANI = "/v1/admin/mani";

export interface Citation {
  title: string;
  kind: "doc" | "code" | "config" | "data" | "tool";
  path: string;
  requirement_id: string | null;
  commit_id: string;
  as_of: string | null;
}
export interface ManiMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations: Citation[];
  created_at: string;
}
export interface Conversation { id: string; title: string; created_at: string; updated_at: string }
export interface ConversationDetail extends Conversation { messages: ManiMessage[] }
export interface Source {
  path: string; kind: string; title: string; status: "active" | "deleted" | "failed";
  indexed_at: string | null; commit_id: string; chunks: number;
}
export interface Sources { items: Source[]; embedding_model: string; last_indexed_at: string | null }
export interface MemoryFact { id: string; text: string; status: "confirmed" | "tentative"; created_at: string }
export interface UsageDay { day: string; calls: number; prompt_tokens: number; completion_tokens: number; cost_usd: number }
export interface Usage {
  budget_usd: number; spent_usd: number; remaining_usd: number; budget_exhausted: boolean;
  failed_calls: number; average_latency_ms: number; days: UsageDay[];
}
export interface ManiStatus {
  founder: boolean; backend: string; chat_model: string; embedding_model: string; budget_exhausted: boolean;
}

/** What the agent reports while it works on one message (contracts.TurnEvent). */
export type TurnEvent =
  | { kind: "run_started"; data: { run_id: string } }
  | { kind: "tool_call"; data: { name: string; arguments?: Record<string, unknown> } }
  | { kind: "tool_result"; data: { name: string; summary: string } }
  | { kind: "answer"; data: { message_id: string; content: string; citations: Citation[] } }
  | { kind: "budget_exhausted"; data: { spent_usd: number; budget_usd: number } }
  | { kind: "error"; data: { message: string } }
  | { kind: "done"; data: { run_id: string; status: string } };

export type ManiAccess = "loading" | "founder" | "denied" | "error";

/**
 * Whether the signed-in admin is the Founder: true only when the status call
 * answers 200 with `founder: true`. A 403 is a plain "no", not an error.
 */
export function useManiAccess(): { access: ManiAccess; status: ManiStatus | null; retry: () => void } {
  const q = useQuery({
    queryKey: ["mani", "status"],
    queryFn: async (): Promise<ManiStatus | null> => {
      try {
        const s = await api<ManiStatus>(`${MANI}/status`);
        return s && s.founder === true ? s : null;
      } catch (e) {
        if (e instanceof ApiError && (e.status === 403 || e.status === 401)) return null;
        throw e;
      }
    },
    retry: false,
    staleTime: 60_000,
  });
  const access: ManiAccess = q.isPending ? "loading" : q.isError ? "error" : q.data ? "founder" : "denied";
  return { access, status: q.data ?? null, retry: () => void q.refetch() };
}

export const listConversations = () => api<{ items: Conversation[] }>(`${MANI}/conversations`);
export const createConversation = () => api<Conversation>(`${MANI}/conversations`, { method: "POST", body: {} });
export const getConversation = (id: string) => api<ConversationDetail>(`${MANI}/conversations/${id}`);
export const deleteConversation = (id: string) => api<void>(`${MANI}/conversations/${id}`, { method: "DELETE" });
export const getSources = () => api<Sources>(`${MANI}/sources`);
export const listMemory = () => api<{ items: MemoryFact[] }>(`${MANI}/memory`);
export const patchMemory = (id: string, body: { text?: string; status?: "confirmed" | "tentative" }) =>
  api<MemoryFact>(`${MANI}/memory/${id}`, { method: "PATCH", body });
export const deleteMemory = (id: string) => api<void>(`${MANI}/memory/${id}`, { method: "DELETE" });
export const getUsage = () => api<Usage>(`${MANI}/usage`);

/** A failed send. `status` is the HTTP status (0 when the stream broke). */
export class ManiStreamError extends Error {
  readonly status: number;
  constructor(status: number, message: string) {
    super(message);
    this.name = "ManiStreamError";
    this.status = status;
  }
}

/** Parses one server-sent event block (`data: {...}`) into a TurnEvent, or null. */
export function parseEvent(block: string): TurnEvent | null {
  const data = block.split(/\r?\n/).filter((l) => l.startsWith("data:")).map((l) => l.slice(5).trimStart()).join("\n");
  if (!data) return null;
  try {
    const e = JSON.parse(data);
    return e && typeof e.kind === "string" ? ({ kind: e.kind, data: e.data ?? {} } as TurnEvent) : null;
  } catch {
    return null;
  }
}

/**
 * Sends a message and yields the events of the reply as they arrive. The reply is a
 * `text/event-stream`, so it is read with fetch and a stream, not through `api`.
 * It sends the same cookie and CSRF header as `api` does for a change.
 */
export async function* sendMessage(conversationId: string, text: string, signal?: AbortSignal): AsyncGenerator<TurnEvent> {
  const headers: Record<string, string> = {
    Accept: "text/event-stream", "Content-Type": "application/json",
  };
  const csrf = readCookie("priveo_csrf");
  if (csrf) headers["X-CSRF-Token"] = csrf;

  let res: Response;
  try {
    res = await fetch(`${MANI}/conversations/${conversationId}/messages`, {
      method: "POST", headers, credentials: "same-origin", body: JSON.stringify({ text }), signal,
    });
  } catch (e) {
    if (e instanceof DOMException && e.name === "AbortError") throw e;
    throw new ManiStreamError(0, "Cannot reach the server. Check the connection.");
  }
  if (res.status === 401) {
    notifyUnauthorized();
    throw new ManiStreamError(401, "Your session ended. Please sign in again.");
  }
  if (res.status === 403) throw new ManiStreamError(403, "Mani Bond is available to the Founder only.");
  if (!res.ok || !res.body) {
    let message = "Mani could not answer. Please try again.";
    try {
      const b = await res.json();
      if (b && typeof b.message === "string" && b.message) message = b.message;
    } catch { /* not JSON */ }
    throw new ManiStreamError(res.status, message);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  try {
    for (;;) {
      const { value, done } = await reader.read();
      buffer += decoder.decode(value, { stream: !done });
      const blocks = buffer.split(/\r?\n\r?\n/);
      buffer = done ? "" : blocks.pop() ?? "";
      for (const b of blocks) {
        const ev = parseEvent(b);
        if (ev) yield ev;
      }
      if (done) break;
    }
  } catch (e) {
    if (e instanceof DOMException && e.name === "AbortError") throw e;
    throw new ManiStreamError(0, "The connection broke before Mani finished.");
  }
}
