import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useSite } from "../../site/SiteContext";
import { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../../api/client";
import { Button, Card, SelectField, StatusChip, TextField, useToast } from "../../components";
import { ApiErrorNote } from "../../components/ApiErrorNote";
import { showDate } from "../../components/format";

export interface OperationJob {
  id: string; visit_id: string; date: string; society: string; customer_id: string;
  customer_name: string; vehicle: string; registration: string; crew_name: string | null;
  service: string; status: string; reason: string; note: string; photo_url: string | null;
  outcome: string | null; covered_on: string | null; rescheduled_on: string | null;
  replacement_assigned: boolean | null; replacement_status: string | null;
  resolution_reason: string; resolution_note: string; resolved_by: string | null; resolved_at: string | null;
}

function JobCard({ job, reasons }: { job: OperationJob; reasons: { key: string; label: string }[] }) {
  const [reason, setReason] = useState(""); const [note, setNote] = useState("");
  const qc = useQueryClient(); const toast = useToast();
  const action = useMutation({ mutationFn: (choice: "Skip" | "Reschedule" | "Visit") => api(
    choice === "Visit" ? `/v1/admin/operations/visits/${job.visit_id}/skip` : `/v1/admin/operations/jobs/${job.id}/resolve`,
    { method: "POST", body: { ...(choice !== "Visit" ? { action: choice } : {}), reason, note } }),
    onSuccess: () => { toast.show("Outcome saved.", "ok"); for (const key of ["operations", "board", "needs-scheduling", "payments", "subscriptions"]) void qc.invalidateQueries({ queryKey: [key] }); } });
  const resolved = !!job.resolved_at;
  return <Card title={`${job.service} · ${job.registration}`}>
    <p><Link to={`/customers/${job.customer_id}`}>{job.customer_name}</Link> · {job.society} · {showDate(job.date)} · {job.crew_name || "Unassigned"}</p>
    <p>{job.vehicle} · <StatusChip>{job.status === "Could not complete" ? "Missed" : job.status}</StatusChip></p>
    {(job.reason || job.note) && <p>{job.reason} {job.note}</p>}
    {job.photo_url && <a href={job.photo_url} target="_blank" rel="noreferrer"><img src={job.photo_url} alt="Could not complete evidence" style={{ maxWidth: 240, maxHeight: 180 }} /></a>}
    {job.covered_on && <p>Covered by the next day’s regular Exterior service on {showDate(job.covered_on)}. No extra job or plan extension is needed.</p>}
    {job.rescheduled_on && <p>Rescheduled on {showDate(job.rescheduled_on)} · {job.replacement_assigned ? "Assigned" : "Needs scheduling"} · {job.replacement_status}</p>}
    {resolved && <p>{job.outcome} · {job.resolution_reason} {job.resolution_note} · {job.resolved_by} · {showDate(job.resolved_at)}</p>}
    <ApiErrorNote error={action.error} />
    {!resolved && ["Scheduled", "Could not complete"].includes(job.status) && <>
      <SelectField label="Operations reason" value={reason} onChange={e => setReason(e.target.value)}><option value="">No reason selected</option>{reasons.map(r => <option key={r.key} value={r.label}>{r.label}</option>)}</SelectField>
      <TextField label="Outcome note" value={note} onChange={e => setNote(e.target.value)} maxLength={2000} />
      <p>{job.service === "Cleaning-External" ? "Skipping adds one day to the plan and moves unpaid renewal dates." : job.service === "Deep Spa" ? "Skipping does not extend the plan. Handle any refund or rebooking separately." : "Skipping loses this Interior service and does not extend the plan."}</p>
      <Button busy={action.isPending} onClick={() => action.mutate("Skip")}>Skip job by operations</Button>
      {job.status === "Could not complete" && job.service !== "Cleaning-External" && <Button variant="secondary" busy={action.isPending} onClick={() => action.mutate("Reschedule")}>Reschedule for next day</Button>}
      {job.status === "Scheduled" && <Button variant="secondary" busy={action.isPending} onClick={() => action.mutate("Visit")}>Skip remaining jobs on this visit</Button>}
    </>}
  </Card>;
}

export function OperationsPage() {
  const [queue, setQueue] = useState("missed"); const society = useSite().id;
  const [from, setFrom] = useState(""); const [to, setTo] = useState(""); const [reason, setReason] = useState("");
  const [unresolved, setUnresolved] = useState(false);
  const params = new URLSearchParams({ queue });
  if (society) params.set("society_id", society); if (from) params.set("date_from", from);
  if (to) params.set("date_to", to); if (reason) params.set("reason_key", reason);
  if (unresolved && queue === "missed") params.set("unresolved", "true");
  const jobs = useQuery({ queryKey: ["operations", params.toString()], queryFn: () => api<OperationJob[]>(`/v1/admin/operations/jobs?${params}`) });
  const reasons = useQuery({ queryKey: ["operations-reasons"], queryFn: () => api<{ key: string; label: string }[]>("/v1/admin/operations/reasons") });
  return <><h1 className="page-title">Operations</h1><Card title="Service outcomes">
    <SelectField label="Queue" value={queue} onChange={e => setQueue(e.target.value)}><option value="missed">Missed jobs</option><option value="scheduled">Scheduled work</option><option value="history">Resolution history</option></SelectField>
    <TextField label="From date" type="date" value={from} onChange={e => setFrom(e.target.value)} /><TextField label="To date" type="date" value={to} onChange={e => setTo(e.target.value)} />
    <SelectField label="Failure reason" value={reason} onChange={e => setReason(e.target.value)}><option value="">All reasons</option>{reasons.data?.map(r => <option key={r.key} value={r.key}>{r.label}</option>)}</SelectField>
    {queue === "missed" && <label><input type="checkbox" checked={unresolved} onChange={e => setUnresolved(e.target.checked)} />Only Interior/Spa jobs awaiting an outcome</label>}
    <ApiErrorNote error={jobs.error ?? reasons.error} />
    {jobs.isPending && <p>Loading jobs…</p>}{jobs.data?.length === 0 && <p>No jobs match these filters.</p>}
  </Card>{jobs.data?.map(j => <JobCard key={`${j.id}:${j.resolved_at ?? "open"}`} job={j} reasons={reasons.data ?? []} />)}</>;
}
