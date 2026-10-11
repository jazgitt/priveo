import { useState } from "react";
import { Link } from "react-router-dom";

import { useMarkAlertRead, useMergedAlerts } from "../pages/support/hooks";
import "../pages/support/support.css";

/** The notification bell with the unread count (ADM-ACC-09). The shell mounts it. */
export function AlertBell() {
  const [open, setOpen] = useState(false);
  const { items, unread } = useMergedAlerts();
  const markRead = useMarkAlertRead();
  const latest = items.filter((a) => !a.read).slice(0, 5);

  return (
    <div className="sp-bell">
      <button type="button" className="btn btn-ghost" aria-expanded={open}
              aria-label={`Alerts, ${unread} unread`} onClick={() => setOpen((o) => !o)}>
        Alerts{unread > 0 && <span className="sp-bell-badge">{unread}</span>}
      </button>
      {open && (
        <div className="sp-bell-panel" role="region" aria-label="Latest alerts">
          {latest.length === 0 && <p className="muted">No unread alerts.</p>}
          <ul className="sp-list">
            {latest.map((a) => (
              <li key={a.key}>
                <strong>{a.title}</strong>
                <p>{a.body}</p>
                <button type="button" className="btn btn-ghost"
                        onClick={() => markRead.mutate(a)}>Mark read</button>
              </li>
            ))}
          </ul>
          <Link className="sp-link" to="/alerts" onClick={() => setOpen(false)}>
            See all alerts
          </Link>
        </div>
      )}
    </div>
  );
}
