import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "../../api/client";
import { Button, Dialog, SelectField, TextField } from "../../components";
import { ApiErrorNote } from "../../components/ApiErrorNote";
import { newVehicle, times, uploadCustomerAsset, weekdays, type Catalogue, type Plan, type Society, type VehicleInput } from "./api";

export function VehicleWizard({ customerId, onClose, onSaved }: {
  customerId?: string; onClose: () => void; onSaved: (id: string) => void;
}) {
  const [step, setStep] = useState(0);
  const [vehicle, setVehicle] = useState(newVehicle);
  const [person, setPerson] = useState({ first_name: "", last_name: "", email: "", mobile: "", flat: "" });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [search, setSearch] = useState("");
  const [photoUrl, setPhotoUrl] = useState("");
  const [make, setMake] = useState("");
  const [model, setModel] = useState("");
  const societies = useQuery({ queryKey: ["customer-societies"], queryFn: () => api<Society[]>("/v1/admin/directory/societies") });
  const catalogue = useQuery({ queryKey: ["customer-catalogue"], queryFn: () => api<Catalogue[]>("/v1/admin/directory/vehicle-catalogue") });
  const plans = useQuery({ queryKey: ["customer-plans"], queryFn: () => api<Plan[]>("/v1/admin/directory/plans") });
  const active = (catalogue.data ?? []).filter(c => c.active);
  const plan = plans.data?.find(p => p.id === vehicle.plan_id);
  const entry = active.find(c => c.id === vehicle.catalogue_id);
  const society = societies.data?.find(s => s.id === vehicle.society_id);
  const set = <K extends keyof VehicleInput>(key: K, value: VehicleInput[K]) => setVehicle(v => ({ ...v, [key]: value }));
  const stages = customerId ? ["Society", "Vehicle", "Parking", "Plan", "Preferences", "Review"] : ["Customer", "Society", "Vehicle", "Parking", "Plan", "Preferences", "Review"];
  const stage = stages[step];
  const upload = async (file: File | undefined, purpose: "vehicle" | "rc") => {
    if (!file) return;
    setBusy(true); setError(null);
    try {
      const r = await uploadCustomerAsset(file, purpose);
      set(purpose === "vehicle" ? "photo_upload_id" : "rc_upload_id", r.id);
      if (purpose === "vehicle") setPhotoUrl(r.url);
    } catch (e) { setError(e); } finally { setBusy(false); }
  };
  const save = async () => {
    setBusy(true); setError(null);
    try {
      const r = await api<{ id: string; existing?: boolean; welcome_sent?: boolean }>(customerId ? `/v1/admin/customers/${customerId}/vehicles` : "/v1/admin/customers", {
        method: "POST", body: customerId ? vehicle : { ...person, vehicle },
      });
      onSaved(customerId ?? r.id);
    } catch (e) { setError(e); } finally { setBusy(false); }
  };
  const valid = stage === "Customer" ? person.first_name && person.last_name && /^\S+@\S+\.\S+$/.test(person.email) && /^\d{10}$/.test(person.mobile)
    : stage === "Society" ? vehicle.society_id : stage === "Vehicle" ? vehicle.catalogue_id && vehicle.registration && vehicle.photo_upload_id
    : stage === "Parking" ? vehicle.parking_basement && /^\d{1,5}$/.test(vehicle.parking_number)
    : stage === "Plan" ? vehicle.plan_id : stage === "Preferences" ? vehicle.cutoff_time && (!plan?.includes_interior || vehicle.interior_day) : true;
  return <Dialog open title={customerId ? "Add vehicle" : "Create customer"} onClose={onClose} footer={<>
    <Button variant="secondary" onClick={onClose}>Cancel</Button>
    {step > 0 && <Button variant="secondary" disabled={busy} onClick={() => setStep(s => s - 1)}>Back</Button>}
    <Button busy={busy} disabled={!valid} onClick={() => step === stages.length - 1 ? void save() : setStep(s => s + 1)}>{stage === "Review" ? "Create" : "Continue"}</Button>
  </>}>
    <p>Step {step + 1} of {stages.length}: {stage}</p>
    <ApiErrorNote error={error ?? societies.error ?? catalogue.error ?? plans.error} />
    {error instanceof Error && !("code" in error) && <p role="alert">{error.message}</p>}
    {stage === "Customer" && Object.entries(person).map(([key, value]) => <TextField key={key} label={{ first_name: "First name", last_name: "Last name", email: "Email", mobile: "Mobile number", flat: "Flat" }[key] ?? key} value={value} onChange={e => setPerson(p => ({ ...p, [key]: e.target.value }))} />)}
    {stage === "Society" && <><TextField label="Search society" value={search} onChange={e => setSearch(e.target.value)} /><SelectField label="Society" value={vehicle.society_id} onChange={e => { set("society_id", e.target.value); set("parking_basement", ""); }}><option value="">Choose</option>{(societies.data ?? []).filter(s => s.active && s.name.toLowerCase().includes(search.toLowerCase())).map(s => <option key={s.id} value={s.id}>{s.name}</option>)}</SelectField><p>A vehicle's society cannot be changed after creation.</p></>}
    {stage === "Vehicle" && <>
      <SelectField label="Make" value={make} onChange={e => { setMake(e.target.value); setModel(""); set("catalogue_id", ""); }}><option value="">Choose</option>{[...new Set(active.map(c => c.make))].map(m => <option key={m}>{m}</option>)}</SelectField>
      <SelectField label="Model" value={model} onChange={e => { setModel(e.target.value); set("catalogue_id", ""); }}><option value="">Choose</option>{[...new Set(active.filter(c => c.make === make).map(c => c.model))].map(m => <option key={m}>{m}</option>)}</SelectField>
      <SelectField label="Variant" value={vehicle.catalogue_id} onChange={e => set("catalogue_id", e.target.value)}><option value="">Choose</option>{active.filter(c => c.make === make && c.model === model).map(c => <option key={c.id} value={c.id}>{c.variant || "Standard"}</option>)}</SelectField>
      {entry && <p>Category: {entry.category} · Auto-detected</p>}
      <TextField label="Registration" value={vehicle.registration} onChange={e => set("registration", e.target.value.toUpperCase())} hint="For example HR26EC4321" />
      <label>Vehicle photo (required)<input type="file" accept="image/jpeg,image/png,image/heic,image/heif,image/webp" disabled={busy} onChange={e => void upload(e.target.files?.[0], "vehicle")} /></label>
      {photoUrl && <img src={photoUrl} alt="Vehicle" style={{ maxWidth: 180, maxHeight: 120 }} />}
      <label>RC document (optional, JPG, PNG or PDF up to 5 MB)<input type="file" accept="image/jpeg,image/png,application/pdf" disabled={busy} onChange={e => void upload(e.target.files?.[0], "rc")} /></label>
      {vehicle.rc_upload_id && <p>RC uploaded</p>}
    </>}
    {stage === "Parking" && <><SelectField label="Basement" value={vehicle.parking_basement} onChange={e => set("parking_basement", e.target.value)}><option value="">Choose</option>{society?.parking_basements.map(b => <option key={b}>{b}</option>)}</SelectField><TextField label="Parking number" value={vehicle.parking_number} onChange={e => set("parking_number", e.target.value)} /><p>{vehicle.parking_basement} · {vehicle.parking_number}</p></>}
    {stage === "Plan" && <><SelectField label="Plan" value={vehicle.plan_id} onChange={e => { set("plan_id", e.target.value); set("interior_day", null); }}><option value="">Choose</option>{plans.data?.filter(p => p.active).map(p => <option key={p.id} value={p.id}>{p.name} · ₹{p.monthly_price_rupees}/month</option>)}</SelectField>{plan && <><p>{plan.badge} · Cancel anytime · GST included</p>{plan.list_price_rupees && <del>₹{plan.list_price_rupees}</del>}<ul>{plan.inclusions.map(i => <li key={i}>{i}</li>)}</ul></>}</>}
    {stage === "Preferences" && <><SelectField label="Service cutoff time" value={vehicle.cutoff_time} onChange={e => set("cutoff_time", e.target.value)}>{times.map(t => <option key={t}>{t}</option>)}</SelectField><p>Priveo assigns the exact service slot.</p>{plan?.includes_interior && <SelectField label="Interior care day" value={vehicle.interior_day ?? ""} onChange={e => set("interior_day", e.target.value)}><option value="">Choose</option>{weekdays.map(d => <option key={d}>{d}</option>)}</SelectField>}</>}
    {stage === "Review" && <><p>{person.first_name} {person.last_name} · {person.email}</p><p>{society?.name} · {entry?.make} {entry?.model} {entry?.variant} · {vehicle.registration}</p><p>Parking: {vehicle.parking_basement} · {vehicle.parking_number}</p><p>Cutoff: {vehicle.cutoff_time} {vehicle.interior_day && `· Interior: ${vehicle.interior_day}`}</p><p>{plan?.name} · Total ₹{plan?.monthly_price_rupees}, including GST</p><p>Priveo will confirm the start date. The subscription starts Activating.</p><SelectField label="First payment status" value={vehicle.first_payment_status} onChange={e => set("first_payment_status", e.target.value)}>{["Due", "Over due", "Initiated", "Received"].map(s => <option key={s}>{s}</option>)}</SelectField></>}
  </Dialog>;
}
