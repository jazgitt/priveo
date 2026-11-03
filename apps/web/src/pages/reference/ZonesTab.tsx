import { Plus } from "lucide-react";
import { useState } from "react";

import { DataTable } from "@/blocks/DataTable";
import { Field } from "@/blocks/fields";
import { FormDialog } from "@/blocks/FormDialog";
import { EmptyState, Panel } from "@/blocks/layout";
import { useSite } from "@/site/SiteContext";
import { Button } from "@/ui/button";
import { Input } from "@/ui/input";

import { fieldError, useDirectory, useDirSave } from "./api";
import { ActiveChip, Notice, QueryState, RowActions } from "./common";
import type { Zone } from "./types";

function ZoneForm({ societyId, zone, onClose }: { societyId: string; zone: Zone | null; onClose: () => void }) {
  const save = useDirSave();
  const [name, setName] = useState(zone?.name ?? "");
  const submit = () => {
    const body = { name: name.trim() };
    save.mutate(zone ? { path: `/zones/${zone.id}`, method: "PATCH", body, done: "Zone saved." }
      : { path: `/societies/${societyId}/zones`, body, done: "Zone added." }, { onSuccess: onClose });
  };
  return (
    <FormDialog open onOpenChange={(o) => !o && onClose()} title={zone ? "Rename zone" : "Add a zone"}
                submitLabel="Save" busy={save.isPending} disabled={!name.trim()} onSubmit={submit}>
      <Field label="Zone name" error={fieldError(save.error, "name")}>
        {(p) => <Input {...p} maxLength={60} value={name} onChange={(e) => setName(e.target.value)} />}
      </Field>
    </FormDialog>
  );
}

/** Zones of the chosen society: add, rename, deactivate and reactivate. A zone is picked in Add Vehicle. */
export function ZonesTab() {
  const site = useSite();
  const chosen = site.id;
  const list = useDirectory<Zone[]>(`/societies/${chosen}/zones`, Boolean(chosen));
  const toggle = useDirSave();
  const [editing, setEditing] = useState<Zone | "new" | null>(null);

  return (
    <Panel title="Zones" description="Parking zones of this society. A vehicle gets its zone when it is added. A deactivated zone is no longer offered."
           actions={<Button size="sm" disabled={!chosen} onClick={() => setEditing("new")}><Plus aria-hidden /> Add a zone</Button>}>
      {!chosen ? <EmptyState title="Add a society first.">Zones belong to a society.</EmptyState> : (
        <>
          <Notice error={toggle.error} />
          <QueryState query={list}>
            {(rows) => (
              <DataTable rows={rows} rowKey={(z) => z.id} empty={<EmptyState title="No zones yet" />} columns={[
                { key: "name", header: "Zone", cell: (z) => <span className="font-medium">{z.name}</span> },
                { key: "cars", header: "Vehicles", width: "6rem", align: "right", cell: (z) => z.vehicles },
                { key: "st", header: "Status", width: "7rem", cell: (z) => <ActiveChip active={z.active} /> },
                { key: "act", header: "", width: "13rem", align: "right", cell: (z) => (
                  <RowActions name={z.name} active={z.active} path={`/zones/${z.id}`} toggle={toggle} onEdit={() => setEditing(z)}
                              what="It is no longer offered in Add Vehicle. Vehicles already in it keep it." />) },
              ]} />
            )}
          </QueryState>
          {editing && <ZoneForm societyId={chosen} zone={editing === "new" ? null : editing} onClose={() => setEditing(null)} />}
        </>
      )}
    </Panel>
  );
}
