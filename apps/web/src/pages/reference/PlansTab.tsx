import { Plus } from "lucide-react";
import { useState } from "react";

import { DataTable } from "@/blocks/DataTable";
import { Field, NONE, SelectBox } from "@/blocks/fields";
import { FormDialog } from "@/blocks/FormDialog";
import { EmptyState, Panel } from "@/blocks/layout";
import { inr } from "@/components/format";
import { Button } from "@/ui/button";
import { Input } from "@/ui/input";
import { Switch } from "@/ui/switch";
import { Textarea } from "@/ui/textarea";

import { fieldError, useDirectory, useDirSave } from "./api";
import { ActiveChip, Notice, QueryState, RowActions } from "./common";
import type { Plan } from "./types";

function PlanForm({ plan, onClose }: { plan: Plan | null; onClose: () => void }) {
  const save = useDirSave();
  const categories = useDirectory<string[]>("/vehicle-catalogue/categories");
  const [name, setName] = useState(plan?.name ?? "");
  const [price, setPrice] = useState(plan ? String(plan.monthly_price_rupees) : "");
  const [list, setList] = useState(plan?.list_price_rupees ? String(plan.list_price_rupees) : "");
  const [interior, setInterior] = useState(plan?.includes_interior ?? false);
  const [inclusions, setInclusions] = useState((plan?.inclusions ?? []).join("\n"));
  const [badge, setBadge] = useState(plan?.badge ?? "");
  const [order, setOrder] = useState(String(plan?.sort_order ?? 0));
  const [category, setCategory] = useState(plan?.vehicle_category ?? "");
  const choices = [...new Set([...(categories.data ?? []), ...(plan?.vehicle_category ? [plan.vehicle_category] : [])])]
    .map((c) => ({ value: c, label: c }));
  const fe = (f: string) => fieldError(save.error, f);

  const submit = () => {
    const body: Record<string, unknown> = {
      name: name.trim(), monthly_price_rupees: Number(price), includes_interior: interior,
      inclusions: inclusions.split("\n").map((l) => l.trim()).filter(Boolean),
      badge: badge.trim(), sort_order: Number(order || 0),
    };
    if (list.trim()) body.list_price_rupees = Number(list);
    else if (plan?.list_price_rupees) body.clear_list_price = true;
    if (category) body.vehicle_category = category;
    else if (plan?.vehicle_category) body.clear_vehicle_category = true;
    save.mutate(plan ? { path: `/plans/${plan.id}`, method: "PATCH", body, done: "Plan saved." }
      : { path: "/plans", body, done: "Plan added." }, { onSuccess: onClose });
  };

  return (
    <FormDialog open onOpenChange={(o) => !o && onClose()} title={plan ? "Edit plan" : "Add a plan"} size="lg"
                submitLabel="Save" busy={save.isPending} disabled={!name.trim() || !price} onSubmit={submit}>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <Field label="Name" error={fe("name")}>{(p) => <Input {...p} maxLength={80} value={name} onChange={(e) => setName(e.target.value)} />}</Field>
        <Field label="Badge" optional error={fe("badge")}>{(p) => <Input {...p} maxLength={40} value={badge} onChange={(e) => setBadge(e.target.value)} />}</Field>
        <Field label="Monthly price (Rs, GST included)" error={fe("monthly_price_rupees")}>{(p) => <Input {...p} type="number" min={1} value={price} onChange={(e) => setPrice(e.target.value)} />}</Field>
        <Field label="List price (Rs, struck through)" hint="Leave empty for no struck-through price." error={fe("list_price_rupees")}>{(p) => <Input {...p} type="number" min={1} value={list} onChange={(e) => setList(e.target.value)} />}</Field>
        <Field label="Inclusions (one per line)" className="sm:col-span-2" error={fe("inclusions")}>{(p) => <Textarea {...p} rows={4} value={inclusions} onChange={(e) => setInclusions(e.target.value)} />}</Field>
        <Field label="Sort order" error={fe("sort_order")}>{(p) => <Input {...p} type="number" min={0} value={order} onChange={(e) => setOrder(e.target.value)} />}</Field>
        <Field label="Vehicle category" optional hint="Shown on the plan. It does not limit which vehicles can take it yet." error={fe("vehicle_category")}>
          {(p) => (
            <SelectBox {...p} value={category || NONE} onChange={(v) => setCategory(v === NONE ? "" : v)} placeholder="No category"
                       choices={[{ value: NONE, label: "No category" }, ...choices]} />
          )}
        </Field>
        <label className="flex items-center gap-3 self-end pb-2 text-sm">
          <Switch aria-label="Includes interior care" checked={interior} onCheckedChange={setInterior} /> Includes interior care
        </label>
      </div>
    </FormDialog>
  );
}

/** Plans: price, inclusions and active state (ADM-SUB, ADM-SET-01). */
export function PlansTab() {
  const list = useDirectory<Plan[]>("/plans");
  const toggle = useDirSave();
  const [editing, setEditing] = useState<Plan | "new" | null>(null);

  return (
    <Panel title="Plans" description="Prices include GST."
           actions={<Button size="sm" onClick={() => setEditing("new")}><Plus aria-hidden /> Add a plan</Button>}>
      <Notice error={toggle.error} />
      <QueryState query={list}>
        {(rows) => (
          <DataTable rows={rows} rowKey={(p) => p.id} empty={<EmptyState title="No plans yet" />} columns={[
            { key: "code", header: "Plan ID", width: "7rem", cell: (p) => <span className="tabular-nums">{p.code}</span> },
            { key: "name", header: "Plan", cell: (p) => <span><span className="font-medium">{p.name}</span>{p.badge && <span className="text-muted-foreground"> · {p.badge}</span>}</span> },
            { key: "price", header: "Monthly price", width: "8rem", align: "right", cell: (p) => inr(p.monthly_price_rupees) },
            { key: "list", header: "List price", width: "7rem", align: "right", cell: (p) => (p.list_price_rupees ? <del className="text-muted-foreground">{inr(p.list_price_rupees)}</del> : "-") },
            { key: "cat", header: "Vehicle category", width: "9rem", cell: (p) => p.vehicle_category ?? "-" },
            { key: "int", header: "Interior", width: "6rem", cell: (p) => (p.includes_interior ? "Yes" : "No") },
            { key: "subs", header: "Subscriptions", width: "8rem", align: "right", cell: (p) => p.active_subscriptions },
            { key: "st", header: "Status", width: "7rem", cell: (p) => <ActiveChip active={p.active} /> },
            { key: "act", header: "", width: "13rem", align: "right", cell: (p) => (
              <RowActions name={p.name} active={p.active} path={`/plans/${p.id}`} toggle={toggle} onEdit={() => setEditing(p)}
                          what="It is no longer offered. You can reactivate it later." />) },
          ]} />
        )}
      </QueryState>
      {editing && <PlanForm plan={editing === "new" ? null : editing} onClose={() => setEditing(null)} />}
    </Panel>
  );
}
