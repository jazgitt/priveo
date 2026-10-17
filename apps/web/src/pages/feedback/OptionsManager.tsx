import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowDown, ArrowUp, Pencil, Plus } from "lucide-react";
import { useState } from "react";

import { api } from "@/api/client";
import { useConfirm } from "@/blocks/confirm";
import { Field, SelectBox } from "@/blocks/fields";
import { BusyButton, FormDialog } from "@/blocks/FormDialog";
import { ErrorState, Panel } from "@/blocks/layout";
import { useAppMutation } from "@/blocks/mutation";
import { StatusBadge } from "@/blocks/status";
import { cn } from "@/lib/utils";
import { Button } from "@/ui/button";
import { Input } from "@/ui/input";
import { Skeleton } from "@/ui/skeleton";

import type { OptionAdmin } from "../support/types";

const KEY = ["admin", "support-options"] as const;
const KINDS: { kind: string; label: string; about: string }[] = [
  { kind: "feedback_category", label: "Feedback categories", about: "What a customer's feedback is about." },
  { kind: "positive_tag", label: "Positive rating tags", about: "Tags a customer can pick when rating a visit." },
  { kind: "checkin_category", label: "Check-in categories", about: "What the monthly check-in asks about." },
];

/** Add, rename, describe, reorder and deactivate the support lists (ADM-FDB-06, -07). Past answers keep their names. */
export function OptionsManager() {
  const qc = useQueryClient();
  const confirm = useConfirm();
  const list = useQuery({ queryKey: KEY, queryFn: () => api<OptionAdmin[]>("/v1/admin/support/options") });
  const [kind, setKind] = useState(KINDS[0].kind);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [editing, setEditing] = useState<OptionAdmin | null>(null);
  const refresh = () => qc.invalidateQueries({ queryKey: KEY });

  const add = useAppMutation<void>({
    mutationFn: () => api("/v1/admin/support/options", { method: "POST", body: { kind, name: name.trim(), description } }),
    success: () => `${name.trim()} added.`,
    onSuccess: () => { setName(""); setDescription(""); void refresh(); },
  });
  const patch = useAppMutation<{ id: string; patch: Partial<OptionAdmin>; done: string }>({
    mutationFn: (v) => api(`/v1/admin/support/options/${v.id}`, { method: "PATCH", body: v.patch }),
    success: (_d, v) => v.done,
    onSuccess: () => void refresh(),
  });

  if (list.isLoading) return <Skeleton className="h-64" />;
  if (list.isError) return <ErrorState message="Could not load the lists." onRetry={() => void list.refetch()} />;
  const all = list.data ?? [];

  return (
    <div className="grid grid-cols-1 items-start gap-6 xl:grid-cols-[minmax(0,1fr)_22rem]">
      <div className="flex flex-col gap-6">
        {KINDS.map((k) => {
          const rows = all.filter((o) => o.kind === k.kind).sort((a, b) => a.sort_order - b.sort_order);
          // Moving swaps sort order with the neighbour.
          const swap = (a: OptionAdmin, b: OptionAdmin) => {
            patch.mutate({ id: a.id, patch: { sort_order: b.sort_order }, done: "Order saved." });
            patch.mutate({ id: b.id, patch: { sort_order: a.sort_order }, done: "Order saved." });
          };
          return (
            <Panel key={k.kind} title={k.label} description={k.about} bodyClassName="p-0">
              {rows.length === 0 && <p className="m-0 px-5 py-4 text-sm text-muted-foreground">None yet.</p>}
              <ul className="m-0 list-none divide-y p-0">
                {rows.map((o, i) => (
                  <li key={o.id} className={cn("flex items-center gap-3 px-5 py-2.5", !o.active && "bg-muted/40")}>
                    <div className="min-w-0 flex-1">
                      <p className={cn("m-0 text-sm font-medium", !o.active && "text-muted-foreground")}>{o.name}</p>
                      {o.description && <p className="m-0 truncate text-xs text-muted-foreground">{o.description}</p>}
                    </div>
                    {!o.active && <StatusBadge status="Inactive" tone="neutral" />}
                    <div className="flex items-center gap-0.5">
                      <Button size="icon-sm" variant="ghost" disabled={i === 0 || patch.isPending} aria-label={`Move ${o.name} up`} onClick={() => swap(o, rows[i - 1])}><ArrowUp /></Button>
                      <Button size="icon-sm" variant="ghost" disabled={i === rows.length - 1 || patch.isPending} aria-label={`Move ${o.name} down`} onClick={() => swap(o, rows[i + 1])}><ArrowDown /></Button>
                      <Button size="sm" variant="ghost" onClick={() => setEditing(o)}><Pencil aria-hidden /> Edit</Button>
                      <Button size="sm" variant="ghost" className={o.active ? "text-destructive" : undefined} disabled={patch.isPending} onClick={async () => {
                        if (!o.active) patch.mutate({ id: o.id, patch: { active: true }, done: `${o.name} is active.` });
                        else if (await confirm({ title: `Deactivate ${o.name}?`, description: "Customers no longer see it. Past answers keep it.", confirmLabel: "Deactivate", tone: "danger" })) {
                          patch.mutate({ id: o.id, patch: { active: false }, done: `${o.name} is inactive.` });
                        }
                      }}>{o.active ? "Deactivate" : "Activate"}</Button>
                    </div>
                  </li>
                ))}
              </ul>
            </Panel>
          );
        })}
      </div>

      <Panel title="Add an item" className="xl:sticky xl:top-20">
        <form className="flex flex-col gap-4" onSubmit={(e) => { e.preventDefault(); if (name.trim()) add.mutate(); }}>
          <Field label="List">{(p) => <SelectBox {...p} value={kind} onChange={setKind} choices={KINDS.map((k) => ({ value: k.kind, label: k.label }))} />}</Field>
          <Field label="New name">{(p) => <Input {...p} maxLength={80} value={name} onChange={(e) => setName(e.target.value)} />}</Field>
          <Field label="New description" optional>{(p) => <Input {...p} maxLength={300} value={description} onChange={(e) => setDescription(e.target.value)} />}</Field>
          <BusyButton type="submit" busy={add.isPending} disabled={!name.trim()}><Plus aria-hidden /> Add</BusyButton>
        </form>
      </Panel>

      {editing && <EditDialog key={editing.id} option={editing} busy={patch.isPending} onClose={() => setEditing(null)}
                              onSave={(p) => { patch.mutate({ id: editing.id, patch: p, done: "Saved." }); setEditing(null); }} />}
    </div>
  );
}

function EditDialog({ option, busy, onClose, onSave }: {
  option: OptionAdmin; busy: boolean; onClose: () => void; onSave: (p: Partial<OptionAdmin>) => void;
}) {
  const [name, setName] = useState(option.name);
  const [description, setDescription] = useState(option.description);
  return (
    <FormDialog open onOpenChange={(o) => !o && onClose()} title={`Edit ${option.name}`} size="sm"
                description="Past answers keep the name they were given."
                submitLabel="Save" busy={busy} disabled={!name.trim()} onSubmit={() => onSave({ name: name.trim(), description })}>
      <Field label="Name">{(p) => <Input {...p} maxLength={80} value={name} onChange={(e) => setName(e.target.value)} />}</Field>
      <Field label="Description" optional>{(p) => <Input {...p} maxLength={300} value={description} onChange={(e) => setDescription(e.target.value)} />}</Field>
    </FormDialog>
  );
}
