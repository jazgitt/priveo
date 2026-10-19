import { Check } from "lucide-react";
import { useState } from "react";

import { api } from "@/api/client";
import { Field, SelectBox } from "@/blocks/fields";
import { FormDialog } from "@/blocks/FormDialog";
import { DetailList, ErrorState } from "@/blocks/layout";
import { EVENTS } from "@/analytics/events";
import { errorMessage, useAppMutation } from "@/blocks/mutation";
import { inr } from "@/components/format";
import { cn } from "@/lib/utils";
import { useSite } from "@/site/SiteContext";
import { Button } from "@/ui/button";
import { Input } from "@/ui/input";
import { Switch } from "@/ui/switch";

import { newVehicle, times, uploadCustomerAsset, weekdays, type VehicleInput } from "./api";
import { useCatalogue, usePlans, useSocietyList } from "./dialogs";

const LABELS = { first_name: "First name", last_name: "Last name", email: "Email", mobile: "Mobile number", flat: "Flat" } as const;

/** Create a customer with their first vehicle (ADM-CUS-01), or add a vehicle (ADM-CUS-05). */
export function VehicleWizard({ customerId, onClose, onSaved }: {
  customerId?: string; onClose: () => void; onSaved: (id: string) => void;
}) {
  const [step, setStep] = useState(0);
  const [withSubscription, setWithSubscription] = useState(true);
  const site = useSite();
  // The society starts as the site the admin is working on.
  const [vehicle, setVehicle] = useState(() => ({ ...newVehicle(), society_id: site.id }));
  const [person, setPerson] = useState({ first_name: "", last_name: "", email: "", mobile: "", flat: "" });
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<unknown>(null);
  const [photoUrl, setPhotoUrl] = useState("");
  const [make, setMake] = useState("");
  const [model, setModel] = useState("");
  const societies = useSocietyList();
  const catalogue = useCatalogue();
  const plans = usePlans();
  const active = (catalogue.data ?? []).filter((c) => c.active);
  const plan = plans.data?.find((p) => p.id === vehicle.plan_id);
  const entry = active.find((c) => c.id === vehicle.catalogue_id);
  const society = societies.data?.find((s) => s.id === vehicle.society_id);
  const set = <K extends keyof VehicleInput>(key: K, value: VehicleInput[K]) => setVehicle((v) => ({ ...v, [key]: value }));
  const stages = customerId ? ["Society", "Vehicle", "Parking", "Plan", "Preferences", "Review"]
    : ["Customer", "Society", "Vehicle", "Parking", "Plan", "Preferences", "Review"];
  const stage = stages[step];

  const upload = async (file: File | undefined) => {
    if (!file) return;
    setUploading(true); setUploadError(null);
    try {
      const r = await uploadCustomerAsset(file);
      set("photo_upload_id", r.id);
      setPhotoUrl(r.url);
    } catch (e) { setUploadError(e); } finally { setUploading(false); }
  };
  // The photo is optional: no photo is sent as null, not as an empty string.
  const payload = () => {
    const car = { ...vehicle, photo_upload_id: vehicle.photo_upload_id || null };
    return withSubscription ? car : { ...car, plan_id: null, cutoff_time: null, interior_day: null };
  };
  const save = useAppMutation<void, { id: string; existing?: boolean }>({
    event: EVENTS.customerOrVehicleAdded,
    mutationFn: () => api(customerId ? `/v1/admin/customers/${customerId}/vehicles` : "/v1/admin/customers", {
      method: "POST", body: customerId ? payload() : { ...person, vehicle: payload() },
    }),
    pending: customerId ? "Adding the vehicle…" : "Creating the customer…",
    success: (r) => customerId ? "Vehicle added."
      : r.existing ? "That email already belongs to a customer. Opening them." : "Customer created. The welcome email is on its way.",
    invalidate: customerId ? [["customer", customerId], ["customers"]] : [["customers"]],
    onSuccess: (r) => onSaved(customerId ?? r.id),
  });

  const emailOk = /^\S+@\S+\.\S+$/.test(person.email);
  const mobileOk = /^\d{10}$/.test(person.mobile);
  const valid = stage === "Customer" ? Boolean(person.first_name.trim() && person.last_name.trim() && emailOk && mobileOk)
    : stage === "Society" ? Boolean(vehicle.society_id)
    : stage === "Vehicle" ? Boolean(vehicle.catalogue_id && vehicle.registration)
    : stage === "Parking" ? Boolean(vehicle.parking_basement && /^\d{1,5}$/.test(vehicle.parking_number))
    : stage === "Plan" ? !withSubscription || Boolean(vehicle.plan_id)
    : stage === "Preferences" ? !withSubscription || Boolean(vehicle.cutoff_time && (!plan?.includes_interior || vehicle.interior_day))
    : true;
  const lookupError = societies.error ?? catalogue.error ?? plans.error ?? uploadError;
  const noSociety = societies.data !== undefined && societies.data.every((s) => !s.active);

  return (
    <FormDialog
      open onOpenChange={(o) => !o && onClose()} size="lg"
      title={customerId ? "Add vehicle" : "Create customer"}
      description={`Step ${step + 1} of ${stages.length}: ${stage}`}
      submitLabel={stage === "Review" ? "Create" : "Continue"}
      busy={save.isPending || uploading} disabled={!valid}
      onSubmit={() => (stage === "Review" ? save.mutate() : setStep((s) => s + 1))}
      extraActions={step > 0 ? <Button type="button" variant="ghost" disabled={save.isPending} onClick={() => setStep((s) => s - 1)}>Back</Button> : undefined}
    >
      <ol className="m-0 flex list-none flex-wrap gap-1.5 p-0" aria-label="Steps">
        {stages.map((s, i) => (
          <li key={s} aria-current={i === step ? "step" : undefined}
              className={cn("flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs",
                i === step && "border-foreground bg-foreground text-background",
                i < step && "border-ok/40 bg-ok/10 text-ok")}>
            {i < step && <Check className="size-3" aria-hidden />}{s}
          </li>
        ))}
      </ol>
      {lookupError ? <ErrorState message={errorMessage(lookupError)} /> : null}

      {stage === "Customer" && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          {(Object.keys(LABELS) as (keyof typeof LABELS)[]).map((key) => (
            <Field key={key} label={LABELS[key]} optional={key === "flat"} className={key === "email" ? "sm:col-span-2" : undefined}
                   error={key === "email" && person.email && !emailOk ? "Enter a valid email address."
                     : key === "mobile" && person.mobile && !mobileOk ? "Enter a 10-digit mobile number." : undefined}>
              {(p) => <Input {...p} type={key === "email" ? "email" : "text"} inputMode={key === "mobile" ? "numeric" : undefined}
                             value={person[key]} onChange={(e) => setPerson((x) => ({ ...x, [key]: e.target.value }))} />}
            </Field>
          ))}
          <p className="text-xs text-muted-foreground sm:col-span-2">A welcome email goes to this address. It holds no code or password.</p>
        </div>
      )}

      {stage === "Society" && noSociety && (
        <ErrorState message="There is no active society yet. Create a society under Site Setup first; a customer needs one." />
      )}
      {stage === "Society" && (
        <Field label="Society" hint="A vehicle's society cannot be changed after creation.">
          {(p) => (
            <SelectBox {...p} value={vehicle.society_id} placeholder="Choose a society"
                       onChange={(id) => { set("society_id", id); set("parking_basement", ""); }}
                       choices={(societies.data ?? []).filter((s) => s.active).map((s) => ({ value: s.id, label: s.name }))} />
          )}
        </Field>
      )}

      {stage === "Vehicle" && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <Field label="Make">
            {(p) => <SelectBox {...p} value={make} onChange={(m) => { setMake(m); setModel(""); set("catalogue_id", ""); }}
                               choices={[...new Set(active.map((c) => c.make))].map((m) => ({ value: m, label: m }))} />}
          </Field>
          <Field label="Model">
            {(p) => <SelectBox {...p} value={model} disabled={!make} onChange={(m) => { setModel(m); set("catalogue_id", ""); }}
                               choices={[...new Set(active.filter((c) => c.make === make).map((c) => c.model))].map((m) => ({ value: m, label: m }))} />}
          </Field>
          <Field label="Variant" hint={entry ? `Category: ${entry.category}` : undefined}>
            {(p) => <SelectBox {...p} value={vehicle.catalogue_id} disabled={!model} onChange={(id) => set("catalogue_id", id)}
                               choices={active.filter((c) => c.make === make && c.model === model).map((c) => ({ value: c.id, label: c.variant || "Standard" }))} />}
          </Field>
          <Field label="Registration" hint="For example HR26EC4321" className="sm:col-span-3">
            {(p) => <Input {...p} className="reg uppercase" value={vehicle.registration}
                           onChange={(e) => set("registration", e.target.value.toUpperCase().replaceAll(" ", ""))} />}
          </Field>
          <div className="grid grid-cols-1 gap-4 rounded-lg border bg-muted/40 p-4 sm:col-span-3 sm:grid-cols-[minmax(0,1fr)_9rem]">
            <Field label="Vehicle photo" optional hint={uploading ? "Uploading…" : "JPG, PNG, HEIC or WebP, under 10 MB."}>
              {(p) => <Input {...p} type="file" accept="image/jpeg,image/png,image/heic,image/heif,image/webp,.heic,.heif" disabled={uploading}
                             onChange={(e) => void upload(e.target.files?.[0])} />}
            </Field>
            {photoUrl
              ? <img src={photoUrl} alt="Vehicle" className="aspect-[4/3] w-36 self-center rounded-md border object-cover" />
              : <div className="flex aspect-[4/3] w-36 items-center justify-center self-center rounded-md border border-dashed text-xs text-muted-foreground">No photo yet</div>}
          </div>
        </div>
      )}

      {stage === "Parking" && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <Field label="Basement">
            {(p) => <SelectBox {...p} value={vehicle.parking_basement} onChange={(b) => set("parking_basement", b)}
                               choices={(society?.parking_basements ?? []).map((b) => ({ value: b, label: b }))} />}
          </Field>
          <Field label="Parking number" error={vehicle.parking_number && !/^\d{1,5}$/.test(vehicle.parking_number) ? "Up to 5 digits." : undefined}>
            {(p) => <Input {...p} inputMode="numeric" value={vehicle.parking_number} onChange={(e) => set("parking_number", e.target.value)} />}
          </Field>
        </div>
      )}

      {stage === "Plan" && (
        <div className="flex flex-col gap-4">
          <label className="flex items-center justify-between gap-3 rounded-lg border p-3">
            <span>
              <span className="block text-sm font-medium">Create a subscription</span>
              <span className="block text-xs text-muted-foreground">
                {withSubscription ? "A plan payment is created." : "No plan payment. This vehicle can book standalone Deep Spa."}
              </span>
            </span>
            <Switch aria-label="Create a subscription" checked={withSubscription} onCheckedChange={setWithSubscription} />
          </label>
          {withSubscription && (
            <>
              <Field label="Plan">
                {(p) => <SelectBox {...p} value={vehicle.plan_id} onChange={(id) => { set("plan_id", id); set("interior_day", null); }}
                                   choices={(plans.data ?? []).filter((x) => x.active).map((x) => ({ value: x.id, label: `${x.name} · ${inr(x.monthly_price_rupees)}/month` }))} />}
              </Field>
              {plan && (
                <div className="rounded-lg border bg-muted/40 p-4 text-sm">
                  <p className="m-0 font-medium">
                    {plan.name} · {inr(plan.monthly_price_rupees)}/month
                    {plan.list_price_rupees && <del className="ml-2 font-normal text-muted-foreground">{inr(plan.list_price_rupees)}</del>}
                  </p>
                  <p className="m-0 mt-0.5 text-xs text-muted-foreground">{[plan.badge, "Cancel anytime", "GST included"].filter(Boolean).join(" · ")}</p>
                  {plan.inclusions.length > 0 && <ul className="mt-2 mb-0">{plan.inclusions.map((i) => <li key={i}>{i}</li>)}</ul>}
                </div>
              )}
            </>
          )}
        </div>
      )}

      {stage === "Preferences" && !withSubscription && (
        <p className="text-sm text-muted-foreground">Standalone Spa uses a date and finish-by time chosen at booking.</p>
      )}
      {stage === "Preferences" && withSubscription && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <Field label="Service cutoff time" hint="Priveo assigns the exact service slot.">
            {(p) => <SelectBox {...p} value={vehicle.cutoff_time} onChange={(t) => set("cutoff_time", t)} choices={times.map((t) => ({ value: t, label: t }))} />}
          </Field>
          {plan?.includes_interior && (
            <Field label="Interior care day">
              {(p) => <SelectBox {...p} value={vehicle.interior_day ?? ""} onChange={(d) => set("interior_day", d)} choices={weekdays.map((d) => ({ value: d, label: d }))} />}
            </Field>
          )}
        </div>
      )}

      {stage === "Review" && (
        <div className="flex flex-col gap-4">
          <DetailList columns={2} items={[
            ...(!customerId ? [
              { label: "Customer", value: `${person.first_name} ${person.last_name}` },
              { label: "Email", value: person.email },
              { label: "Mobile", value: person.mobile },
              { label: "Flat", value: person.flat },
            ] : []),
            { label: "Society", value: society?.name },
            { label: "Vehicle", value: entry ? `${entry.make} ${entry.model} ${entry.variant}` : "" },
            { label: "Registration", value: <span className="reg">{vehicle.registration}</span> },
            { label: "Parking", value: `${vehicle.parking_basement}-${vehicle.parking_number}` },
            ...(withSubscription ? [
              { label: "Plan", value: plan ? `${plan.name} · ${inr(plan.monthly_price_rupees)}/month, GST included` : "" },
              { label: "Service cutoff", value: vehicle.cutoff_time },
              { label: "Interior care day", value: vehicle.interior_day ?? "None" },
            ] : [{ label: "Subscription", value: "None. Standalone Deep Spa is available after sign-in." }]),
          ]} />
          {withSubscription && (
            <>
              <Field label="First payment status" className="max-w-xs">
                {(p) => <SelectBox {...p} value={vehicle.first_payment_status} onChange={(s) => set("first_payment_status", s)}
                                   choices={["Due", "Over due", "Initiated", "Received"].map((s) => ({ value: s, label: s }))} />}
              </Field>
              <p className="text-xs text-muted-foreground">The subscription starts as Activating. You set the first service date when you activate it.</p>
            </>
          )}
        </div>
      )}
    </FormDialog>
  );
}
