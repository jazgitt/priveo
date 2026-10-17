import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { api } from "@/api/client";
import { DataTable } from "@/blocks/DataTable";
import { Field, NONE, SelectBox } from "@/blocks/fields";
import { EmptyState, ErrorState, PageHeader } from "@/blocks/layout";
import { showDateTime } from "@/components/format";
import { Input } from "@/ui/input";

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
  if (entries.length === 0) return <span className="text-muted-foreground">-</span>;
  return (
    <dl className="m-0 grid grid-cols-[auto_minmax(0,1fr)] gap-x-3 gap-y-1 text-sm">
      {entries.map(([field, v]) => (
        <div key={field} className="contents">
          <dt className="text-muted-foreground">{field.replaceAll("_", " ")}</dt>
          <dd className="m-0 break-words">
            {Array.isArray(v) && v.length === 2 ? (
              <><del className="text-muted-foreground">{show(v[0])}</del>{" → "}<span className="font-medium">{show(v[1])}</span></>
            ) : show(v)}
          </dd>
        </div>
      ))}
    </dl>
  );
}

/** What changed in the reference data and settings, newest first. */
export function AuditPage() {
  const [entity, setEntity] = useState("");
  const [limit, setLimit] = useState(100);
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [actor, setActor] = useState("");
  const q = new URLSearchParams();
  if (entity) q.set("entity", entity);
  q.set("limit", String(limit));
  if (from) q.set("date_from", from);
  if (to) q.set("date_to", to);
  if (actor) q.set("actor_id", actor);
  const list = useQuery({
    queryKey: ["admin-audit", entity, limit, from, to, actor],
    queryFn: () => api<AuditEntry[]>(`/v1/admin/directory/audit?${q.toString()}`),
  });

  return (
    <>
      <PageHeader title="Audit" description="Who changed what, newest first." />
      {list.isError && <div className="mb-4"><ErrorState message="Could not load the audit." onRetry={() => void list.refetch()} /></div>}
      <DataTable
        rows={list.data}
        loading={list.isLoading}
        rowKey={(a) => a.id}
        toolbar={(
          <div className="flex flex-wrap items-end gap-3">
            <Field label="From date" className="w-44">{(p) => <Input {...p} type="date" value={from} onChange={(e) => setFrom(e.target.value)} />}</Field>
            <Field label="To date" className="w-44">{(p) => <Input {...p} type="date" value={to} onChange={(e) => setTo(e.target.value)} />}</Field>
            <Field label="Entity" className="w-48">
              {(p) => <SelectBox {...p} value={entity || NONE} onChange={(v) => setEntity(v === NONE ? "" : v)}
                                 choices={[{ value: NONE, label: "All" }, ...ENTITIES.map((x) => ({ value: x, label: x.replaceAll("_", " ") }))]} />}
            </Field>
            <Field label="Actor ID" optional className="w-64">{(p) => <Input {...p} value={actor} onChange={(e) => setActor(e.target.value)} />}</Field>
            <Field label="Show" className="w-36">
              {(p) => <SelectBox {...p} value={String(limit)} onChange={(v) => setLimit(Number(v))} choices={LIMITS.map((n) => ({ value: String(n), label: `${n} entries` }))} />}
            </Field>
          </div>
        )}
        empty={<EmptyState title="No changes recorded" />}
        columns={[
          { key: "at", header: "When", width: "9.5rem", cell: (a) => showDateTime(a.at) },
          { key: "entity", header: "Entity", width: "9rem", cell: (a) => a.entity.replaceAll("_", " ") },
          { key: "action", header: "Action", width: "8rem", cell: (a) => a.action },
          { key: "by", header: "By", width: "9rem", cell: (a) => a.admin_login_id ?? "system" },
          { key: "detail", header: "Change", wrap: true, cell: (a) => <Diff detail={a.detail} /> },
          { key: "id", header: "Record", width: "8rem", cell: (a) => <span className="text-xs text-muted-foreground" title={a.entity_id}>{a.entity_id.slice(0, 8)}</span> },
        ]}
      />
    </>
  );
}
