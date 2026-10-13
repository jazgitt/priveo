import { useMutation, useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "../../api/client";
import { Button, Card, SelectField } from "../../components";
import { ApiErrorNote } from "../../components/ApiErrorNote";
import { showDate } from "../../components/format";
import type { Board } from "./api";
import { Link } from "react-router-dom";

interface Suggestions { fingerprint: string; items: { job_id: string; crew_id: string; start_minute: number; date: string; service: string }[] }
export function ScheduleActions({ board, refresh }: { board: Board | null; refresh: () => void }) {
  const [first, setFirst] = useState(""); const [second, setSecond] = useState("");
  const [preview, setPreview] = useState<Suggestions | null>(null);
  const [selected, setSelected] = useState<string[]>([]);
  const cutoff = useQuery({ queryKey: ["cutoff-requests"], queryFn: () => api<{ id: string; registration: string; customer_name: string; date: string; cutoff_time: string; old_cutoff: string | null; crew_name: string | null; start_time: string | null }[]>("/v1/admin/scheduling/cutoff-requests") });
  const pending = useQuery({ queryKey: ["unplanned-addons"], queryFn: () => api<{ pending_addons: { id: string; registration: string; date: string; finish_by: string }[] }>("/v1/admin/scheduling/needs-scheduling") });
  const action = useMutation({ mutationFn: (r: { path: string; body: unknown }) => api(r.path, { method: "POST", body: r.body }),
    onSuccess: () => { setPreview(null); setSelected([]); refresh(); void cutoff.refetch(); } });
  const suggest = useMutation({ mutationFn: () => api<Suggestions>(`/v1/admin/scheduling/schedules/${board!.schedule.id}/suggestions`), onSuccess: r => { setPreview(r); setSelected([]); } });
  const editable = board?.schedule.status === "Draft";
  const jobs = board?.jobs.filter(j => j.status === "Scheduled" && j.crew_id) ?? [];
  return <><Card title="Cutoff change requests"><ApiErrorNote error={cutoff.error ?? action.error} />{cutoff.data?.length === 0 && <p>No pending cutoff requests.</p>}
    {cutoff.data?.map(r => <p key={r.id}>{r.customer_name} · {r.registration} · {showDate(r.date)} · {r.old_cutoff ?? "—"} → {r.cutoff_time} {r.crew_name && `· ${r.crew_name} at ${r.start_time}`}
      <Button busy={action.isPending} onClick={() => action.mutate({ path: `/v1/admin/scheduling/cutoff-requests/${r.id}/handle`, body: { apply: true } })}>Apply and schedule</Button>
      <Button variant="secondary" busy={action.isPending} onClick={() => action.mutate({ path: `/v1/admin/scheduling/cutoff-requests/${r.id}/handle`, body: { apply: false } })}>Reject</Button></p>)}
    <p>Unfreeze the relevant schedule before applying a request, review the result, then freeze again.</p>
    {(pending.data?.pending_addons?.length ?? 0) > 0 && <><h3>Add-ons awaiting a scheduling period</h3>{pending.data!.pending_addons.map(b => <p key={b.id}>{b.registration} · {showDate(b.date)} · Finish by {b.finish_by} <Link to="/addons">Manage booking</Link></p>)}</>}
  </Card>{board && <Card title="Draft improvements"><ApiErrorNote error={action.error ?? suggest.error} />
    {!editable && <p>Unfreeze this schedule to swap work or apply improvements.</p>}
    <SelectField label="First job" value={first} onChange={e => setFirst(e.target.value)}><option value="">Choose</option>{jobs.map(j => <option key={j.id} value={j.id}>{showDate(j.date)} · {j.registration} · {j.service}</option>)}</SelectField>
    <SelectField label="Second job" value={second} onChange={e => setSecond(e.target.value)}><option value="">Choose</option>{jobs.filter(j => j.id !== first).map(j => <option key={j.id} value={j.id}>{showDate(j.date)} · {j.registration} · {j.service}</option>)}</SelectField>
    <Button disabled={!editable || !first || !second} busy={action.isPending} onClick={() => action.mutate({ path: "/v1/admin/scheduling/jobs/swap", body: { first_job_id: first, second_job_id: second } })}>Swap crew and times</Button>
    <Button disabled={!editable} busy={suggest.isPending} onClick={() => suggest.mutate()}>Preview improvements</Button>
    {preview && <>{preview.items.length === 0 && <p>No improvements suggested.</p>}{preview.items.map(i => <label key={i.job_id}><input type="checkbox" checked={selected.includes(i.job_id)} onChange={e => setSelected(s => e.target.checked ? [...s, i.job_id] : s.filter(id => id !== i.job_id))} />{board.jobs.find(j => j.id === i.job_id)?.registration} · {i.service} · {showDate(i.date)} · {board.crew.find(c => c.id === i.crew_id)?.name} at {String(Math.floor(i.start_minute / 60)).padStart(2, "0")}:{String(i.start_minute % 60).padStart(2, "0")}</label>)}
      <Button disabled={!editable || selected.length === 0} busy={action.isPending} onClick={() => action.mutate({ path: `/v1/admin/scheduling/schedules/${board.schedule.id}/suggestions/apply`, body: { fingerprint: preview.fingerprint, job_ids: selected } })}>Apply selected improvements</Button>
    </>}
  </Card>}</>;
}
