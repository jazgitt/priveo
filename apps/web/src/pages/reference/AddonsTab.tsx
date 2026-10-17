import { Plus } from "lucide-react";
import { useState } from "react";

import { DataTable } from "@/blocks/DataTable";
import { Field } from "@/blocks/fields";
import { FormDialog } from "@/blocks/FormDialog";
import { EmptyState, Panel } from "@/blocks/layout";
import { inr } from "@/components/format";
import { Button } from "@/ui/button";
import { Input } from "@/ui/input";
import { Textarea } from "@/ui/textarea";

import { fieldError, useDirectory, useDirSave } from "./api";
import { ActiveChip, Notice, QueryState, RowActions } from "./common";
import type { Addon } from "./types";

function AddonForm({ addon, onClose }: { addon: Addon | null; onClose: () => void }) {
  const save = useDirSave();
  const [name, setName] = useState(addon?.name ?? "");
  const [description, setDescription] = useState(addon?.description ?? "");
  const [price, setPrice] = useState(addon ? String(addon.price_rupees) : "");
  const [list, setList] = useState(addon?.list_price_rupees ? String(addon.list_price_rupees) : "");
  const [duration, setDuration] = useState(addon ? String(addon.duration_minutes) : "");
  const [order, setOrder] = useState(String(addon?.sort_order ?? 0));
  const fe = (f: string) => fieldError(save.error, f);

  const submit = () => {
    const body: Record<string, unknown> = { name: name.trim(), description, price_rupees: Number(price), sort_order: Number(order || 0) };
    if (list.trim()) body.list_price_rupees = Number(list);
    else if (addon?.list_price_rupees) body.clear_list_price = true;
    if (duration.trim()) body.duration_minutes = Number(duration);
    save.mutate(addon ? { path: `/addons/${addon.id}`, method: "PATCH", body, done: "Add-on saved." }
      : { path: "/addons", body, done: "Add-on added." }, { onSuccess: onClose });
  };

  return (
    <FormDialog open onOpenChange={(o) => !o && onClose()} title={addon ? "Edit add-on" : "Add an add-on"} size="lg"
                submitLabel="Save" busy={save.isPending} disabled={!name.trim() || price === ""} onSubmit={submit}>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <Field label="Name" error={fe("name")} className="sm:col-span-2">{(p) => <Input {...p} maxLength={80} value={name} onChange={(e) => setName(e.target.value)} />}</Field>
        <Field label="Description" optional error={fe("description")} className="sm:col-span-2">{(p) => <Textarea {...p} rows={3} maxLength={1000} value={description} onChange={(e) => setDescription(e.target.value)} />}</Field>
        <Field label="Price (Rs, GST included)" error={fe("price_rupees")}>{(p) => <Input {...p} type="number" min={0} value={price} onChange={(e) => setPrice(e.target.value)} />}</Field>
        <Field label="List price (Rs, struck through)" optional error={fe("list_price_rupees")}>{(p) => <Input {...p} type="number" min={0} value={list} onChange={(e) => setList(e.target.value)} />}</Field>
        <Field label="Duration (minutes)" hint="Leave empty to use the service's duration." error={fe("duration_minutes")}>{(p) => <Input {...p} type="number" min={5} value={duration} onChange={(e) => setDuration(e.target.value)} />}</Field>
        <Field label="Sort order" error={fe("sort_order")}>{(p) => <Input {...p} type="number" min={0} value={order} onChange={(e) => setOrder(e.target.value)} />}</Field>
      </div>
    </FormDialog>
  );
}

/** The add-on catalogue (ADM-ADD-01). */
export function AddonsTab() {
  const list = useDirectory<Addon[]>("/addons");
  const toggle = useDirSave();
  const [editing, setEditing] = useState<Addon | "new" | null>(null);

  return (
    <Panel title="Add-on catalogue" description="Prices include GST."
           actions={<Button size="sm" onClick={() => setEditing("new")}><Plus aria-hidden /> Add an add-on</Button>}>
      <Notice error={toggle.error} />
      <QueryState query={list}>
        {(rows) => (
          <DataTable rows={rows} rowKey={(a) => a.id} empty={<EmptyState title="No add-ons yet" />} columns={[
            { key: "code", header: "Add-on ID", width: "7.5rem", cell: (a) => <span className="tabular-nums">{a.code}</span> },
            { key: "name", header: "Add-on", cell: (a) => <span className="font-medium">{a.name}</span> },
            { key: "svc", header: "Service", width: "9rem", cell: (a) => a.service },
            { key: "price", header: "Price", width: "7rem", align: "right", cell: (a) => inr(a.price_rupees) },
            { key: "list", header: "List price", width: "7rem", align: "right", cell: (a) => (a.list_price_rupees ? <del className="text-muted-foreground">{inr(a.list_price_rupees)}</del> : "-") },
            { key: "dur", header: "Minutes", width: "6rem", align: "right", cell: (a) => a.duration_minutes },
            { key: "st", header: "Status", width: "7rem", cell: (a) => <ActiveChip active={a.active} /> },
            { key: "act", header: "", width: "13rem", align: "right", cell: (a) => (
              <RowActions name={a.name} active={a.active} path={`/addons/${a.id}`} toggle={toggle} onEdit={() => setEditing(a)}
                          what="It is no longer offered. You can reactivate it later." />) },
          ]} />
        )}
      </QueryState>
      {editing && <AddonForm addon={editing === "new" ? null : editing} onClose={() => setEditing(null)} />}
    </Panel>
  );
}
