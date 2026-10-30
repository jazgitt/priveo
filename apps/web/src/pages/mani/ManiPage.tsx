import { useQuery, useQueryClient } from "@tanstack/react-query";
import { History, Plus, Send, Trash2 } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import {
  createConversation, deleteConversation, getConversation, listConversations, sendMessage,
  useManiAccess, type Citation, type Conversation, type ManiMessage,
} from "@/api/mani";
import { useConfirm } from "@/blocks/confirm";
import { ErrorState, PageHeader } from "@/blocks/layout";
import { useAppMutation, errorMessage } from "@/blocks/mutation";
import { showDate } from "@/components/format";
import { cn } from "@/lib/utils";
import { Button } from "@/ui/button";
import { Sheet, SheetContent, SheetDescription, SheetTitle } from "@/ui/sheet";
import { Skeleton } from "@/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/ui/tabs";
import { Textarea } from "@/ui/textarea";
import { ManiGate } from "./ManiGate";
import { MemoryPanel } from "./MemoryPanel";
import { SourcesPanel } from "./SourcesPanel";

const CONVERSATIONS = ["mani", "conversations"];

/** Where an answer's evidence came from, with its freshness, so a stale source is visible. */
export function Citations({ items }: { items: Citation[] }) {
  if (items.length === 0) return null;
  return (
    <ul aria-label="Sources" className="m-0 mt-3 flex list-none flex-col gap-1 border-t p-0 pt-2 text-xs text-muted-foreground">
      {items.map((c, i) => (
        <li key={`${c.path}-${i}`} className="break-words">
          <span className="font-medium text-foreground">{c.title}</span>
          {c.path && <> · {c.kind === "tool" ? `tool ${c.path}` : c.path}</>}
          {c.requirement_id && <> · {c.requirement_id}</>}
          {c.commit_id && <> · commit {c.commit_id.slice(0, 7)}</>}
          {c.as_of && <> · as of {showDate(c.as_of)}</>}
        </li>
      ))}
    </ul>
  );
}

/** A reply that starts "Proposal:" is shown as a draft card. Nothing is executed. */
function Content({ text }: { text: string }) {
  if (text.startsWith("Proposal:")) {
    return (
      <div className="rounded-lg border border-dashed border-gold-text/60 bg-background p-3">
        <p className="m-0 mb-2 text-xs font-semibold tracking-wide text-gold-text uppercase">Proposal</p>
        <p className="m-0 whitespace-pre-wrap break-words text-sm">{text.slice("Proposal:".length).trim()}</p>
        <p className="m-0 mt-2 text-xs text-muted-foreground">Draft, nothing has been changed.</p>
      </div>
    );
  }
  return <p className="m-0 whitespace-pre-wrap break-words text-sm">{text}</p>;
}

function Bubble({ m }: { m: Pick<ManiMessage, "role" | "content" | "citations"> }) {
  const mine = m.role === "user";
  return (
    <div className={cn("flex", mine ? "justify-end" : "justify-start")}>
      <div className={cn("max-w-[85%] rounded-xl px-4 py-3", mine ? "bg-accent" : "border bg-card")}>
        <p className="sr-only">{mine ? "You" : "Mani"}</p>
        <Content text={m.content} />
        <Citations items={m.citations} />
      </div>
    </div>
  );
}

interface Activity { id: number; text: string }
interface Live {
  user: string;
  activity: Activity[];
  answer: { content: string; citations: Citation[] } | null;
}

function ConversationList({ items, selected, onSelect, onNew, onDelete, creating }: {
  items: Conversation[] | undefined; selected: string | null;
  onSelect: (id: string) => void; onNew: () => void; onDelete: (c: Conversation) => void; creating: boolean;
}) {
  return (
    <div className="flex flex-col gap-2">
      <Button variant="outline" onClick={onNew} disabled={creating}><Plus aria-hidden /> New conversation</Button>
      {items === undefined && <Skeleton className="h-24" />}
      {items?.length === 0 && <p className="m-0 px-1 text-sm text-muted-foreground">No conversations yet.</p>}
      <ul aria-label="Conversations" className="m-0 flex list-none flex-col gap-1 p-0">
        {items?.map((c) => (
          <li key={c.id} className={cn("flex items-center gap-1 rounded-md", c.id === selected && "bg-accent")}>
            <button type="button" onClick={() => onSelect(c.id)} aria-current={c.id === selected || undefined}
                    className="min-h-10 min-w-0 flex-1 cursor-pointer rounded-md px-3 py-1.5 text-left text-sm hover:bg-accent">
              <span className="block truncate font-medium">{c.title || "New conversation"}</span>
              <span className="block text-xs text-muted-foreground">{showDate(c.updated_at)}</span>
            </button>
            <Button variant="ghost" size="icon" aria-label={`Delete conversation ${c.title || "New conversation"}`} onClick={() => onDelete(c)}>
              <Trash2 aria-hidden />
            </Button>
          </li>
        ))}
      </ul>
    </div>
  );
}

