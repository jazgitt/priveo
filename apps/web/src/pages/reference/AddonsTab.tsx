import { useState } from "react";

import { Button, Card, Dialog, Table, TextField, useToast } from "../../components";
import { rupees } from "../../components/format";
import { fieldError, useDirectory, useDirMutation } from "./api";
import { ActiveChip, Notice, QueryState } from "./common";
import type { Addon } from "./types";

function AddonForm({ addon, onClose }: { addon: Addon | null; onClose: () => void }) {
  const toast = useToast();
  const save = useDirMutation();
  const [name, setName] = useState(addon?.name ?? "");
  const [description, setDescription] = useState(addon?.description ?? "");
  const [price, setPrice] = useState(addon ? String(addon.price_rupees) : "");
  const [list, setList] = useState(addon?.list_price_rupees ? String(addon.list_price_rupees) : "");
  const [duration, setDuration] = useState(addon ? String(addon.duration_minutes) : "");
  const [order, setOrder] = useState(String(addon?.sort_order ?? 0));

  const submit = () => {
    const body: Record<string, unknown> = {
      name: name.trim(), description, price_rupees: Number(price),
      sort_order: Number(order || 0),
    };
    if (list.trim()) body.list_price_rupees = Number(list);
    else if (addon?.list_price_rupees) body.clear_list_price = true;
    if (duration.trim()) body.duration_minutes = Number(duration);
    save.mutate(
      addon ? { path: `/addons/${addon.id}`, method: "PATCH", body } : { path: "/addons", body },
      { onSuccess: () => { toast.show("Add-on saved.", "ok"); onClose(); } },
    );
  };

  return (
    <Dialog open title={addon ? "Edit add-on" : "Add an add-on"} onClose={onClose}
            footer={<>
              <Button variant="secondary" onClick={onClose}>Cancel</Button>
              <Button busy={save.isPending} disabled={!name.trim() || price === ""}
                      onClick={submit}>Save</Button>
            </>}>
      <TextField label="Name" value={name} maxLength={80} error={fieldError(save.error, "name")}
                 onChange={(e) => setName(e.target.value)} />
      <TextField label="Description" value={description} maxLength={1000}
                 error={fieldError(save.error, "description")}
                 onChange={(e) => setDescription(e.target.value)} />
      <TextField label="Price (Rs, GST included)" type="number" min={0} value={price}
                 error={fieldError(save.error, "price_rupees")}
                 onChange={(e) => setPrice(e.target.value)} />
      <TextField label="List price (Rs, struck through)" type="number" min={0} value={list}
                 error={fieldError(save.error, "list_price_rupees")}
                 onChange={(e) => setList(e.target.value)} />
      <TextField label="Duration (minutes)" type="number" min={5} value={duration}
                 hint="Leave empty to use the service's duration."
                 error={fieldError(save.error, "duration_minutes")}
                 onChange={(e) => setDuration(e.target.value)} />
      <TextField label="Sort order" type="number" min={0} value={order}
                 error={fieldError(save.error, "sort_order")}
                 onChange={(e) => setOrder(e.target.value)} />
    </Dialog>
  );
}

/** The add-on catalogue (ADM-ADD-01). */
export function AddonsTab() {
  const list = useDirectory<Addon[]>("/addons");
  const toggle = useDirMutation();
  const [editing, setEditing] = useState<Addon | "new" | null>(null);

  return (
    <Card title="Add-on catalogue"
          actions={<Button onClick={() => setEditing("new")}>Add an add-on</Button>}>
      <Notice error={toggle.error} />
      <QueryState query={list}>
        {(rows) => (
          <Table rows={rows} rowKey={(a) => a.id} empty="No add-ons yet." columns={[
            { key: "name", header: "Add-on", render: (a) => a.name },
            { key: "svc", header: "Service", render: (a) => a.service },
            { key: "price", header: "Price", align: "right", render: (a) => rupees(a.price_rupees) },
            { key: "list", header: "List price", align: "right",
              render: (a) => (a.list_price_rupees ? rupees(a.list_price_rupees) : "-") },
            { key: "dur", header: "Minutes", align: "right", render: (a) => a.duration_minutes },
            { key: "st", header: "Status", render: (a) => <ActiveChip active={a.active} /> },
            { key: "act", header: "", render: (a) => (
              <div className="ref-actions">
                <Button variant="ghost" aria-label={`Edit ${a.name}`}
                        onClick={() => setEditing(a)}>Edit</Button>
                <Button variant="ghost" busy={toggle.isPending}
                        aria-label={`${a.active ? "Deactivate" : "Reactivate"} ${a.name}`}
                        onClick={() => toggle.mutate({
                          path: `/addons/${a.id}/${a.active ? "deactivate" : "reactivate"}`,
                        })}>
                  {a.active ? "Deactivate" : "Reactivate"}
                </Button>
              </div>
            ) },
          ]} />
        )}
      </QueryState>
      {editing && <AddonForm addon={editing === "new" ? null : editing} onClose={() => setEditing(null)} />}
    </Card>
  );
}
