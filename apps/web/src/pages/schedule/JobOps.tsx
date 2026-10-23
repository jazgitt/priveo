import { useState } from "react";

import { api } from "@/api/client";
import { Field, SelectBox } from "@/blocks/fields";
import { FormDialog } from "@/blocks/FormDialog";
import { useAppMutation } from "@/blocks/mutation";
import { showDate } from "@/components/format";
import { Input } from "@/ui/input";
import { Textarea } from "@/ui/textarea";

import { weekday, type AdminJob, type Board } from "./api";

const dayText = (iso: string) => `${weekday(iso)} ${showDate(iso)}`;

/** S-05: move one scheduled service to any date from today on. The pattern is untouched. */
export function MoveToDateDialog({ job, today, onClose, onDone }: {
  job: AdminJob; today: string; onClose: () => void; onDone: () => void;
}) {
  const [date, setDate] = useState("");
  const [reason, setReason] = useState("");
  const move = useAppMutation<void>({
    mutationFn: () => api(`/v1/admin/scheduling/jobs/${job.id}/move-date`, { method: "POST", body: { date, reason: reason.trim() } }),
    pending: "Moving the service…",
    success: `${job.registration}: ${job.service} moved to ${date ? showDate(date) : "the new date"}.`,
    onSuccess: onDone,
  });
  const tooEarly = !!date && date < today;
  return (
    <FormDialog open onOpenChange={(o) => !o && onClose()} title={`Move ${job.service} to another date`} size="sm"
                description={`${job.registration} is now on ${dayText(job.date)}. The recurring plan does not change. Both dates stay on record.`}
                submitLabel="Move service" busy={move.isPending} disabled={!date || tooEarly || !reason.trim()}
                onSubmit={() => move.mutate()}>
      <Field label="New date" error={tooEarly ? "Choose today or a later date." : undefined}>
        {(p) => <Input {...p} type="date" min={today} value={date} onChange={(e) => setDate(e.target.value)} />}
      </Field>
      <Field label="Reason">
        {(p) => <Textarea {...p} rows={2} maxLength={200} value={reason} onChange={(e) => setReason(e.target.value)} />}
      </Field>
    </FormDialog>
  );
}

/** S-09: hand one crew member's whole day to another crew member. */
export function ReassignCrewDayDialog({ board, date, onClose, onDone }: {
  board: Board; date: string; onClose: () => void; onDone: () => void;
}) {
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [reason, setReason] = useState("");
  const crew = board.crew.map((c) => ({ value: c.id, label: c.name }));
  const reassign = useAppMutation<void, { reassigned: number }>({
    mutationFn: () => api(`/v1/admin/scheduling/reassign`, {
      method: "POST", body: { from_crew_id: from, date, to_crew_id: to, reason: reason.trim() },
    }),
    pending: "Reassigning…",
    success: (r) => `${r.reassigned} ${r.reassigned === 1 ? "job" : "jobs"} reassigned.`,
    onSuccess: onDone,
  });
  return (
    <FormDialog open onOpenChange={(o) => !o && onClose()} title="Reassign crew day" size="sm"
                description={`Every open job of the first crew member on ${dayText(date)} goes to the second, at the same times. If one job cannot move, nothing changes.`}
                submitLabel="Reassign" busy={reassign.isPending}
                disabled={!from || !to || from === to || !reason.trim()} onSubmit={() => reassign.mutate()}>
      <Field label="From crew member">
        {(p) => <SelectBox {...p} value={from} onChange={setFrom} choices={crew} />}
      </Field>
      <Field label="To crew member">
        {(p) => <SelectBox {...p} value={to} onChange={setTo} choices={crew.filter((c) => c.value !== from)} />}
      </Field>
      <Field label="Reason">
        {(p) => <Textarea {...p} rows={2} maxLength={200} value={reason} onChange={(e) => setReason(e.target.value)} />}
      </Field>
    </FormDialog>
  );
}
