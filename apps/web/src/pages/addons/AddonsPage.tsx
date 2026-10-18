import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";

import { api } from "@/api/client";
import { useConfirm } from "@/blocks/confirm";
import { DataTable } from "@/blocks/DataTable";
import { Field, NONE, SelectBox } from "@/blocks/fields";
import { BusyButton, FormDialog } from "@/blocks/FormDialog";
import { DetailList, EmptyState, ErrorState, PageHeader } from "@/blocks/layout";
import { errorMessage, useAppMutation } from "@/blocks/mutation";
import { StatusBadge } from "@/blocks/status";
import { inr, showDate } from "@/components/format";
import { useSite } from "@/site/SiteContext";
import { Button } from "@/ui/button";
import { Input } from "@/ui/input";

import { times } from "../customers/api";
import { CustomerPicker, VehiclePicker, type PickedCustomer } from "../customers/picker";

interface Booking {
  id: string; service: string; customer_name: string; vehicle: string; society: string; date: string;
  finish_by: string; status: string; payment_id: string | null; payment_status: string | null;
  price_rupees: number | null; standalone: boolean; contact_mobile: string; notes: string;
  change_requested: boolean; requested_date: string | null; requested_finish_by: string | null;
  crew_name: string | null; start_time: string | null;
}

const STATUSES = ["Requested", "Scheduled", "Completed", "Missed", "Cancelled"];
const timeChoices = times.map((t) => ({ value: t, label: t }));

function useBookingRefresh() {
  const qc = useQueryClient();
  return () => Promise.all([
    qc.invalidateQueries({ queryKey: ["addon-bookings"] }),
    qc.invalidateQueries({ queryKey: ["needs-scheduling"] }),
    qc.invalidateQueries({ queryKey: ["board"] }),
  ]);
}

/** Deep Spa and other add-on requests (ADM-ADD-*, ADM-SCH-30, -31). */
export function AddonsPage() {
  const site = useSite();
  const [status, setStatus] = useState("");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [service, setService] = useState("");
  const [requesting, setRequesting] = useState(false);
  const [openId, setOpenId] = useState<string | null>(null);
  const params = new URLSearchParams();
  if (status) params.set("status", status);
  if (site.id) params.set("society_id", site.id);
  if (from) params.set("date_from", from);
  if (to) params.set("date_to", to);
  if (service) params.set("service", service);
  const bookings = useQuery({ queryKey: ["addon-bookings", params.toString()], queryFn: () => api<Booking[]>(`/v1/admin/addons?${params}`) });
  const open = bookings.data?.find((b) => b.id === openId) ?? null;
  const changes = bookings.data?.filter((b) => b.change_requested).length ?? 0;

  return (
    <>
      <PageHeader title="Add on Service Requests" site={site.name || undefined}
                  description={changes > 0 ? `${changes} ${changes === 1 ? "booking has" : "bookings have"} a change requested by the customer.` : "Deep Spa bookings for subscribers and standalone customers."}
                  actions={<Button onClick={() => setRequesting(true)}><Plus aria-hidden /> Request Deep Spa</Button>} />
      {bookings.isError && <div className="mb-4"><ErrorState message={errorMessage(bookings.error)} onRetry={() => void bookings.refetch()} /></div>}
      <DataTable
        rows={bookings.data}
        loading={bookings.isPending}
        rowKey={(b) => b.id}
        onRowClick={(b) => setOpenId(b.id)}
        rowLabel={(b) => `Open ${b.service} for ${b.vehicle || b.customer_name}`}
        toolbar={(
          <div className="grid grid-cols-2 items-end gap-3 rounded-xl border bg-card p-4 shadow-xs md:grid-cols-[11rem_10rem_10rem_11rem_auto]">
            <Field label="Status filter">
              {(p) => <SelectBox {...p} value={status || NONE} onChange={(v) => setStatus(v === NONE ? "" : v)}
                                 choices={[{ value: NONE, label: "All" }, ...STATUSES.map((s) => ({ value: s, label: s }))]} />}
            </Field>
            <Field label="From date">{(p) => <Input {...p} type="date" value={from} onChange={(e) => setFrom(e.target.value)} />}</Field>
            <Field label="To date">{(p) => <Input {...p} type="date" value={to} onChange={(e) => setTo(e.target.value)} />}</Field>
            <Field label="Add-on filter">
              {(p) => <SelectBox {...p} value={service || NONE} onChange={(v) => setService(v === NONE ? "" : v)}
                                 choices={[{ value: NONE, label: "All add-ons" }, { value: "Deep Spa", label: "Deep Spa" }]} />}
            </Field>
            <Button variant="ghost" className="justify-self-start" disabled={!status && !from && !to && !service}
                    onClick={() => { setStatus(""); setFrom(""); setTo(""); setService(""); }}>Clear</Button>
          </div>
        )}
        empty={<EmptyState title="No add-on requests">Requests made in the app or here appear in this list.</EmptyState>}
        columns={[
          { key: "who", header: "Vehicle", width: "19%", cell: (b) => (
            <div className="min-w-0"><span className="reg block truncate">{b.vehicle || "-"}</span>
              <span className="block truncate text-xs text-muted-foreground">{b.customer_name}</span></div>) },
          { key: "service", header: "Add-on", width: "8rem", cell: (b) => (
            <div><span className="block">{b.service}</span>{b.standalone && <span className="text-xs text-muted-foreground">Standalone</span>}</div>) },
          { key: "date", header: "Date", width: "9rem", cell: (b) => (
            <div><span className="block">{showDate(b.date)}</span><span className="text-xs text-muted-foreground">Finish by {b.finish_by}</span></div>) },
          { key: "crew", header: "Assigned", width: "11rem", cell: (b) => (b.crew_name ? `${b.crew_name} at ${b.start_time}` : <span className="text-muted-foreground">Waiting for assignment</span>) },
          { key: "pay", header: "Payment", width: "10rem", cell: (b) => (b.standalone ? <span className="text-muted-foreground">Standalone request</span> : (
            <span className="flex items-center gap-2"><span className="tabular-nums">{inr(b.price_rupees)}</span>{b.payment_status && <StatusBadge status={b.payment_status} />}</span>)) },
          { key: "status", header: "Status", wrap: true, cell: (b) => (
            <span className="flex flex-wrap gap-1.5"><StatusBadge status={b.status} />{b.change_requested && <StatusBadge status="Change requested" tone="warn" />}</span>) },
          { key: "act", header: "", width: "6rem", align: "right", cell: (b) => <Button size="sm" variant="outline" onClick={() => setOpenId(b.id)}>Open</Button> },
        ]}
      />
      {open && <BookingDialog key={`${open.id}:${open.date}:${open.finish_by}:${open.status}`} b={open} onClose={() => setOpenId(null)} />}
      {requesting && <RequestDialog onClose={() => setRequesting(false)} />}
    </>
  );
}

