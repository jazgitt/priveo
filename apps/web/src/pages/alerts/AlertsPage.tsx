import { useState } from "react";
import { Link } from "react-router-dom";

import { Button, Card, StatusChip, useToast } from "../../components";
import { formatDate } from "../support/format";
import { useMarkAlertRead, useMarkAllRead, useMergedAlerts } from "../support/hooks";
import "../support/support.css";

/** The admin alerts, from both sources in one list (ADM-ACC-09). */
export function AlertsPage() {
  const toast = useToast();
  const { items, unread, loading, error } = useMergedAlerts();
  const markRead = useMarkAlertRead();
  const markAll = useMarkAllRead();
  const [unreadOnly, setUnreadOnly] = useState(false);
  const shown = unreadOnly ? items.filter((a) => !a.read) : items;

  async function readAll() {
    const ids = items.filter((a) => a.source === "payment" && !a.read).map((a) => a.id);
    try {
      await markAll.mutateAsync(ids);
    } catch {
      toast.show("Could not mark the alerts as read.", "error");
    }
  }

  return (
    <>
      <h1 className="page-title">Alerts</h1>
      <Card
        title={`${unread} unread`}
        actions={
          <div className="sp-row">
            <label>
              <input type="checkbox" checked={unreadOnly}
                     onChange={(e) => setUnreadOnly(e.target.checked)} /> Unread only
            </label>
            <Button variant="secondary" onClick={readAll} busy={markAll.isPending}
                    disabled={unread === 0}>Mark all read</Button>
          </div>
        }
      >
        {loading && <p className="muted">Loading...</p>}
        {error && <p role="alert">Could not load the alerts.</p>}
        {!loading && shown.length === 0 && <p className="muted">No alerts.</p>}
        <ul className="sp-list">
          {shown.map((a) => (
            <li key={a.key}>
              <div className="sp-row">
                <StatusChip tone={a.source === "payment" ? "info" : "warn"}>
                  {a.source === "payment" ? "Payment" : "Support"}
                </StatusChip>
                <span className={a.read ? undefined : "sp-unread"}>{a.title}</span>
                <span className="muted">{formatDate(a.created_at)}</span>
              </div>
              <p>{a.body}</p>
              <div className="sp-row">
                {a.link && <Link className="sp-link" to={a.link}>Open</Link>}
                {!a.read && (
                  <Button variant="ghost" onClick={() => markRead.mutate(a)}>Mark read</Button>
                )}
              </div>
            </li>
          ))}
        </ul>
      </Card>
    </>
  );
}
