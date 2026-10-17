import { useState, type CSSProperties } from "react";
import { useSite } from "../../site/SiteContext";
import { useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { api, ApiError } from "../../api/client";
import { ApiErrorNote } from "../../components/ApiErrorNote";
import { rupees, showDate } from "../../components/format";
import {
  Button, Card, Dialog, SelectField, StatusChip, Table, TextField, useToast,
  type ChipTone, type Column,
} from "../../components";
import {
  useAction, useAlerts, useCreatePayment, useInvoice, usePayments, useReadAlert, useSetStatus,
} from "./api";
import {
  NO_FILTERS, STATUSES, canConfirm, canReject,
  type AdminPayment, type Invoice, type PaymentFilters,
} from "./types";

const TONE: Record<string, ChipTone> = {
  Due: "info", "Over due": "error", Initiated: "warn", Received: "ok",
};

const row: CSSProperties = { display: "flex", flexWrap: "wrap", gap: "0.75rem", alignItems: "flex-end" };

export function PaymentsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [draft, setDraft] = useState<PaymentFilters>(NO_FILTERS);
  const [filters, setFilters] = useState<PaymentFilters>(NO_FILTERS);
  const society = useSite().name;
  const [page, setPage] = useState(0);
  const [open, setOpen] = useState<AdminPayment | null>(null);
  const [recording, setRecording] = useState(false);
  const list = usePayments(filters, page, society);
  const alerts = useAlerts();
  const readAlert = useReadAlert();

  const rows = list.data ?? [];
  const linkedId = searchParams.get("payment");
  const linked = useQuery({ queryKey: ["linked-payment", linkedId], enabled: !!linkedId,
    queryFn: () => api<AdminPayment>(`/v1/admin/payments/${linkedId}`) });
  const shown = open ?? linked.data;

  const set = (k: keyof PaymentFilters) => (e: { target: { value: string } }) =>
    setDraft((d) => ({ ...d, [k]: e.target.value }));

  const columns: Column<AdminPayment>[] = [
    { key: "customer", header: "Customer", render: (p) => `${p.customer_name}, ${p.flat}` },
    { key: "society", header: "Society", render: (p) => p.society },
    { key: "vehicle", header: "Vehicle", render: (p) => p.vehicle },
    { key: "kind", header: "Type", render: (p) => p.kind },
    { key: "amount", header: "Amount", align: "right", render: (p) => rupees(p.amount_rupees) },
    { key: "due", header: "Due", render: (p) => showDate(p.due_date) },
    { key: "status", header: "Status",
      render: (p) => <StatusChip tone={TONE[p.status] ?? "neutral"}>{p.status}</StatusChip> },
    { key: "act", header: "", render: (p) =>
      <Button variant="secondary" onClick={() => setOpen(p)}>Open</Button> },
  ];

  return (
    <>
      <h1 className="page-title">Payments</h1>
      <ApiErrorNote error={linked.error} />

      {(alerts.data?.length ?? 0) > 0 && (
        <Card title="Payments marked as paid">
          <ul style={{ margin: 0, paddingLeft: "1.25rem" }}>
            {alerts.data!.map((a) => (
              <li key={a.id} style={{ marginBottom: "0.5rem" }}>
                {a.message} <span className="muted">({showDate(a.created_at)})</span>{" "}
                <Button variant="ghost" onClick={() => readAlert.mutate(a.id)}>Mark read</Button>
              </li>
            ))}
          </ul>
          <Button variant="secondary" onClick={() => {
            const f = { ...NO_FILTERS, status: "Initiated" };
            setDraft(f);
            setFilters(f);
            setPage(0);
          }}>Show Initiated payments</Button>
        </Card>
      )}

      <Card title="Filter" actions={
        <Button onClick={() => setRecording(true)}>Record a payment</Button>}>
        <form style={row} onSubmit={(e) => { e.preventDefault(); setFilters(draft); setPage(0); }}>
          <SelectField label="Status" value={draft.status} onChange={set("status")}>
            <option value="">All</option>
            {STATUSES.map((s) => <option key={s}>{s}</option>)}
          </SelectField>
          <SelectField label="Type" value={draft.kind} onChange={set("kind")}>
            <option value="">All</option>
            <option>Plan</option>
            <option>Add-on</option>
          </SelectField>
          <TextField label="Customer ID" value={draft.customer_id} onChange={set("customer_id")} />
          <TextField label="Vehicle ID" value={draft.vehicle_id} onChange={set("vehicle_id")} />
          <TextField label="Due after" type="date" value={draft.due_after} onChange={set("due_after")} />
          <TextField label="Due before" type="date" value={draft.due_before} onChange={set("due_before")} />
          <Button type="submit">Apply</Button>
          <Button variant="ghost" onClick={() => {
            setDraft(NO_FILTERS);
            setFilters(NO_FILTERS);
            setPage(0);
          }}>Clear</Button>
        </form>
      </Card>

      <Card>
        {list.isPending && <p className="loading">Loading...</p>}
        {list.isError && <ApiErrorNote error={list.error} />}
        {list.data && <Table columns={columns} rows={rows} rowKey={(p) => p.id}
                             empty="No payments match these filters." />}
        <nav aria-label="Payment pages"><Button disabled={page === 0 || list.isFetching} onClick={() => setPage(page - 1)}>Previous</Button> Page {page + 1} <Button disabled={list.isFetching || (list.data?.length ?? 0) < 50} onClick={() => setPage(page + 1)}>Next</Button></nav>
      </Card>

      {shown && <PaymentDialog payment={shown} onChange={setOpen} onClose={() => { setOpen(null); setSearchParams({}); }} />}
      {recording && <RecordDialog onClose={() => setRecording(false)} />}
    </>
  );
}

