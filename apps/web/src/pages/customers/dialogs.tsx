import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { api } from "@/api/client";
import { Field, NONE, SelectBox } from "@/blocks/fields";
import { FormDialog } from "@/blocks/FormDialog";
import { useAppMutation } from "@/blocks/mutation";
import { inr, showDate } from "@/components/format";
import { useSite } from "@/site/SiteContext";
import { Checkbox } from "@/ui/checkbox";
import { Input } from "@/ui/input";
import { Textarea } from "@/ui/textarea";

import {
  times, uploadCustomerAsset, weekdays,
  type Catalogue, type Customer, type Plan, type SchedulePattern, type Society, type Subscription, type Vehicle,
} from "./api";

type Call = { path: string; method?: string; body?: unknown };
const call = (r: Call) => api<unknown>(r.path, { method: r.method ?? "POST", body: r.body });

/** Saves a change to a customer and refreshes their page and the list. */
function useCustomerSave(customerId: string, success: string, onDone: () => void) {
  return useAppMutation<Call>({
    mutationFn: call, success, onSuccess: onDone,
    invalidate: [["customer", customerId], ["customers"]],
  });
}

export const usePlans = () => useQuery({ queryKey: ["customer-plans"], queryFn: () => api<Plan[]>("/v1/admin/directory/plans") });
export const useCatalogue = () => useQuery({ queryKey: ["customer-catalogue"], queryFn: () => api<Catalogue[]>("/v1/admin/directory/vehicle-catalogue") });
export const useSocietyList = () => useQuery({ queryKey: ["customer-societies"], queryFn: () => api<Society[]>("/v1/admin/directory/societies") });

const timeChoices = times.map((t) => ({ value: t, label: t }));

// ---- customer ------------------------------------------------------------

export function CustomerDialog({ customer: c, open, onClose }: { customer: Customer; open: boolean; onClose: () => void }) {
  return open ? <CustomerForm c={c} onClose={onClose} /> : null;
}

function CustomerForm({ c, onClose }: { c: Customer; onClose: () => void }) {
  const site = useSite();
  const societies = useSocietyList();
  const list = (societies.data ?? []).filter((s) => s.active || s.id === c.society_id);
  // The customer's society, or the selected site when they have none yet.
  const societyId = c.society_id ?? site.id;
  const home = list.find((s) => s.id === societyId);
  // Empty address lines start from what was entered when the society was created.
  const fromSociety = { line1: home?.name ?? "", line2: [home?.sector, home?.city].filter(Boolean).join(", ") };
  const [v, setV] = useState({
    first_name: c.first_name, last_name: c.last_name, mobile: c.mobile, flat: c.flat ?? "",
    address_line1: c.address_line1 ?? "", address_line2: c.address_line2 ?? "", society_id: societyId,
  });
  const [touched, setTouched] = useState(false);
  const shown = touched ? v : {
    ...v,
    address_line1: v.address_line1 || fromSociety.line1,
    address_line2: v.address_line2 || fromSociety.line2,
    society_id: v.society_id || site.id,
  };
  const save = useCustomerSave(c.id, "Customer details saved.", onClose);
  const mobileOk = /^\d{10}$/.test(v.mobile);
  const set = (k: keyof typeof v) => (e: React.ChangeEvent<HTMLInputElement>) => {
    setV({ ...shown, [k]: e.target.value }); setTouched(true);
  };
  return (
    <FormDialog open onOpenChange={(o) => !o && onClose()} title="Edit customer details"
                description="The customer is not notified. The change is recorded in the audit log."
                submitLabel="Save customer" busy={save.isPending}
                disabled={!shown.first_name.trim() || !shown.last_name.trim() || !mobileOk}
                onSubmit={() => save.mutate({ path: `/v1/admin/customers/${c.id}`, method: "PATCH", body: { ...shown, society_id: shown.society_id || undefined } })}>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <Field label="First name">{(p) => <Input {...p} value={shown.first_name} onChange={set("first_name")} />}</Field>
        <Field label="Last name">{(p) => <Input {...p} value={shown.last_name} onChange={set("last_name")} />}</Field>
        <Field label="Mobile" hint="10 digits" error={shown.mobile && !mobileOk ? "Enter a 10-digit mobile number." : undefined}>
          {(p) => <Input {...p} inputMode="numeric" value={shown.mobile} onChange={set("mobile")} />}
        </Field>
        <Field label="Flat" optional>{(p) => <Input {...p} value={shown.flat} onChange={set("flat")} />}</Field>
        <Field label="Address line 1" optional className="sm:col-span-2">
          {(p) => <Input {...p} value={shown.address_line1} onChange={set("address_line1")} />}
        </Field>
        <Field label="Address line 2" optional className="sm:col-span-2">
          {(p) => <Input {...p} value={shown.address_line2} onChange={set("address_line2")} />}
        </Field>
        <Field label="Society" className="sm:col-span-2">
          {(p) => (
            <SelectBox {...p} value={shown.society_id}
                       onChange={(id) => { setV({ ...shown, society_id: id }); setTouched(true); }}
                       choices={list.map((s) => ({ value: s.id, label: s.name }))} />
          )}
        </Field>
      </div>
    </FormDialog>
  );
}