/** Ask for Deep Spa for a subscriber or a standalone customer (ADM-ADD-*). */
function RequestDialog({ onClose }: { onClose: () => void }) {
  const refresh = useBookingRefresh();
  const [customer, setCustomer] = useState<PickedCustomer | null>(null);
  const [vehicleId, setVehicleId] = useState("");
  const [date, setDate] = useState("");
  const [finish, setFinish] = useState("12:00");
  const create = useAppMutation<void>({
    mutationFn: () => api("/v1/admin/addons", { method: "POST", body: { vehicle_id: vehicleId, service: "Deep Spa", date, finish_by: finish } }),
    pending: "Requesting Deep Spa…", success: "Deep Spa requested. It is placed when its date is scheduled.",
    onSuccess: () => { void refresh(); onClose(); },
  });
  return (
    <FormDialog open onOpenChange={(o) => !o && onClose()} title="Request Deep Spa" size="lg"
                description="For an Active subscriber's vehicle or a standalone vehicle. Scheduling does not wait for payment."
                submitLabel="Request Deep Spa" busy={create.isPending} disabled={!vehicleId || !date} onSubmit={() => create.mutate()}>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <CustomerPicker value={customer} onChange={(c) => { setCustomer(c); setVehicleId(""); }} />
        <VehiclePicker customerId={customer?.id ?? null} value={vehicleId} onChange={(id) => setVehicleId(id)}
                       allow={(v) => !v.subscription || v.subscription.status === "Active"}
                       describe={(v) => `${v.registration || "No registration"} · ${v.society}${!v.subscription ? " · Standalone" : ""}`} />
        <Field label="Proposed date">{(p) => <Input {...p} type="date" value={date} onChange={(e) => setDate(e.target.value)} />}</Field>
        <Field label="Finish by">{(p) => <SelectBox {...p} value={finish} onChange={setFinish} choices={timeChoices} />}</Field>
      </div>
    </FormDialog>
  );
}

