import { Plus } from "lucide-react";
import { useState } from "react";

import { DataTable } from "@/blocks/DataTable";
import { Field } from "@/blocks/fields";
import { FormDialog } from "@/blocks/FormDialog";
import { EmptyState, Panel } from "@/blocks/layout";
import { Button } from "@/ui/button";
import { Input } from "@/ui/input";

import { fieldError, useDirectory, useDirSave } from "./api";
import { ActiveChip, Notice, QueryState, RowActions } from "./common";
import type { Society } from "./types";

function SocietyForm({ society, onClose }: { society: Society | null; onClose: () => void }) {
  const save = useDirSave();
  const [name, setName] = useState(society?.name ?? "");
  const [sector, setSector] = useState(society?.sector ?? "");
  const [city, setCity] = useState(society?.city ?? "");
  const [basements, setBasements] = useState((society?.parking_basements ?? []).join(", "));

  const submit = () => {
    const list = basements.split(",").map((b) => b.trim()).filter(Boolean);
    const body: Record<string, unknown> = { name: name.trim(), sector: sector.trim(), city: city.trim() };
    if (list.length > 0) body.parking_basements = list;
    save.mutate(society ? { path: `/societies/${society.id}`, method: "PATCH", body, done: "Society saved." }
      : { path: "/societies", body, done: "Society added." }, { onSuccess: onClose });
  };

  return (
    <FormDialog open onOpenChange={(o) => !o && onClose()} title={society ? "Edit society" : "Add a society"}
                submitLabel="Save" busy={save.isPending} disabled={!name.trim()} onSubmit={submit}>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <Field label="Name" error={fieldError(save.error, "name")} className="sm:col-span-2">
          {(p) => <Input {...p} maxLength={120} value={name} onChange={(e) => setName(e.target.value)} />}
        </Field>
        <Field label="Sector" optional error={fieldError(save.error, "sector")}>{(p) => <Input {...p} maxLength={80} value={sector} onChange={(e) => setSector(e.target.value)} />}</Field>
        <Field label="City" optional error={fieldError(save.error, "city")}>{(p) => <Input {...p} maxLength={80} value={city} onChange={(e) => setCity(e.target.value)} />}</Field>
        <Field label="Parking basements" className="sm:col-span-2" hint="Separate with commas. Leave empty for B1, B2, B3, B4." error={fieldError(save.error, "parking_basements")}>
          {(p) => <Input {...p} value={basements} onChange={(e) => setBasements(e.target.value)} />}
        </Field>
      </div>
    </FormDialog>
  );
}

/** Societies: add, edit, deactivate and reactivate (ADM-REF-01 to -06). */
export function SocietiesTab() {
  const list = useDirectory<Society[]>("/societies");
  const toggle = useDirSave();
  const [editing, setEditing] = useState<Society | "new" | null>(null);

  return (
    <Panel title="Societies" description="A society cannot be deactivated while it has active subscriptions or active crew."
           actions={<Button size="sm" onClick={() => setEditing("new")}><Plus aria-hidden /> Add a society</Button>}>
      <Notice error={toggle.error} />
      <QueryState query={list}>
        {(rows) => (
          <DataTable rows={rows} rowKey={(s) => s.id} empty={<EmptyState title="No societies yet" />} columns={[
            { key: "name", header: "Society", width: "20%", cell: (s) => <span className="font-medium">{s.name}</span> },
            { key: "place", header: "Sector, city", width: "15%", cell: (s) => [s.sector, s.city].filter(Boolean).join(", ") || "-" },
            { key: "bas", header: "Basements", cell: (s) => s.parking_basements.join(", ") },
            { key: "cars", header: "Cars", width: "5rem", align: "right", cell: (s) => s.cars_serviced },
            { key: "subs", header: "Subscriptions", width: "8rem", align: "right", cell: (s) => s.active_subscriptions },
            { key: "crew", header: "Crew", width: "5rem", align: "right", cell: (s) => s.active_crew },
            { key: "st", header: "Status", width: "7rem", cell: (s) => <ActiveChip active={s.active} /> },
            { key: "act", header: "", width: "13rem", align: "right", cell: (s) => (
              <RowActions name={s.name} active={s.active} path={`/societies/${s.id}`} toggle={toggle} onEdit={() => setEditing(s)}
                          what="It is no longer offered. You can reactivate it later." />) },
          ]} />
        )}
      </QueryState>
      {editing && <SocietyForm society={editing === "new" ? null : editing} onClose={() => setEditing(null)} />}
    </Panel>
  );
}