export function EmailDialog({ customer: c, open, onClose }: { customer: Customer; open: boolean; onClose: () => void }) {
  return open ? <EmailForm c={c} onClose={onClose} /> : null;
}

function EmailForm({ c, onClose }: { c: Customer; onClose: () => void }) {
  const [email, setEmail] = useState(c.email);
  const save = useCustomerSave(c.id, "Email updated. A new welcome email is on its way.", onClose);
  const ok = /^\S+@\S+\.\S+$/.test(email) && email.trim().toLowerCase() !== c.email.toLowerCase();
  return (
    <FormDialog open onOpenChange={(o) => !o && onClose()} title="Update email" danger
                description="The customer's password is cleared and they are signed out everywhere. A new welcome email goes to the new address; they verify it and set a new password (ADM-CUS-19)."
                submitLabel="Update email" busy={save.isPending} disabled={!ok}
                onSubmit={() => save.mutate({ path: `/v1/admin/customers/${c.id}/email`, method: "PATCH", body: { email: email.trim() } })}>
      <Field label="New email" hint={`Now ${c.email}`}>
        {(p) => <Input {...p} type="email" value={email} onChange={(e) => setEmail(e.target.value)} />}
      </Field>
    </FormDialog>
  );
}

// ---- vehicle --------------------------------------------------------------

export function CarDialog({ v, customerId, onClose }: { v: Vehicle; customerId: string; onClose: () => void }) {
  const catalogue = useCatalogue();
  const societies = useSocietyList();
  const basements = societies.data?.find((s) => s.id === v.society_id || s.name === v.society)?.parking_basements ?? [];
  const [reg, setReg] = useState(v.registration.replaceAll(" ", ""));
  const [catalogueId, setCatalogueId] = useState(NONE);
  const [basement, setBasement] = useState(v.parking_basement);
  const [parking, setParking] = useState(v.parking_number);
  const [uploading, setUploading] = useState(false);
  const save = useCustomerSave(customerId, "Car details saved.", onClose);
  const instant = useCustomerSave(customerId, "Saved.", () => {});
  const upload = async (file: File | undefined) => {
    if (!file) return;
    setUploading(true);
    try {
      await instant.mutateAsync({
        path: `/v1/admin/vehicles/${v.id}`, method: "PATCH",
        body: { photo_upload_id: (await uploadCustomerAsset(file)).id },
      });
    } catch {
      // The toast from the save says what went wrong.
    } finally { setUploading(false); }
  };
  const valid = reg.trim() !== "" && basement && /^\d{1,5}$/.test(parking);
  return (
    <FormDialog open onOpenChange={(o) => !o && onClose()} title={`Edit car and parking, ${v.registration}`} size="lg"
                submitLabel="Save car details" busy={save.isPending} disabled={!valid}
                onSubmit={() => save.mutate({ path: `/v1/admin/vehicles/${v.id}`, method: "PATCH", body: {
                  registration: reg, parking_basement: basement, parking_number: parking,
                  ...(catalogueId !== NONE ? { catalogue_id: catalogueId } : {}),
                } })}>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <Field label="Registration" hint="For example HR26EC4321">
          {(p) => <Input {...p} className="reg uppercase" value={reg} onChange={(e) => setReg(e.target.value.toUpperCase().replaceAll(" ", ""))} />}
        </Field>
        <Field label="Make, model and variant" hint={`Now ${v.make} ${v.model} ${v.variant}`.trim()}>
          {(p) => (
            <SelectBox {...p} value={catalogueId} onChange={setCatalogueId} choices={[
              { value: NONE, label: "Keep current vehicle" },
              ...(catalogue.data ?? []).filter((c) => c.active).map((c) => ({
                value: c.id, label: `${c.make} ${c.model} ${c.variant} · ${c.category}`,
              })),
            ]} />
          )}
        </Field>
        <Field label="Basement">
          {(p) => basements.length > 0
            ? <SelectBox {...p} value={basement} onChange={setBasement}
                         choices={[...new Set([...basements, v.parking_basement].filter(Boolean))].map((b) => ({ value: b, label: b }))} />
            : <Input {...p} value={basement} onChange={(e) => setBasement(e.target.value)} />}
        </Field>
        <Field label="Parking number" error={parking && !/^\d{1,5}$/.test(parking) ? "Up to 5 digits." : undefined}>
          {(p) => <Input {...p} inputMode="numeric" value={parking} onChange={(e) => setParking(e.target.value)} />}
        </Field>
      </div>
      <div className="rounded-lg border bg-muted/40 p-4">
        <Field label={v.photo_url ? "Replace vehicle photo" : "Vehicle photo"} optional
               hint={uploading ? "Uploading…" : "Saved as soon as it is uploaded."}>
          {(p) => <Input {...p} type="file" accept="image/*,.heic,.heif" disabled={uploading} onChange={(e) => void upload(e.target.files?.[0])} />}
        </Field>
      </div>
    </FormDialog>
  );
}

