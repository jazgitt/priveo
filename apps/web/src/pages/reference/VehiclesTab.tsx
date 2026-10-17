import { Plus, Search } from "lucide-react";
import { useState } from "react";

import { DataTable } from "@/blocks/DataTable";
import { Field, NONE, SelectBox } from "@/blocks/fields";
import { FormDialog } from "@/blocks/FormDialog";
import { EmptyState, Panel } from "@/blocks/layout";
import { Button } from "@/ui/button";
import { Input } from "@/ui/input";

import { useDebounced } from "../customers/api";
import { fieldError, useDirectory, useDirSave } from "./api";
import { ActiveChip, Notice, QueryState, RowActions } from "./common";
import type { Vehicle } from "./types";

function VehicleForm({ vehicle, categories, onClose }: { vehicle: Vehicle | null; categories: string[]; onClose: () => void }) {
  const save = useDirSave();
  const [make, setMake] = useState(vehicle?.make ?? "");
  const [model, setModel] = useState(vehicle?.model ?? "");
  const [variant, setVariant] = useState(vehicle?.variant ?? "");
  const [category, setCategory] = useState(vehicle?.category ?? "");
  const fe = (f: string) => fieldError(save.error, f);

  const submit = () => {
    const body = { make: make.trim(), model: model.trim(), variant: variant.trim(), category: category.trim() };
    save.mutate(vehicle ? { path: `/vehicle-catalogue/${vehicle.id}`, method: "PATCH", body, done: "Vehicle saved." }
      : { path: "/vehicle-catalogue", body, done: "Vehicle added." }, { onSuccess: onClose });
  };

  return (
    <FormDialog open onOpenChange={(o) => !o && onClose()} title={vehicle ? "Edit vehicle" : "Add a vehicle"}
                submitLabel="Save" busy={save.isPending} disabled={!make.trim() || !model.trim() || !category.trim()} onSubmit={submit}>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <Field label="Make" error={fe("make")}>{(p) => <Input {...p} maxLength={60} value={make} onChange={(e) => setMake(e.target.value)} />}</Field>
        <Field label="Model" error={fe("model")}>{(p) => <Input {...p} maxLength={80} value={model} onChange={(e) => setModel(e.target.value)} />}</Field>
        <Field label="Variant" optional error={fe("variant")}>{(p) => <Input {...p} maxLength={80} value={variant} onChange={(e) => setVariant(e.target.value)} />}</Field>
        <Field label="Category" error={fe("category")} hint="Pick one in use or type a new one.">
          {(p) => <Input {...p} maxLength={40} list="vehicle-categories" value={category} onChange={(e) => setCategory(e.target.value)} />}
        </Field>
      </div>
      <datalist id="vehicle-categories">{categories.map((c) => <option key={c} value={c} />)}</datalist>
    </FormDialog>
  );
}

/** The vehicle catalogue: search, categories, add, edit, deactivate (ADM-REF). */
export function VehiclesTab() {
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("");
  const [editing, setEditing] = useState<Vehicle | "new" | null>(null);
  const toggle = useDirSave();
  const categories = useDirectory<string[]>("/vehicle-catalogue/categories");
  const q = useDebounced(search.trim(), 250);
  const list = useDirectory<Vehicle[]>(`/vehicle-catalogue${q ? `?q=${encodeURIComponent(q)}` : ""}`);

  return (
    <Panel title="Vehicle catalogue" description="Customers pick their car from this list."
           actions={<Button size="sm" onClick={() => setEditing("new")}><Plus aria-hidden /> Add a vehicle</Button>}>
      <div className="mb-4 flex flex-wrap items-end gap-3">
        <div className="relative w-full max-w-xs">
          <Search className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" aria-hidden />
          <Input aria-label="Search make or model" placeholder="Search make or model" className="bg-card pl-9" value={search} onChange={(e) => setSearch(e.target.value)} />
        </div>
        <Field label="Category" className="w-48">
          {(p) => <SelectBox {...p} value={category || NONE} onChange={(v) => setCategory(v === NONE ? "" : v)}
                             choices={[{ value: NONE, label: "All categories" }, ...(categories.data ?? []).map((c) => ({ value: c, label: c }))]} />}
        </Field>
      </div>
      <Notice error={toggle.error} />
      <QueryState query={list}>
        {(all) => (
          <DataTable rows={category ? all.filter((v) => v.category === category) : all} rowKey={(v) => v.id}
                     empty={<EmptyState title="No vehicles match" />} columns={[
            { key: "make", header: "Make", width: "18%", cell: (v) => <span className="font-medium">{v.make}</span> },
            { key: "model", header: "Model", width: "20%", cell: (v) => v.model },
            { key: "variant", header: "Variant", cell: (v) => v.variant || "-" },
            { key: "cat", header: "Category", width: "10rem", cell: (v) => v.category },
            { key: "st", header: "Status", width: "7rem", cell: (v) => <ActiveChip active={v.active} /> },
            { key: "act", header: "", width: "13rem", align: "right", cell: (v) => (
              <RowActions name={`${v.make} ${v.model} ${v.variant}`.trim()} active={v.active} path={`/vehicle-catalogue/${v.id}`}
                          toggle={toggle} onEdit={() => setEditing(v)} what="It is no longer offered. You can reactivate it later." />) },
          ]} />
        )}
      </QueryState>
      {editing && <VehicleForm vehicle={editing === "new" ? null : editing} categories={categories.data ?? []} onClose={() => setEditing(null)} />}
    </Panel>
  );
}
