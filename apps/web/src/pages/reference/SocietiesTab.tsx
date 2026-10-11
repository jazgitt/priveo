import { useState } from "react";

import { Button, Card, Dialog, Table, TextField, useToast } from "../../components";
import { fieldError, useDirectory, useDirMutation } from "./api";
import { ActiveChip, Notice, QueryState } from "./common";
import type { Society } from "./types";

function SocietyForm({ society, onClose }: { society: Society | null; onClose: () => void }) {
  const toast = useToast();
  const save = useDirMutation();
  const [name, setName] = useState(society?.name ?? "");
  const [sector, setSector] = useState(society?.sector ?? "");
  const [city, setCity] = useState(society?.city ?? "");
  const [basements, setBasements] = useState((society?.parking_basements ?? []).join(", "));

  const submit = () => {
    const list = basements.split(",").map((b) => b.trim()).filter(Boolean);
    const body: Record<string, unknown> = { name: name.trim(), sector: sector.trim(), city: city.trim() };
    if (list.length > 0) body.parking_basements = list;
    save.mutate(
      society ? { path: `/societies/${society.id}`, method: "PATCH", body }
        : { path: "/societies", body },
      { onSuccess: () => { toast.show("Society saved.", "ok"); onClose(); } },
    );
  };

  return (
    <Dialog open title={society ? "Edit society" : "Add a society"} onClose={onClose}
            footer={<>
              <Button variant="secondary" onClick={onClose}>Cancel</Button>
              <Button busy={save.isPending} disabled={!name.trim()} onClick={submit}>Save</Button>
            </>}>
      <TextField label="Name" value={name} maxLength={120} error={fieldError(save.error, "name")}
                 onChange={(e) => setName(e.target.value)} />
      <TextField label="Sector" value={sector} maxLength={80} error={fieldError(save.error, "sector")}
                 onChange={(e) => setSector(e.target.value)} />
      <TextField label="City" value={city} maxLength={80} error={fieldError(save.error, "city")}
                 onChange={(e) => setCity(e.target.value)} />
      <TextField label="Parking basements" value={basements}
                 hint="Separate with commas. Leave empty for B1, B2, B3, B4."
                 error={fieldError(save.error, "parking_basements")}
                 onChange={(e) => setBasements(e.target.value)} />
    </Dialog>
  );
}

/** Societies: add, edit, deactivate and reactivate (ADM-REF-01 to -06). */
export function SocietiesTab() {
  const list = useDirectory<Society[]>("/societies");
  const toggle = useDirMutation();
  const [editing, setEditing] = useState<Society | "new" | null>(null);

  return (
    <Card title="Societies" actions={<Button onClick={() => setEditing("new")}>Add a society</Button>}>
      <Notice error={toggle.error} />
      <QueryState query={list}>
        {(rows) => (
          <Table rows={rows} rowKey={(s) => s.id} empty="No societies yet." columns={[
            { key: "name", header: "Society", render: (s) => s.name },
            { key: "place", header: "Sector, city",
              render: (s) => [s.sector, s.city].filter(Boolean).join(", ") || "-" },
            { key: "bas", header: "Basements", render: (s) => s.parking_basements.join(", ") },
            { key: "cars", header: "Cars", align: "right", render: (s) => s.cars_serviced },
            { key: "subs", header: "Active subscriptions", align: "right",
              render: (s) => s.active_subscriptions },
            { key: "crew", header: "Active crew", align: "right", render: (s) => s.active_crew },
            { key: "st", header: "Status", render: (s) => <ActiveChip active={s.active} /> },
            { key: "act", header: "", render: (s) => (
              <div className="ref-actions">
                <Button variant="ghost" aria-label={`Edit ${s.name}`}
                        onClick={() => setEditing(s)}>Edit</Button>
                <Button variant="ghost" busy={toggle.isPending}
                        aria-label={`${s.active ? "Deactivate" : "Reactivate"} ${s.name}`}
                        onClick={() => toggle.mutate({
                          path: `/societies/${s.id}/${s.active ? "deactivate" : "reactivate"}`,
                        })}>
                  {s.active ? "Deactivate" : "Reactivate"}
                </Button>
              </div>
            ) },
          ]} />
        )}
      </QueryState>
      {editing && (
        <SocietyForm society={editing === "new" ? null : editing} onClose={() => setEditing(null)} />
      )}
    </Card>
  );
}
