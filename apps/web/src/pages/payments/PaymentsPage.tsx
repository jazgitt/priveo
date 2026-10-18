import { useQuery } from "@tanstack/react-query";
import { CheckCheck, FileText, Plus } from "lucide-react";
import { useState } from "react";
import { useSearchParams } from "react-router-dom";

import { api, ApiError } from "@/api/client";
import { useConfirm } from "@/blocks/confirm";
import { DataTable, Pager } from "@/blocks/DataTable";
import { Field, NONE, SelectBox } from "@/blocks/fields";
import { BusyButton, FormDialog } from "@/blocks/FormDialog";
import { DetailList, EmptyState, ErrorState, PageHeader, Panel, StatRow, StatTile } from "@/blocks/layout";
import { errorMessage, useAppMutation } from "@/blocks/mutation";
import { StatusBadge } from "@/blocks/status";
import { inr, showDate } from "@/components/format";
import { useSite } from "@/site/SiteContext";
import { Button } from "@/ui/button";
import { Input } from "@/ui/input";

import { CustomerPicker, VehiclePicker, type PickedCustomer } from "../customers/picker";
import { useAction, useAlerts, useCreatePayment, useInvoice, usePayments, usePaymentsSummary, useReadAlert, useSetStatus } from "./api";
import { NO_FILTERS, STATUSES, canConfirm, canReject, type AdminPayment, type Invoice, type PaymentFilters } from "./types";

const ALL = NONE;

