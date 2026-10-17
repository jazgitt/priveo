import { CheckCheck } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";

import { BusyButton } from "@/blocks/FormDialog";
import { EmptyState, ErrorState, PageHeader, Panel } from "@/blocks/layout";
import { useAppMutation } from "@/blocks/mutation";
import { StatusBadge } from "@/blocks/status";
import { showDateTime } from "@/components/format";
import { cn } from "@/lib/utils";
import { Button } from "@/ui/button";
import { Skeleton } from "@/ui/skeleton";
import { Switch } from "@/ui/switch";

import { useMarkAlertRead, useMarkAllRead, useMergedAlerts } from "../support/hooks";

/** The admin alerts, from both sources in one list (ADM-ACC-09). */
export function AlertsPage() {
  const { items, unread, loading, error } = useMergedAlerts();
  const markRead = useMarkAlertRead();
  const markAll = useMarkAllRead();
  const readAll = useAppMutation<void>({
    mutationFn: () => markAll.mutateAsync(items.filter((a) => a.source === "payment" && !a.read).map((a) => a.id)),
    pending: "Marking all as read…",
    success: "All alerts are read.",
  });
  const [unreadOnly, setUnreadOnly] = useState(false);
  const shown = unreadOnly ? items.filter((a) => !a.read) : items;

  return (
    <>
      <PageHeader title="Alerts" description="Support and payment alerts in one list, newest first." />
      <Panel
        title={`${unread} unread`}
        actions={(
          <>
            <label className="flex items-center gap-2 text-sm">
              <Switch aria-label="Unread only" checked={unreadOnly} onCheckedChange={setUnreadOnly} />
              Unread only
            </label>
            <BusyButton variant="outline" size="sm" busy={readAll.isPending} disabled={unread === 0} onClick={() => readAll.mutate()}>
              <CheckCheck aria-hidden /> Mark all read
            </BusyButton>
          </>
        )}
        bodyClassName="p-0"
      >
        {loading && <div className="flex flex-col gap-3 p-5"><Skeleton className="h-12" /><Skeleton className="h-12" /><Skeleton className="h-12" /></div>}
        {error && <div className="p-5"><ErrorState message="Could not load the alerts." /></div>}
        {!loading && shown.length === 0 && (
          <div className="p-5"><EmptyState title={unreadOnly ? "No unread alerts" : "No alerts"}>New alerts appear here and on the bell.</EmptyState></div>
        )}
        <ul className="m-0 list-none divide-y p-0">
          {shown.map((a) => (
            <li key={a.key} className={cn("grid grid-cols-1 gap-x-4 gap-y-1 px-5 py-3.5 sm:grid-cols-[6.5rem_minmax(0,1fr)_auto]", !a.read && "bg-gold/5")}>
              <div><StatusBadge status={a.source === "payment" ? "Payment" : "Support"} tone={a.source === "payment" ? "info" : "warn"} /></div>
              <div className="min-w-0">
                <p className={cn("m-0 text-sm", !a.read ? "font-semibold" : "font-medium text-foreground/80")}>
                  {!a.read && <span className="mr-2 inline-block size-2 rounded-full bg-gold align-middle" aria-label="Unread" />}
                  {a.title}
                </p>
                <p className="m-0 mt-0.5 text-sm break-words text-muted-foreground">{a.body}</p>
                <p className="m-0 mt-1 text-xs text-muted-foreground">{showDateTime(a.created_at)}</p>
              </div>
              <div className="flex items-start gap-2 sm:justify-end">
                {a.link && <Button asChild size="sm" variant="outline"><Link to={a.link}>Open</Link></Button>}
                {!a.read && <Button size="sm" variant="ghost" disabled={markRead.isPending} onClick={() => markRead.mutate(a)}>Mark read</Button>}
              </div>
            </li>
          ))}
        </ul>
      </Panel>
    </>
  );
}
