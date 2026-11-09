import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { api } from "@/api/client";
import { useConfirm } from "@/blocks/confirm";
import { DataTable } from "@/blocks/DataTable";
import { Field, NONE, SelectBox } from "@/blocks/fields";
import { BusyButton, FormDialog } from "@/blocks/FormDialog";
import { DetailList, EmptyState, ErrorState, PageHeader } from "@/blocks/layout";
import { errorMessage, useAppMutation } from "@/blocks/mutation";
import { StatusBadge } from "@/blocks/status";
import { Tabs } from "@/components";
import { showDate } from "@/components/format";
import { useSite } from "@/site/SiteContext";
import { Button } from "@/ui/button";
import { Input } from "@/ui/input";
import { Checkbox } from "@/ui/checkbox";
import { Switch } from "@/ui/switch";
import { Textarea } from "@/ui/textarea";

export interface OperationJob {
  id: string; visit_id: string; date: string; society: string; customer_id: string;
  customer_name: string; vehicle: string; registration: string; crew_name: string | null;
  service: string; status: string; reason: string; note: string; photo_url: string | null;
  outcome: string | null; covered_on: string | null; rescheduled_on: string | null;
  replacement_assigned: boolean | null; replacement_status: string | null;
  resolution_reason: string; resolution_note: string; resolved_by: string | null; resolved_at: string | null;
  /** Derived for the whole visit. A partial visit has some jobs done and some not. */
  visit_outcome?: string; partial?: boolean; planned_services?: string[]; delivered_services?: string[];
  outcome_summary?: string; reported_by?: string | null; reported_at?: string | null;
}
type Reason = { key: string; label: string };
/** The statuses the crew app sets, and the could-not-complete reasons with whether each defers the job. */
type CompletionOptions = { statuses: string[]; reasons: (Reason & { defers: boolean })[] };

const QUEUES = [
  { id: "missed", label: "Missed jobs" },
  { id: "scheduled", label: "Scheduled work" },
  { id: "history", label: "Resolution history" },
] as const;

const shownStatus = (j: OperationJob) => (j.status === "Could not complete" ? "Missed" : j.status);

/** What skipping a job does to the plan, by service (ADM-OPS-01, ADM-CNC-03 to -06). */
function skipEffect(service: string): string {
  return service === "Cleaning-External" ? "Skipping adds one day to the plan and moves unpaid renewal dates."
    : service === "Deep Spa" ? "Skipping does not extend the plan. Handle any refund or rebooking separately."
    : "Skipping loses this Interior service and does not extend the plan.";
}