export function PaymentsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [filters, setFilters] = useState<PaymentFilters>(NO_FILTERS);
  const [customer, setCustomer] = useState<PickedCustomer | null>(null);
  const site = useSite();
  const [page, setPage] = useState(0);
  const [open, setOpen] = useState<AdminPayment | null>(null);
  const [recording, setRecording] = useState(false);
  const list = usePayments(filters, page, site.name);
  const summary = usePaymentsSummary(site.name);
  const counts = summary.data;
  const alerts = useAlerts();
  const readAlert = useReadAlert();

  const linkedId = searchParams.get("payment");
  const linked = useQuery({ queryKey: ["linked-payment", linkedId], enabled: !!linkedId,
    queryFn: () => api<AdminPayment>(`/v1/admin/payments/${linkedId}`) });
  const shown = open ?? linked.data;

  const setFilter = (k: keyof PaymentFilters, v: string) => { setFilters((f) => ({ ...f, [k]: v === ALL ? "" : v })); setPage(0); };
  const filtered = Object.values(filters).some(Boolean);

  return (
    <>
      <PageHeader title="Payments" site={site.name || undefined}
                  description="Confirm UPI payments, set statuses and issue GST invoices."
                  actions={<Button onClick={() => setRecording(true)}><Plus aria-hidden /> Record a payment</Button>} />
      {linked.error ? <div className="mb-4"><ErrorState message={errorMessage(linked.error)} /></div> : null}

      {(alerts.data?.length ?? 0) > 0 && (
        <Panel className="mb-6" title={`Payments marked as paid (${alerts.data!.length})`}
               description="Customers say they have paid. Check the money arrived, then confirm."
               actions={<Button size="sm" variant="outline" onClick={() => { setFilters({ ...NO_FILTERS, status: "Initiated" }); setCustomer(null); setPage(0); }}>
                 Show Initiated payments
               </Button>}
               bodyClassName="p-0">
          <ul className="m-0 list-none divide-y p-0">
            {alerts.data!.map((a) => (
              <li key={a.id} className="flex items-center justify-between gap-3 px-5 py-2.5 text-sm">
                <span className="min-w-0">{a.message} <span className="text-muted-foreground">· {showDate(a.created_at)}</span></span>
                <Button size="sm" variant="ghost" disabled={readAlert.isPending} onClick={() => readAlert.mutate(a.id)}>Mark read</Button>
              </li>
            ))}
          </ul>
        </Panel>
      )}

      <StatRow label="Payment summary">
        <StatTile label="All payments" value={counts?.total} loading={summary.isPending}
                  hint={counts ? inr(counts.total_rupees) : undefined}
                  selected={!filters.status} onSelect={() => setFilter("status", ALL)} />
        {STATUSES.map((st) => (
          <StatTile key={st} label={st} value={counts?.by_status[st]?.count ?? 0} loading={summary.isPending}
                    hint={counts ? inr(counts.by_status[st]?.rupees ?? 0) : undefined}
                    selected={filters.status === st} onSelect={() => setFilter("status", filters.status === st ? ALL : st)} />
        ))}
      </StatRow>
      <DataTable
        rows={list.data}
        loading={list.isPending}
        rowKey={(p) => p.id}
        onRowClick={setOpen}
        rowLabel={(p) => `Open payment of ${p.customer_name}`}
        toolbar={(
          <div className="grid grid-cols-2 items-end gap-3 rounded-xl border bg-card p-4 shadow-xs md:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-[9rem_8rem_minmax(0,1fr)_minmax(0,1fr)_9.5rem_9.5rem_auto]">
            <Field label="Status">
              {(p) => <SelectBox {...p} value={filters.status || ALL} onChange={(v) => setFilter("status", v)}
                                 choices={[{ value: ALL, label: "All" }, ...STATUSES.map((s) => ({ value: s, label: s }))]} />}
            </Field>
            <Field label="Type">
              {(p) => <SelectBox {...p} value={filters.kind || ALL} onChange={(v) => setFilter("kind", v)}
                                 choices={[{ value: ALL, label: "All" }, { value: "Plan", label: "Plan" }, { value: "Add-on", label: "Add-on" }]} />}
            </Field>
            <CustomerPicker compact value={customer} onChange={(c) => { setCustomer(c); setFilters((f) => ({ ...f, customer_id: c?.id ?? "", vehicle_id: "" })); setPage(0); }} />
            <VehiclePicker customerId={customer?.id ?? null} value={filters.vehicle_id} label="Vehicle" emptyText="All vehicles"
                           onChange={(id) => setFilter("vehicle_id", id)} />
            <Field label="Due after">
              {(p) => <Input {...p} type="date" value={filters.due_after} onChange={(e) => setFilter("due_after", e.target.value)} />}
            </Field>
            <Field label="Due before">
              {(p) => <Input {...p} type="date" value={filters.due_before} onChange={(e) => setFilter("due_before", e.target.value)} />}
            </Field>
            <Button variant="ghost" disabled={!filtered} onClick={() => { setFilters(NO_FILTERS); setCustomer(null); setPage(0); }}>Clear</Button>
          </div>
        )}
        empty={filtered ? <EmptyState title="No payments match these filters" /> : <EmptyState title="No payments yet" />}
        columns={[
          { key: "customer", header: "Customer", width: "17%", cell: (p) => (
            <div className="min-w-0"><span className="block truncate font-medium">{p.customer_name}</span>
              <span className="block truncate text-xs text-muted-foreground">Flat {p.flat} · {p.society}</span></div>) },
          { key: "vehicle", header: "Vehicle", width: "18%", cell: (p) => p.vehicle },
          { key: "kind", header: "Type", width: "6rem", cell: (p) => p.kind },
          { key: "desc", header: "For", cell: (p) => p.description || "-" },
          { key: "amount", header: "Amount", width: "7rem", align: "right", cell: (p) => <span className="tabular-nums">{inr(p.amount_rupees)}</span> },
          { key: "due", header: "Due", width: "7rem", cell: (p) => showDate(p.due_date) },
          { key: "status", header: "Status", width: "7.5rem", cell: (p) => <StatusBadge status={p.status} /> },
          { key: "act", header: "", width: "5.5rem", align: "right", cell: (p) => <Button size="sm" variant="outline" onClick={() => setOpen(p)}>Open</Button> },
        ]}
        footer={<Pager page={page} size={50} count={list.data?.length ?? 0} busy={list.isFetching} onPage={setPage} />}
      />
      {list.isError && <div className="mt-3"><ErrorState message={errorMessage(list.error)} onRetry={() => void list.refetch()} /></div>}

      {shown && <PaymentDialog key={shown.id} payment={shown} onChange={setOpen} onClose={() => { setOpen(null); setSearchParams({}); }} />}
      {recording && <RecordDialog onClose={() => setRecording(false)} />}
    </>
  );
}

