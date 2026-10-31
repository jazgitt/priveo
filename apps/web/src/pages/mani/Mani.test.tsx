import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { AppRoutes } from "@/App";
import { setUnauthorizedListener } from "@/api/client";
import { sendMessage, type TurnEvent } from "@/api/mani";
import { AuthProvider } from "@/auth/AuthContext";
import { ToastProvider } from "@/components";
import { confirmWith, PortalProviders } from "@/test/portal";
import { ManiPage } from "./ManiPage";
import { UsagePage } from "./UsagePage";

const fetchMock = vi.fn();
const profile = { user_id: "u1", role: "admin", display_name: "Priveo Papa" };
const status = { founder: true, backend: "local", chat_model: "m", embedding_model: "e", budget_exhausted: false };
const forbidden = { code: "forbidden", message: "Founder only.", fields: {}, request_id: "" };
const conv = { id: "c1", title: "Plans review", created_at: "2026-10-20T05:00:00Z", updated_at: "2026-10-21T05:00:00Z" };
const facts = [{ id: "f1", text: "Prefers short answers", status: "tentative", created_at: "2026-10-22T05:00:00Z" }];

const json = (status: number, body?: unknown) => new Response(body === undefined ? null : JSON.stringify(body), { status });
const sse = (events: object[], status = 200) => {
  const enc = new TextEncoder();
  const body = new ReadableStream({
    start(c) {
      // Split mid-event to prove the parser joins chunks.
      const text = events.map((e) => `data: ${JSON.stringify(e)}\n\n`).join("");
      c.enqueue(enc.encode(text.slice(0, 20)));
      c.enqueue(enc.encode(text.slice(20)));
      c.close();
    },
  });
  return new Response(body, { status, headers: { "Content-Type": "text/event-stream" } });
};

type Handler = (url: string, init?: RequestInit) => Response | Promise<Response>;
let routes: Record<string, Handler> = {};
const calls = (needle: string, method = "GET") =>
  fetchMock.mock.calls.filter((c) => String(c[0]).includes(needle) && (c[1]?.method ?? "GET") === method);

beforeEach(() => {
  routes = {
    "/v1/web/me": () => json(200, profile),
    "/v1/admin/mani/status": () => json(200, status),
    "/v1/admin/mani/conversations": (_u, init) => init?.method === "POST" ? json(201, conv) : json(200, { items: [conv] }),
    "/v1/admin/mani/conversations/c1": (_u, init) => init?.method === "DELETE"
      ? json(204) : json(200, { ...conv, messages: [] }),
    "/v1/admin/mani/memory": () => json(200, { items: facts }),
    "/v1/admin/mani/memory/f1": () => json(200, facts[0]),
    "/v1/admin/mani/sources": () => json(200, {
      items: [{ path: "docs/a.md", kind: "doc", title: "Plan doc", status: "active", indexed_at: "2026-10-05T01:00:00Z", commit_id: "abc1234", chunks: 4 }],
      embedding_model: "bge-m3", last_indexed_at: "2026-10-06T01:00:00Z",
    }),
    "/v1/admin/mani/usage": () => json(200, {
      budget_usd: 50, spent_usd: 12.5, remaining_usd: 37.5, budget_exhausted: false, failed_calls: 3, average_latency_ms: 840,
      days: [{ day: "2026-10-07", calls: 9, prompt_tokens: 1200, completion_tokens: 300, cost_usd: 0.42 }],
    }),
  };
  fetchMock.mockImplementation(async (url: string, init?: RequestInit) => {
    const path = String(url).split("?")[0];
    const h = routes[path] ?? routes[Object.keys(routes).find((k) => path.startsWith(k + "/messages")) ?? ""];
    return h ? h(path, init) : json(404, { code: "not_found", message: "no", fields: {}, request_id: "" });
  });
  vi.stubGlobal("fetch", fetchMock);
});
afterEach(() => { fetchMock.mockReset(); vi.unstubAllGlobals(); });

function wrap(ui: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter><PortalProviders>{ui}</PortalProviders></MemoryRouter>
    </QueryClientProvider>,
  );
}
function app(path: string) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[path]}>
        <ToastProvider><AuthProvider><AppRoutes /></AuthProvider></ToastProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}
const messageRoute = (events: object[], status = 200) => {
  routes["/v1/admin/mani/conversations/c1/messages"] = () => sse(events, status);
};
async function ask(text: string) {
  await userEvent.click(await screen.findByRole("button", { name: /^Plans review/ }));
  await userEvent.type(screen.getByLabelText("Message"), text);
  await userEvent.click(screen.getByRole("button", { name: "Send" }));
}

