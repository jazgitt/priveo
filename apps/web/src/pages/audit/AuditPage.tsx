import { useQuery } from "@tanstack/react-query";
import { RefreshCw } from "lucide-react";
import { useState } from "react";

import { api } from "@/api/client";
import { DataTable, Pager } from "@/blocks/DataTable";
import { Field, NONE, SelectBox } from "@/blocks/fields";
import { EmptyState, ErrorState, PageHeader } from "@/blocks/layout";
import { showDateTime } from "@/components/format";
import { Button } from "@/ui/button";
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
  "setting", "addon", "customer", "subscription", "cutoff_request", "schedule_change", "operations", "schedule", "payment", "crew", "job"];
/** The most events the page ever loads. Older ones are not shown. */
export const MAX_EVENTS = 1000;
export const PAGE_SIZE = 50;

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

/**
 * What changed in the reference data and settings, newest first. The last 1000
 * events are loaded once and paged here. The page does not reload by itself:
 * the admin presses Refresh to see newer events.
 */
export function AuditPage() {
  const [entity, setEntity] = useState("");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [actor, setActor] = useState("");
  const [page, setPage] = useState(0);
  const q = new URLSearchParams();
  if (entity) q.set("entity", entity);
  q.set("limit", String(MAX_EVENTS));
  if (from) q.set("date_from", from);
  if (to) q.set("date_to", to);
  if (actor) q.set("actor_id", actor);
  const list = useQuery({
    queryKey: ["admin-audit", entity, from, to, actor],
    queryFn: () => api<AuditEntry[]>(`/v1/admin/directory/audit?${q.toString()}`),
    // Never reload on its own: not on a timer (the app polls every 30 s by default), not on focus, not on reconnect.
    staleTime: Infinity,
    refetchInterval: false,
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
    refetchOnMount: false,
  });
  const all = list.data;
  const shown = all?.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);
  const change = (set: (v: string) => void) => (v: string) => { set(v); setPage(0); };

  return (
    <>
      <PageHeader title="Audit" description="Who changed what, newest first."
                  actions={(
                    <Button variant="outline" disabled={list.isFetching} onClick={() => { setPage(0); void list.refetch(); }}>
                      <RefreshCw className={list.isFetching ? "animate-spin" : undefined} aria-hidden /> Refresh
                    </Button>
                  )} />
      <p role="note" className="mb-4 text-sm text-muted-foreground">
        This list does not update by itself. Press Refresh to load the latest events. It shows the last {MAX_EVENTS} events{all && all.length >= MAX_EVENTS ? " (older ones are not loaded)" : ""}.
        {list.dataUpdatedAt > 0 && <> Loaded at {new Date(list.dataUpdatedAt).toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" })}.</>}
      </p>
      {list.isError && <div className="mb-4"><ErrorState message="Could not load the audit." onRetry={() => void list.refetch()} /></div>}
      <DataTable
        rows={shown}
        loading={list.isLoading}
        rowKey={(a) => a.id}
        toolbar={(
          <div className="flex flex-wrap items-end gap-3">
            <Field label="From date" className="w-44">{(p) => <Input {...p} type="date" value={from} onChange={(e) => change(setFrom)(e.target.value)} />}</Field>
            <Field label="To date" className="w-44">{(p) => <Input {...p} type="date" value={to} onChange={(e) => change(setTo)(e.target.value)} />}</Field>
            <Field label="Entity" className="w-48">
              {(p) => <SelectBox {...p} value={entity || NONE} onChange={(v) => change(setEntity)(v === NONE ? "" : v)}
                                 choices={[{ value: NONE, label: "All" }, ...ENTITIES.map((x) => ({ value: x, label: x.replaceAll("_", " ") }))]} />}
            </Field>
            <Field label="Actor ID" optional className="w-64">{(p) => <Input {...p} value={actor} onChange={(e) => change(setActor)(e.target.value)} />}</Field>
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
        footer={<Pager page={page} size={PAGE_SIZE} count={shown?.length ?? 0} total={all?.length} busy={list.isFetching} onPage={setPage} />}
      />
    </>
  );
}