/** Missed jobs, work to skip by operations, and how each was resolved. */
export function OperationsPage() {
  const site = useSite();
  // The dashboard links here with the queue and a day in the address (A-02).
  const [linked] = useSearchParams();
  const [queue, setQueue] = useState(QUEUES.some((q) => q.id === linked.get("queue")) ? linked.get("queue")! : "missed");
  const [from, setFrom] = useState(linked.get("date_from") ?? "");
  const [to, setTo] = useState(linked.get("date_to") ?? "");
  const [reason, setReason] = useState("");
  const [unresolved, setUnresolved] = useState(false);
  const [openId, setOpenId] = useState<string | null>(null);
  // Jobs picked in the table. A bulk skip acts on the visits of the picked jobs (S-12);
  // a bulk status acts on the picked jobs (P1-3).
  const [picked, setPicked] = useState<string[]>([]);
  const [bulkOpen, setBulkOpen] = useState(false);
  // The jobs for a status change: one from its row, or the picked jobs in bulk.
  const [statusFor, setStatusFor] = useState<{ jobs: OperationJob[]; bulk: boolean } | null>(null);
  const params = new URLSearchParams({ queue });
  if (site.id) params.set("society_id", site.id);
  if (from) params.set("date_from", from);
  if (to) params.set("date_to", to);
  if (reason) params.set("reason_key", reason);
  if (unresolved && queue === "missed") params.set("unresolved", "true");
  const jobs = useQuery({ queryKey: ["operations", params.toString()], queryFn: () => api<OperationJob[]>(`/v1/admin/operations/jobs?${params}`) });
  const reasons = useQuery({ queryKey: ["operations-reasons"], queryFn: () => api<Reason[]>("/v1/admin/operations/reasons") });
  const options = useQuery({ queryKey: ["operations-completion-options"], enabled: queue === "scheduled",
    queryFn: () => api<CompletionOptions>("/v1/admin/operations/completion-options") });
  const open = jobs.data?.find((j) => j.id === openId) ?? null;
  const pickedRows = (jobs.data ?? []).filter((j) => picked.includes(j.id));
  const pickedVisitIds = [...new Set(pickedRows.map((j) => j.visit_id))];

  return (
    <>
      <PageHeader title="Operations" site={site.name || undefined}
                  description="Decide what happens to jobs the crew could not do, and skip work by operations." />
      <Tabs tabs={QUEUES} active={queue} label="Queues" onChange={(q) => { setQueue(q); setOpenId(null); setPicked([]); }}>
        {(jobs.isError || reasons.isError) && <div className="mb-4"><ErrorState message={errorMessage(jobs.error ?? reasons.error)} /></div>}
        <DataTable
          rows={jobs.data}
          loading={jobs.isPending}
          rowKey={(j) => `${j.id}:${j.resolved_at ?? "open"}`}
          onRowClick={(j) => setOpenId(j.id)}
          rowLabel={(j) => `Open ${j.service} for ${j.registration}`}
          toolbar={(
            <div className="flex flex-wrap items-end gap-3">
              <Field label="From date" className="w-44">{(p) => <Input {...p} type="date" value={from} onChange={(e) => setFrom(e.target.value)} />}</Field>
              <Field label="To date" className="w-44">{(p) => <Input {...p} type="date" value={to} onChange={(e) => setTo(e.target.value)} />}</Field>
              <Field label="Failure reason" className="w-56">
                {(p) => <SelectBox {...p} value={reason || NONE} onChange={(v) => setReason(v === NONE ? "" : v)}
                                   choices={[{ value: NONE, label: "All reasons" }, ...(reasons.data ?? []).map((r) => ({ value: r.key, label: r.label }))]} />}
              </Field>
              {queue === "scheduled" && (
                <Button type="button" variant="outline" disabled={pickedRows.length === 0} onClick={() => setStatusFor({ jobs: pickedRows, bulk: true })}>
                  Set status ({pickedRows.length})
                </Button>
              )}
              {queue !== "history" && (
                <Button type="button" variant="destructive" disabled={pickedVisitIds.length === 0} onClick={() => setBulkOpen(true)}>
                  Skip selected ({pickedVisitIds.length})
                </Button>
              )}
              {queue === "missed" && (
                <label className="flex items-center gap-2 pb-2 text-sm">
                  <Switch aria-label="Only Interior/Spa jobs awaiting an outcome" checked={unresolved} onCheckedChange={setUnresolved} />
                  Only Interior and Spa jobs awaiting an outcome
                </label>
              )}
            </div>
          )}
          empty={<EmptyState title="No jobs match these filters" />}
          columns={[
            ...(queue === "history" ? [] : [{ key: "sel", header: "", width: "3rem", cell: (j: OperationJob) => (
              <Checkbox aria-label={`Select ${j.registration} ${j.service}`} checked={picked.includes(j.id)}
                        onCheckedChange={(on) => setPicked((p) => (on ? [...new Set([...p, j.id])] : p.filter((v) => v !== j.id)))} />
            ) }]),
            { key: "date", header: "Date", width: "7rem", cell: (j) => showDate(j.date) },
            { key: "veh", header: "Vehicle", width: "17%", cell: (j) => (
              <div className="min-w-0"><span className="reg block truncate">{j.registration}</span>
                <span className="block truncate text-xs text-muted-foreground">{j.customer_name}</span></div>) },
            { key: "svc", header: "Service", width: "10rem", cell: (j) => j.service },
            { key: "crew", header: "Crew", width: "9rem", cell: (j) => j.crew_name || "Unassigned" },
            { key: "why", header: "Reason", wrap: true, cell: (j) => (j.reason || j.note ? <>{j.reason}{j.reason && j.note ? " · " : ""}<span className="text-muted-foreground">{j.note}</span></> : "-") },
            { key: "status", header: "Status", width: "11rem", wrap: true, cell: (j) => (
              <span className="flex flex-wrap gap-1.5"><StatusBadge status={shownStatus(j)} />{j.partial && <StatusBadge status="Partially Completed" tone="warn" />}{j.resolved_at && <StatusBadge status={j.outcome ?? "Resolved"} tone="ok" />}</span>) },
            { key: "act", header: "", width: queue === "scheduled" ? "11rem" : "6rem", align: "right", cell: (j) => (
              <span className="flex justify-end gap-2">
                {queue === "scheduled" && (
                  <Button size="sm" variant="outline" aria-label={`Set status for ${j.registration} ${j.service}`}
                          onClick={(e) => { e.stopPropagation(); setStatusFor({ jobs: [j], bulk: false }); }}>Set status</Button>
                )}
                <Button size="sm" variant="outline" onClick={() => setOpenId(j.id)}>Open</Button>
              </span>) },
          ]}
        />
      </Tabs>
      {bulkOpen && <BulkSkipDialog visitIds={pickedVisitIds} reasons={reasons.data ?? []} onClose={() => setBulkOpen(false)}
                                   onDone={() => { setBulkOpen(false); setPicked([]); }} />}
      {statusFor && <CompletionDialog jobs={statusFor.jobs} bulk={statusFor.bulk} options={options.data} onClose={() => setStatusFor(null)}
                                      onDone={() => { setStatusFor(null); setPicked([]); }} />}
      {open && <JobDialog key={`${open.id}:${open.resolved_at ?? "open"}`} job={open} reasons={reasons.data ?? []} onClose={() => setOpenId(null)} />}
    </>
  );
}

