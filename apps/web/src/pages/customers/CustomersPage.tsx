import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../../api/client";
import { Button, Card, SelectField, StatusChip, TextField, useToast } from "../../components";
import { showDate } from "../../components/format";
import { ApiErrorNote } from "../../components/ApiErrorNote";
import { times, uploadCustomerAsset, weekdays, type Catalogue, type Customer, type Plan, type Vehicle } from "./api";
import { VehicleWizard } from "./VehicleWizard";

export function CustomersPage() {
  const navigate = useNavigate();
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(0);
  const [creating, setCreating] = useState(false);
  const list = useQuery({ queryKey: ["customers", search, page], queryFn: () => api<{ id: string; name: string; email: string; mobile: string }[]>(`/v1/admin/customers?q=${encodeURIComponent(search)}&limit=50&offset=${page * 50}`) });
  return <><h1 className="page-title">Customers</h1><Card title="Find a customer">
    <TextField label="Search by name, mobile, registration or society" value={search} onChange={e => { setSearch(e.target.value); setPage(0); }} />
    <Button onClick={() => setCreating(true)}>Create customer</Button><ApiErrorNote error={list.error} />
    {list.isPending && <p>Loading customersâ€¦</p>}
    {list.data?.length === 0 && <p>No customers found.</p>}
    <table><thead><tr><th>Name</th><th>Email</th><th>Mobile</th></tr></thead><tbody>{list.data?.map(c => <tr key={c.id}><td><Link to={`/customers/${c.id}`}>{c.name}</Link></td><td>{c.email}</td><td>{c.mobile}</td></tr>)}</tbody></table>
    <nav aria-label="Customer pages"><Button disabled={page === 0 || list.isFetching} onClick={() => setPage(page - 1)}>Previous</Button> Page {page + 1} <Button disabled={list.isFetching || (list.data?.length ?? 0) < 50} onClick={() => setPage(page + 1)}>Next</Button></nav>
  </Card>{creating && <VehicleWizard onClose={() => setCreating(false)} onSaved={id => { setCreating(false); navigate(`/customers/${id}`); }} />}</>;
}

function useAction(customerId: string) {
  const qc = useQueryClient(); const toast = useToast();
  return useMutation({ mutationFn: (r: { path: string; method?: string; body?: unknown }) => api<unknown>(r.path, { method: r.method ?? "POST", body: r.body }),
    onSuccess: () => { toast.show("Saved.", "ok"); void qc.invalidateQueries({ queryKey: ["customer", customerId] }); void qc.invalidateQueries({ queryKey: ["customers"] }); } });
}

