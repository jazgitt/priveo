import { useState, type CSSProperties } from "react";

import { useSite } from "../../site/SiteContext";
import { ApiError } from "../../api/client";
import { ApiErrorNote } from "../../components/ApiErrorNote";
import { showDate } from "../../components/format";
import {
  Button, Card, Dialog, SelectField, StatusChip, Table, TextField, useToast,
  type ChipTone, type Column,
} from "../../components";
import {
  allowedMoves, useChangeActions, useChanges, useSetSubscriptionStatus, useSubscriptionEvents,
  useSubscriptions, type SubscriptionRow,
} from "./api";

const TONE: Record<string, ChipTone> = {
  Active: "ok", Activating: "info", Paused: "warn", Inactive: "error",
};

const row: CSSProperties = { display: "flex", flexWrap: "wrap", gap: "0.75rem", alignItems: "flex-end" };

interface Target { id: string; status: string | null; label: string }

export function SubscriptionsPage() {
  const [status, setStatus] = useState("");
  const [target, setTarget] = useState<Target | null>(null);
  const [subId, setSubId] = useState("");
  const [vehicleId, setVehicleId] = useState("");
  const [changesFor, setChangesFor] = useState("");
  const site = useSite();
  const list = useSubscriptions(status, site.id);
  const missing = list.error instanceof ApiError && [404, 405].includes(list.error.status);

  const columns: Column<SubscriptionRow>[] = [
    { key: "customer", header: "Customer", render: (s) => `${s.customer_name}, ${s.flat}` },
    { key: "society", header: "Society", render: (s) => s.society },
    { key: "vehicle", header: "Vehicle", render: (s) => s.vehicle },
    { key: "plan", header: "Plan", render: (s) => s.plan_name ?? "-" },
    { key: "status", header: "Status",
      render: (s) => <StatusChip tone={TONE[s.status] ?? "neutral"}>{s.status}</StatusChip> },
    { key: "first", header: "First service", render: (s) => showDate(s.first_service_date) },
    { key: "renewal", header: "Renewal", render: (s) => showDate(s.renewal_date) },
    { key: "act", header: "", render: (s) => (
      <div style={row}>
        <Button variant="secondary" onClick={() => setTarget({
          id: s.subscription_id, status: s.status === "Paused" ? "Active" : s.status,
          label: `${s.customer_name}, ${s.vehicle}`,
        })}>Change status</Button>
        <Button variant="ghost" onClick={() => { setVehicleId(s.vehicle_id); setChangesFor(s.vehicle_id); }}>
          Skips and pauses
        </Button>
      </div>) },
  ];

  return (
    <>
      <h1 className="page-title">Subscriptions</h1>

      <Card title="Subscriptions">
        <div style={row}>
          <SelectField label="Status" value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="">All</option>
            <option>Active</option>
            <option>Activating</option>
            <option>Paused</option>
            <option>Inactive</option>
          </SelectField>
        </div>
        {list.isPending && <p className="loading">Loading...</p>}
        {missing && (
          <p className="muted" role="status">
            The list of subscriptions is not available from the server yet. Use the
            subscription ID below to change a status.
          </p>
        )}
        {list.isError && !missing && <ApiErrorNote error={list.error} />}
        {list.data && <Table columns={columns} rows={list.data} rowKey={(s) => s.subscription_id}
                             empty="No subscriptions match." />}
      </Card>

      <Card title="Change a status by ID">
        <form style={row} onSubmit={(e) => {
          e.preventDefault();
          if (subId.trim()) setTarget({ id: subId.trim(), status: null, label: subId.trim() });
        }}>
          <TextField label="Subscription ID" value={subId} onChange={(e) => setSubId(e.target.value)} />
          <Button type="submit" disabled={!subId.trim()}>Change status</Button>
        </form>
      </Card>

      <Card title="Skip or pause for a customer">
        <form style={row} onSubmit={(e) => { e.preventDefault(); setChangesFor(vehicleId.trim()); }}>
          <TextField label="Vehicle ID" value={vehicleId} onChange={(e) => setVehicleId(e.target.value)} />
          <Button type="submit" disabled={!vehicleId.trim()}>Show</Button>
        </form>
        {changesFor && <ChangesPanel vehicleId={changesFor} />}
      </Card>

      {target && <StatusDialog key={target.id} target={target} onClose={() => setTarget(null)} />}
    </>
  );
}