function JobDialog({ job, reasons, onClose }: { job: OperationJob; reasons: Reason[]; onClose: () => void }) {
  const qc = useQueryClient();
  const confirm = useConfirm();
  const [reason, setReason] = useState("");
  const [note, setNote] = useState("");
  const action = useAppMutation<{ choice: "Skip" | "Reschedule" | "Visit"; done: string }>({
    mutationFn: (v) => api(
      v.choice === "Visit" ? `/v1/admin/operations/visits/${job.visit_id}/skip` : `/v1/admin/operations/jobs/${job.id}/resolve`,
      { method: "POST", body: { ...(v.choice !== "Visit" ? { action: v.choice } : {}), reason, note } }),
    success: (_d, v) => v.done,
    onSuccess: () => { for (const key of ["operations", "board", "needs-scheduling", "payments", "subscriptions"]) void qc.invalidateQueries({ queryKey: [key] }); },
  });
  const resolved = !!job.resolved_at;
  const actionable = !resolved && ["Scheduled", "Could not complete"].includes(job.status);
  const ask = async (choice: "Skip" | "Reschedule" | "Visit", title: string, description: string, label: string, done: string, danger = true) => {
    if (await confirm({ title, description, confirmLabel: label, tone: danger ? "danger" : "default" })) action.mutate({ choice, done });
  };

  return (
    <FormDialog open onOpenChange={(o) => !o && onClose()} title={`${job.service}, ${job.registration}`} size="lg"
                submitLabel="Close" cancelLabel={null} onSubmit={onClose}>
      <DetailList columns={3} items={[
        { label: "Customer", value: <Link to={`/customers/${job.customer_id}`}>{job.customer_name}</Link> },
        { label: "Society", value: job.society },
        { label: "Date", value: showDate(job.date) },
        { label: "Vehicle", value: job.vehicle },
        { label: "Crew", value: job.crew_name || "Unassigned" },
        { label: "Status", value: <StatusBadge status={shownStatus(job)} /> },
        { label: "Crew's reason", value: [job.reason, job.note].filter(Boolean).join(". "), wide: true },
        ...(job.reported_by ? [{ label: "Recorded by", value: `${job.reported_by}${job.reported_at ? `, ${showDate(job.reported_at)}` : ""}` }] : []),
        ...(job.visit_outcome ? [{ label: "Visit outcome", value: job.visit_outcome }] : []),
        ...(job.partial ? [{
          label: "Planned and delivered", wide: true,
          value: `Planned ${(job.planned_services ?? []).join(", ")}. Delivered ${(job.delivered_services ?? []).join(", ") || "none"}.`,
        }] : []),
      ]} />
      {job.partial && job.outcome_summary && <p className="m-0 rounded-md bg-warn/10 px-3 py-2 text-sm">Partially completed visit. {job.outcome_summary}</p>}
      {job.photo_url && (
        <a href={job.photo_url} target="_blank" rel="noreferrer" className="self-start">
          <img src={job.photo_url} alt="Could not complete evidence" className="max-h-48 rounded-lg border object-cover" />
        </a>
      )}
      {job.covered_on && <p className="m-0 rounded-md bg-ok/10 px-3 py-2 text-sm">Covered by the next day's regular Exterior service on {showDate(job.covered_on)}. No extra job or plan extension is needed.</p>}
      {job.rescheduled_on && <p className="m-0 text-sm">Rescheduled on {showDate(job.rescheduled_on)} · {job.replacement_assigned ? "Assigned" : "Needs scheduling"} · {job.replacement_status}</p>}
      {resolved && (
        <div className="rounded-lg border bg-muted/40 p-3 text-sm">
          <p className="m-0 font-medium">{job.outcome}</p>
          <p className="m-0 text-muted-foreground">{[job.resolution_reason, job.resolution_note].filter(Boolean).join(". ")} · {job.resolved_by} · {showDate(job.resolved_at)}</p>
        </div>
      )}
      {actionable && (
        <section className="flex flex-col gap-4 border-t pt-4">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Field label="Operations reason" optional>
              {(p) => <SelectBox {...p} value={reason || NONE} onChange={(v) => setReason(v === NONE ? "" : v)}
                                 choices={[{ value: NONE, label: "No reason selected" }, ...reasons.map((r) => ({ value: r.label, label: r.label }))]} />}
            </Field>
            <Field label="Outcome note" optional className="sm:col-span-2">
              {(p) => <Textarea {...p} rows={2} maxLength={2000} value={note} onChange={(e) => setNote(e.target.value)} />}
            </Field>
          </div>
          <p className="m-0 text-sm text-muted-foreground">{skipEffect(job.service)}</p>
          <div className="flex flex-wrap gap-2">
            <BusyButton type="button" variant="destructive" busy={action.isPending}
                        onClick={() => void ask("Skip", `Skip ${job.service} for ${job.registration}?`, skipEffect(job.service), "Skip job", "Job skipped by operations.")}>
              Skip job by operations
            </BusyButton>
            {job.status === "Could not complete" && job.service !== "Cleaning-External" && (
              <BusyButton type="button" variant="outline" busy={action.isPending}
                          onClick={() => void ask("Reschedule", "Reschedule for the next day?", "A new job goes into the next day's schedule, assigned automatically or to Needs scheduling.", "Reschedule", "Rescheduled for the next day.", false)}>
                Reschedule for next day
              </BusyButton>
            )}
            {job.status === "Scheduled" && (
              <BusyButton type="button" variant="outline" busy={action.isPending}
                          onClick={() => void ask("Visit", "Skip the rest of this visit?", `Every remaining job of ${job.registration}'s visit on ${showDate(job.date)} is skipped by operations.`, "Skip remaining jobs", "Remaining jobs skipped.")}>
                Skip remaining jobs on this visit
              </BusyButton>
            )}
          </div>
        </section>
      )}
    </FormDialog>
  );
}

/**
 * P1-3: set the completion status of one scheduled job, or of the picked jobs. Not completed
 * needs a reason and a remark (ADM-CNC-07). A deferring reason is Deferred and any other reason
 * is Could not complete, as for the crew. Works on a Draft or a Frozen schedule.
 */
function CompletionDialog({ jobs, bulk, options, onClose, onDone }: {
  jobs: OperationJob[]; bulk: boolean; options: CompletionOptions | undefined; onClose: () => void; onDone: () => void;
}) {
  const qc = useQueryClient();
  const [status, setStatus] = useState("");
  const [reason, setReason] = useState("");
  const [note, setNote] = useState("");
  const notCompleted = status !== "" && status !== "Completed";
  // Deferred takes only the reasons that defer the job; Could not complete takes the others.
  const reasonChoices = (options?.reasons ?? []).filter((r) => (status === "Deferred" ? r.defers : !r.defers));
  const valid = status !== "" && (!notCompleted || (reason !== "" && note.trim() !== ""));
  const label = bulk ? `${jobs.length} jobs` : `${jobs[0].service}, ${jobs[0].registration}`;
  const save = useAppMutation<void, unknown>({
    mutationFn: () => {
      const body = { status, ...(notCompleted ? { reason_key: reason, note: note.trim() } : {}) };
      return !bulk
        ? api(`/v1/admin/operations/jobs/${jobs[0].id}/completion`, { method: "POST", body })
        : api("/v1/admin/operations/bulk-completion", { method: "POST", body: { ...body, job_ids: jobs.map((j) => j.id) } });
    },
    pending: "Saving…",
    success: `${label} set to ${status}.`,
    onSuccess: () => { for (const key of ["operations", "board", "needs-scheduling"]) void qc.invalidateQueries({ queryKey: [key] }); onDone(); },
  });
  return (
    <FormDialog open onOpenChange={(o) => !o && onClose()} title={`Set status, ${label}`} size="md"
                submitLabel="Save status" busy={save.isPending} disabled={!valid}
                description="A job that is not completed goes to the Missed list until the admin decides what happens to it."
                onSubmit={() => save.mutate()}>
      <Field label="Completion status">
        {(p) => <SelectBox {...p} value={status || NONE} onChange={(v) => { setStatus(v === NONE ? "" : v); setReason(""); }}
                           choices={[{ value: NONE, label: "Choose a status" }, ...(options?.statuses ?? []).map((s) => ({ value: s, label: s }))]} />}
      </Field>
      {notCompleted && (
        <>
          <Field label="Reason">
            {(p) => <SelectBox {...p} value={reason || NONE} onChange={(v) => setReason(v === NONE ? "" : v)}
                               choices={[{ value: NONE, label: "Choose a reason" }, ...reasonChoices.map((r) => ({ value: r.key, label: r.label }))]} />}
          </Field>
          <Field label="Remark">
            {(p) => <Textarea {...p} rows={2} maxLength={2000} value={note} onChange={(e) => setNote(e.target.value)} />}
          </Field>
        </>
      )}
    </FormDialog>
  );
}

/** S-12: skip every open job of the chosen visits for a disruption. One reason, one confirm. */
function BulkSkipDialog({ visitIds, reasons, onClose, onDone }: {
  visitIds: string[]; reasons: Reason[]; onClose: () => void; onDone: () => void;
}) {
  const qc = useQueryClient();
  const confirm = useConfirm();
  const [reason, setReason] = useState("");
  const [note, setNote] = useState("");
  const skip = useAppMutation<void, { visits_skipped: number; jobs_skipped: number }>({
    mutationFn: () => api("/v1/admin/operations/bulk-skip", { method: "POST", body: { visit_ids: visitIds, reason, note } }),
    pending: "Skipping…",
    success: (r) => `${r.visits_skipped} ${r.visits_skipped === 1 ? "visit" : "visits"} skipped (${r.jobs_skipped} jobs).`,
    onSuccess: () => { for (const key of ["operations", "board", "needs-scheduling"]) void qc.invalidateQueries({ queryKey: [key] }); onDone(); },
  });
  const submit = async () => {
    if (await confirm({
      title: `Skip ${visitIds.length} ${visitIds.length === 1 ? "visit" : "visits"}?`,
      description: "Every open job on these visits is skipped by operations and customers are told. Nothing is added to the plan. This cannot be undone here.",
      confirmLabel: "Skip visits", tone: "danger",
    })) skip.mutate();
  };
  return (
    <FormDialog open onOpenChange={(o) => !o && onClose()} title="Skip selected visits" size="md" danger
                submitLabel="Skip visits" busy={skip.isPending} disabled={!reason}
                description="Use this when something stops work for many cars, such as a water cut or heavy rain."
                onSubmit={() => void submit()}>
      <Field label="Reason">
        {(p) => <SelectBox {...p} value={reason || NONE} onChange={(v) => setReason(v === NONE ? "" : v)}
                           choices={[{ value: NONE, label: "Choose a reason" }, ...reasons.map((r) => ({ value: r.label, label: r.label }))]} />}
      </Field>
      <Field label="Note" optional>
        {(p) => <Textarea {...p} rows={2} maxLength={2000} value={note} onChange={(e) => setNote(e.target.value)} />}
      </Field>
    </FormDialog>
  );
}