function Chat({ budgetUsed }: { budgetUsed: boolean }) {
  const qc = useQueryClient();
  const confirm = useConfirm();
  const [selected, setSelected] = useState<string | null>(null);
  const [drawer, setDrawer] = useState(false);
  const [text, setText] = useState("");
  const [live, setLive] = useState<Live | null>(null);
  const [error, setError] = useState("");
  const [budgetBanner, setBudgetBanner] = useState(false);
  const abort = useRef<AbortController | null>(null);
  const bottom = useRef<HTMLDivElement>(null);

  const list = useQuery({ queryKey: CONVERSATIONS, queryFn: listConversations });
  const detail = useQuery({
    queryKey: ["mani", "conversation", selected],
    queryFn: () => getConversation(selected as string),
    enabled: selected !== null,
  });

  useEffect(() => () => abort.current?.abort(), []);
  useEffect(() => { bottom.current?.scrollIntoView?.({ block: "end" }); }, [detail.data, live]);

  const create = useAppMutation({
    mutationFn: createConversation,
    success: "New conversation started.",
    invalidate: [CONVERSATIONS],
    onSuccess: (c) => { setSelected(c.id); setDrawer(false); setError(""); setLive(null); },
  });
  const remove = useAppMutation<Conversation>({
    mutationFn: (c) => deleteConversation(c.id),
    success: "Conversation deleted.",
    invalidate: [CONVERSATIONS],
    onSuccess: (_d, c) => { if (c.id === selected) setSelected(null); },
  });

  async function askDelete(c: Conversation) {
    const ok = await confirm({
      title: "Delete this conversation?",
      description: `"${c.title || "New conversation"}" and its messages will be removed. This cannot be undone.`,
      confirmLabel: "Delete",
      tone: "danger",
    });
    if (ok) remove.mutate(c);
  }

  async function send() {
    const value = text.trim();
    if (!value || live) return;
    setError("");
    setText("");
    let id = selected;
    try {
      if (!id) {
        const c = await createConversation();
        id = c.id;
        setSelected(id);
        void qc.invalidateQueries({ queryKey: CONVERSATIONS });
      }
    } catch (e) {
      setError(errorMessage(e));
      setText(value);
      return;
    }
    const ctl = new AbortController();
    abort.current = ctl;
    let n = 0;
    setLive({ user: value, activity: [], answer: null });
    try {
      for await (const ev of sendMessage(id, value, ctl.signal)) {
        if (ev.kind === "tool_call") {
          setLive((l) => l && { ...l, activity: [...l.activity, { id: n++, text: `Looking up ${ev.data.name}…` }] });
        } else if (ev.kind === "tool_result") {
          setLive((l) => l && { ...l, activity: [...l.activity, { id: n++, text: `${ev.data.name}: ${ev.data.summary}` }] });
        } else if (ev.kind === "answer") {
          setLive((l) => l && { ...l, answer: { content: ev.data.content, citations: ev.data.citations ?? [] } });
        } else if (ev.kind === "budget_exhausted") {
          setBudgetBanner(true);
        } else if (ev.kind === "error") {
          setError(ev.data.message || "Mani could not answer. Please try again.");
        }
      }
    } catch (e) {
      if (!(e instanceof DOMException && e.name === "AbortError")) setError(errorMessage(e));
    }
    await Promise.all([
      qc.invalidateQueries({ queryKey: ["mani", "conversation", id] }),
      qc.invalidateQueries({ queryKey: CONVERSATIONS }),
      qc.invalidateQueries({ queryKey: ["mani", "status"] }),
    ]);
    setLive(null);
  }

  const exhausted = budgetUsed || budgetBanner;
  const sidebar = (
    <ConversationList items={list.data?.items} selected={selected}
                      onSelect={(id) => { setSelected(id); setDrawer(false); setError(""); }}
                      onNew={() => create.mutate()} onDelete={(c) => void askDelete(c)} creating={create.isPending} />
  );
  const messages = detail.data?.messages ?? [];

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-[16rem_minmax(0,1fr)]">
      <aside className="hidden lg:block">{sidebar}</aside>
      <Sheet open={drawer} onOpenChange={setDrawer}>
        <SheetContent side="left" className="w-80 max-w-[85vw] p-4 lg:hidden">
          <SheetTitle>Conversations</SheetTitle>
          <SheetDescription className="sr-only">Choose a conversation or start a new one.</SheetDescription>
          {sidebar}
        </SheetContent>
      </Sheet>

      <section aria-label="Conversation" className="flex min-h-[28rem] min-w-0 flex-col gap-4">
        <div className="lg:hidden">
          <Button variant="outline" onClick={() => setDrawer(true)}><History aria-hidden /> Conversations</Button>
        </div>
        {exhausted && (
          <p role="alert" className="m-0 rounded-lg border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm text-destructive">
            The Mani Bond budget is used up, so Mani cannot answer now. Old conversations can still be read.
          </p>
        )}
        {detail.isError && <ErrorState message="Could not load this conversation." onRetry={() => void detail.refetch()} />}
        <div className="flex flex-1 flex-col gap-3" aria-live="polite">
          {selected === null && !live && (
            <p className="m-0 text-sm text-muted-foreground">Ask Mani a question, or choose a conversation.</p>
          )}
          {detail.isLoading && <Skeleton className="h-32" />}
          {messages.map((m) => <Bubble key={m.id} m={m} />)}
          {live && (
            <>
              <Bubble m={{ role: "user", content: live.user, citations: [] }} />
              {live.activity.length > 0 && (
                <ul aria-label="Mani is working" className="m-0 flex list-none flex-col gap-1 p-0 text-xs text-muted-foreground">
                  {live.activity.map((a) => <li key={a.id}>{a.text}</li>)}
                </ul>
              )}
              {live.answer
                ? <Bubble m={{ role: "assistant", content: live.answer.content, citations: live.answer.citations }} />
                : <p className="m-0 text-sm text-muted-foreground">Mani is working…</p>}
            </>
          )}
          <div ref={bottom} />
        </div>
        {error && <ErrorState message={error} />}
        <form className="flex flex-col gap-2 sm:flex-row sm:items-end"
              onSubmit={(e) => { e.preventDefault(); void send(); }}>
          <Textarea aria-label="Message" value={text} maxLength={4000} rows={2} disabled={exhausted}
                    placeholder="Ask Mani…" onChange={(e) => setText(e.target.value)}
                    onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); void send(); } }} />
          <Button type="submit" className="max-lg:h-11" disabled={!text.trim() || live !== null || exhausted}>
            <Send aria-hidden /> Send
          </Button>
        </form>
      </section>
    </div>
  );
}

function Mani() {
  const { status } = useManiAccess();
  return (
    <>
      <PageHeader title="Mani Bond" description="Your Chief of Staff. Mani reads, drafts and advises. They change nothing." />
      <Tabs defaultValue="chat">
        <TabsList className="mb-4">
          <TabsTrigger value="chat">Chat</TabsTrigger>
          <TabsTrigger value="memory">Memory</TabsTrigger>
          <TabsTrigger value="sources">Sources</TabsTrigger>
        </TabsList>
        <TabsContent value="chat"><Chat budgetUsed={status?.budget_exhausted ?? false} /></TabsContent>
        <TabsContent value="memory"><MemoryPanel /></TabsContent>
        <TabsContent value="sources"><SourcesPanel /></TabsContent>
      </Tabs>
    </>
  );
}

/** Mani Bond: the Founder's chat, with what Mani remembers and reads (Founder only). */
export function ManiPage() {
  return <ManiGate><Mani /></ManiGate>;
}
