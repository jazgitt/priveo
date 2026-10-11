import { useState } from "react";

import { Button, Card, Dialog, SelectField, Table, TextField, useToast } from "../../components";
import { fieldError, useDirectory, useDirMutation } from "./api";
import { Notice, QueryState } from "./common";
import { SERVICE_NAMES, WEEKDAYS, type Slot, type Society } from "./types";

function SlotForm({ societyId, slot, service, onClose }: {
  societyId: string;
  slot: Slot | null;
  service: string;
  onClose: () => void;
}) {
  const toast = useToast();
  const save = useDirMutation();
  const [svc, setSvc] = useState(slot?.service ?? service);
  const [start, setStart] = useState(slot?.start ?? "05:00");
  const [end, setEnd] = useState(slot?.end ?? "11:00");
  const [days, setDays] = useState<string[]>(slot?.days ?? [...WEEKDAYS]);

  const flip = (d: string) =>
    setDays((xs) => (xs.includes(d) ? xs.filter((x) => x !== d) : [...xs, d]));
  const submit = () => {
    const ordered = WEEKDAYS.filter((d) => days.includes(d));
    save.mutate(
      slot ? { path: `/slots/${slot.id}`, method: "PATCH", body: { start, end, days: ordered } }
        : { path: `/societies/${societyId}/slots`,
            body: { service: svc, start, end, days: ordered } },
      { onSuccess: () => { toast.show("Slot saved.", "ok"); onClose(); } },
    );
  };

  return (
    <Dialog open title={slot ? "Edit working slot" : "Add a working slot"} onClose={onClose}
            footer={<>
              <Button variant="secondary" onClick={onClose}>Cancel</Button>
              <Button busy={save.isPending} disabled={days.length === 0} onClick={submit}>Save</Button>
            </>}>
      {!slot && (
        <SelectField label="Service" value={svc} error={fieldError(save.error, "service")}
                     onChange={(e) => setSvc(e.target.value)}>
          {SERVICE_NAMES.map((s) => <option key={s}>{s}</option>)}
        </SelectField>
      )}
      <TextField label="Start (HH:MM)" value={start} maxLength={5}
                 error={fieldError(save.error, "start")} onChange={(e) => setStart(e.target.value)} />
      <TextField label="End (HH:MM, 24:00 for midnight)" value={end} maxLength={5}
                 error={fieldError(save.error, "end")} onChange={(e) => setEnd(e.target.value)} />
      <fieldset className="ref-days">
        <legend>Days</legend>
        {WEEKDAYS.map((d) => (
          <label key={d}>
            <input type="checkbox" checked={days.includes(d)} onChange={() => flip(d)} />
            {d}
          </label>
        ))}
      </fieldset>
      {fieldError(save.error, "days") && <p className="field-msg" role="alert">
        {fieldError(save.error, "days")}</p>}
    </Dialog>
  );
}

/** Working slots per society and service (ADM-SVS-05 to -08). */
export function SlotsTab() {
  const societies = useDirectory<Society[]>("/societies?include_inactive=false");
  const [society, setSociety] = useState("");
  const [service, setService] = useState<string>(SERVICE_NAMES[0]);
  const [editing, setEditing] = useState<Slot | "new" | null>(null);
  const del = useDirMutation();

  const chosen = society || societies.data?.[0]?.id || "";
  const slots = useDirectory<Slot[]>(
    `/societies/${chosen}/slots?service=${encodeURIComponent(service)}`, Boolean(chosen));

  return (
    <Card title="Working slots" actions={
      <Button disabled={!chosen} onClick={() => setEditing("new")}>Add a slot</Button>}>
      <div className="ref-toolbar">
        <SelectField label="Society" value={chosen} onChange={(e) => setSociety(e.target.value)}>
          {(societies.data ?? []).map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
        </SelectField>
        <SelectField label="Service" value={service} onChange={(e) => setService(e.target.value)}>
          {SERVICE_NAMES.map((s) => <option key={s}>{s}</option>)}
        </SelectField>
      </div>
      <Notice error={del.error} />
      {chosen ? (
        <QueryState query={slots}>
          {(rows) => (
            <Table rows={rows} rowKey={(s) => s.id} empty="No slots for this service." columns={[
              { key: "time", header: "Time", render: (s) => `${s.start} to ${s.end}` },
              { key: "days", header: "Days", render: (s) => s.days.join(", ") },
              { key: "act", header: "", render: (s) => (
                <div className="ref-actions">
                  <Button variant="ghost" onClick={() => setEditing(s)}>Edit</Button>
                  <Button variant="ghost" busy={del.isPending}
                          onClick={() => del.mutate({ path: `/slots/${s.id}`, method: "DELETE" })}>
                    Delete
                  </Button>
                </div>
              ) },
            ]} />
          )}
        </QueryState>
      ) : <p className="muted">Add a society first.</p>}
      {editing && (
        <SlotForm societyId={chosen} service={service} slot={editing === "new" ? null : editing}
                  onClose={() => setEditing(null)} />
      )}
    </Card>
  );
}
