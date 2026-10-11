import { useState } from "react";

import { Button, TextField, useToast } from "../../components";
import { fieldError, moved, useDirMutation } from "./api";
import { ActiveChip, Notice } from "./common";

export interface OrderedRow {
  id: string;
  label: string;
  active: boolean;
}

/**
 * A list the admin can add to, rename, reorder and deactivate. Used for the
 * checklists (ADM-CHK) and the could-not-complete reasons (ADM-CNC).
 * `itemPath` is the base for rename/deactivate, `addPath` and `orderPath` are
 * full paths under the directory API.
 */
export function OrderedList({ rows, noun, addPath, orderPath, itemPath, renameNote }: {
  rows: OrderedRow[];
  noun: string;
  addPath: string;
  orderPath: string;
  itemPath: string;
  renameNote?: string;
}) {
  const toast = useToast();
  const mut = useDirMutation();
  const [label, setLabel] = useState("");
  const [editId, setEditId] = useState<string | null>(null);
  const [draft, setDraft] = useState("");

  return (
    <div>
      {renameNote && <p className="muted">{renameNote}</p>}
      <Notice error={mut.error} />
      <ul className="ref-list">
        {rows.map((r, i) => (
          <li key={r.id}>
            {editId === r.id ? (
              <div className="ref-inline">
                <TextField label={`New text for ${r.label}`} value={draft} maxLength={120}
                           onChange={(e) => setDraft(e.target.value)} />
                <Button busy={mut.isPending} disabled={!draft.trim()}
                        onClick={() => mut.mutate(
                          { path: `${itemPath}/${r.id}`, method: "PATCH", body: { label: draft.trim() } },
                          { onSuccess: () => { setEditId(null); toast.show("Renamed.", "ok"); } })}>
                  Save
                </Button>
                <Button variant="ghost" onClick={() => setEditId(null)}>Cancel</Button>
              </div>
            ) : (
              <>
                <span className={`ref-label${r.active ? "" : " ref-inactive"}`}>{r.label}</span>
                <ActiveChip active={r.active} />
                <div className="ref-actions">
                  <Button variant="ghost" aria-label={`Rename ${r.label}`}
                          onClick={() => { setEditId(r.id); setDraft(r.label); }}>Rename</Button>
                  <Button variant="ghost" busy={mut.isPending}
                          aria-label={`${r.active ? "Deactivate" : "Reactivate"} ${r.label}`}
                          onClick={() => mut.mutate({
                            path: `${itemPath}/${r.id}/${r.active ? "deactivate" : "reactivate"}`,
                          })}>{r.active ? "Deactivate" : "Reactivate"}</Button>
                  <Button variant="ghost" disabled={i === 0 || mut.isPending}
                          aria-label={`Move ${r.label} up`}
                          onClick={() => mut.mutate({ path: orderPath, method: "PUT",
                                                      body: { ids: moved(rows, i, -1) } })}>Up</Button>
                  <Button variant="ghost" disabled={i === rows.length - 1 || mut.isPending}
                          aria-label={`Move ${r.label} down`}
                          onClick={() => mut.mutate({ path: orderPath, method: "PUT",
                                                      body: { ids: moved(rows, i, 1) } })}>Down</Button>
                </div>
              </>
            )}
          </li>
        ))}
        {rows.length === 0 && <li className="muted">None yet.</li>}
      </ul>
      <div className="ref-add">
        <TextField label={`New ${noun}`} value={label} maxLength={120}
                   error={fieldError(mut.error, "label")}
                   onChange={(e) => setLabel(e.target.value)} />
        <Button busy={mut.isPending} disabled={!label.trim()}
                onClick={() => mut.mutate({ path: addPath, body: { label: label.trim() } },
                  { onSuccess: () => { setLabel(""); toast.show("Added.", "ok"); } })}>
          Add {noun}
        </Button>
      </div>
    </div>
  );
}
