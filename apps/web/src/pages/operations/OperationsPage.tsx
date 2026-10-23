import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";

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
  const [queue, setQueue] = useState("missed");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [reason, setReason] = useState("");
  const [unresolved, setUnresolved] = useState(false);
  const [openId, setOpenId] = useState<string | null>(null);
  const params = new URLSearchParams({ queue });
  if (site.id) params.set("society_id", site.id);
  if (from) params.set("date_from", from);
  if (to) params.set("date_to", to);
  if (reason) params.set("reason_key", reason);
  if (unresolved && queue === "missed") params.set("unresolved", "true");
  const jobs = useQuery({ queryKey: ["operations", params.toString()], queryFn: () => api<OperationJob[]>(`/v1/admin/operations/jobs?${params}`) });
  const reasons = useQuery({ queryKey: ["operations-reasons"], queryFn: () => api<Reason[]>("/v1/admin/operations/reasons") });
  const open = jobs.data?.find((j) => j.id === openId) ?? null;

  return (
    <>
      <PageHeader title="Operations" site={site.name || undefined}
                  description="Decide what happens to jobs the crew could not do, and skip work by operations." />
      <Tabs tabs={QUEUES} active={queue} label="Queues" onChange={(q) => { setQueue(q); setOpenId(null); }}>
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
            { key: "date", header: "Date", width: "7rem", cell: (j) => showDate(j.date) },
            { key: "veh", header: "Vehicle", width: "17%", cell: (j) => (
              <div className="min-w-0"><span className="reg block truncate">{j.registration}</span>
                <span className="block truncate text-xs text-muted-foreground">{j.customer_name}</span></div>) },
            { key: "svc", header: "Service", width: "10rem", cell: (j) => j.service },
            { key: "crew", header: "Crew", width: "9rem", cell: (j) => j.crew_name || "Unassigned" },
            { key: "why", header: "Reason", wrap: true, cell: (j) => (j.reason || j.note ? <>{j.reason}{j.reason && j.note ? " · " : ""}<span className="text-muted-foreground">{j.note}</span></> : "-") },
            { key: "status", header: "Status", width: "11rem", wrap: true, cell: (j) => (
              <span className="flex flex-wrap gap-1.5"><StatusBadge status={shownStatus(j)} />{j.partial && <StatusBadge status="Partially Completed" tone="warn" />}{j.resolved_at && <StatusBadge status={j.outcome ?? "Resolved"} tone="ok" />}</span>) },
            { key: "act", header: "", width: "6rem", align: "right", cell: (j) => <Button size="sm" variant="outline" onClick={() => setOpenId(j.id)}>Open</Button> },
          ]}
        />
      </Tabs>
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