describe("Founder gating", () => {
  it("shows the nav items and the page to the Founder", async () => {
    app("/mani");
    const nav = await screen.findByRole("navigation", { name: "Admin areas" });
    expect(await within(nav).findByRole("link", { name: "Mani Bond" })).toBeInTheDocument();
    expect(within(nav).getByRole("link", { name: "Agent" })).toBeInTheDocument();
    expect(await screen.findByRole("heading", { name: "Mani Bond" })).toBeInTheDocument();
  });

  it("hides the nav items from another admin and says Not available at the URL", async () => {
    routes["/v1/admin/mani/status"] = () => json(403, forbidden);
    app("/mani");
    expect(await screen.findByRole("heading", { name: "Not available" })).toBeInTheDocument();
    const nav = screen.getByRole("navigation", { name: "Admin areas" });
    expect(within(nav).queryByRole("link", { name: "Mani Bond" })).not.toBeInTheDocument();
    expect(within(nav).queryByRole("link", { name: "Agent" })).not.toBeInTheDocument();
    expect(calls("/conversations")).toHaveLength(0);
  });

  it("shows Not available on the Agent report too", async () => {
    routes["/v1/admin/mani/status"] = () => json(403, forbidden);
    app("/reports/agent");
    expect(await screen.findByRole("heading", { name: "Not available" })).toBeInTheDocument();
    expect(calls("/usage")).toHaveLength(0);
  });
});

