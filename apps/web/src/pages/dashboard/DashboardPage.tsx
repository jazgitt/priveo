import { useQuery } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { Link } from "react-router-dom";

import { api } from "../../api/client";
import { Card } from "../../components";
import { formatDate } from "../support/format";
import { KEYS, useMergedAlerts, useNeedsScheduling, usePayments } from "../support/hooks";
import type { ComplaintSummary } from "../support/types";
import "../support/support.css";

function Tile({ title, to, count, loading, error, children }: {
  title: string; to: string; count: number; loading: boolean; error: boolean; children?: ReactNode;
}) {
  return (
    <Card title={title} actions={<Link className="sp-link" to={to}>Open</Link>}>
      {error ? <p role="alert">Could not load.</p>
        : loading ? <p className="muted">Loading...</p>
        : <p className="sp-count" aria-label={`${title} count`}>{count}</p>}
      {children}
    </Card>
  );
}

/** Today at a glance: alerts, scheduling, payments and complaints. */
export function DashboardPage() {
  const alerts = useMergedAlerts();
  const needs = useNeedsScheduling();
  const initiated = usePayments("Initiated");
  const complaints = useQuery({
    queryKey: KEYS.complaints,
    queryFn: () => api<ComplaintSummary[]>("/v1/admin/complaints"),
  });
  const overdue = (complaints.data ?? []).filter((c) => c.overdue && c.status === "Raised");
  const unreadAlerts = alerts.items.filter((a) => !a.read).slice(0, 5);

  return (
    <>
      <h1 className="page-title">Dashboard</h1>
      <div className="sp-grid">
        <Tile title="Unread alerts" to="/alerts" count={alerts.unread}
              loading={alerts.loading} error={alerts.error}>
          <ul className="sp-list">
            {unreadAlerts.map((a) => <li key={a.key}>{a.title}: {a.body}</li>)}
          </ul>
        </Tile>
        <Tile title="Needs scheduling" to="/schedule" count={needs.data?.jobs.length ?? 0}
              loading={needs.isLoading} error={needs.isError}>
          <ul className="sp-list">
            {(needs.data?.jobs ?? []).slice(0, 5).map((j) => (
              <li key={j.id}>{formatDate(j.date)} - {j.registration} - {j.service}</li>
            ))}
          </ul>
        </Tile>
        <Tile title="Payments to confirm" to="/payments" count={initiated.data?.length ?? 0}
              loading={initiated.isLoading} error={initiated.isError}>
          <ul className="sp-list">
            {(initiated.data ?? []).slice(0, 5).map((p) => (
              <li key={p.id}>{p.customer_name} - Rs {p.amount_rupees} - due {formatDate(p.due_date)}</li>
            ))}
          </ul>
        </Tile>
        <Tile title="Complaints overdue" to="/complaints" count={overdue.length}
              loading={complaints.isLoading} error={complaints.isError}>
          <ul className="sp-list">
            {overdue.slice(0, 5).map((c) => (
              <li key={c.id}>
                <Link className="sp-link" to={`/complaints/${c.id}`}>{c.display_id}</Link>
                {" "}{c.customer_name} - {c.category}
              </li>
            ))}
          </ul>
        </Tile>
      </div>
    </>
  );
}
