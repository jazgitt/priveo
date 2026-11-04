import { useQuery, useQueryClient } from "@tanstack/react-query";
import { RefreshCw } from "lucide-react";
import { useState } from "react";

import { api } from "@/api/client";
import { DataTable, Pager } from "@/blocks/DataTable";
import { Field, NONE, SelectBox } from "@/blocks/fields";
import { EmptyState, ErrorState, PageHeader } from "@/blocks/layout";
import { showDateTime } from "@/components/format";
import { useSite } from "@/site/SiteContext";
import { Badge } from "@/ui/badge";
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
  /** The site the change belongs to; null when it applies to all sites. */
  society_id?: string | null;
}

const ENTITIES = ["society", "plan", "vehicle", "slot", "service", "checklist", "reason",
  "setting", "addon", "zone", "customer", "subscription", "cutoff_request", "schedule_change", "operations", "schedule", "payment", "crew", "job"];
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

/** One page of the audit trail, as the API sends it. */
export interface AuditPageData {
  items: AuditEntry[];
  total: number;
  limit: number;
  offset: number;
}

/**
 * What changed in the chosen site, newest first, 50 events a page. The server pages
 * and counts. The page does not reload by itself: the admin presses Refresh to see
 * newer events. Changes that belong to no site (settings, plans, logins) are not here.
 */
export function AuditPage() {
  const site = useSite();
  const qc = useQueryClient();
  const [entity, setEntity] = useState("");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [actor, setActor] = useState("");
  const [page, setPage] = useState(0);
  const [lastSite, setLastSite] = useState(site.id);
  // A new site starts again from the first page.
  if (lastSite !== site.id) { setLastSite(site.id); setPage(0); }
  const q = new URLSearchParams();
  q.set("society_id", site.id);
  if (entity) q.set("entity", entity);
  q.set("limit", String(PAGE_SIZE));
  q.set("offset", String(page * PAGE_SIZE));
  if (from) q.set("date_from", from);
  if (to) q.set("date_to", to);
  if (actor) q.set("actor_id", actor);
  const list = useQuery({
    queryKey: ["admin-audit", site.id, entity, from, to, actor, page],
    queryFn: () => api<AuditPageData>(`/v1/admin/directory/audit?${q.toString()}`),
    enabled: !!site.id,
    // Never reload on its own: not on a timer (the app polls every 30 s by default), not on focus, not on reconnect.
    staleTime: Infinity,
    refetchInterval: false,
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
    refetchOnMount: false,
  });
  const change = (set: (v: string) => void) => (v: string) => { set(v); setPage(0); };
  const refresh = () => {
    // Pages read earlier are out of date too: forget them, then load the first page again.
    qc.removeQueries({ queryKey: ["admin-audit"], type: "inactive" });
    if (page === 0) void list.refetch(); else setPage(0);
  };

  return (
    <>
      <PageHeader title="Audit trail" site={site.name || undefined} description="Who changed what at this site, and the changes that apply to all sites, newest first."
                  actions={(
                    <Button variant="outline" disabled={list.isFetching} onClick={refresh}>
                      <RefreshCw className={list.isFetching ? "animate-spin" : undefined} aria-hidden /> Refresh
                    </Button>
                  )} />
      <p role="note" className="mb-4 text-sm text-muted-foreground">
        This list does not update by itself. Press Refresh to load the latest events. It shows the changes made to this site and the changes marked All sites, such as settings, plans and sign-in events, which apply to every site.
        {list.dataUpdatedAt > 0 && <> Loaded at {new Date(list.dataUpdatedAt).toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" })}.</>}
      </p>
      {list.isError && <div className="mb-4"><ErrorState message="Could not load the audit trail." onRetry={() => void list.refetch()} /></div>}
      <DataTable
        rows={list.data?.items}
        loading={!!site.id && list.isLoading}
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
        empty={<EmptyState title="No changes recorded for this site or for all sites" />}
        columns={[
          { key: "at", header: "When", width: "9.5rem", cell: (a) => showDateTime(a.at) },
          { key: "site", header: "Site", width: "8rem", cell: (a) => a.society_id
            ? (site.sites.find((s) => s.id === a.society_id)?.name ?? site.name)
            : <Badge variant="secondary">All sites</Badge> },
          { key: "entity", header: "Entity", width: "9rem", cell: (a) => a.entity.replaceAll("_", " ") },
          { key: "action", header: "Action", width: "8rem", cell: (a) => a.action },
          { key: "by", header: "By", width: "9rem", cell: (a) => a.admin_login_id ?? "system" },
          { key: "detail", header: "Change", wrap: true, cell: (a) => <Diff detail={a.detail} /> },
          { key: "id", header: "Record", width: "8rem", cell: (a) => <span className="text-xs text-muted-foreground" title={a.entity_id}>{a.entity_id.slice(0, 8)}</span> },
        ]}
        footer={<Pager page={page} size={PAGE_SIZE} count={list.data?.items.length ?? 0} total={list.data?.total} busy={list.isFetching} onPage={setPage} />}
      />
    </>
  );
}