describe("chat", () => {
  it("streams tool activity, then the answer with citations and dd-Mon-yy dates", async () => {
    // An open stream, so the screen can be checked before the reply ends.
    const enc = new TextEncoder();
    let ctl!: ReadableStreamDefaultController<Uint8Array>;
    const push = (e: object) => ctl.enqueue(enc.encode(`data: ${JSON.stringify(e)}\n\n`));
    routes["/v1/admin/mani/conversations/c1/messages"] = () => new Response(
      new ReadableStream<Uint8Array>({ start(c) { ctl = c; } }), { status: 200 });
    wrap(<ManiPage />);
    await ask("How many payments are over due?");
    await waitFor(() => expect(ctl).toBeDefined());
    push({ kind: "run_started", data: { run_id: "r1" } });
    push({ kind: "tool_call", data: { name: "payments_summary", arguments: {} } });
    expect(await screen.findByText("Looking up payments_summary…")).toBeInTheDocument();
    push({ kind: "tool_result", data: { name: "payments_summary", summary: "12 payments over due" } });
    expect(await screen.findByText("payments_summary: 12 payments over due")).toBeInTheDocument();
    expect(screen.queryByText("Twelve payments are over due.")).not.toBeInTheDocument();
    push({ kind: "answer", data: { message_id: "m2", content: "Twelve payments are over due.", citations: [
      { title: "Payments summary", kind: "tool", path: "payments_summary", requirement_id: "ADM-PAY-01", commit_id: "", as_of: "2026-10-07T04:00:00Z" },
      { title: "Billing doc", kind: "doc", path: "docs/billing.md", requirement_id: null, commit_id: "abcdef123456", as_of: "2026-10-05T04:00:00Z" },
    ] } });
    expect(await screen.findByText("Twelve payments are over due.")).toBeInTheDocument();
    const cites = screen.getByRole("list", { name: "Sources" });
    expect(cites).toHaveTextContent("Payments summary · tool payments_summary · ADM-PAY-01 · as of 07-Oct-26");
    expect(cites).toHaveTextContent("Billing doc · docs/billing.md · commit abcdef1 · as of 05-Oct-26");
    const [, init] = calls("/messages", "POST")[0];
    expect(JSON.parse(init.body)).toEqual({ text: "How many payments are over due?" });
    expect(init.credentials).toBe("same-origin");
    push({ kind: "done", data: { run_id: "r1", status: "ok" } });
    ctl.close();
  });

  it("shows a budget banner when the budget runs out", async () => {
    messageRoute([
      { kind: "budget_exhausted", data: { spent_usd: 50, budget_usd: 50 } },
      { kind: "done", data: { run_id: "r1", status: "budget" } },
    ]);
    wrap(<ManiPage />);
    await ask("Hello");
    expect(await screen.findByRole("alert")).toHaveTextContent("budget is used up");
    expect(screen.getByLabelText("Message")).toBeDisabled();
  });

  it("shows the banner at once when the status says the budget is used", async () => {
    routes["/v1/admin/mani/status"] = () => json(200, { ...status, budget_exhausted: true });
    wrap(<ManiPage />);
    expect(await screen.findByRole("alert")).toHaveTextContent("budget is used up");
  });

  it("shows an error event plainly", async () => {
    messageRoute([{ kind: "error", data: { message: "The model timed out." } }, { kind: "done", data: { run_id: "r1", status: "error" } }]);
    wrap(<ManiPage />);
    await ask("Hello");
    expect(await screen.findByText("The model timed out.")).toBeInTheDocument();
  });

  it("shows a failed request plainly", async () => {
    routes["/v1/admin/mani/conversations/c1/messages"] = () => json(500, { code: "x", message: "Mani is down." });
    wrap(<ManiPage />);
    await ask("Hello");
    expect(await screen.findByText("Mani is down.")).toBeInTheDocument();
  });

  it("shows a proposal as a draft card", async () => {
    routes["/v1/admin/mani/conversations/c1"] = () => json(200, { ...conv, messages: [
      { id: "m1", role: "assistant", content: "Proposal: raise the Gold plan by 5%.", citations: [], created_at: "2026-10-21T05:00:00Z" },
    ] });
    wrap(<ManiPage />);
    await userEvent.click(await screen.findByRole("button", { name: /^Plans review/ }));
    expect(await screen.findByText("Draft, nothing has been changed.")).toBeInTheDocument();
    expect(screen.getByText("raise the Gold plan by 5%.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /execute|apply/i })).not.toBeInTheDocument();
  });

  it("asks before deleting a conversation", async () => {
    wrap(<ManiPage />);
    await userEvent.click(await screen.findByRole("button", { name: "Delete conversation Plans review" }));
    await screen.findByRole("alertdialog");
    expect(calls("/conversations/c1", "DELETE")).toHaveLength(0);
    await confirmWith("Delete");
    await waitFor(() => expect(calls("/conversations/c1", "DELETE")).toHaveLength(1));
  });
});

describe("stream reader", () => {
  it("fails cleanly on 403 and sends the CSRF header", async () => {
    document.cookie = "priveo_csrf=tok123";
    routes["/v1/admin/mani/conversations/c1/messages"] = () => json(403, forbidden);
    const run = async () => { const out: TurnEvent[] = []; for await (const e of sendMessage("c1", "hi")) out.push(e); return out; };
    await expect(run()).rejects.toMatchObject({ status: 403 });
    expect(calls("/messages", "POST")[0][1].headers["X-CSRF-Token"]).toBe("tok123");
    document.cookie = "priveo_csrf=; expires=Thu, 01 Jan 1970 00:00:00 GMT";
  });

  it("shows the sign-in prompt when the session has ended (401)", async () => {
    const signedOut = vi.fn();
    setUnauthorizedListener(signedOut);
    routes["/v1/admin/mani/conversations/c1/messages"] = () => json(401, { code: "unauthorized", message: "Please sign in." });
    const run = async () => { const out: TurnEvent[] = []; for await (const e of sendMessage("c1", "hi")) out.push(e); return out; };
    await expect(run()).rejects.toMatchObject({ status: 401 });
    expect(signedOut).toHaveBeenCalledTimes(1);
    setUnauthorizedListener(null);
  });
});

describe("memory and sources", () => {
  it("asks before saving a memory edit and before deleting it", async () => {
    wrap(<ManiPage />);
    await userEvent.click(await screen.findByRole("tab", { name: "Memory" }));
    await userEvent.click(await screen.findByRole("button", { name: /Edit memory/ }));
    const box = screen.getByRole("textbox", { name: "Memory" });
    await userEvent.clear(box);
    await userEvent.type(box, "Prefers bullet points");
    await userEvent.click(screen.getByRole("button", { name: "Save" }));
    await screen.findByRole("alertdialog");
    expect(calls("/memory/f1", "PATCH")).toHaveLength(0);
    await confirmWith("Save change");
    await waitFor(() => expect(calls("/memory/f1", "PATCH")).toHaveLength(1));
    expect(JSON.parse(calls("/memory/f1", "PATCH")[0][1].body)).toEqual({ text: "Prefers bullet points", status: "tentative" });

    await userEvent.click(await screen.findByRole("button", { name: /Delete memory/ }));
    await screen.findByRole("alertdialog");
    expect(calls("/memory/f1", "DELETE")).toHaveLength(0);
    await confirmWith("Delete");
    await waitFor(() => expect(calls("/memory/f1", "DELETE")).toHaveLength(1));
  });

  it("lists sources with status, indexed date and the embedding model", async () => {
    wrap(<ManiPage />);
    await userEvent.click(await screen.findByRole("tab", { name: "Sources" }));
    expect(await screen.findByText("Plan doc")).toBeInTheDocument();
    expect(screen.getByText("Active")).toBeInTheDocument();
    expect(screen.getByText("05-Oct-26")).toBeInTheDocument();
    expect(screen.getByText("06-Oct-26")).toBeInTheDocument();
    expect(screen.getByText("bge-m3")).toBeInTheDocument();
  });
});

describe("Agent report", () => {
  it("shows the usage numbers and the daily table", async () => {
    wrap(<UsagePage />);
    expect(await screen.findByText("$50.00")).toBeInTheDocument();
    expect(screen.getByText("$12.50")).toBeInTheDocument();
    expect(screen.getByText("$37.50")).toBeInTheDocument();
    expect(screen.getByText("840 ms")).toBeInTheDocument();
    expect(screen.getByText("07-Oct-26")).toBeInTheDocument();
    expect(screen.getByText("$0.42")).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("flags an exhausted budget", async () => {
    routes["/v1/admin/mani/usage"] = () => json(200, {
      budget_usd: 50, spent_usd: 50, remaining_usd: 0, budget_exhausted: true, failed_calls: 0, average_latency_ms: 100, days: [],
    });
    wrap(<UsagePage />);
    expect(await screen.findByRole("alert")).toHaveTextContent("budget is used up");
    expect(screen.getByText("Budget used up")).toBeInTheDocument();
  });
});