function PaymentDialog({ payment, onChange, onClose }: {
  payment: AdminPayment;
  onChange: (p: AdminPayment) => void;
  onClose: () => void;
}) {
  const toast = useToast();
  const setStatus = useSetStatus();
  const confirm = useAction("confirm");
  const reject = useAction("reject");
  const invoice = useInvoice();
  const [next, setNext] = useState("");
  const [inv, setInv] = useState<Invoice | null>(null);
  const error = setStatus.error ?? confirm.error ?? reject.error ?? invoice.error;
  const busy = setStatus.isPending || confirm.isPending || reject.isPending;

  const done = (msg: string) => (p: AdminPayment) => {
    onChange(p);
    setNext("");
    setInv(null);
    toast.show(msg, "ok");
  };

  return (
    <Dialog open title="Payment" onClose={onClose}
            footer={<Button variant="secondary" onClick={onClose}>Close</Button>}>
      <dl style={{ display: "grid", gridTemplateColumns: "auto 1fr", gap: "0.25rem 1rem", margin: 0 }}>
        <dt>Customer</dt><dd>{payment.customer_name}, {payment.flat}, {payment.society}</dd>
        <dt>Vehicle</dt><dd>{payment.vehicle}</dd>
        <dt>Type</dt><dd>{payment.kind}</dd>
        <dt>Description</dt><dd>{payment.description || "-"}</dd>
        <dt>Amount</dt><dd>{rupees(payment.amount_rupees)} (GST included)</dd>
        <dt>Due</dt><dd>{showDate(payment.due_date)}</dd>
        <dt>Cycle</dt><dd>{showDate(payment.cycle_start)} to {showDate(payment.cycle_end)}</dd>
        <dt>Status</dt>
        <dd><StatusChip tone={TONE[payment.status] ?? "neutral"}>{payment.status}</StatusChip></dd>
        <dt>Received on</dt><dd>{showDate(payment.received_on)}</dd>
        <dt>Invoice</dt><dd>{payment.invoice_number ?? "Not issued"}</dd>
      </dl>

      <div style={{ ...row, marginTop: "1rem" }}>
        {canConfirm(payment) && (
          <Button busy={confirm.isPending} disabled={busy}
                  onClick={() => confirm.mutate(payment.id, { onSuccess: done("Payment confirmed.") })}>
            Confirm received
          </Button>
        )}
        {canReject(payment) && (
          <Button variant="danger" busy={reject.isPending} disabled={busy}
                  onClick={() => reject.mutate(payment.id, { onSuccess: done("Payment moved back.") })}>
            Reject (money did not arrive)
          </Button>
        )}
        {payment.status === "Received" && (
          <Button variant="secondary" busy={invoice.isPending}
                  onClick={() => invoice.mutate(payment.id, {
                    onSuccess: (i) => {
                      setInv(i);
                      onChange({ ...payment, invoice_number: i.number });
                    },
                  })}>
            {payment.invoice_number ? "View invoice" : "Issue invoice"}
          </Button>
        )}
      </div>

      <div style={{ ...row, marginTop: "1rem" }}>
        <SelectField label="Set status" value={next} onChange={(e) => setNext(e.target.value)}>
          <option value="">Choose</option>
          {STATUSES.filter((s) => s !== payment.status).map((s) => <option key={s}>{s}</option>)}
        </SelectField>
        <Button variant="secondary" disabled={!next || busy} busy={setStatus.isPending}
                onClick={() => setStatus.mutate({ id: payment.id, status: next },
                                                { onSuccess: done("Status updated.") })}>
          Save status
        </Button>
      </div>

      <ApiErrorNote error={error} />

      {inv && (
        <section aria-label="Invoice" style={{ marginTop: "1rem" }}>
          <h3>Invoice {inv.number}</h3>
          <p>Issued {showDate(inv.issued_on)}. {inv.customer_name}, {inv.vehicle}.</p>
          <p>{inv.description}: {rupees(inv.amount_rupees)}{inv.gst_included ? " including GST" : ""}.</p>
          <p className="muted">{inv.seller_name}, {inv.seller_address}. GSTIN {inv.seller_gstin}.</p>
          <a href={`/v1/admin/payments/${encodeURIComponent(payment.id)}/invoice.pdf`} target="_blank" rel="noreferrer">Open invoice PDF</a>
        </section>
      )}
    </Dialog>
  );
}