/** Cutoff, interior care day and plan at next renewal (ADM-CUS-09, ADM-CUS-15). */
export function SettingsDialog({ sub, customerId, onClose }: { sub: Subscription; customerId: string; onClose: () => void }) {
  const plans = usePlans();
  const [planId, setPlanId] = useState(NONE);
  const [cutoff, setCutoff] = useState(sub.cutoff_time || "09:00");
  const [interior, setInterior] = useState(sub.interior_day ?? "");
  const [starts, setStarts] = useState("");
  const save = useCustomerSave(customerId, "Schedule settings saved.", onClose);
  const current = plans.data?.find((p) => p.id === sub.plan_id);
  const next = planId !== NONE ? plans.data?.find((p) => p.id === planId) : undefined;
  const interiorPlan = next ?? current;
  const needsInterior = Boolean(interiorPlan?.includes_interior);
  return (
    <FormDialog open onOpenChange={(o) => !o && onClose()} title="Schedule settings"
                description="The 9 PM deadline does not apply to the admin. The customer is not notified."
                submitLabel="Save settings" busy={save.isPending} disabled={needsInterior && !interior}
                onSubmit={() => save.mutate({ path: `/v1/admin/subscriptions/${sub.id}`, method: "PATCH", body: {
                  cutoff_time: cutoff,
                  ...(needsInterior && interior ? { interior_day: interior } : {}),
                  ...(planId !== NONE ? { plan_id: planId, ...(starts ? { effective_from: starts } : {}) } : {}),
                } })}>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <Field label="Service cutoff" hint="Visits finish by this time.">
          {(p) => <SelectBox {...p} value={cutoff} onChange={setCutoff} choices={timeChoices} />}
        </Field>
        {needsInterior ? (
          <Field label="Interior care day">
            {(p) => <SelectBox {...p} value={interior} onChange={setInterior} choices={weekdays.map((d) => ({ value: d, label: d }))} />}
          </Field>
        ) : (
          <Field label="Interior care day" hint="The plan does not include interior care.">
            {(p) => <Input {...p} disabled value="Not in this plan" />}
          </Field>
        )}
        <Field label="New plan" className="sm:col-span-2"
               hint={sub.pending_from ? `A change already starts on ${showDate(sub.pending_from)}. A new choice replaces it.` : "Without a date, the new plan and price start on the next renewal date (ADM-CUS-15)."}>
          {(p) => (
            <SelectBox {...p} value={planId} onChange={setPlanId} choices={[
              { value: NONE, label: `Keep current plan${current ? ` (${current.name})` : ""}` },
              ...(plans.data ?? []).filter((x) => x.active && x.id !== sub.plan_id).map((x) => ({
                value: x.id, label: `${x.name} · ${inr(x.monthly_price_rupees)}/month`,
              })),
            ]} />
          )}
        </Field>
        {planId !== NONE && (
          <Field label="Plan starts on (optional)" className="sm:col-span-2"
                 hint="Visits follow the new plan from this day. The next payment that is created uses the new price. A payment that already exists keeps its price.">
            {(p) => <Input {...p} type="date" min={new Date().toISOString().slice(0, 10)} value={starts} onChange={(e) => setStarts(e.target.value)} />}
          </Field>
        )}
      </div>
    </FormDialog>
  );
}

