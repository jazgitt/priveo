import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { api } from "../../api/client";
import { Card, SelectField, Table, TextField } from "../../components";
import "../reference/reference.css";

export interface AuditEntry {
  id: string;
  at: string;
  admin_login_id: string | null;
  entity: string;
  entity_id: string;
  action: string;
  detail: Record<string, unknown>;
}

const ENTITIES = ["society", "plan", "vehicle", "slot", "service", "checklist", "reason",
  "setting", "addon", "customer", "subscription", "cutoff_request", "schedule_change", "operations", "schedule", "payment", "crew"];
const LIMITS = [50, 100, 250, 500];

function show(v: unknown): string {
  if (v === null || v === undefined || v === "") return "(empty)";
  return typeof v === "string" ? v : JSON.stringify(v);
}

/** A change detail: `{field: [old, new]}` is a diff, anything else is listed as is. */
export function Diff({ detail }: { detail: Record<string, unknown> }) {
  const entries = Object.entries(detail);
  if (entries.length === 0) return <span className="muted">-</span>;
  return (
    <ul className="ref-diff">
      {entries.map(([field, v]) => (
        <li key={field}>
          <strong>{field}</strong>:{" "}
          {Array.isArray(v) && v.length === 2 ? (
            <>
              <span className="ref-old">{show(v[0])}</span>
              {" to "}
              <span className="ref-new">{show(v[1])}</span>
            </>
          ) : show(v)}
        </li>
      ))}
    </ul>
  );
}

/** What changed in the reference data and settings, newest first. */
export function AuditPage() {
  const [entity, setEntity] = useState("");
  const [limit, setLimit] = useState(100);
  const [from, setFrom] = useState(""); const [to, setTo] = useState(""); const [actor, setActor] = useState("");
  const q = new URLSearchParams();
  if (entity) q.set("entity", entity);
  q.set("limit", String(limit));
  if (from) q.set("date_from", from); if (to) q.set("date_to", to); if (actor) q.set("actor_id", actor);
  const list = useQuery({
    queryKey: ["admin-audit", entity, limit, from, to, actor],
    queryFn: () => api<AuditEntry[]>(`/v1/admin/directory/audit?${q.toString()}`),
  });

  return (
    <>
      <h1 className="page-title">Audit</h1>
      <Card>
        <div className="ref-toolbar">
          <TextField label="From date" type="date" value={from} onChange={e => setFrom(e.target.value)} />
          <TextField label="To date" type="date" value={to} onChange={e => setTo(e.target.value)} />
          <TextField label="Actor ID" value={actor} onChange={e => setActor(e.target.value)} />
          <SelectField label="Entity" value={entity} onChange={(e) => setEntity(e.target.value)}>
            <option value="">All</option>
            {ENTITIES.map((x) => <option key={x}>{x}</option>)}
          </SelectField>
          <SelectField label="Show" value={String(limit)}
                       onChange={(e) => setLimit(Number(e.target.value))}>
            {LIMITS.map((n) => <option key={n} value={n}>{n} entries</option>)}
          </SelectField>
        </div>
        {list.isLoading && <p className="muted">Loading...</p>}
        {list.isError && <p role="alert" className="form-error">Could not load the audit.</p>}
        {list.data && (
          <Table rows={list.data} rowKey={(a) => a.id} empty="No changes recorded." columns={[
            { key: "at", header: "When", render: (a) => new Date(a.at).toLocaleString("en-IN") },
            { key: "entity", header: "Entity", render: (a) => a.entity },
            { key: "action", header: "Action", render: (a) => a.action },
            { key: "id", header: "Record", render: (a) => a.entity_id },
            { key: "by", header: "By", render: (a) => a.admin_login_id ?? "system" },
            { key: "detail", header: "Change", render: (a) => <Diff detail={a.detail} /> },
          ]} />
        )}
      </Card>
    </>
  );
}
