import { useQuery } from "@tanstack/react-query";
import { RefreshCw } from "lucide-react";
import { useState } from "react";

import { api } from "@/api/client";
import { DataTable } from "@/blocks/DataTable";
import { useConfirm } from "@/blocks/confirm";
import { EmptyState, ErrorState, PageHeader } from "@/blocks/layout";
import { errorMessage, useAppMutation } from "@/blocks/mutation";
import { StatusBadge, type Tone } from "@/blocks/status";
import { showDateTime } from "@/components/format";
import { Button } from "@/ui/button";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/ui/sheet";
import { Switch } from "@/ui/switch";

export interface CronRun {
  id: string;
  trigger: string;
  started_at: string;
  finished_at: string | null;
  status: string;
  duration_ms: number | null;
  what_it_did: string;
  error: string;
}

export interface CronJob {
  job: string;
  label: string;
  purpose: string;
  schedule_utc: string;
  schedule_ist: string;
  scheduled_on_vercel: boolean;
  enabled: boolean;
  status: string;
  last_run: CronRun | null;
  purpose_achieved: boolean | null;
  purpose_achieved_text: string;
}

const base = "/v1/admin/operations/cron";
const TONES: Record<string, Tone> = {
  Success: "ok", "Did nothing": "neutral", Failed: "error", "Timed out": "error", Late: "warn",
  Skipped: "neutral", Disabled: "neutral", "Never run": "neutral", Running: "info",
};

/** What stops when each job is switched off, in plain words. */
const STOPS: Record<string, string> = {
  "payments-daily": "New payments will not be made, late payments will not be marked Over due and no subscription will become Inactive.",
  "complaints-overdue": "Admins will not be alerted about complaints waiting over 4 hours and queued alert emails will not be sent.",
  "freeze-due": "Draft schedules will not freeze by themselves, so crew will not see their jobs until an admin freezes each schedule.",
  "automatic-planning": "No schedule draft will be made automatically. Plan each society by hand.",
  "renewal-reminders": "Customers will not get renewal reminders. A missed day is not made up.",
  "checkin-notify": "Customers will not get the monthly check-in reminder. A missed day is not made up.",
  "mani-retention": "Old Mani chats and audit rows will not be deleted.",
};

function RunHistory({ job, onClose }: { job: CronJob | null; onClose: () => void }) {
  const runs = useQuery({
    queryKey: ["cron-runs", job?.job],
    queryFn: () => api<CronRun[]>(`${base}/${job!.job}/runs?limit=20`),
    enabled: job !== null,
  });
  return (
    <Sheet open={job !== null} onOpenChange={(o) => { if (!o) onClose(); }}>
      <SheetContent className="w-full overflow-y-auto bg-card sm:max-w-2xl">
        <SheetHeader className="border-b px-6 py-5">
          <SheetTitle>{job?.label}</SheetTitle>
          <SheetDescription>The last 20 runs. Times are India time.</SheetDescription>
        </SheetHeader>
        <div className="px-6 py-4">
          {runs.isError && <ErrorState message="Could not load the runs." onRetry={() => void runs.refetch()} />}
          {runs.data && runs.data.length === 0 && <EmptyState title="No runs recorded yet" />}
          <ul className="m-0 flex list-none flex-col gap-3 p-0">
            {runs.data?.map((r) => (
              <li key={r.id} className="rounded-md border p-3 text-sm">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-medium">{showDateTime(r.started_at)}</span>
                  <StatusBadge status={r.status} tone={TONES[r.status]} />
                  <span className="text-muted-foreground">
                    {r.duration_ms === null ? "" : `${r.duration_ms} ms`} · {r.trigger === "vercel" ? "Scheduled" : "Manual call"}
                  </span>
                </div>
                <p className="m-0 mt-1">{r.what_it_did}</p>
                {r.error && <p className="m-0 mt-1 break-words text-destructive">{r.error}</p>}
              </li>
            ))}
          </ul>
        </div>
      </SheetContent>
    </Sheet>
  );
}

/** Every scheduled job: its switch, its last run and whether it did its work (ADM-OPS-05 to ADM-OPS-09). */
export function ScheduledJobsPage() {
  const confirm = useConfirm();
  const [open, setOpen] = useState<CronJob | null>(null);
  const list = useQuery({ queryKey: ["cron-jobs"], queryFn: () => api<CronJob[]>(base) });
  const toggle = useAppMutation<{ job: CronJob; enabled: boolean }, CronJob>({
    mutationFn: ({ job, enabled }) => api(`${base}/${job.job}`, { method: "PUT", body: { enabled } }),
    success: (r) => `${r.label} is ${r.enabled ? "on" : "off"}.`,
    invalidate: [["cron-jobs"]],
  });

  async function change(job: CronJob, enabled: boolean) {
    if (!enabled) {
      const ok = await confirm({
        title: `Switch off ${job.label}?`,
        description: STOPS[job.job] ?? "This job will stop running.",
        confirmLabel: "Switch off",
        tone: "danger",
      });
      if (!ok) return;
    }
    toggle.mutate({ job, enabled });
  }

  return (
    <>
      <PageHeader title="Scheduled jobs" description="The jobs that run by themselves each day. Switch one off to stop it."
                  actions={(
                    <Button variant="outline" disabled={list.isFetching} onClick={() => void list.refetch()}>
                      <RefreshCw className={list.isFetching ? "animate-spin" : undefined} aria-hidden /> Refresh
                    </Button>
                  )} />
      {list.isError && <div className="mb-4"><ErrorState message={errorMessage(list.error)} onRetry={() => void list.refetch()} /></div>}
      <DataTable
        rows={list.data}
        loading={list.isLoading}
        rowKey={(j) => j.job}
        onRowClick={setOpen}
        rowLabel={(j) => `Runs of ${j.label}`}
        empty={<EmptyState title="No scheduled jobs" />}
        columns={[
          { key: "job", header: "Job", width: "11rem", wrap: true, cell: (j) => (<><span className="font-medium">{j.label}</span><br /><span className="text-xs text-muted-foreground">{j.job}</span></>) },
          { key: "purpose", header: "Purpose", width: "18rem", wrap: true, cell: (j) => j.purpose },
          { key: "schedule", header: "Schedule (IST)", width: "11rem", wrap: true, cell: (j) => j.schedule_ist },
          {
            key: "state", header: "State", width: "6rem",
            cell: (j) => (
              <span onClick={(e) => e.stopPropagation()} onKeyDown={(e) => e.stopPropagation()}>
                <Switch aria-label={`${j.label} on or off`} checked={j.enabled} disabled={toggle.isPending}
                        onCheckedChange={(on) => void change(j, on)} />
              </span>
            ),
          },
          { key: "last", header: "Last run (IST)", width: "9.5rem", cell: (j) => (j.last_run ? showDateTime(j.last_run.started_at) : "-") },
          { key: "status", header: "Status", width: "7.5rem", cell: (j) => <StatusBadge status={j.status} tone={TONES[j.status]} /> },
          { key: "did", header: "What it did", width: "16rem", wrap: true, cell: (j) => j.last_run?.what_it_did ?? "-" },
          {
            key: "achieved", header: "Purpose achieved", width: "14rem", wrap: true,
            cell: (j) => (j.purpose_achieved === null
              ? <span className="text-muted-foreground">{j.purpose_achieved_text}</span>
              : <span className={j.purpose_achieved ? "text-ok" : "text-destructive"}>{j.purpose_achieved ? "Yes. " : "No. "}{j.purpose_achieved_text}</span>),
          },
        ]}
      />
      <RunHistory job={open} onClose={() => setOpen(null)} />
    </>
  );
}
