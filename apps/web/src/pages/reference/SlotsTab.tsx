import { Pencil, Plus, Trash2 } from "lucide-react";
import { useState } from "react";

import { useConfirm } from "@/blocks/confirm";
import { DataTable } from "@/blocks/DataTable";
import { Field, SelectBox } from "@/blocks/fields";
import { FormDialog } from "@/blocks/FormDialog";
import { EmptyState, PageHeader } from "@/blocks/layout";
import { cn } from "@/lib/utils";
import { useSite } from "@/site/SiteContext";
import { Button } from "@/ui/button";
import { Input } from "@/ui/input";

import { fieldError, useDirectory, useDirSave } from "./api";
import { Notice, QueryState } from "./common";
import { SERVICE_NAMES, WEEKDAYS, type Slot } from "./types";

const services = SERVICE_NAMES.map((s) => ({ value: s, label: s }));

function SlotForm({ societyId, slot, service, onClose }: { societyId: string; slot: Slot | null; service: string; onClose: () => void }) {
  const save = useDirSave();
  const [svc, setSvc] = useState(slot?.service ?? service);
  const [start, setStart] = useState(slot?.start ?? "05:00");
  const [end, setEnd] = useState(slot?.end ?? "11:00");
  const [days, setDays] = useState<string[]>(slot?.days ?? [...WEEKDAYS]);
  const flip = (d: string) => setDays((xs) => (xs.includes(d) ? xs.filter((x) => x !== d) : [...xs, d]));

  const submit = () => {
    const ordered = WEEKDAYS.filter((d) => days.includes(d));
    save.mutate(slot
      ? { path: `/slots/${slot.id}`, method: "PATCH", body: { start, end, days: ordered }, done: "Slot saved." }
      : { path: `/societies/${societyId}/slots`, body: { service: svc, start, end, days: ordered }, done: "Slot added." },
    { onSuccess: onClose });
  };

  return (
    <FormDialog open onOpenChange={(o) => !o && onClose()} title={slot ? "Edit working slot" : "Add a working slot"}
                submitLabel="Save" busy={save.isPending} disabled={days.length === 0} onSubmit={submit}>
      {!slot && (
        <Field label="Service" error={fieldError(save.error, "service")}>{(p) => <SelectBox {...p} value={svc} onChange={setSvc} choices={services} />}</Field>
      )}
      <div className="grid grid-cols-2 gap-4">
        <Field label="Start (HH:MM)" error={fieldError(save.error, "start")}>{(p) => <Input {...p} maxLength={5} value={start} onChange={(e) => setStart(e.target.value)} />}</Field>
        <Field label="End (HH:MM, 24:00 for midnight)" error={fieldError(save.error, "end")}>{(p) => <Input {...p} maxLength={5} value={end} onChange={(e) => setEnd(e.target.value)} />}</Field>
      </div>
      <fieldset className="m-0 border-0 p-0">
        <legend className="mb-2 text-[0.8125rem] font-medium">Days</legend>
        <div className="flex flex-wrap gap-2">
          {WEEKDAYS.map((d) => (
            <label key={d} className={cn("flex cursor-pointer items-center gap-2 rounded-md border px-3 py-1.5 text-sm transition-colors",
              days.includes(d) ? "border-foreground bg-foreground text-background" : "bg-card hover:bg-accent")}>
              <input type="checkbox" className="sr-only" checked={days.includes(d)} onChange={() => flip(d)} />
              {d}
            </label>
          ))}
        </div>
        {fieldError(save.error, "days") && <p className="mt-2 mb-0 text-xs text-destructive" role="alert">{fieldError(save.error, "days")}</p>}
        {days.length === 0 && <p className="mt-2 mb-0 text-xs text-muted-foreground">Choose at least one day.</p>}
      </fieldset>
    </FormDialog>
  );
}

const DAY_LETTERS = WEEKDAYS.map((d) => d.slice(0, 3));

/** Working slots of the chosen site, per service (ADM-SVS-05 to -08). */
export function SlotsTab() {
  const site = useSite();
  const confirm = useConfirm();
  const [service, setService] = useState<string>(SERVICE_NAMES[0]);
  const [editing, setEditing] = useState<Slot | "new" | null>(null);
  const del = useDirSave();
  const chosen = site.id;
  const slots = useDirectory<Slot[]>(`/societies/${chosen}/slots?service=${encodeURIComponent(service)}`, Boolean(chosen));

  return (
    <>
      <PageHeader title="Working slots" site={site.name || undefined}
                  description="When each service can be done in this society. The scheduler only places jobs inside these slots."
                  actions={<Button disabled={!chosen} onClick={() => setEditing("new")}><Plus aria-hidden /> Add a slot</Button>} />
      {!chosen ? <EmptyState title="Add a society first.">Working slots belong to a society.</EmptyState> : (
        <>
          <div className="mb-4 flex flex-wrap items-end gap-3">
            <Field label="Service" className="w-56">{(p) => <SelectBox {...p} value={service} onChange={setService} choices={services} />}</Field>
          </div>
          <Notice error={del.error} />
          <QueryState query={slots}>
            {(rows) => (
              <DataTable rows={rows} rowKey={(s) => s.id}
                         empty={<EmptyState title="No slots for this service" action={<Button variant="outline" onClick={() => setEditing("new")}>Add a slot</Button>} />}
                         columns={[
                { key: "time", header: "Time", width: "12rem", cell: (s) => <span className="font-medium tabular-nums">{s.start} to {s.end}</span> },
                { key: "days", header: "Days", wrap: true, cell: (s) => (
                  <span className="flex flex-wrap gap-1" aria-label={s.days.join(", ")}>
                    {WEEKDAYS.map((d, i) => (
                      <span key={d} className={cn("rounded px-1.5 py-0.5 text-xs", s.days.includes(d) ? "bg-gold/20 font-medium" : "text-muted-foreground/50")}>{DAY_LETTERS[i]}</span>
                    ))}
                  </span>) },
                { key: "act", header: "", width: "12rem", align: "right", cell: (s) => (
                  <div className="flex justify-end gap-1">
                    <Button size="sm" variant="ghost" onClick={() => setEditing(s)}><Pencil aria-hidden /> Edit</Button>
                    <Button size="sm" variant="ghost" className="text-destructive" disabled={del.isPending} onClick={async () => {
                      if (await confirm({ title: `Delete the ${s.start} to ${s.end} slot?`, description: `${service} can no longer be scheduled in this slot.`, confirmLabel: "Delete", tone: "danger" })) {
                        del.mutate({ path: `/slots/${s.id}`, method: "DELETE", done: "Slot deleted." });
                      }
                    }}><Trash2 aria-hidden /> Delete</Button>
                  </div>) },
              ]} />
            )}
          </QueryState>
        </>
      )}
      {editing && <SlotForm societyId={chosen} service={service} slot={editing === "new" ? null : editing} onClose={() => setEditing(null)} />}
    </>
  );
}