function BookingDialog({ b, onClose }: { b: Booking; onClose: () => void }) {
  const confirm = useConfirm();
  const refresh = useBookingRefresh();
  const [date, setDate] = useState(b.date);
  const [finish, setFinish] = useState(b.finish_by);
  const act = useAppMutation<{ body: unknown; done: string }>({
    mutationFn: (v) => api(`/v1/admin/addons/${b.id}`, { method: "PATCH", body: v.body }),
    success: (_d, v) => v.done,
    onSuccess: () => void refresh(),
  });
  const editable = b.status === "Requested" || b.status === "Scheduled";
  const ask = async (title: string, description: string, label: string, body: unknown, done: string, danger = false) => {
    if (await confirm({ title, description, confirmLabel: label, tone: danger ? "danger" : "default" })) act.mutate({ body, done });
  };

  return (
    <FormDialog open onOpenChange={(o) => !o && onClose()} title={`${b.service}, ${b.vehicle || b.customer_name}`} size="lg"
                submitLabel="Close" cancelLabel={null} onSubmit={onClose}>
      <DetailList columns={3} items={[
        { label: "Customer", value: b.customer_name },
        { label: "Society", value: b.society },
        { label: "Status", value: <StatusBadge status={b.status} /> },
        { label: "Date", value: showDate(b.date) },
        { label: "Finish by", value: b.finish_by },
        { label: "Assigned", value: b.crew_name ? `${b.crew_name} at ${b.start_time}` : "Waiting for assignment" },
        ...(b.standalone
          ? [{ label: "Contact", value: b.contact_mobile }, { label: "Notes", value: b.notes, wide: true }]
          : [{ label: "Price", value: inr(b.price_rupees) }, { label: "Payment", value: b.payment_status ? <StatusBadge status={b.payment_status} /> : "-" }]),
      ]} />
      <div className="flex flex-wrap gap-3 text-sm">
        {b.payment_id && <Link to={`/payments?payment=${b.payment_id}`}>Open payment</Link>}
        <Link to="/schedule">Open schedule</Link>
      </div>

      {b.change_requested && (
        <section className="rounded-lg border border-warn/40 bg-warn/5 p-4">
          <h3 className="m-0 text-sm font-semibold">The customer asked for a change</h3>
          <p className="text-sm">New date {showDate(b.requested_date)}, finish by {b.requested_finish_by}.</p>
          <div className="mt-2 flex flex-wrap gap-2">
            <BusyButton type="button" size="sm" busy={act.isPending}
                        onClick={() => void ask("Apply the requested change?", `The booking moves to ${showDate(b.requested_date)}, finish by ${b.requested_finish_by}.`, "Apply requested change", { resolve_change: true }, "Requested change applied.")}>
              Apply requested change
            </BusyButton>
            <BusyButton type="button" size="sm" variant="outline" busy={act.isPending}
                        onClick={() => void ask("Reject the requested change?", `The booking stays on ${showDate(b.date)}, finish by ${b.finish_by}.`, "Reject requested change", { reject_change: true }, "Requested change rejected.", true)}>
              Reject requested change
            </BusyButton>
          </div>
        </section>
      )}

      {editable && (
        <section className="flex flex-col gap-3 border-t pt-4">
          <p className="m-0 text-sm text-muted-foreground">If the schedule is frozen, unfreeze it before changing the date or time. Cancelling removes the job without a code.</p>
          <div className="grid grid-cols-1 items-end gap-3 sm:grid-cols-[11rem_9rem_auto]">
            <Field label="Service date">{(p) => <Input {...p} type="date" value={date} onChange={(e) => setDate(e.target.value)} />}</Field>
            <Field label="Finish by">{(p) => <SelectBox {...p} value={finish} onChange={setFinish} choices={timeChoices} />}</Field>
            <BusyButton type="button" variant="outline" className="justify-self-start" busy={act.isPending} disabled={!date || (date === b.date && finish === b.finish_by)}
                        onClick={() => act.mutate({ body: { date, finish_by: finish }, done: "Date and time saved." })}>
              Save date and time
            </BusyButton>
          </div>
          <Button type="button" variant="ghost" className="self-start text-destructive" disabled={act.isPending}
                  onClick={() => void ask("Cancel this booking?", `${b.service} for ${b.vehicle || b.customer_name} on ${showDate(b.date)} is cancelled and its job removed.`, "Cancel booking", { status: "Cancelled" }, "Booking cancelled.", true)}>
            Cancel booking
          </Button>
        </section>
      )}
    </FormDialog>
  );
}