function VehicleControls({ v, customerId }: { v: Vehicle; customerId: string }) {
  const action = useAction(customerId);
  const [date, setDate] = useState(""); const [end, setEnd] = useState(""); const [reason, setReason] = useState("");
  const [status, setStatus] = useState(v.subscription?.status ?? "Activating");
  const [planId, setPlanId] = useState(""); const [cutoff, setCutoff] = useState(v.subscription?.cutoff_time ?? "09:00");
  const [interior, setInterior] = useState(v.subscription?.interior_day ?? "");
  const [reg, setReg] = useState(v.registration.replaceAll(" ", "")); const [catalogueId, setCatalogueId] = useState("");
  const [basement, setBasement] = useState(v.parking_basement); const [parking, setParking] = useState(v.parking_number);
  const [uploadBusy, setUploadBusy] = useState(false); const [uploadError, setUploadError] = useState<unknown>(null);
  const plans = useQuery({ queryKey: ["customer-plans"], queryFn: () => api<Plan[]>("/v1/admin/directory/plans") });
  const catalogue = useQuery({ queryKey: ["customer-catalogue"], queryFn: () => api<Catalogue[]>("/v1/admin/directory/vehicle-catalogue") });
  const changes = useQuery({ queryKey: ["customer", customerId, "changes", v.id], queryFn: () => api<{ skips: { id: string; start_date: string }[]; pauses: { id: string; start_date: string; end_date: string }[] }>(`/v1/admin/vehicles/${v.id}/changes`) });
  const upload = async (file: File | undefined, purpose: "vehicle" | "rc") => {
    if (!file) return; setUploadBusy(true); setUploadError(null);
    try { const r = await uploadCustomerAsset(file, purpose); await action.mutateAsync({ path: `/v1/admin/vehicles/${v.id}`, method: "PATCH", body: { [purpose === "vehicle" ? "photo_upload_id" : "rc_upload_id"]: r.id } }); }
    catch (e) { setUploadError(e); } finally { setUploadBusy(false); }
  };
  return <Card title={`${v.registration} Â· ${v.make} ${v.model}`}>
    <p>{v.society} Â· Parking {v.parking_basement}-{v.parking_number} Â· {v.category}</p>
    {v.photo_url && <img src={v.photo_url} alt={v.registration} style={{ maxWidth: 180, maxHeight: 120 }} />}
    <ApiErrorNote error={action.error ?? changes.error ?? uploadError} />
    <details><summary>Edit car and parking</summary><TextField label="Registration" value={reg} onChange={e => setReg(e.target.value.toUpperCase())} />
      <SelectField label="Make, model and variant" value={catalogueId} onChange={e => setCatalogueId(e.target.value)}><option value="">Keep current vehicle details</option>{catalogue.data?.filter(c => c.active).map(c => <option key={c.id} value={c.id}>{c.make} {c.model} {c.variant} Â· {c.category}</option>)}</SelectField>
      <TextField label="Basement" value={basement} onChange={e => setBasement(e.target.value)} /><TextField label="Parking number" value={parking} onChange={e => setParking(e.target.value)} />
      <Button busy={action.isPending} onClick={() => action.mutate({ path: `/v1/admin/vehicles/${v.id}`, method: "PATCH", body: { registration: reg, parking_basement: basement, parking_number: parking, ...(catalogueId ? { catalogue_id: catalogueId } : {}) } })}>Save car details</Button>
      <label>Replace vehicle photo<input type="file" accept="image/*" disabled={uploadBusy} onChange={e => void upload(e.target.files?.[0], "vehicle")} /></label>
      <label>Upload RC document<input type="file" accept="image/jpeg,image/png,application/pdf" disabled={uploadBusy} onChange={e => void upload(e.target.files?.[0], "rc")} /></label>
      {v.rc_url && <><a href={v.rc_url} target="_blank" rel="noreferrer">Open RC</a><label><input type="checkbox" checked={v.rc_verified} onChange={e => action.mutate({ path: `/v1/admin/vehicles/${v.id}`, method: "PATCH", body: { rc_verified: e.target.checked } })} />RC verified</label></>}
    </details>
    {v.subscription && <><p><StatusChip>{v.subscription.status}</StatusChip> {v.subscription.plan_name} Â· â‚¹{v.subscription.price_rupees}/month</p>
      {v.subscription.pending_from && <p>Plan change starts on {showDate(v.subscription.pending_from)}.</p>}
      <details><summary>Subscription and schedule settings</summary>
        <SelectField label="Subscription status" value={status} onChange={e => setStatus(e.target.value)}>{["Activating", "Active", "Inactive"].map(s => <option key={s}>{s}</option>)}</SelectField>
        <TextField label="First service date" type="date" value={date} onChange={e => setDate(e.target.value)} /><TextField label="Reason" value={reason} onChange={e => setReason(e.target.value)} />
        <Button busy={action.isPending} onClick={() => action.mutate({ path: `/v1/admin/subscriptions/${v.subscription!.id}/status`, method: "PUT", body: { status, reason, ...(date ? { first_service_date: date } : {}) } })}>Set subscription status</Button>
        <SelectField label="Plan at next renewal" value={planId} onChange={e => setPlanId(e.target.value)}><option value="">Keep current plan</option>{plans.data?.filter(p => p.active).map(p => <option key={p.id} value={p.id}>{p.name} Â· â‚¹{p.monthly_price_rupees}</option>)}</SelectField>
        <SelectField label="Service cutoff" value={cutoff} onChange={e => setCutoff(e.target.value)}>{times.map(t => <option key={t}>{t}</option>)}</SelectField>
        <SelectField label="Interior care day" value={interior} onChange={e => setInterior(e.target.value)}><option value="">None</option>{weekdays.map(d => <option key={d}>{d}</option>)}</SelectField>
        <Button busy={action.isPending} onClick={() => action.mutate({ path: `/v1/admin/subscriptions/${v.subscription!.id}`, method: "PATCH", body: { cutoff_time: cutoff, ...(interior && (!planId || plans.data?.find(p => p.id === planId)?.includes_interior) ? { interior_day: interior } : {}), ...(planId ? { plan_id: planId } : {}) } })}>Save settings</Button>
      </details>
      <details><summary>Skip and pause on behalf of customer</summary><TextField label="Service date / pause start" type="date" value={date} onChange={e => setDate(e.target.value)} /><TextField label="Pause end" type="date" value={end} onChange={e => setEnd(e.target.value)} />
        <Button disabled={!date} onClick={() => action.mutate({ path: `/v1/admin/vehicles/${v.id}/skips`, body: { date } })}>Skip date</Button>
        <Button disabled={!date || !end} onClick={() => action.mutate({ path: `/v1/admin/vehicles/${v.id}/pauses`, body: { from_date: date, to_date: end } })}>Pause</Button>
        {changes.data?.skips.map(s => <p key={s.id}>{showDate(s.start_date)} <Button variant="secondary" onClick={() => action.mutate({ path: `/v1/admin/vehicles/${v.id}/skips/${s.id}`, method: "DELETE" })}>Un-skip</Button></p>)}
        {changes.data?.pauses.map(p => <p key={p.id}>{showDate(p.start_date)} to {showDate(p.end_date)} <Button variant="secondary" onClick={() => action.mutate({ path: `/v1/admin/vehicles/${v.id}/pauses/${p.id}`, method: "DELETE" })}>End pause</Button></p>)}
      </details>
    </>}
    <h3>Payments</h3>{v.payments.map(p => <p key={p.id}>â‚¹{p.amount_rupees} Â· Due {showDate(p.due_date)} Â· <StatusChip>{p.status}</StatusChip></p>)}<Link to="/payments">Manage payments</Link>
  </Card>;
}

