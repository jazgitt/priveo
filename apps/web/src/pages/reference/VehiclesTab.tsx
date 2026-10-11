import { useState } from "react";

import { Button, Card, Dialog, SelectField, Table, TextField, useToast } from "../../components";
import { fieldError, useDirectory, useDirMutation } from "./api";
import { ActiveChip, Notice, QueryState } from "./common";
import type { Vehicle } from "./types";

function VehicleForm({ vehicle, categories, onClose }: {
  vehicle: Vehicle | null;
  categories: string[];
  onClose: () => void;
}) {
  const toast = useToast();
  const save = useDirMutation();
  const [make, setMake] = useState(vehicle?.make ?? "");
  const [model, setModel] = useState(vehicle?.model ?? "");
  const [variant, setVariant] = useState(vehicle?.variant ?? "");
  const [category, setCategory] = useState(vehicle?.category ?? "");

  const submit = () => {
    const body = { make: make.trim(), model: model.trim(), variant: variant.trim(),
                   category: category.trim() };
    save.mutate(
      vehicle ? { path: `/vehicle-catalogue/${vehicle.id}`, method: "PATCH", body }
        : { path: "/vehicle-catalogue", body },
      { onSuccess: () => { toast.show("Vehicle saved.", "ok"); onClose(); } },
    );
  };

  return (
    <Dialog open title={vehicle ? "Edit vehicle" : "Add a vehicle"} onClose={onClose}
            footer={<>
              <Button variant="secondary" onClick={onClose}>Cancel</Button>
              <Button busy={save.isPending}
                      disabled={!make.trim() || !model.trim() || !category.trim()}
                      onClick={submit}>Save</Button>
            </>}>
      <TextField label="Make" value={make} maxLength={60} error={fieldError(save.error, "make")}
                 onChange={(e) => setMake(e.target.value)} />
      <TextField label="Model" value={model} maxLength={80} error={fieldError(save.error, "model")}
                 onChange={(e) => setModel(e.target.value)} />
      <TextField label="Variant" value={variant} maxLength={80}
                 error={fieldError(save.error, "variant")}
                 onChange={(e) => setVariant(e.target.value)} />
      <TextField label="Category" value={category} maxLength={40} list="vehicle-categories"
                 error={fieldError(save.error, "category")}
                 onChange={(e) => setCategory(e.target.value)} />
      <datalist id="vehicle-categories">
        {categories.map((c) => <option key={c} value={c} />)}
      </datalist>
    </Dialog>
  );
}

/** The vehicle catalogue: search, categories, add, edit, deactivate (ADM-REF). */
export function VehiclesTab() {
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("");
  const [editing, setEditing] = useState<Vehicle | "new" | null>(null);
  const toggle = useDirMutation();
  const categories = useDirectory<string[]>("/vehicle-catalogue/categories");
  const q = search.trim();
  const list = useDirectory<Vehicle[]>(
    `/vehicle-catalogue${q ? `?q=${encodeURIComponent(q)}` : ""}`);

  return (
    <Card title="Vehicle catalogue"
          actions={<Button onClick={() => setEditing("new")}>Add a vehicle</Button>}>
      <div className="ref-toolbar">
        <TextField label="Search make or model" value={search}
                   onChange={(e) => setSearch(e.target.value)} />
        <SelectField label="Category" value={category} onChange={(e) => setCategory(e.target.value)}>
          <option value="">All categories</option>
          {(categories.data ?? []).map((c) => <option key={c}>{c}</option>)}
        </SelectField>
      </div>
      <Notice error={toggle.error} />
      <QueryState query={list}>
        {(all) => {
          const rows = category ? all.filter((v) => v.category === category) : all;
          return (
            <Table rows={rows} rowKey={(v) => v.id} empty="No vehicles match." columns={[
              { key: "make", header: "Make", render: (v) => v.make },
              { key: "model", header: "Model", render: (v) => v.model },
              { key: "variant", header: "Variant", render: (v) => v.variant || "-" },
              { key: "cat", header: "Category", render: (v) => v.category },
              { key: "st", header: "Status", render: (v) => <ActiveChip active={v.active} /> },
              { key: "act", header: "", render: (v) => (
                <div className="ref-actions">
                  <Button variant="ghost" aria-label={`Edit ${v.make} ${v.model} ${v.variant}`}
                          onClick={() => setEditing(v)}>Edit</Button>
                  <Button variant="ghost" busy={toggle.isPending}
                          aria-label={`${v.active ? "Deactivate" : "Reactivate"} ${v.make} ${v.model} ${v.variant}`}
                          onClick={() => toggle.mutate({
                            path: `/vehicle-catalogue/${v.id}/${v.active ? "deactivate" : "reactivate"}`,
                          })}>
                    {v.active ? "Deactivate" : "Reactivate"}
                  </Button>
                </div>
              ) },
            ]} />
          );
        }}
      </QueryState>
      {editing && (
        <VehicleForm vehicle={editing === "new" ? null : editing}
                     categories={categories.data ?? []} onClose={() => setEditing(null)} />
      )}
    </Card>
  );
}
