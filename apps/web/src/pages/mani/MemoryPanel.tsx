import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { deleteMemory, listMemory, patchMemory, type MemoryFact } from "@/api/mani";
import { useConfirm } from "@/blocks/confirm";
import { Field, SelectBox } from "@/blocks/fields";
import { EmptyState, ErrorState } from "@/blocks/layout";
import { useAppMutation } from "@/blocks/mutation";
import { StatusBadge } from "@/blocks/status";
import { showDate } from "@/components/format";
import { Button } from "@/ui/button";
import { Skeleton } from "@/ui/skeleton";
import { Textarea } from "@/ui/textarea";

const KEY = ["mani", "memory"];

function FactRow({ fact }: { fact: MemoryFact }) {
  const confirm = useConfirm();
  const [editing, setEditing] = useState(false);
  const [text, setText] = useState(fact.text);
  const [status, setStatus] = useState<MemoryFact["status"]>(fact.status);

  const save = useAppMutation({
    mutationFn: () => patchMemory(fact.id, { text: text.trim(), status }),
    success: "Memory updated.",
    invalidate: [KEY],
    onSuccess: () => setEditing(false),
  });
  const remove = useAppMutation({
    mutationFn: () => deleteMemory(fact.id),
    success: "Memory deleted.",
    invalidate: [KEY],
  });

  async function onSave() {
    const ok = await confirm({
      title: "Change this memory?",
      description: "Mani will use the new wording from the next message.",
      confirmLabel: "Save change",
    });
    if (ok) save.mutate();
  }
  async function onDelete() {
    const ok = await confirm({
      title: "Delete this memory?",
      description: "Mani will forget this fact. This cannot be undone.",
      confirmLabel: "Delete",
      tone: "danger",
    });
    if (ok) remove.mutate();
  }

  if (editing) {
    return (
      <li className="flex flex-col gap-3 py-3">
        <Field label="Memory">{(p) => <Textarea {...p} value={text} maxLength={2000} onChange={(e) => setText(e.target.value)} />}</Field>
        <Field label="Status" className="w-48">
          {(p) => <SelectBox {...p} value={status} onChange={(v) => setStatus(v as MemoryFact["status"])}
                             choices={[{ value: "confirmed", label: "Confirmed" }, { value: "tentative", label: "Tentative" }]} />}
        </Field>
        <div className="flex gap-2">
          <Button disabled={!text.trim() || save.isPending} onClick={() => void onSave()}>Save</Button>
          <Button variant="outline" onClick={() => { setEditing(false); setText(fact.text); setStatus(fact.status); }}>Cancel</Button>
        </div>
      </li>
    );
  }
  return (
    <li className="flex flex-wrap items-start justify-between gap-3 py-3">
      <div className="min-w-0 flex-1">
        <p className="m-0 text-sm break-words">{fact.text}</p>
        <p className="m-0 mt-1 flex items-center gap-2 text-xs text-muted-foreground">
          <StatusBadge status={fact.status === "confirmed" ? "Confirmed" : "Tentative"} tone={fact.status === "confirmed" ? "ok" : "warn"} />
          Saved {showDate(fact.created_at)}
        </p>
      </div>
      <div className="flex gap-2">
        <Button variant="outline" size="sm" className="max-lg:h-10" aria-label={`Edit memory: ${fact.text}`} onClick={() => setEditing(true)}>Edit</Button>
        <Button variant="outline" size="sm" className="max-lg:h-10" aria-label={`Delete memory: ${fact.text}`} disabled={remove.isPending} onClick={() => void onDelete()}>Delete</Button>
      </div>
    </li>
  );
}

/** What Mani remembers about the Founder's way of working. Each fact can be corrected or deleted. */
export function MemoryPanel() {
  const list = useQuery({ queryKey: KEY, queryFn: listMemory });
  if (list.isLoading) return <Skeleton className="h-40" />;
  if (list.isError) return <ErrorState message="Could not load the memory." onRetry={() => void list.refetch()} />;
  const items = list.data?.items ?? [];
  if (items.length === 0) return <EmptyState title="Nothing remembered yet">Mani saves a fact here only when you ask them to.</EmptyState>;
  return <ul className="m-0 list-none divide-y p-0">{items.map((f) => <FactRow key={f.id} fact={f} />)}</ul>;
}
