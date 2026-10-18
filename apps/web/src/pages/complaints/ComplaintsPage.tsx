import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { api } from "@/api/client";
import { DataTable } from "@/blocks/DataTable";
import { Field, NONE, SelectBox } from "@/blocks/fields";
import { EmptyState, ErrorState, PageHeader, StatRow, StatTile } from "@/blocks/layout";
import { StatusBadge, type Tone } from "@/blocks/status";
import { useSite } from "@/site/SiteContext";

import { formatDate } from "../support/format";
import { KEYS } from "../support/hooks";
import type { ComplaintSummary } from "../support/types";

export const STATUSES = ["Raised", "In progress", "Resolved"] as const;

export function statusTone(status: string): Tone {
  return status === "Resolved" ? "ok" : status === "In progress" ? "info" : "warn";
}

/** The complaints list with filters. Overdue ones (Raised for over 4 hours) are marked (ADM-CMP-*). */
export function ComplaintsPage() {
  const navigate = useNavigate();
  const [status, setStatus] = useState("");
  const [category, setCategory] = useState("");
  const [overdueOnly, setOverdueOnly] = useState(false);
  const site = useSite();

  const params = new URLSearchParams();
  if (status) params.set("status", status);
  if (category) params.set("category", category);
  const qs = params.toString();

  const list = useQuery({
    queryKey: [...KEYS.complaints, qs],
    queryFn: () => api<ComplaintSummary[]>(`/v1/admin/complaints${qs ? `?${qs}` : ""}`),
  });
  // Category choices come from the rows seen so far.
  const all = useQuery({ queryKey: [...KEYS.complaints, ""], queryFn: () => api<ComplaintSummary[]>("/v1/admin/complaints") });
  const categories = [...new Set((all.data ?? []).map((c) => c.category))].sort();
  const rows = list.data?.filter((c) => (!site.name || c.society === site.name) && (!overdueOnly || c.overdue));
  // The tiles count every complaint of the site, whatever the filters below say.
  const ofSite = all.data?.filter((c) => !site.name || c.society === site.name);
  const count = (f: (c: ComplaintSummary) => boolean) => ofSite?.filter(f).length;
  const overdue = count((c) => c.overdue) ?? 0;
  const loading = all.isPending;
  const clear = () => { setStatus(""); setCategory(""); setOverdueOnly(false); };

  return (
    <>
      <PageHeader title="Complaints" site={site.name || undefined}
                  description={overdue > 0 ? `${overdue} overdue: raised more than 4 hours ago with no reply.` : "Customer complaints, newest first."} />
      {list.isError && <div className="mb-4"><ErrorState message="Could not load the complaints." onRetry={() => void list.refetch()} /></div>}
      <StatRow label="Complaint summary">
        <StatTile label="Total complaints" value={ofSite?.length} loading={loading}
                  selected={!status && !overdueOnly} onSelect={clear} />
        {STATUSES.map((st) => (
          <StatTile key={st} label={st} value={count((c) => c.status === st)} loading={loading}
                    selected={status === st} onSelect={() => { setOverdueOnly(false); setStatus(status === st ? "" : st); }} />
        ))}
        <StatTile label="Overdue" value={overdue} loading={loading} hint="Raised over 4 hours ago, no reply"
                  selected={overdueOnly} onSelect={() => { setStatus(""); setOverdueOnly(!overdueOnly); }} />
      </StatRow>
      <DataTable
        rows={rows}
        loading={list.isLoading}
        rowKey={(c) => c.id}
        onRowClick={(c) => navigate(`/complaints/${c.id}`)}
        toolbar={(
          <div className="flex flex-wrap items-end gap-3">
            <Field label="Status" className="w-44">
              {(p) => <SelectBox {...p} value={status || NONE} onChange={(v) => setStatus(v === NONE ? "" : v)}
                                 choices={[{ value: NONE, label: "All" }, ...STATUSES.map((s) => ({ value: s, label: s }))]} />}
            </Field>
            <Field label="Category" className="w-56">
              {(p) => <SelectBox {...p} value={category || NONE} onChange={(v) => setCategory(v === NONE ? "" : v)}
                                 choices={[{ value: NONE, label: "All" }, ...categories.map((s) => ({ value: s, label: s }))]} />}
            </Field>
          </div>
        )}
        empty={<EmptyState title="No complaints match" />}
        columns={[
          { key: "id", header: "ID", width: "7rem", cell: (c) => <Link to={`/complaints/${c.id}`} className="font-medium">{c.display_id}</Link> },
          { key: "customer", header: "Customer", width: "18%", cell: (c) => (
            <div className="min-w-0"><span className="block truncate">{c.customer_name}</span>
              <span className="block truncate text-xs text-muted-foreground">Flat {c.flat}</span></div>) },
          { key: "category", header: "Category", width: "13rem", cell: (c) => c.category },
          { key: "what", header: "Complaint", cell: (c) => <span className="text-muted-foreground">{c.description}</span> },
          { key: "vehicle", header: "Vehicle", width: "11rem", cell: (c) => c.vehicle || "Not linked" },
          { key: "raised", header: "Raised", width: "7rem", cell: (c) => formatDate(c.created_at) },
          { key: "status", header: "Status", width: "10rem", wrap: true, cell: (c) => (
            <span className="flex flex-wrap gap-1.5"><StatusBadge status={c.status} tone={statusTone(c.status)} />
              {c.overdue && <StatusBadge status="Overdue" tone="error" />}</span>) },
        ]}
      />
    </>
  );
}
