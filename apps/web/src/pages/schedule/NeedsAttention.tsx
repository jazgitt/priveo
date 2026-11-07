import { useState } from "react";

import { api } from "@/api/client";
import { Field, SelectBox } from "@/blocks/fields";
import { FormDialog } from "@/blocks/FormDialog";
import { EmptyState, ErrorState, Panel } from "@/blocks/layout";
import { errorMessage, useAppMutation } from "@/blocks/mutation";
import { Textarea } from "@/ui/textarea";

import { CUSTOM_DAY, interiorDays } from "../customers/api";
import { useInteriorDayMissing, type InteriorDayMissing } from "./api";

/**
 * Cars on a plan with Interior care and no preferred Interior day. The scheduler gives
 * such a car no Interior visit, so the admin sets its day here, and the car is considered
 * in the next run (Needs Attention).
 */
export function NeedsAttention({ societyId }: { societyId: string }) {
  const cars = useInteriorDayMissing(societyId);
  const [chosen, setChosen] = useState<InteriorDayMissing | null>(null);
  const list = cars.data ?? [];

  if (!societyId) return <EmptyState title="Choose a site">Pick a site at the top left to see its cars that need an Interior day.</EmptyState>;

  return (
    <>
      <Panel title="Needs Attention"
             description="Cars on a plan with Interior care that have no preferred Interior day. Click a car to set its day. The scheduler considers the day on the next run."
             bodyClassName="p-0">
        {cars.isError ? <div className="p-4"><ErrorState message={errorMessage(cars.error)} /></div> : cars.isPending ? (
          <p className="p-4 text-sm text-muted-foreground">Loading…</p>
        ) : list.length === 0 ? (
          <p className="p-4 text-sm text-muted-foreground">Every car on Interior care has its preferred day.</p>
        ) : (
          <ul className="m-0 flex list-none flex-col divide-y p-0">
            {list.map((car) => (
              <li key={car.subscription_id}>
                <button type="button" aria-label={`Set the Interior day for ${car.registration}`}
                        onClick={() => setChosen(car)}
                        className="flex w-full flex-wrap items-center justify-between gap-x-4 gap-y-1 px-5 py-3 text-left text-sm text-destructive hover:bg-destructive/5 focus-visible:outline-2 focus-visible:outline-ring">
                  <span className="font-medium">
                    <span className="reg text-[0.8125rem]">{car.registration}</span> {car.vehicle}
                  </span>
                  <span>{car.customer_name}, {car.plan_name}. No Interior day set.</span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </Panel>
      {chosen && <SetInteriorDay key={chosen.subscription_id} car={chosen} onClose={() => setChosen(null)} />}
    </>
  );
}

/** Sets a car's preferred Interior day (and the notes for Custom) through the subscription. */
function SetInteriorDay({ car, onClose }: { car: InteriorDayMissing; onClose: () => void }) {
  const [day, setDay] = useState("");
  const [notes, setNotes] = useState("");
  const save = useAppMutation<{ day: string; notes: string }>({
    mutationFn: ({ day: d, notes: n }) => api(`/v1/admin/subscriptions/${car.subscription_id}`, {
      method: "PATCH",
      body: d === CUSTOM_DAY ? { interior_day: d, interior_day_notes: n.trim() || null } : { interior_day: d },
    }),
    pending: "Saving the Interior day…",
    success: (_d, v) => `${car.registration}: Interior day set to ${v.day}. It is considered in the next run.`,
    invalidate: [["interior-day-missing"]],
    onSuccess: onClose,
  });

  return (
    <FormDialog open onOpenChange={(o) => { if (!o) onClose(); }}
                title={`Interior day for ${car.registration}`}
                description={`${car.customer_name}, ${car.plan_name}. The scheduler plans Interior care on this day.`}
                submitLabel="Save Interior day" busy={save.isPending} disabled={!day}
                onSubmit={() => save.mutate({ day, notes })}>
      <Field label="Interior care day">
        {(p) => <SelectBox {...p} value={day} onChange={setDay} choices={interiorDays.map((d) => ({ value: d, label: d }))} />}
      </Field>
      {day === CUSTOM_DAY && (
        <Field label="Interior day notes" optional hint="Whose car's turn it is, for a customer whose cars take turns.">
          {(p) => <Textarea {...p} rows={2} maxLength={500} value={notes} onChange={(e) => setNotes(e.target.value)} />}
        </Field>
      )}
    </FormDialog>
  );
}
