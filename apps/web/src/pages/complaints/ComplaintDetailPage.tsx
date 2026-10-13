import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";

import { api, ApiError } from "../../api/client";
import { Button, Card, SelectField, StatusChip, useToast } from "../../components";
import { formatDate } from "../support/format";
import { KEYS } from "../support/hooks";
import type { ComplaintDetail } from "../support/types";
import "../support/support.css";
import { STATUSES, statusTone } from "./ComplaintsPage";

/** One complaint: the thread, the status and a note box (ADM-CMP-02 to -04, -06, -07). */
export function ComplaintDetailPage() {
  const { id = "" } = useParams();
  const qc = useQueryClient();
  const toast = useToast();
  const [note, setNote] = useState("");
  const [status, setStatus] = useState("");
  const path = `/v1/admin/complaints/${id}`;

  const detail = useQuery({ queryKey: [...KEYS.complaints, id], queryFn: () => api<ComplaintDetail>(path) });
  const visit = useQuery({ queryKey: ["complaint-visit", id, detail.data?.visit_id],
    enabled: !!detail.data?.visit_id,
    queryFn: () => api<{ status: string; date: string; jobs: { id: string; service: string;
      crew_name: string; checklist: { key: string; label: string; checked_at: string | null }[];
      proof: { id: string; kind: string; url: string }[] }[] }>(`${path}/visit`) });

  const save = useMutation({
    mutationFn: (v: { kind: "status" | "note"; status?: string; note: string }) =>
      api<ComplaintDetail>(`${path}/${v.kind === "status" ? "status" : "notes"}`, {
        method: "POST",
        body: v.kind === "status" ? { status: v.status, note: v.note } : { note: v.note },
      }),
    onSuccess: (data) => {
      qc.setQueryData([...KEYS.complaints, id], data);
      void qc.invalidateQueries({ queryKey: KEYS.complaints });
      setNote("");
      setStatus("");
      toast.show("Saved.", "ok");
    },
    onError: (e) => toast.show(e instanceof ApiError ? e.message : "Could not save.", "error"),
  });

  if (detail.isLoading) return <p className="loading">Loading...</p>;
  if (detail.isError || !detail.data) {
    return <p role="alert">Could not load this complaint.</p>;
  }
  const c = detail.data;

  return (
    <>
      <p><Link className="sp-link" to="/complaints">Back to complaints</Link></p>
      <h1 className="page-title">
        {c.display_id}{" "}
        <StatusChip tone={statusTone(c.status)}>{c.status}</StatusChip>
        {c.overdue && <span className="sp-overdue"> Overdue</span>}
      </h1>
      <div className="sp-stack">
        <Card title="Complaint">
          <p><strong>{c.category}</strong></p>
          <p>{c.description}</p>
          <p className="muted">
            {c.customer_name}, {c.flat}, {c.society}. Raised {formatDate(c.created_at)}.
            {c.visit_id ? ` Visit ${c.visit_id}.` : ""}
          </p>
          {c.photo_keys.length > 0 && (
            <p className="muted">{c.photo_keys.length} photo(s) attached.</p>
          )}
          <p>{c.vehicle || "No vehicle linked"}</p>
          {(c.photo_urls ?? []).map((url, i) => <a key={url} href={url} target="_blank" rel="noreferrer"><img src={url} alt={`Complaint photo ${i + 1}`} style={{ maxWidth: 240, maxHeight: 180 }} /></a>)}
          {c.visit_id && <section aria-label="Linked visit">
            <h3>Linked visit</h3>{visit.isPending && <p>Loading visit…</p>}
            {visit.isError && <><p role="alert">Could not load visit proof.</p><Button onClick={() => void visit.refetch()}>Retry visit</Button></>}
            {visit.data && <><p>{formatDate(visit.data.date)} · {visit.data.status}</p>
              {visit.data.jobs.map(j => <div key={j.id}><h4>{j.service} · {j.crew_name}</h4>
                <ul>{j.checklist.map(item => <li key={item.key}>{item.label} · {item.checked_at ? formatDate(item.checked_at) : "Not checked"}</li>)}</ul>
                {j.proof.map(p => p.kind === "video" ? <video key={p.id} src={p.url} controls preload="metadata" style={{ maxWidth: 320 }} /> : <a key={p.id} href={p.url} target="_blank" rel="noreferrer"><img src={p.url} alt="Linked visit proof" style={{ maxWidth: 240 }} /></a>)}
              </div>)}</>}
          </section>}
        </Card>

        <Card title="Thread">
          <div className="sp-thread">
            {c.updates.length === 0 && <p className="muted">No updates yet.</p>}
            {c.updates.map((u) => (
              <div key={u.id} className={`sp-msg${u.author_role === "admin" ? " sp-msg-admin" : ""}`}>
                <div className="muted">
                  {u.author_role === "admin" ? "Admin" : "Customer"}, {formatDate(u.created_at)}
                  {u.status ? `, status ${u.status}` : ""}
                </div>
                <div>{u.note}</div>
              </div>
            ))}
          </div>
        </Card>

        <Card title="Update">
          <form className="sp-form" onSubmit={(e) => {
            e.preventDefault();
            if (status) save.mutate({ kind: "status", status, note: note.trim() });
            else if (note.trim()) save.mutate({ kind: "note", note: note.trim() });
          }}>
            <SelectField label="Set status" value={status} onChange={(e) => setStatus(e.target.value)}>
              <option value="">Keep {c.status}</option>
              {STATUSES.filter((s) => s !== c.status).map((s) => <option key={s} value={s}>{s}</option>)}
            </SelectField>
            <div className="field">
              <label htmlFor="cmp-note">Note for the customer</label>
              <textarea id="cmp-note" value={note} maxLength={1000}
                        onChange={(e) => setNote(e.target.value)} />
            </div>
            <Button type="submit" busy={save.isPending} disabled={!status && !note.trim()}>
              {status ? "Change status" : "Add note"}
            </Button>
          </form>
        </Card>
      </div>
    </>
  );
}