export function SkipDialog({ v, customerId, onClose }: { v: Vehicle; customerId: string; onClose: () => void }) {
  const [date, setDate] = useState("");
  const save = useCustomerSave(customerId, "Date skipped.", onClose);
  return (
    <FormDialog open onOpenChange={(o) => !o && onClose()} title={`Skip a date, ${v.registration}`} size="sm"
                description="On the customer's behalf. If the schedule is frozen, the visit is removed from it."
                submitLabel="Skip date" busy={save.isPending} disabled={!date}
                onSubmit={() => save.mutate({ path: `/v1/admin/vehicles/${v.id}/skips`, body: { date } })}>
      <Field label="Service date">{(p) => <Input {...p} type="date" value={date} onChange={(e) => setDate(e.target.value)} />}</Field>
    </FormDialog>
  );
}

export function PauseDialog({ v, customerId, onClose }: { v: Vehicle; customerId: string; onClose: () => void }) {
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const save = useCustomerSave(customerId, "Pause saved.", onClose);
  const order = from && to && to < from ? "The pause must end on or after its first day." : undefined;
  return (
    <FormDialog open onOpenChange={(o) => !o && onClose()} title={`Pause, ${v.registration}`} size="sm"
                description="No visits from the first day to the last day, inclusive."
                submitLabel="Pause" busy={save.isPending} disabled={!from || !to || Boolean(order)}
                onSubmit={() => save.mutate({ path: `/v1/admin/vehicles/${v.id}/pauses`, body: { from_date: from, to_date: to } })}>
      <div className="grid grid-cols-2 gap-4">
        <Field label="First day">{(p) => <Input {...p} type="date" value={from} onChange={(e) => setFrom(e.target.value)} />}</Field>
        <Field label="Last day" error={order}>{(p) => <Input {...p} type="date" value={to} onChange={(e) => setTo(e.target.value)} />}</Field>
      </div>
    </FormDialog>
  );
}

/** "1, 3-5, 9" as day numbers, or null when it is not a list of numbers. */
export function parseDays(text: string): number[] | null {
  const out: number[] = [];
  for (const part of text.split(",").map((s) => s.trim()).filter(Boolean)) {
    const range = /^(\d+)\s*-\s*(\d+)$/.exec(part);
    if (range) {
      const [a, b] = [Number(range[1]), Number(range[2])];
      if (b < a || b - a > 60) return null;
      for (let n = a; n <= b; n++) out.push(n);
    } else if (/^\d+$/.test(part)) out.push(Number(part));
    else return null;
  }
  return out;
}

/** The schedule pattern of a subscription: Default, Weekly or Cycle (S-02, ADM-SCH-41). */
export function PatternDialog({ sub, registration, customerId, onClose }: {
  sub: Subscription; registration: string; customerId: string; onClose: () => void;
}) {
  const current = useQuery({
    queryKey: ["customer", customerId, "pattern", sub.id],
    queryFn: () => api<SchedulePattern>(`/v1/admin/subscriptions/${sub.id}/schedule-pattern`),
  });
  return current.data
    ? <PatternForm key={current.data.kind} sub={sub} registration={registration} customerId={customerId} current={current.data} onClose={onClose} />
    : null;
}

