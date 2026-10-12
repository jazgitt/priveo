import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../../api/client";
import { Button, Card, SelectField, StatusChip, TextField } from "../../components";
import { ApiErrorNote } from "../../components/ApiErrorNote";
import { showDate } from "../../components/format";
import { times, type Customer, type Society } from "../customers/api";

interface Booking {
  id: string; service: string; customer_name: string; vehicle: string; society: string; date: string;
  finish_by: string; status: string; payment_id: string | null; payment_status: string | null;
  price_rupees: number | null; standalone: boolean; contact_mobile: string; notes: string;
  change_requested: boolean; requested_date: string | null; requested_finish_by: string | null;
  crew_name: string | null; start_time: string | null;
}

function BookingCard({ b }: { b: Booking }) {
  const qc = useQueryClient(); const [date, setDate] = useState(b.date); const [finish, setFinish] = useState(b.finish_by);
  const action = useMutation({ mutationFn: (body: unknown) => api(`/v1/admin/addons/${b.id}`, { method: "PATCH", body }),
    onSuccess: () => { void qc.invalidateQueries({ queryKey: ["addon-bookings"] }); void qc.invalidateQueries({ queryKey: ["needs-scheduling"] }); void qc.invalidateQueries({ queryKey: ["board"] }); } });
  const open = b.status === "Requested" || b.status === "Scheduled";
  return <Card title={`${b.service} · ${b.vehicle || b.customer_name}`}>
    <p>{b.customer_name} · {b.society} · {showDate(b.date)} · Finish by {b.finish_by} · <StatusChip>{b.status}</StatusChip></p>
    <p>{b.crew_name ? `${b.crew_name} at ${b.start_time}` : "Waiting for assignment"}</p>
    {b.standalone ? <p>Standalone request · {b.contact_mobile} · {b.notes}</p> : <p>₹{b.price_rupees} · Payment {b.payment_status}</p>}
    {b.payment_id && <Link to={`/payments?payment=${b.payment_id}`}>Open payment</Link>}
    <ApiErrorNote error={action.error} />
    {b.change_requested && <><p>Change requested: {showDate(b.requested_date)} · Finish by {b.requested_finish_by}</p>
      <Button busy={action.isPending} onClick={() => action.mutate({ resolve_change: true })}>Apply requested change</Button>
      <Button variant="secondary" busy={action.isPending} onClick={() => action.mutate({ reject_change: true })}>Reject requested change</Button>
    </>}
    {open && <><TextField label="Service date" type="date" value={date} onChange={e => setDate(e.target.value)} />
      <SelectField label="Finish by" value={finish} onChange={e => setFinish(e.target.value)}>{times.map(t => <option key={t}>{t}</option>)}</SelectField>
      <Button busy={action.isPending} onClick={() => action.mutate({ date, finish_by: finish })}>Save date and time</Button>
      <Button variant="secondary" busy={action.isPending} onClick={() => action.mutate({ status: "Cancelled" })}>Cancel booking</Button>
      <p>If the schedule is frozen, unfreeze it before changing the date or time. Cancellation removes the job without a code.</p><Link to="/schedule">Open schedule</Link>
    </>}
  </Card>;
}

export function AddonsPage() {
  const qc = useQueryClient(); const [status, setStatus] = useState(""); const [search, setSearch] = useState("");
  const [customerId, setCustomerId] = useState(""); const [vehicleId, setVehicleId] = useState("");
  const [date, setDate] = useState(""); const [finish, setFinish] = useState("12:00");
  const [society, setSociety] = useState(""); const [from, setFrom] = useState(""); const [to, setTo] = useState(""); const [service, setService] = useState("");
  const societies = useQuery({ queryKey: ["customer-societies"], queryFn: () => api<Society[]>("/v1/admin/directory/societies") });
  const params = new URLSearchParams();
  if (status) params.set("status", status); if (society) params.set("society_id", society);
  if (from) params.set("date_from", from); if (to) params.set("date_to", to); if (service) params.set("service", service);
  const bookings = useQuery({ queryKey: ["addon-bookings", params.toString()], queryFn: () => api<Booking[]>(`/v1/admin/addons?${params}`) });
  const customers = useQuery({ queryKey: ["customers", search], queryFn: () => api<{ id: string; name: string }[]>(`/v1/admin/customers?q=${encodeURIComponent(search)}`) });
  const customer = useQuery({ queryKey: ["customer", customerId], enabled: !!customerId, queryFn: () => api<Customer>(`/v1/admin/customers/${customerId}`) });
  const create = useMutation({ mutationFn: () => api("/v1/admin/addons", { method: "POST", body: { vehicle_id: vehicleId, service: "Deep Spa", date, finish_by: finish } }),
    onSuccess: () => { setVehicleId(""); setDate(""); void qc.invalidateQueries({ queryKey: ["addon-bookings"] }); void qc.invalidateQueries({ queryKey: ["needs-scheduling"] }); } });
  return <><h1 className="page-title">Add-ons</h1><Card title="Request Deep Spa for a customer">
    <TextField label="Find customer" value={search} onChange={e => setSearch(e.target.value)} />
    <SelectField label="Customer" value={customerId} onChange={e => { setCustomerId(e.target.value); setVehicleId(""); }}><option value="">Choose</option>{customers.data?.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}</SelectField>
    <SelectField label="Vehicle" value={vehicleId} onChange={e => setVehicleId(e.target.value)}><option value="">Choose an Active vehicle</option>{customer.data?.vehicles.filter(v => v.subscription?.status === "Active").map(v => <option key={v.id} value={v.id}>{v.registration} · {v.society}</option>)}</SelectField>
    <TextField label="Proposed date" type="date" value={date} onChange={e => setDate(e.target.value)} /><SelectField label="Finish by" value={finish} onChange={e => setFinish(e.target.value)}>{times.map(t => <option key={t}>{t}</option>)}</SelectField>
    <ApiErrorNote error={create.error ?? customers.error ?? customer.error} /><Button busy={create.isPending} disabled={!vehicleId || !date} onClick={() => create.mutate()}>Request Deep Spa</Button>
  </Card><Card title="Requests"><SelectField label="Status filter" value={status} onChange={e => setStatus(e.target.value)}><option value="">All</option>{["Requested", "Scheduled", "Completed", "Missed", "Cancelled"].map(s => <option key={s}>{s}</option>)}</SelectField><ApiErrorNote error={bookings.error} />{bookings.isPending && <p>Loading…</p>}{bookings.data?.length === 0 && <p>No add-on requests.</p>}</Card>
    <Card title="Filter requests"><SelectField label="Society filter" value={society} onChange={e => setSociety(e.target.value)}><option value="">All societies</option>{societies.data?.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}</SelectField>
      <TextField label="From date" type="date" value={from} onChange={e => setFrom(e.target.value)} /><TextField label="To date" type="date" value={to} onChange={e => setTo(e.target.value)} />
      <SelectField label="Add-on filter" value={service} onChange={e => setService(e.target.value)}><option value="">All add-ons</option><option value="Deep Spa">Deep Spa</option></SelectField><ApiErrorNote error={societies.error} />
    </Card>{bookings.data?.map(b => <BookingCard key={`${b.id}:${b.date}:${b.finish_by}`} b={b} />)}
  </>;
}
