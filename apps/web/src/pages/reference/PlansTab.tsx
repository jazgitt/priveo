import { useState } from "react";

import { Button, Card, Dialog, Table, TextField, useToast } from "../../components";
import { rupees } from "../../components/format";
import { fieldError, useDirectory, useDirMutation } from "./api";
import { ActiveChip, Notice, QueryState } from "./common";
import type { Plan } from "./types";

function PlanForm({ plan, onClose }: { plan: Plan | null; onClose: () => void }) {
  const toast = useToast();
  const save = useDirMutation();
  const [name, setName] = useState(plan?.name ?? "");
  const [price, setPrice] = useState(plan ? String(plan.monthly_price_rupees) : "");
  const [list, setList] = useState(plan?.list_price_rupees ? String(plan.list_price_rupees) : "");
  const [interior, setInterior] = useState(plan?.includes_interior ?? false);
  const [inclusions, setInclusions] = useState((plan?.inclusions ?? []).join("\n"));
  const [badge, setBadge] = useState(plan?.badge ?? "");
  const [order, setOrder] = useState(String(plan?.sort_order ?? 0));

  const submit = () => {
    const body: Record<string, unknown> = {
      name: name.trim(),
      monthly_price_rupees: Number(price),
      includes_interior: interior,
      inclusions: inclusions.split("\n").map((l) => l.trim()).filter(Boolean),
      badge: badge.trim(),
      sort_order: Number(order || 0),
    };
    if (list.trim()) body.list_price_rupees = Number(list);
    else if (plan?.list_price_rupees) body.clear_list_price = true;
    save.mutate(
      plan ? { path: `/plans/${plan.id}`, method: "PATCH", body } : { path: "/plans", body },
      { onSuccess: () => { toast.show("Plan saved.", "ok"); onClose(); } },
    );
  };

  return (
    <Dialog open title={plan ? "Edit plan" : "Add a plan"} onClose={onClose}
            footer={<>
              <Button variant="secondary" onClick={onClose}>Cancel</Button>
              <Button busy={save.isPending} disabled={!name.trim() || !price} onClick={submit}>
                Save
              </Button>
            </>}>
      <TextField label="Name" value={name} maxLength={80} error={fieldError(save.error, "name")}
                 onChange={(e) => setName(e.target.value)} />
      <TextField label="Monthly price (Rs, GST included)" type="number" min={1} value={price}
                 error={fieldError(save.error, "monthly_price_rupees")}
                 onChange={(e) => setPrice(e.target.value)} />
      <TextField label="List price (Rs, struck through)" type="number" min={1} value={list}
                 hint="Leave empty for no struck-through price."
                 error={fieldError(save.error, "list_price_rupees")}
                 onChange={(e) => setList(e.target.value)} />
      <label className="ref-check">
        <input type="checkbox" checked={interior} onChange={(e) => setInterior(e.target.checked)} />
        Includes interior care
      </label>
      <div className={`field${fieldError(save.error, "inclusions") ? " field-error" : ""}`}>
        <label htmlFor="plan-inclusions">Inclusions (one per line)</label>
        <textarea id="plan-inclusions" rows={4} value={inclusions}
                  onChange={(e) => setInclusions(e.target.value)} />
        {fieldError(save.error, "inclusions") && (
          <p className="field-msg" role="alert">{fieldError(save.error, "inclusions")}</p>)}
      </div>
      <TextField label="Badge" value={badge} maxLength={40} error={fieldError(save.error, "badge")}
                 onChange={(e) => setBadge(e.target.value)} />
      <TextField label="Sort order" type="number" min={0} value={order}
                 error={fieldError(save.error, "sort_order")}
                 onChange={(e) => setOrder(e.target.value)} />
    </Dialog>
  );
}

/** Plans: price, inclusions and active state (ADM-SUB, ADM-SET-01). */
export function PlansTab() {
  const list = useDirectory<Plan[]>("/plans");
  const toggle = useDirMutation();
  const [editing, setEditing] = useState<Plan | "new" | null>(null);

  return (
    <Card title="Plans" actions={<Button onClick={() => setEditing("new")}>Add a plan</Button>}>
      <Notice error={toggle.error} />
      <QueryState query={list}>
        {(rows) => (
          <Table rows={rows} rowKey={(p) => p.id} empty="No plans yet." columns={[
            { key: "name", header: "Plan", render: (p) => (
              <>{p.name}{p.badge && <> <span className="muted">({p.badge})</span></>}</>) },
            { key: "price", header: "Monthly price", align: "right",
              render: (p) => rupees(p.monthly_price_rupees) },
            { key: "list", header: "List price", align: "right",
              render: (p) => (p.list_price_rupees ? rupees(p.list_price_rupees) : "-") },
            { key: "int", header: "Interior", render: (p) => (p.includes_interior ? "Yes" : "No") },
            { key: "subs", header: "Subscriptions", align: "right",
              render: (p) => p.active_subscriptions },
            { key: "st", header: "Status", render: (p) => <ActiveChip active={p.active} /> },
            { key: "act", header: "", render: (p) => (
              <div className="ref-actions">
                <Button variant="ghost" aria-label={`Edit ${p.name}`}
                        onClick={() => setEditing(p)}>Edit</Button>
                <Button variant="ghost" busy={toggle.isPending}
                        aria-label={`${p.active ? "Deactivate" : "Reactivate"} ${p.name}`}
                        onClick={() => toggle.mutate({
                          path: `/plans/${p.id}/${p.active ? "deactivate" : "reactivate"}`,
                        })}>
                  {p.active ? "Deactivate" : "Reactivate"}
                </Button>
              </div>
            ) },
          ]} />
        )}
      </QueryState>
      {editing && <PlanForm plan={editing === "new" ? null : editing} onClose={() => setEditing(null)} />}
    </Card>
  );
}