function StatusDialog({ target, onClose }: { target: Target; onClose: () => void }) {
  const toast = useToast();
  const set = useSetSubscriptionStatus();
  const events = useSubscriptionEvents(target.id);
  const moves = allowedMoves(target.status);
  const [next, setNext] = useState("");
  const [reason, setReason] = useState("");
  const [first, setFirst] = useState("");
  const needsDate = next === "Active";
  const valid = next !== "" && (next !== "Inactive" || reason.trim() !== "")
    && (!needsDate || first !== "");
  const fe = set.error instanceof ApiError ? set.error.fields : {};

  return (
    <Dialog open title="Change subscription status" onClose={onClose}
            footer={<>
              <Button variant="secondary" onClick={onClose}>Close</Button>
              <Button busy={set.isPending} disabled={!valid}
                      onClick={() => set.mutate(
                        { id: target.id, status: next, reason: reason.trim(),
                          first_service_date: first || null },
                        { onSuccess: () => {
                          toast.show(`Subscription is now ${next}.`, "ok");
                          onClose();
                        } })}>
                Save
              </Button>
            </>}>
      <p>{target.label}{target.status ? `. Now ${target.status}.` : "."}</p>
      {moves.length === 0 ? (
        <p className="muted">This status cannot be changed.</p>
      ) : (
        <SelectField label="New status" value={next} onChange={(e) => setNext(e.target.value)}
                     error={fe.status}>
          <option value="">Choose</option>
          {moves.map((m) => <option key={m}>{m}</option>)}
        </SelectField>
      )}
      <TextField label="Reason" value={reason} onChange={(e) => setReason(e.target.value)}
                 hint={next === "Inactive" ? "Required when making a subscription Inactive." : undefined}
                 error={fe.reason} />
      {(needsDate || next === "Activating") && (
        <TextField label="First service date" type="date" value={first}
                   onChange={(e) => setFirst(e.target.value)}
                   hint="The billing cycle starts on this date."
                   error={fe.first_service_date} />
      )}
      <ApiErrorNote error={set.error} />

      <h3>History</h3>
      {events.isPending && <p className="muted">Loading...</p>}
      {events.isError && <p className="muted">The history is not available yet.</p>}
      {events.data && (events.data.length === 0
        ? <p className="muted">No changes yet.</p>
        : <ul>{events.data.map((e, i) => (
            <li key={i}>
              {showDate(e.at)}: {e.from_status} to {e.to_status} by {e.by}
              {e.reason ? `. ${e.reason}` : ""}
            </li>))}
          </ul>)}
    </Dialog>
  );
}

function ChangesPanel({ vehicleId }: { vehicleId: string }) {
  const toast = useToast();
  const changes = useChanges(vehicleId);
  const act = useChangeActions(vehicleId);
  const [skipDate, setSkipDate] = useState("");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const error = act.skip.error ?? act.unskip.error ?? act.pause.error ?? act.endPause.error;
  const ok = (m: string) => ({ onSuccess: () => toast.show(m, "ok") });

  if (changes.isPending) return <p className="loading">Loading...</p>;
  if (changes.isError) return <ApiErrorNote error={changes.error} />;
  const c = changes.data;
  const live = (x: { status: string }) => x.status !== "Cancelled" && x.status !== "Ended";

  return (
    <div style={{ marginTop: "1rem" }}>
      <h3>Skips</h3>
      {c.skips.filter(live).length === 0 ? <p className="muted">No skips.</p> : (
        <ul>{c.skips.filter(live).map((s) => (
          <li key={s.id}>
            {showDate(s.start_date)} ({s.status}, by {s.actor}){" "}
            <Button variant="ghost" onClick={() => act.unskip.mutate(s.id, ok("Skip removed."))}>
              Remove skip
            </Button>
          </li>))}
        </ul>)}
      <div style={row}>
        <TextField label="Skip date" type="date" value={skipDate}
                   onChange={(e) => setSkipDate(e.target.value)} />
        <Button disabled={!skipDate} busy={act.skip.isPending}
                onClick={() => act.skip.mutate(skipDate, ok("Skip added."))}>Skip this day</Button>
      </div>

      <h3>Pauses</h3>
      {c.pauses.filter(live).length === 0 ? <p className="muted">No pauses.</p> : (
        <ul>{c.pauses.filter(live).map((p) => (
          <li key={p.id}>
            {showDate(p.start_date)} to {showDate(p.end_date)} ({p.status}, by {p.actor}){" "}
            <Button variant="ghost" onClick={() => act.endPause.mutate(p.id, ok("Pause ended."))}>
              End pause
            </Button>
          </li>))}
        </ul>)}
      <div style={row}>
        <TextField label="Pause from" type="date" value={from} onChange={(e) => setFrom(e.target.value)} />
        <TextField label="Pause to" type="date" value={to} onChange={(e) => setTo(e.target.value)} />
        <Button disabled={!from || !to} busy={act.pause.isPending}
                onClick={() => act.pause.mutate({ from_date: from, to_date: to }, ok("Pause added."))}>
          Pause
        </Button>
      </div>
      <ApiErrorNote error={error} />
    </div>
  );
}