function PaymentDialog({ payment, onChange, onClose }: {
  payment: AdminPayment; onChange: (p: AdminPayment) => void; onClose: () => void;
}) {
  const confirm = useConfirm();
  const setStatus = useSetStatus();
  const confirmPay = useAction("confirm");
  const reject = useAction("reject");
  const invoice = useInvoice();
  const [next, setNext] = useState("");
  const [inv, setInv] = useState<Invoice | null>(null);
  const busy = setStatus.isPending || confirmPay.isPending || reject.isPending || invoice.isPending;
  const run = useAppMutation<{ go: () => Promise<AdminPayment>; done: string }, AdminPayment>({
    mutationFn: (v) => v.go(), success: (_d, v) => v.done,
    onSuccess: (p) => { onChange(p); setNext(""); setInv(null); },
  });
  const issue = useAppMutation<void, Invoice>({
    mutationFn: () => invoice.mutateAsync(payment.id),
    pending: "Issuing the invoice…",
    success: (i) => (payment.invoice_number ? `Invoice ${i.number}.` : `Invoice ${i.number} issued.`),
    onSuccess: (i) => { setInv(i); onChange({ ...payment, invoice_number: i.number }); },
  });

  const ask = async (title: string, description: string, label: string, go: () => Promise<AdminPayment>, done: string, danger = false) => {
    if (await confirm({ title, description, confirmLabel: label, tone: danger ? "danger" : "default" })) run.mutate({ go, done });
  };
  const who = `${payment.customer_name}, ${inr(payment.amount_rupees)}`;

  return (
    <FormDialog open onOpenChange={(o) => !o && onClose()} title="Payment" size="lg" submitLabel="Close" cancelLabel={null} onSubmit={onClose}>
      <DetailList columns={3} items={[
        { label: "Customer", value: `${payment.customer_name}, flat ${payment.flat}` },
        { label: "Society", value: payment.society },
        { label: "Vehicle", value: payment.vehicle },
        { label: "Type", value: payment.kind },
        { label: "Amount", value: `${inr(payment.amount_rupees)} (GST included)` },
        { label: "Status", value: <StatusBadge status={payment.status} /> },
        { label: "Due", value: showDate(payment.due_date) },
        { label: "Cycle", value: payment.cycle_start ? `${showDate(payment.cycle_start)} to ${showDate(payment.cycle_end)}` : "-" },
        { label: "Received on", value: showDate(payment.received_on) },
        { label: "Description", value: payment.description, wide: true },
        { label: "Invoice", value: payment.invoice_number ?? "Not issued" },
      ]} />

      <div className="flex flex-wrap gap-2 border-t pt-4">
        {canConfirm(payment) && (
          <BusyButton type="button" busy={confirmPay.isPending} disabled={busy}
                      onClick={() => void ask("Confirm the money arrived?", `${who} becomes Received and its received date is today.`, "Confirm received",
                        () => confirmPay.mutateAsync(payment.id), "Payment confirmed.")}>
            <CheckCheck aria-hidden /> Confirm received
          </BusyButton>
        )}
        {canReject(payment) && (
          <BusyButton type="button" variant="outline" className="text-destructive" busy={reject.isPending} disabled={busy}
                      onClick={() => void ask("The money did not arrive?", `${who} moves back from ${payment.status}.`, "Reject",
                        () => reject.mutateAsync(payment.id), "Payment moved back.", true)}>
            Reject (money did not arrive)
          </BusyButton>
        )}
        {payment.status === "Received" && (
          <BusyButton type="button" variant="outline" busy={issue.isPending} disabled={busy}
                      onClick={async () => {
                        if (payment.invoice_number || await confirm({ title: "Issue a GST invoice?", description: `An invoice number is given to ${who}. It cannot be taken back.`, confirmLabel: "Issue invoice" })) issue.mutate();
                      }}>
            <FileText aria-hidden /> {payment.invoice_number ? "View invoice" : "Issue invoice"}
          </BusyButton>
        )}
      </div>

      <div className="grid grid-cols-1 items-end gap-3 sm:grid-cols-[14rem_auto]">
        <Field label="Set status">
          {(p) => <SelectBox {...p} value={next} onChange={setNext} choices={STATUSES.filter((s) => s !== payment.status).map((s) => ({ value: s, label: s }))} />}
        </Field>
        <BusyButton type="button" variant="outline" className="justify-self-start" disabled={!next || busy} busy={setStatus.isPending}
                    onClick={() => void ask(`Set the status to ${next}?`, `${who} is ${payment.status} now.`, "Save status",
                      () => setStatus.mutateAsync({ id: payment.id, status: next }), "Status updated.")}>
          Save status
        </BusyButton>
      </div>

      {inv && (
        <section aria-label="Invoice" className="rounded-lg border bg-muted/40 p-4 text-sm">
          <h3 className="m-0 mb-1 text-sm font-semibold">Invoice {inv.number}</h3>
          <p>Issued {showDate(inv.issued_on)}. {inv.customer_name}, {inv.vehicle}.</p>
          <p>{inv.description}: {inr(inv.amount_rupees)}{inv.gst_included ? " including GST" : ""}.</p>
          <p className="text-muted-foreground">{inv.seller_name}, {inv.seller_address}. GSTIN {inv.seller_gstin}.</p>
          <a href={`/v1/admin/payments/${encodeURIComponent(payment.id)}/invoice.pdf`} target="_blank" rel="noreferrer">Open invoice PDF</a>
        </section>
      )}
    </FormDialog>
  );
}

