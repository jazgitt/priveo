import { useQuery } from "@tanstack/react-query";
import { ArrowRight, Bell, CalendarClock, CreditCard, MessageSquareWarning, type LucideIcon } from "lucide-react";
import type { ReactNode } from "react";
import { Link } from "react-router-dom";

import { api } from "@/api/client";
import { PageHeader } from "@/blocks/layout";
import { inr } from "@/components/format";
import { cn } from "@/lib/utils";
import { Skeleton } from "@/ui/skeleton";

import { formatDate } from "../support/format";
import { KEYS, useMergedAlerts, useNeedsScheduling, usePayments } from "../support/hooks";
import type { ComplaintSummary } from "../support/types";
import { TodaysServices } from "./TodaysServices";

/** One figure with the first few items behind it and a link to the page that deals with them. */
function Tile({ title, to, count, loading, error, icon: Icon, urgent, empty, children }: {
  title: string; to: string; count: number; loading: boolean; error: boolean;
  icon: LucideIcon; urgent?: boolean; empty: string; children?: ReactNode;
}) {
  return (
    <section className="flex flex-col rounded-xl border bg-card shadow-xs">
      <header className="flex items-start justify-between gap-3 px-5 pt-4">
        <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
          <Icon className="size-4" aria-hidden />{title}
        </div>
        <Link to={to} className="inline-flex items-center gap-1 text-sm">Open<ArrowRight className="size-3.5" aria-hidden /></Link>
      </header>
      <div className="px-5 pt-1 pb-3">
        {error ? <p role="alert" className="text-sm text-destructive">Could not load.</p>
          : loading ? <Skeleton className="h-9 w-16" />
          : <p aria-label={`${title} count`}
               className={cn("m-0 text-3xl font-semibold tabular-nums", urgent && count > 0 && "text-destructive")}>{count}</p>}
      </div>
      <div className="flex-1 border-t px-5 py-3 text-sm">
        {!loading && !error && count === 0 ? <p className="m-0 text-muted-foreground">{empty}</p> : children}
      </div>
    </section>
  );
}

function Rows({ children }: { children: ReactNode }) {
  return <ul className="m-0 flex list-none flex-col gap-2 p-0">{children}</ul>;
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
      <PageHeader title="Dashboard" description="What needs the admin's attention now, across all sites." />
      <TodaysServices />
      <div className="grid grid-cols-1 gap-5 md:grid-cols-2 2xl:grid-cols-4">
        <Tile title="Unread alerts" to="/alerts" count={alerts.unread} icon={Bell}
              loading={alerts.loading} error={alerts.error} empty="No unread alerts.">
          <Rows>
            {unreadAlerts.map((a) => (
              <li key={a.key} className="min-w-0">
                <span className="block truncate font-medium">{a.title}</span>
                <span className="block truncate text-xs text-muted-foreground">{a.body}</span>
              </li>
            ))}
          </Rows>
        </Tile>
        <Tile title="Needs scheduling" to="/schedule?tab=needs" count={needs.data?.jobs.length ?? 0} icon={CalendarClock} urgent
              loading={needs.isLoading} error={needs.isError} empty="Every visit has a crew member.">
          <Rows>
            {(needs.data?.jobs ?? []).slice(0, 5).map((j) => (
              <li key={j.id} className="grid grid-cols-[5.5rem_minmax(0,1fr)] gap-2">
                <span className="text-muted-foreground">{formatDate(j.date)}</span>
                <span className="truncate"><span className="reg">{j.registration}</span> · {j.service}</span>
              </li>
            ))}
          </Rows>
        </Tile>
        <Tile title="Payments to confirm" to="/payments" count={initiated.data?.length ?? 0} icon={CreditCard}
              loading={initiated.isLoading} error={initiated.isError} empty="No payment is waiting for confirmation.">
          <Rows>
            {(initiated.data ?? []).slice(0, 5).map((p) => (
              <li key={p.id} className="grid grid-cols-[minmax(0,1fr)_auto] gap-2">
                <span className="truncate">{p.customer_name}<span className="text-muted-foreground"> · due {formatDate(p.due_date)}</span></span>
                <span className="tabular-nums">{inr(p.amount_rupees)}</span>
              </li>
            ))}
          </Rows>
        </Tile>
        <Tile title="Complaints overdue" to="/complaints" count={overdue.length} icon={MessageSquareWarning} urgent
              loading={complaints.isLoading} error={complaints.isError} empty="No complaint is overdue.">
          <Rows>
            {overdue.slice(0, 5).map((c) => (
              <li key={c.id} className="min-w-0 truncate">
                <Link to={`/complaints/${c.id}`} className="font-medium">{c.display_id}</Link>
                <span> {c.customer_name}</span><span className="text-muted-foreground"> · {c.category}</span>
              </li>
            ))}
          </Rows>
        </Tile>
      </div>
    </>
  );
}