export function CustomerDetailPage() {
  const { id = "" } = useParams(); const qc = useQueryClient();
  const [adding, setAdding] = useState(false); const action = useAction(id);
  const details = useQuery({ queryKey: ["customer", id], queryFn: () => api<Customer>(`/v1/admin/customers/${id}`) });
  const sessions = useQuery({ queryKey: ["customer", id, "sessions"], queryFn: () => api<{ id: string; device_name: string; platform: string; app_version: string; last_active: string; channel: string }[]>(`/v1/admin/customers/${id}/sessions`) });
  const preferences = useQuery({ queryKey: ["customer", id, "preferences"], queryFn: () => api<{ items: { event: string; label: string; enabled: boolean }[] }>(`/v1/admin/customers/${id}/notification-preferences`) });
  const c = details.data;
  if (!c) return <><h1>Customer</h1><ApiErrorNote error={details.error} /><p>{details.isPending ? "Loadingâ€¦" : "Customer unavailable."}</p></>;
  return <><Link to="/customers">â† Customers</Link><h1 className="page-title">{c.first_name} {c.last_name}</h1><ApiErrorNote error={action.error} />
    {(c.imported_history?.length ?? 0) > 0 && <Card title="Imported service history">{c.imported_history!.map(h => <article key={h.id}><strong>{h.service}</strong> · {h.vehicle} · {h.date ? showDate(h.date) : "Date unknown"}<p>Completion not recorded · Payment {h.payment_status || "unknown"}</p><p>{h.notes}</p></article>)}</Card>}
    <Card title="Customer details"><p>{c.email} Â· {c.mobile}</p><p>Email {c.email_verified ? "verified" : "not verified"} Â· Password {c.password_set ? "set" : "not set"} Â· Review {c.onboarding_confirmed ? "confirmed" : "pending"}</p>
      <form onSubmit={e => { e.preventDefault(); const f = new FormData(e.currentTarget); action.mutate({ path: `/v1/admin/customers/${id}`, method: "PATCH", body: Object.fromEntries(f) }); }}>
        <TextField label="First name" name="first_name" defaultValue={c.first_name} /><TextField label="Last name" name="last_name" defaultValue={c.last_name} /><TextField label="Mobile" name="mobile" defaultValue={c.mobile} /><TextField label="Flat" name="flat" defaultValue={c.flat} /><Button type="submit" busy={action.isPending}>Save customer</Button>
      </form>
      <Button variant="secondary" onClick={() => action.mutate({ path: `/v1/admin/customers/${id}/resend-welcome` })}>Resend welcome email</Button>
      <details><summary>Email and password reset</summary><p>These actions clear the password and sign the customer out. They verify their email and set a new password at next sign-in.</p>
        <form onSubmit={e => { e.preventDefault(); action.mutate({ path: `/v1/admin/customers/${id}/email`, method: "PATCH", body: { email: new FormData(e.currentTarget).get("email") } }); }}><TextField label="Correct email" name="email" defaultValue={c.email} type="email" /><Button type="submit">Correct email</Button></form>
        <Button onClick={() => action.mutate({ path: `/v1/admin/customers/${id}/reset-password` })}>Clear password</Button>
      </details>
    </Card>
    <Button onClick={() => setAdding(true)}>Add vehicle</Button>{c.vehicles.map(v => <VehicleControls key={v.id} v={v} customerId={id} />)}
    <Card title="Notifications"><ApiErrorNote error={preferences.error} />{preferences.data?.items.map(p => <label key={p.event}><input type="checkbox" checked={p.enabled} onChange={e => action.mutate({ path: `/v1/admin/customers/${id}/notification-preferences`, method: "PUT", body: { items: [{ event: p.event, enabled: e.target.checked }] } })} />{p.label || p.event.replaceAll("_", " ")}</label>)}</Card>
    <Card title="Signed-in sessions"><ApiErrorNote error={sessions.error} />{sessions.data?.length === 0 && <p>No active sessions.</p>}{sessions.data?.map(s => <p key={s.id}>{s.device_name || s.channel} Â· {s.platform} {s.app_version} Â· Last active {new Date(s.last_active).toLocaleString("en-IN")} <Button variant="secondary" onClick={() => action.mutate({ path: `/v1/admin/customers/${id}/sessions/${s.id}/logout` })}>Sign out session</Button></p>)}<Button onClick={() => action.mutate({ path: `/v1/admin/customers/${id}/sessions/logout` })}>Sign out all sessions</Button></Card>
    {adding && <VehicleWizard customerId={id} onClose={() => setAdding(false)} onSaved={() => { setAdding(false); void qc.invalidateQueries({ queryKey: ["customer", id] }); }} />}
  </>;
}