function RecordDialog({ onClose }: { onClose: () => void }) {
  const create = useCreatePayment();
  const [customer, setCustomer] = useState<PickedCustomer | null>(null);
  const [f, setF] = useState({ vehicle_id: "", kind: "Plan", description: "", amount: "", due_date: "", cycle_start: "", status: "Received" });
  const set = (k: keyof typeof f) => (v: string) => setF((x) => ({ ...x, [k]: v }));
  const fe = create.error instanceof ApiError ? create.error.fields : {};
  const save = useAppMutation<void>({
    mutationFn: () => create.mutateAsync({
      vehicle_id: f.vehicle_id, kind: f.kind, description: f.description,
      amount_rupees: Number(f.amount), due_date: f.due_date, cycle_start: f.cycle_start || null, status: f.status,
    }),
    success: "Payment recorded.", onSuccess: onClose,
  });

  return (
    <FormDialog open onOpenChange={(o) => !o && onClose()} title="Record a payment" size="lg"
                description="For a payment made outside the app. Amounts include GST."
                submitLabel="Record" busy={save.isPending} disabled={!f.vehicle_id || !f.amount || !f.due_date}
                onSubmit={() => save.mutate()}>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <CustomerPicker value={customer} onChange={(c) => { setCustomer(c); set("vehicle_id")(""); }} />
        <VehiclePicker customerId={customer?.id ?? null} value={f.vehicle_id} onChange={(id) => set("vehicle_id")(id)} />
        <Field label="Type">{(p) => <SelectBox {...p} value={f.kind} onChange={set("kind")} choices={[{ value: "Plan", label: "Plan" }, { value: "Add-on", label: "Add-on" }]} />}</Field>
        <Field label="Status">{(p) => <SelectBox {...p} value={f.status} onChange={set("status")} choices={STATUSES.map((s) => ({ value: s, label: s }))} />}</Field>
        <Field label="Description" optional className="sm:col-span-2">{(p) => <Input {...p} value={f.description} onChange={(e) => set("description")(e.target.value)} />}</Field>
        <Field label="Amount (₹, GST included)" error={fe.amount_rupees}>{(p) => <Input {...p} type="number" min="1" value={f.amount} onChange={(e) => set("amount")(e.target.value)} />}</Field>
        <Field label="Due date" error={fe.due_date}>{(p) => <Input {...p} type="date" value={f.due_date} onChange={(e) => set("due_date")(e.target.value)} />}</Field>
        <Field label="Cycle start" optional hint="For plan payments.">{(p) => <Input {...p} type="date" value={f.cycle_start} onChange={(e) => set("cycle_start")(e.target.value)} />}</Field>
      </div>
    </FormDialog>
  );
}