function RecordDialog({ onClose }: { onClose: () => void }) {
  const toast = useToast();
  const create = useCreatePayment();
  const [f, setF] = useState({
    vehicle_id: "", kind: "Plan", description: "", amount: "", due_date: "",
    cycle_start: "", status: "Received",
  });
  const set = (k: keyof typeof f) => (e: { target: { value: string } }) =>
    setF((x) => ({ ...x, [k]: e.target.value }));
  const fe = create.error instanceof ApiError ? create.error.fields : {};

  const submit = () => create.mutate({
    vehicle_id: f.vehicle_id.trim(), kind: f.kind, description: f.description,
    amount_rupees: Number(f.amount), due_date: f.due_date,
    cycle_start: f.cycle_start || null, status: f.status,
  }, { onSuccess: () => { toast.show("Payment recorded.", "ok"); onClose(); } });

  return (
    <Dialog open title="Record a payment" onClose={onClose}
            footer={<>
              <Button variant="secondary" onClick={onClose}>Cancel</Button>
              <Button busy={create.isPending}
                      disabled={!f.vehicle_id.trim() || !f.amount || !f.due_date}
                      onClick={submit}>Record</Button>
            </>}>
      <TextField label="Vehicle ID" value={f.vehicle_id} onChange={set("vehicle_id")}
                 error={fe.vehicle_id} />
      <SelectField label="Type" value={f.kind} onChange={set("kind")}>
        <option>Plan</option>
        <option>Add-on</option>
      </SelectField>
      <TextField label="Description" value={f.description} onChange={set("description")} />
      <TextField label="Amount (Rs, GST included)" type="number" min="1" value={f.amount}
                 onChange={set("amount")} error={fe.amount_rupees} />
      <TextField label="Due date" type="date" value={f.due_date} onChange={set("due_date")}
                 error={fe.due_date} />
      <TextField label="Cycle start (plan payments)" type="date" value={f.cycle_start}
                 onChange={set("cycle_start")} />
      <SelectField label="Status" value={f.status} onChange={set("status")}>
        {STATUSES.map((s) => <option key={s}>{s}</option>)}
      </SelectField>
      <ApiErrorNote error={create.error} />
    </Dialog>
  );
}
