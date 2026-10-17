import { ArrowDown, ArrowUp, Pencil, Plus } from "lucide-react";
import { useState } from "react";

import { useConfirm } from "@/blocks/confirm";
import { Field } from "@/blocks/fields";
import { BusyButton } from "@/blocks/FormDialog";
import { cn } from "@/lib/utils";
import { Button } from "@/ui/button";
import { Input } from "@/ui/input";

import { fieldError, moved, useDirSave } from "./api";
import { ActiveChip, Notice } from "./common";

export interface OrderedRow {
  id: string;
  label: string;
  active: boolean;
}

/**
 * A list the admin can add to, rename, reorder and deactivate. Used for the
 * checklists (ADM-CHK) and the could-not-complete reasons (ADM-CNC).
 * `itemPath` is the base for rename/deactivate, `addPath` and `orderPath` are
 * full paths under the directory API.
 */
export function OrderedList({ rows, noun, addPath, orderPath, itemPath, renameNote }: {
  rows: OrderedRow[];
  noun: string;
  addPath: string;
  orderPath: string;
  itemPath: string;
  renameNote?: string;
}) {
  const confirm = useConfirm();
  const mut = useDirSave();
  const [label, setLabel] = useState("");
  const [editId, setEditId] = useState<string | null>(null);
  const [draft, setDraft] = useState("");

  return (
    <div className="flex flex-col gap-4">
      {renameNote && <p className="m-0 text-sm text-muted-foreground">{renameNote}</p>}
      <Notice error={mut.error} />
      <ol className="m-0 list-none divide-y rounded-lg border p-0">
        {rows.map((r, i) => (
          <li key={r.id} className={cn("flex min-h-12 items-center gap-3 px-3 py-1.5", !r.active && "bg-muted/40")}>
            <span className="w-6 text-right text-xs tabular-nums text-muted-foreground">{i + 1}</span>
            {editId === r.id ? (
              <form className="flex flex-1 flex-wrap items-center gap-2"
                    onSubmit={(e) => { e.preventDefault(); if (draft.trim()) mut.mutate({ path: `${itemPath}/${r.id}`, method: "PATCH", body: { label: draft.trim() }, done: "Renamed." }, { onSuccess: () => setEditId(null) }); }}>
                <Input aria-label={`New text for ${r.label}`} className="h-8 max-w-md flex-1" maxLength={120} value={draft} onChange={(e) => setDraft(e.target.value)} autoFocus />
                <BusyButton type="submit" size="sm" busy={mut.isPending} disabled={!draft.trim()}>Save</BusyButton>
                <Button type="button" size="sm" variant="ghost" onClick={() => setEditId(null)}>Cancel</Button>
              </form>
            ) : (
              <>
                <span className={cn("flex-1 text-sm", !r.active && "text-muted-foreground")}>{r.label}</span>
                {!r.active && <ActiveChip active={false} />}
                <div className="flex items-center gap-0.5">
                  <Button size="icon-sm" variant="ghost" disabled={i === 0 || mut.isPending} aria-label={`Move ${r.label} up`}
                          onClick={() => mut.mutate({ path: orderPath, method: "PUT", body: { ids: moved(rows, i, -1) }, done: "Order saved." })}><ArrowUp /></Button>
                  <Button size="icon-sm" variant="ghost" disabled={i === rows.length - 1 || mut.isPending} aria-label={`Move ${r.label} down`}
                          onClick={() => mut.mutate({ path: orderPath, method: "PUT", body: { ids: moved(rows, i, 1) }, done: "Order saved." })}><ArrowDown /></Button>
                  <Button size="sm" variant="ghost" aria-label={`Rename ${r.label}`} onClick={() => { setEditId(r.id); setDraft(r.label); }}><Pencil aria-hidden /> Rename</Button>
                  <Button size="sm" variant="ghost" className={r.active ? "text-destructive" : undefined} disabled={mut.isPending}
                          aria-label={`${r.active ? "Deactivate" : "Reactivate"} ${r.label}`}
                          onClick={async () => {
                            if (!r.active) mut.mutate({ path: `${itemPath}/${r.id}/reactivate`, done: `${r.label} reactivated.` });
                            else if (await confirm({ title: `Deactivate "${r.label}"?`, description: `The crew no longer see this ${noun}. Visits already done keep it.`, confirmLabel: "Deactivate", tone: "danger" })) {
                              mut.mutate({ path: `${itemPath}/${r.id}/deactivate`, done: `${r.label} deactivated.` });
                            }
                          }}>{r.active ? "Deactivate" : "Reactivate"}</Button>
                </div>
              </>
            )}
          </li>
        ))}
        {rows.length === 0 && <li className="px-3 py-3 text-sm text-muted-foreground">None yet.</li>}
      </ol>
      <form className="flex flex-wrap items-end gap-3"
            onSubmit={(e) => { e.preventDefault(); if (label.trim()) mut.mutate({ path: addPath, body: { label: label.trim() }, done: `${label.trim()} added.` }, { onSuccess: () => setLabel("") }); }}>
        <Field label={`New ${noun}`} className="max-w-md flex-1" error={fieldError(mut.error, "label")}>
          {(p) => <Input {...p} maxLength={120} value={label} onChange={(e) => setLabel(e.target.value)} />}
        </Field>
        <BusyButton type="submit" variant="outline" busy={mut.isPending} disabled={!label.trim()}><Plus aria-hidden /> Add {noun}</BusyButton>
      </form>
    </div>
  );
}