function PatternForm({ sub, registration, customerId, current, onClose }: {
  sub: Subscription; registration: string; customerId: string; current: SchedulePattern; onClose: () => void;
}) {
  const [kind, setKind] = useState<string>(current.kind);
  const [exterior, setExterior] = useState<string[]>(current.exterior_weekdays);
  const [interior, setInterior] = useState<string[]>(current.interior_weekdays);
  const [onlyText, setOnlyText] = useState(current.exterior_days.join(", "));
  const [combinedText, setCombinedText] = useState(current.combined_days.join(", "));
  const save = useAppMutation<Call>({
    mutationFn: call, success: "Schedule pattern saved.", onSuccess: onClose,
    invalidate: [["customer", customerId], ["customers"]],
  });
  const only = parseDays(onlyText);
  const combined = parseDays(combinedText);
  const cycleError = kind !== "Cycle" ? undefined
    : only === null || combined === null ? "Use day numbers like 1, 3, 5-7."
    : [...only, ...combined].some((n) => n < 1 || n > current.cycle_days) ? `Day numbers run from 1 to ${current.cycle_days}.`
    : new Set([...only, ...combined]).size !== only.length + combined.length ? "A day is listed twice."
    : undefined;
  const valid = kind === "Default" || (kind === "Weekly" && exterior.length > 0)
    || (kind === "Cycle" && !cycleError && only !== null && combined !== null && only.length + combined.length > 0);
  const toggle = (list: string[], set: (v: string[]) => void, day: string, on: boolean) =>
    set(on ? [...list, day] : list.filter((d) => d !== day));
  const submit = () => {
    const path = `/v1/admin/subscriptions/${sub.id}/schedule-pattern`;
    if (kind === "Default") save.mutate({ path, method: "DELETE" });
    else if (kind === "Weekly") save.mutate({ path, method: "PUT", body: { kind, exterior_weekdays: exterior, interior_weekdays: interior } });
    else save.mutate({ path, method: "PUT", body: { kind, exterior_days: only, combined_days: combined, exterior_count: only!.length, combined_count: combined!.length } });
  };
  return (
    <FormDialog open onOpenChange={(o) => !o && onClose()} title={`Schedule pattern, ${registration}`} size="sm"
                description="Which days this vehicle is serviced. The pattern repeats every week, or every billing cycle."
                submitLabel="Save pattern" busy={save.isPending} disabled={!valid} onSubmit={submit}>
      <Field label="Pattern">
        {(p) => <SelectBox {...p} value={kind} onChange={setKind} choices={[
          { value: "Default", label: `Default: Exterior every day${current.default_interior_day ? `, Interior on ${current.default_interior_day}` : ""}` },
          { value: "Weekly", label: "Weekly: choose weekdays" },
          { value: "Cycle", label: `Cycle: choose day numbers in the ${current.cycle_days}-day billing cycle` },
        ]} />}
      </Field>
      {kind === "Weekly" && (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead><tr className="text-left text-xs text-muted-foreground uppercase">
              <th className="py-1 pr-3 font-semibold">Day</th><th className="py-1 pr-3 font-semibold">Exterior</th><th className="py-1 font-semibold">Interior</th>
            </tr></thead>
            <tbody>
              {weekdays.map((d) => (
                <tr key={d} className="border-t">
                  <td className="py-1.5 pr-3">{d}</td>
                  <td className="py-1.5 pr-3">
                    <Checkbox aria-label={`Exterior ${d}`} checked={exterior.includes(d) || interior.includes(d)} disabled={interior.includes(d)}
                              onCheckedChange={(on) => toggle(exterior, setExterior, d, on === true)} />
                  </td>
                  <td className="py-1.5">
                    <Checkbox aria-label={`Interior ${d}`} checked={interior.includes(d)}
                              onCheckedChange={(on) => {
                                toggle(interior, setInterior, d, on === true);
                                if (on === true && !exterior.includes(d)) setExterior([...exterior, d]);
                              }} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="mt-2 text-xs text-muted-foreground">An Interior day is also an Exterior day.</p>
        </div>
      )}
      {kind === "Cycle" && (
        <div className="grid grid-cols-1 gap-4">
          <Field label="Exterior-only days" hint={`${only?.length ?? 0} days. Day 1 is the first day of each billing cycle.`}>
            {(p) => <Input {...p} value={onlyText} placeholder="1, 3, 5-7" onChange={(e) => setOnlyText(e.target.value)} />}
          </Field>
          <Field label="Exterior + Interior days" hint={`${combined?.length ?? 0} days`} error={cycleError}>
            {(p) => <Input {...p} value={combinedText} placeholder="2, 9" onChange={(e) => setCombinedText(e.target.value)} />}
          </Field>
        </div>
      )}
    </FormDialog>
  );
}

/** A temporary (with an end date) or permanent (from a date) parking change, S-07. */
export function ParkingDialog({ v, customerId, onClose }: { v: Vehicle; customerId: string; onClose: () => void }) {
  const societies = useSocietyList();
  const basements = societies.data?.find((s) => s.id === v.society_id || s.name === v.society)?.parking_basements ?? [];
  const [basement, setBasement] = useState(v.parking_basement);
  const [number, setNumber] = useState("");
  const [temporary, setTemporary] = useState(true);
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [note, setNote] = useState("");
  const save = useCustomerSave(customerId, "Parking change saved.", onClose);
  const order = temporary && from && to && to < from ? "The change must end on or after its first day." : undefined;
  const valid = basement && number.trim() !== "" && from && (!temporary || to) && !order;
  return (
    <FormDialog open onOpenChange={(o) => !o && onClose()} title={`Change parking, ${v.registration}`} size="sm"
                description="The crew see this slot on the job card for these days. The vehicle's own slot is not changed."
                submitLabel="Save change" busy={save.isPending} disabled={!valid}
                onSubmit={() => save.mutate({
                  path: `/v1/admin/vehicles/${v.id}/parking-changes`,
                  body: { basement, number: number.trim(), from_date: from, to_date: temporary ? to : null, note },
                })}>
      <div className="grid grid-cols-2 gap-4">
        <Field label="Basement">
          {(p) => basements.length > 0
            ? <SelectBox {...p} value={basement} onChange={setBasement}
                         choices={[...new Set([...basements, v.parking_basement].filter(Boolean))].map((b) => ({ value: b, label: b }))} />
            : <Input {...p} value={basement} onChange={(e) => setBasement(e.target.value)} />}
        </Field>
        <Field label="Parking number">{(p) => <Input {...p} value={number} onChange={(e) => setNumber(e.target.value)} />}</Field>
      </div>
      <Field label="Applies">
        {(p) => <SelectBox {...p} value={temporary ? "temporary" : "permanent"} onChange={(x) => setTemporary(x === "temporary")}
                           choices={[{ value: "temporary", label: "Temporarily, from a date to a date" }, { value: "permanent", label: "Permanently, from a date" }]} />}
      </Field>
      <div className="grid grid-cols-2 gap-4">
        <Field label="First day">{(p) => <Input {...p} type="date" value={from} onChange={(e) => setFrom(e.target.value)} />}</Field>
        {temporary && <Field label="Last day" error={order}>{(p) => <Input {...p} type="date" value={to} onChange={(e) => setTo(e.target.value)} />}</Field>}
      </div>
      <Field label="Note (optional)">{(p) => <Input {...p} value={note} maxLength={160} onChange={(e) => setNote(e.target.value)} />}</Field>
    </FormDialog>
  );
}

/**
 * The subscription status change that is valid now (ADM-SUB-01, -02, -04):
 * Activate needs the first service date, Make inactive needs a reason.
 */
export function StatusDialog({ sub, to, registration, customerId, onClose }: {
  sub: Subscription; to: "Active" | "Inactive" | "Activating"; registration: string; customerId: string; onClose: () => void;
}) {
  const [date, setDate] = useState(sub.first_service_date ?? "");
  const [reason, setReason] = useState("");
  const done = { Active: "Subscription is now Active.", Inactive: "Subscription is now Inactive.", Activating: "Subscription reactivated. Set the first service date to activate it." }[to];
  const save = useCustomerSave(customerId, done, onClose);
  const send = () => save.mutate({ path: `/v1/admin/subscriptions/${sub.id}/status`, method: "PUT", body: {
    status: to, reason: reason.trim(), ...(to === "Active" && date ? { first_service_date: date } : {}),
  } });
  if (to === "Active") {
    return (
      <FormDialog open onOpenChange={(o) => !o && onClose()} title={`Activate ${registration}`} size="sm"
                  description="Visits are scheduled from the first service date, and the 30-day billing cycle starts on it."
                  submitLabel="Activate" busy={save.isPending} disabled={!date} onSubmit={send}>
        <Field label="First service date">{(p) => <Input {...p} type="date" value={date} onChange={(e) => setDate(e.target.value)} />}</Field>
      </FormDialog>
    );
  }
  if (to === "Inactive") {
    return (
      <FormDialog open onOpenChange={(o) => !o && onClose()} title={`Make ${registration} inactive?`} size="sm" danger
                  description="Its future visits are removed from schedules and it no longer counts in capacity. The customer sees Inactive."
                  submitLabel="Make inactive" busy={save.isPending} disabled={!reason.trim()} onSubmit={send}>
        <Field label="Reason" hint="Recorded in the audit log.">
          {(p) => <Textarea {...p} rows={3} value={reason} onChange={(e) => setReason(e.target.value)} />}
        </Field>
      </FormDialog>
    );
  }
  return (
    <FormDialog open onOpenChange={(o) => !o && onClose()} title={`Reactivate ${registration}?`} size="sm"
                description="The subscription returns to Activating. You then set the new first service date and activate it; a new billing cycle starts from that date."
                submitLabel="Reactivate" busy={save.isPending} onSubmit={send}>
      <Field label="Reason" optional>{(p) => <Textarea {...p} rows={2} value={reason} onChange={(e) => setReason(e.target.value)} />}</Field>
    </FormDialog>
  );
}
