import { useQuery } from "@tanstack/react-query";
import { useSite } from "../../site/SiteContext";
import { useState } from "react";
import { Link } from "react-router-dom";

import { api } from "../../api/client";
import { Card, SelectField, StatusChip, Table, type ChipTone } from "../../components";
import { formatDate } from "../support/format";
import { KEYS } from "../support/hooks";
import type { ComplaintSummary } from "../support/types";
import "../support/support.css";

export const STATUSES = ["Raised", "In progress", "Resolved"] as const;

export function statusTone(status: string): ChipTone {
  return status === "Resolved" ? "ok" : status === "In progress" ? "info" : "warn";
}

/** The complaints list with filters. Overdue ones (Raised for over 4 hours) are marked. */
export function ComplaintsPage() {
  const [status, setStatus] = useState("");
  const [category, setCategory] = useState("");
  const society = useSite().name;

  const params = new URLSearchParams();
  if (status) params.set("status", status);
  if (category) params.set("category", category);
  const qs = params.toString();

  const list = useQuery({
    queryKey: [...KEYS.complaints, qs],
    queryFn: () => api<ComplaintSummary[]>(`/v1/admin/complaints${qs ? `?${qs}` : ""}`),
  });
  // Category choices come from the rows seen so far.
  const all = useQuery({
    queryKey: [...KEYS.complaints, ""],
    queryFn: () => api<ComplaintSummary[]>("/v1/admin/complaints"),
  });
  const categories = [...new Set((all.data ?? []).map((c) => c.category))].sort();
  const rows = (list.data ?? []).filter((c) => !society || c.society === society);

  return (
    <>
      <h1 className="page-title">Complaints</h1>
      <Card>
        <div className="sp-filters">
          <SelectField label="Status" value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="">All</option>
            {STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
          </SelectField>
          <SelectField label="Category" value={category}
                       onChange={(e) => setCategory(e.target.value)}>
            <option value="">All</option>
            {categories.map((s) => <option key={s} value={s}>{s}</option>)}
          </SelectField>
        </div>
        {list.isLoading && <p className="muted">Loading...</p>}
        {list.isError && <p role="alert">Could not load the complaints.</p>}
        {list.data && (
          <Table<ComplaintSummary>
            rows={rows}
            rowKey={(c) => c.id}
            empty="No complaints match."
            columns={[
              { key: "id", header: "ID", render: (c) => (
                <Link className="sp-link" to={`/complaints/${c.id}`}>{c.display_id}</Link>) },
              { key: "customer", header: "Customer", render: (c) => `${c.customer_name}, ${c.flat}` },
              { key: "society", header: "Society", render: (c) => c.society },
              { key: "category", header: "Category", render: (c) => c.category },
              { key: "visit", header: "Visit", render: (c) => c.visit_id ?? "-" },
              { key: "status", header: "Status", render: (c) => (
                <>
                  <StatusChip tone={statusTone(c.status)}>{c.status}</StatusChip>
                  {c.overdue && <span className="sp-overdue"> Overdue</span>}
                </>) },
              { key: "vehicle", header: "Vehicle", render: (c) => c.vehicle || "Not linked" },
              { key: "raised", header: "Raised", render: (c) => formatDate(c.created_at) },
            ]}
          />
        )}
      </Card>
    </>
  );
}
