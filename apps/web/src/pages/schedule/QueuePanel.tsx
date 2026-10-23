import { ArrowDown, ArrowUp, Lock, LockOpen } from "lucide-react";
import { useState } from "react";

import { api } from "@/api/client";
import { Field } from "@/blocks/fields";
import { FormDialog } from "@/blocks/FormDialog";
import { Panel } from "@/blocks/layout";
import { useAppMutation } from "@/blocks/mutation";
import { showDate } from "@/components/format";
import { Button } from "@/ui/button";
import { Textarea } from "@/ui/textarea";

import { serviceCode } from "./Board";
import type { AdminJob, SchedulingCrew } from "./api";

const CLOSED = ["Completed", "Could not complete", "Skipped"];

/** A crew member's jobs for the day in queue order (S-13). */
export function queueOf(jobs: AdminJob[], crewId: string): AdminJob[] {
  return jobs
    .filter((j) => j.crew_id === crewId && j.status !== "Skipped")
    .sort((a, b) => (a.sequence ?? 1e6) - (b.sequence ?? 1e6) || (a.start_minute ?? 0) - (b.start_minute ?? 0));
}

type Pending =
  | { kind: "move"; crew: SchedulingCrew; ordered: string[]; label: string }
  | { kind: "unlock"; job: AdminJob };

/**
 * The crew's ordered queue for the day, with Move up, Move down and Unlock
 * (S-13, C-04, B-06). Each change needs a reason; it is audited and the crew
 * member is told, so the page says so after saving.
 */
export function QueuePanel({ crew, jobs, date, refresh }: {
  crew: SchedulingCrew[]; jobs: AdminJob[]; date: string; refresh: () => unknown;
}) {
  const [pending, setPending] = useState<Pending | null>(null);
  const [reason, setReason] = useState("");
  const dayJobs = jobs.filter((j) => j.date === date);

  const save = useAppMutation<Pending, { message: string }>({
    mutationFn: (p) => (p.kind === "move"
      ? api("/v1/admin/scheduling/queue/reorder", {
        method: "POST",
        body: { crew_id: p.crew.id, date, ordered_job_ids: p.ordered, reason: reason.trim() },
      })
      : api(`/v1/admin/scheduling/jobs/${p.job.id}/unlock`, { method: "POST", body: { reason: reason.trim() } })),
    pending: "Saving the queue change…",
    success: (_d, p) => (p.kind === "move"
      ? `${p.label} The change is in the audit log and ${p.crew.name} was told.`
      : `${p.job.registration} unlocked. The change is in the audit log and ${p.job.crew_name ?? "the crew member"} was told.`),
    onSuccess: () => { setPending(null); setReason(""); void refresh(); },
  });

  const move = (member: SchedulingCrew, queue: AdminJob[], from: number, by: -1 | 1) => {
    const ids = queue.map((j) => j.id);
    [ids[from], ids[from + by]] = [ids[from + by], ids[from]];
    const j = queue[from];
    setReason("");
    setPending({ kind: "move", crew: member, ordered: ids, label: `${j.registration} moved ${by < 0 ? "up" : "down"}.` });
  };

  const members = crew.filter((c) => queueOf(dayJobs, c.id).length > 0);
  const title = pending?.kind === "unlock"
    ? `Unlock ${pending.job.registration}?`
    : pending ? `Change ${pending.crew.name}'s queue?` : "";

  return (
    <Panel title={`Crew queue for ${showDate(date)}`}
           description="Crew finish jobs in this order. Move a job up or down, or unlock one to let the crew do it out of turn. Every change needs a reason and the crew member is told.">
      {members.length === 0 ? <p className="m-0 text-sm text-muted-foreground">No jobs are assigned to crew on this day.</p> : (
        <div className="flex flex-col gap-5">
          {members.map((member) => {
            const queue = queueOf(dayJobs, member.id);
            const firstOpen = queue.find((j) => !CLOSED.includes(j.status));
            return (
              <section key={member.id} aria-label={`Queue of ${member.name}`}>
                <h3 className="m-0 mb-2 text-sm font-medium">{member.name}</h3>
                <ol className="m-0 flex list-none flex-col gap-1 p-0">
                  {queue.map((j, i) => {
                    const open = j.status === "Scheduled";
                    const locked = open && firstOpen !== undefined && firstOpen.id !== j.id && !j.queue_unlocked;
                    return (
                      <li key={j.id} className="flex flex-wrap items-center gap-3 rounded-md border px-3 py-2 text-sm">
                        <span className="w-6 text-muted-foreground">{i + 1}</span>
                        <span className="reg">{j.registration}</span>
                        <span>{serviceCode(j.service)}</span>
                        <span className="text-muted-foreground">{j.start_time ?? ""}</span>
                        <span>{j.status}</span>
                        {locked && <span className="inline-flex items-center gap-1 text-muted-foreground"><Lock className="size-3.5" aria-hidden />Locked</span>}
                        {open && j.queue_unlocked && <span className="inline-flex items-center gap-1 text-muted-foreground"><LockOpen className="size-3.5" aria-hidden />Unlocked by admin</span>}
                        <span className="ml-auto flex gap-1">
                          <Button size="icon-sm" variant="outline" aria-label={`Move ${j.registration} up`}
                                  disabled={!open || i === 0} onClick={() => move(member, queue, i, -1)}>
                            <ArrowUp aria-hidden />
                          </Button>
                          <Button size="icon-sm" variant="outline" aria-label={`Move ${j.registration} down`}
                                  disabled={!open || i === queue.length - 1} onClick={() => move(member, queue, i, 1)}>
                            <ArrowDown aria-hidden />
                          </Button>
                          {locked && (
                            <Button size="sm" variant="outline" aria-label={`Unlock ${j.registration}`}
                                    onClick={() => { setReason(""); setPending({ kind: "unlock", job: j }); }}>
                              <LockOpen aria-hidden />Unlock
                            </Button>
                          )}
                        </span>
                      </li>
                    );
                  })}
                </ol>
              </section>
            );
          })}
        </div>
      )}
      <FormDialog
        open={pending !== null}
        onOpenChange={(o) => { if (!o) setPending(null); }}
        title={title}
        description="Say why. The reason, the old and new order and your name are recorded, and the crew member gets a notification."
        submitLabel={pending?.kind === "unlock" ? "Unlock job" : "Save new order"}
        busy={save.isPending}
        disabled={reason.trim() === ""}
        onSubmit={() => { if (pending) save.mutate(pending); }}
      >
        <Field label="Reason">
          {(p) => <Textarea {...p} rows={3} value={reason} onChange={(e) => setReason(e.target.value)} />}
        </Field>
      </FormDialog>
    </Panel>
  );
}
