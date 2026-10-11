import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { api, ApiError } from "../../api/client";
import { Button, Card, SelectField, StatusChip, TextField, useToast } from "../../components";
import type { OptionAdmin } from "../support/types";
import "../support/support.css";

const KEY = ["admin", "support-options"] as const;
const KINDS: { kind: string; label: string }[] = [
  { kind: "feedback_category", label: "Feedback categories" },
  { kind: "positive_tag", label: "Positive rating tags" },
  { kind: "checkin_category", label: "Check-in categories" },
];

function Row({ option, prev, next, onPatch, busy }: {
  option: OptionAdmin;
  prev?: OptionAdmin;
  next?: OptionAdmin;
  onPatch: (id: string, patch: Partial<OptionAdmin>) => void;
  busy: boolean;
}) {
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState(option.name);
  const [description, setDescription] = useState(option.description);

  if (editing) {
    return (
      <li>
        <TextField label="Name" value={name} maxLength={80} onChange={(e) => setName(e.target.value)} />
        <TextField label="Description" value={description} maxLength={300}
                   onChange={(e) => setDescription(e.target.value)} />
        <div className="sp-row">
          <Button busy={busy} disabled={!name.trim()} onClick={() => {
            onPatch(option.id, { name: name.trim(), description });
            setEditing(false);
          }}>Save</Button>
          <Button variant="ghost" onClick={() => setEditing(false)}>Cancel</Button>
        </div>
      </li>
    );
  }
  // Moving swaps sort order with the neighbour.
  const swap = (other: OptionAdmin) => {
    onPatch(option.id, { sort_order: other.sort_order });
    onPatch(other.id, { sort_order: option.sort_order });
  };
  return (
    <li>
      <div className="sp-row">
        <strong>{option.name}</strong>
        <StatusChip tone={option.active ? "ok" : "neutral"}>
          {option.active ? "Active" : "Inactive"}
        </StatusChip>
      </div>
      {option.description && <p className="muted">{option.description}</p>}
      <div className="sp-row">
        <Button variant="ghost" onClick={() => setEditing(true)}>Edit</Button>
        <Button variant="ghost" disabled={busy}
                onClick={() => onPatch(option.id, { active: !option.active })}>
          {option.active ? "Deactivate" : "Activate"}
        </Button>
        <Button variant="ghost" disabled={!prev || busy} aria-label={`Move ${option.name} up`}
                onClick={() => prev && swap(prev)}>Up</Button>
        <Button variant="ghost" disabled={!next || busy} aria-label={`Move ${option.name} down`}
                onClick={() => next && swap(next)}>Down</Button>
      </div>
    </li>
  );
}

/** Add, rename, describe, reorder and deactivate the support lists (ADM-FDB-06, -07). */
export function OptionsManager() {
  const qc = useQueryClient();
  const toast = useToast();
  const list = useQuery({ queryKey: KEY, queryFn: () => api<OptionAdmin[]>("/v1/admin/support/options") });
  const [kind, setKind] = useState(KINDS[0].kind);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");

  const onError = (e: unknown) =>
    toast.show(e instanceof ApiError ? e.message : "Could not save.", "error");
  const refresh = () => qc.invalidateQueries({ queryKey: KEY });

  const add = useMutation({
    mutationFn: () => api<OptionAdmin>("/v1/admin/support/options", {
      method: "POST", body: { kind, name: name.trim(), description },
    }),
    onSuccess: () => { setName(""); setDescription(""); toast.show("Added.", "ok"); void refresh(); },
    onError,
  });
  const patch = useMutation({
    mutationFn: (v: { id: string; patch: Partial<OptionAdmin> }) => api<OptionAdmin>(
      `/v1/admin/support/options/${v.id}`, { method: "PATCH", body: v.patch }),
    onSuccess: () => void refresh(),
    onError,
  });

  if (list.isLoading) return <p className="muted">Loading...</p>;
  if (list.isError) return <p role="alert">Could not load the lists.</p>;
  const all = list.data ?? [];

  return (
    <div className="sp-stack">
      {KINDS.map((k) => {
        const rows = all.filter((o) => o.kind === k.kind)
          .sort((a, b) => a.sort_order - b.sort_order);
        return (
          <Card key={k.kind} title={k.label}>
            <ul className="sp-list">
              {rows.map((o, i) => (
                <Row key={o.id} option={o} prev={rows[i - 1]} next={rows[i + 1]}
                     busy={patch.isPending}
                     onPatch={(id, p) => patch.mutate({ id, patch: p })} />
              ))}
              {rows.length === 0 && <li className="muted">None yet.</li>}
            </ul>
          </Card>
        );
      })}
      <Card title="Add an item">
        <form onSubmit={(e) => { e.preventDefault(); if (name.trim()) add.mutate(); }}>
          <SelectField label="List" value={kind} onChange={(e) => setKind(e.target.value)}>
            {KINDS.map((k) => <option key={k.kind} value={k.kind}>{k.label}</option>)}
          </SelectField>
          <TextField label="New name" value={name} maxLength={80}
                     onChange={(e) => setName(e.target.value)} />
          <TextField label="New description" value={description} maxLength={300}
                     onChange={(e) => setDescription(e.target.value)} />
          <Button type="submit" busy={add.isPending} disabled={!name.trim()}>Add</Button>
        </form>
      </Card>
    </div>
  );
}
