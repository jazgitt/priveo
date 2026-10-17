import { Bell } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";

import { Button } from "@/ui/button";
import { Popover, PopoverContent, PopoverTrigger } from "@/ui/popover";

import { useMarkAlertRead, useMergedAlerts } from "../pages/support/hooks";

/** The notification bell with the unread count (ADM-ACC-09). The shell mounts it. */
export function AlertBell() {
  const [open, setOpen] = useState(false);
  const { items, unread } = useMergedAlerts();
  const markRead = useMarkAlertRead();
  const latest = items.filter((a) => !a.read).slice(0, 5);

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button variant="ghost" size="sm" className="relative" aria-label={`Alerts, ${unread} unread`}>
          <Bell aria-hidden />
          <span>Alerts</span>
          {unread > 0 && (
            <span className="ml-0.5 inline-flex min-w-5 items-center justify-center rounded-full bg-destructive px-1.5 text-[0.6875rem] font-semibold text-white">
              {unread}
            </span>
          )}
        </Button>
      </PopoverTrigger>
      <PopoverContent align="end" className="w-96 p-0">
        <div role="region" aria-label="Latest alerts">
          <div className="border-b px-4 py-2.5 text-sm font-semibold">Unread alerts</div>
          {latest.length === 0 && <p className="px-4 py-6 text-center text-sm text-muted-foreground">No unread alerts.</p>}
          <ul className="max-h-96 list-none divide-y overflow-y-auto p-0">
            {latest.map((a) => (
              <li key={a.key} className="flex items-start gap-3 px-4 py-3">
                <div className="min-w-0 flex-1">
                  <p className="m-0 text-sm font-medium">{a.title}</p>
                  <p className="m-0 mt-0.5 text-xs break-words text-muted-foreground">{a.body}</p>
                </div>
                <Button variant="ghost" size="xs" onClick={() => markRead.mutate(a)}>Mark read</Button>
              </li>
            ))}
          </ul>
          <div className="border-t px-4 py-2.5 text-sm">
            <Link to="/alerts" onClick={() => setOpen(false)}>See all alerts</Link>
          </div>
        </div>
      </PopoverContent>
    </Popover>
  );
}
