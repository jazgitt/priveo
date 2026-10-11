import { Card } from "../../components";
import { useDirectory } from "./api";
import { QueryState } from "./common";
import { OrderedList } from "./OrderedList";
import type { Checklist, Reason } from "./types";

const RENAME_NOTE =
  "Renaming keeps the old item on visits already done and adds the new text in its place.";

/** The checklist for each service (ADM-CHK-01 to -07). */
export function ChecklistsTab() {
  const list = useDirectory<Checklist[]>("/checklists");
  return (
    <QueryState query={list}>
      {(lists) => (
        <div className="ref-stack">
          {lists.map((c) => (
            <Card key={c.service} title={c.service}>
              <OrderedList
                rows={c.items.map((i) => ({ id: i.id, label: i.label, active: i.active }))}
                noun="item"
                addPath={`/checklists/${encodeURIComponent(c.service)}/items`}
                orderPath={`/checklists/${encodeURIComponent(c.service)}/order`}
                itemPath="/checklist-items"
                renameNote={RENAME_NOTE} />
            </Card>
          ))}
        </div>
      )}
    </QueryState>
  );
}

/** The reasons a crew member can give for a job not completed (ADM-CNC). */
export function ReasonsTab() {
  const list = useDirectory<Reason[]>("/reasons");
  return (
    <Card title="Could not complete reasons">
      <QueryState query={list}>
        {(rows) => (
          <OrderedList
            rows={rows.map((r) => ({ id: r.id, label: r.label, active: r.active }))}
            noun="reason" addPath="/reasons" orderPath="/reasons/order" itemPath="/reasons" />
        )}
      </QueryState>
    </Card>
  );
}
