import { useQuery } from "@tanstack/react-query";
import { ArrowLeftRight, Sparkles } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";

import { api } from "@/api/client";
import { useConfirm } from "@/blocks/confirm";
import { DataTable } from "@/blocks/DataTable";
import { Field, SelectBox } from "@/blocks/fields";
import { BusyButton } from "@/blocks/FormDialog";
import { EmptyState, ErrorState, Panel } from "@/blocks/layout";
import { errorMessage, useAppMutation } from "@/blocks/mutation";
import { showDate } from "@/components/format";
import { Button } from "@/ui/button";
import { Checkbox } from "@/ui/checkbox";

import { serviceCode } from "./Board";
import { hhmm, weekday, type Board, type PendingAddon } from "./api";

interface CutoffRequest {
  id: string; registration: string; customer_name: string; date: string; cutoff_time: string;
  old_cutoff: string | null; crew_name: string | null; start_time: string | null;
}
interface Suggestions { fingerprint: string; items: { job_id: string; crew_id: string; start_minute: number; date: string; service: string }[] }

const dayText = (iso: string) => `${weekday(iso)} ${showDate(iso)}`;

/** Cutoff changes customers made after the freeze (ADM-SCH-22, -23). */
export function CutoffRequests({ refresh }: { refresh: () => unknown }) {
  const confirm = useConfirm();
  const requests = useQuery({ queryKey: ["cutoff-requests"], queryFn: () => api<CutoffRequest[]>("/v1/admin/scheduling/cutoff-requests") });
  const handle = useAppMutation<{ r: CutoffRequest; apply: boolean }>({
    mutationFn: ({ r, apply }) => api(`/v1/admin/scheduling/cutoff-requests/${r.id}/handle`, { method: "POST", body: { apply } }),
    pending: (v) => (v.apply ? "Applying the new cutoff…" : "Rejecting the request…"),
    success: (_d, v) => (v.apply ? `${v.r.registration}: cutoff ${v.r.cutoff_time} applied and scheduled.` : `${v.r.registration}: request rejected.`),
    invalidate: [["cutoff-requests"]],
    onSuccess: () => void refresh(),
  });
  const ask = async (r: CutoffRequest, apply: boolean) => {
    if (await confirm(apply ? {
      title: `Apply the new cutoff for ${r.registration}?`,
      description: `The cutoff becomes ${r.cutoff_time} and the visit on ${dayText(r.date)} is scheduled to fit it.`,
      confirmLabel: "Apply and schedule",
    } : {
      title: `Reject the request for ${r.registration}?`,
      description: `The cutoff stays ${r.old_cutoff ?? "as it is"}. The assigned visit does not move.`,
      confirmLabel: "Reject", tone: "danger",
    })) handle.mutate({ r, apply });
  };

  return (
    <Panel title="Cutoff change requests"
           description="Unfreeze the schedule before applying a request, review the result, then freeze again."
           bodyClassName="p-0">
      {requests.error ? <div className="p-4"><ErrorState message={errorMessage(requests.error)} /></div> : (
        <DataTable
          className="[&>div]:rounded-none [&>div]:border-0"
          rows={requests.data}
          loading={requests.isPending}
          rowKey={(r) => r.id}
          empty={<p className="text-sm text-muted-foreground">No pending cutoff requests.</p>}
          columns={[
            { key: "c", header: "Customer", width: "13rem", cell: (r) => r.customer_name },
            { key: "v", header: "Vehicle", width: "9rem", cell: (r) => <span className="reg text-[0.8125rem]">{r.registration}</span> },
            { key: "d", header: "Date", width: "9rem", cell: (r) => dayText(r.date) },
            { key: "t", header: "Cutoff", width: "9rem", cell: (r) => <>{r.old_cutoff ?? "-"} <span aria-hidden>→</span><span className="sr-only">to</span> <strong>{r.cutoff_time}</strong></> },
            { key: "a", header: "Assigned now", cell: (r) => (r.crew_name ? `${r.crew_name} at ${r.start_time}` : "Not assigned") },
            { key: "x", header: "", width: "15rem", align: "right", cell: (r) => (
              <div className="flex justify-end gap-2">
                <Button size="sm" disabled={handle.isPending} onClick={() => void ask(r, true)}>Apply and schedule</Button>
                <Button size="sm" variant="outline" disabled={handle.isPending} onClick={() => void ask(r, false)}>Reject</Button>
              </div>
            ) },
          ]}
        />
      )}
    </Panel>
  );
}

/** Add-ons whose date has no schedule yet; they are placed when that period is run. */
export function PendingAddons({ addons }: { addons: PendingAddon[] }) {
  if (addons.length === 0) return null;
  return (
    <Panel title="Add-ons awaiting a scheduling period" description="They are placed when the scheduler runs for their date." bodyClassName="p-0">
      <DataTable
        className="[&>div]:rounded-none [&>div]:border-0"
        rows={addons}
        rowKey={(b) => b.id}
        empty={null}
        columns={[
          { key: "v", header: "Vehicle", width: "12rem", cell: (b) => <span className="reg text-[0.8125rem]">{b.registration}</span> },
          { key: "d", header: "Date", width: "10rem", cell: (b) => dayText(b.date) },
          { key: "f", header: "Finish by", cell: (b) => b.finish_by },
          { key: "a", header: "", width: "10rem", align: "right", cell: () => <Button size="sm" variant="link" asChild><Link to="/addons">Manage booking</Link></Button> },
        ]}
      />
    </Panel>
  );
}

/** Swap two jobs, or apply the scheduler's suggested improvements, in a draft (ADM-SCH-13, -15). */
export function DraftImprovements({ board, refresh }: { board: Board | null; refresh: () => unknown }) {
  const confirm = useConfirm();
  const [first, setFirst] = useState("");
  const [second, setSecond] = useState("");
  const [preview, setPreview] = useState<Suggestions | null>(null);
  const [selected, setSelected] = useState<string[]>([]);
  const swap = useAppMutation<void>({
    mutationFn: () => api("/v1/admin/scheduling/jobs/swap", { method: "POST", body: { first_job_id: first, second_job_id: second } }),
    pending: "Swapping…", success: "The two jobs swapped crew and times.",
    onSuccess: () => { setFirst(""); setSecond(""); setPreview(null); void refresh(); },
  });
  const suggest = useAppMutation<void, Suggestions>({
    mutationFn: () => api(`/v1/admin/scheduling/schedules/${board!.schedule.id}/suggestions`),
    pending: "Looking for improvements…",
    success: (r) => (r.items.length === 0 ? "No improvements found." : `${r.items.length} ${r.items.length === 1 ? "improvement" : "improvements"} suggested.`),
    onSuccess: (r) => { setPreview(r); setSelected([]); },
  });
  const apply = useAppMutation<void>({
    mutationFn: () => api(`/v1/admin/scheduling/schedules/${board!.schedule.id}/suggestions/apply`, {
      method: "POST", body: { fingerprint: preview!.fingerprint, job_ids: selected },
    }),
    pending: "Applying…", success: "The selected improvements are applied.",
    onSuccess: () => { setPreview(null); setSelected([]); void refresh(); },
  });

  if (!board) {
    return <EmptyState title="No draft yet">Run the scheduler to make a draft first.</EmptyState>;
  }
  const editable = board.schedule.status === "Draft";
  const jobs = board.jobs.filter((j) => j.status === "Scheduled" && j.crew_id);
  const jobChoice = (j: (typeof jobs)[number]) => ({
    value: j.id, label: `${dayText(j.date)} · ${j.start_time ?? ""} · ${serviceCode(j.service)} ${j.registration} · ${j.crew_name ?? ""}`,
  });
  const name = (id: string) => board.jobs.find((j) => j.id === id)?.registration ?? "";

  const askSwap = async () => {
    if (await confirm({
      title: "Swap these two jobs?",
      description: `${name(first)} and ${name(second)} exchange their crew members and start times.`,
      confirmLabel: "Swap crew and times",
    })) swap.mutate();
  };
  const askApply = async () => {
    if (await confirm({
      title: `Apply ${selected.length} ${selected.length === 1 ? "improvement" : "improvements"}?`,
      description: "The chosen jobs move to the suggested crew member and time. Other jobs stay where they are.",
      confirmLabel: "Apply selected improvements",
    })) apply.mutate();
  };

  return (
    <div className="flex flex-col gap-6">
      {!editable && (
        <p className="rounded-lg border bg-muted/50 px-4 py-3 text-sm">Unfreeze this schedule to swap work or apply improvements.</p>
      )}
      <Panel title="Swap two jobs" description="The two jobs exchange crew members and start times.">
        <div className="grid grid-cols-1 items-end gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_auto]">
          <Field label="First job">
            {(p) => <SelectBox {...p} value={first} disabled={!editable} onChange={setFirst} choices={jobs.map(jobChoice)} />}
          </Field>
          <Field label="Second job">
            {(p) => <SelectBox {...p} value={second} disabled={!editable || !first} onChange={setSecond}
                               choices={jobs.filter((j) => j.id !== first).map(jobChoice)} />}
          </Field>
          <BusyButton busy={swap.isPending} disabled={!editable || !first || !second} onClick={() => void askSwap()}>
            <ArrowLeftRight aria-hidden /> Swap crew and times
          </BusyButton>
        </div>
      </Panel>

      <Panel title="Suggested improvements" description="Moves that make better use of crew time. Nothing changes until you apply it."
             actions={<BusyButton variant="outline" size="sm" busy={suggest.isPending} disabled={!editable} onClick={() => suggest.mutate()}>
               <Sparkles aria-hidden /> Preview improvements
             </BusyButton>}
             bodyClassName={preview && preview.items.length > 0 ? "p-0" : undefined}>
        {suggest.error ? <ErrorState message={errorMessage(suggest.error)} /> : null}
        {!preview && <p className="text-sm text-muted-foreground">Press Preview improvements to see what could be better.</p>}
        {preview && preview.items.length === 0 && <p className="text-sm text-muted-foreground">No improvements suggested.</p>}
        {preview && preview.items.length > 0 && (
          <>
            <DataTable
              className="[&>div]:rounded-none [&>div]:border-0"
              rows={preview.items}
              rowKey={(i) => i.job_id}
              empty={null}
              onRowClick={(i) => setSelected((s) => (s.includes(i.job_id) ? s.filter((x) => x !== i.job_id) : [...s, i.job_id]))}
              columns={[
                { key: "s", header: "", width: "3rem", cell: (i) => (
                  <Checkbox aria-label={`Apply for ${name(i.job_id)}`} checked={selected.includes(i.job_id)}
                            onCheckedChange={(on) => setSelected((s) => (on ? [...s, i.job_id] : s.filter((x) => x !== i.job_id)))} />
                ) },
                { key: "v", header: "Vehicle", width: "10rem", cell: (i) => <span className="reg text-[0.8125rem]">{name(i.job_id)}</span> },
                { key: "sv", header: "Service", width: "11rem", cell: (i) => i.service },
                { key: "d", header: "Date", width: "9rem", cell: (i) => dayText(i.date) },
                { key: "to", header: "Move to", cell: (i) => `${board.crew.find((c) => c.id === i.crew_id)?.name ?? "-"} at ${hhmm(i.start_minute)}` },
              ]}
            />
            <div className="flex justify-end border-t px-5 py-3">
              <BusyButton busy={apply.isPending} disabled={!editable || selected.length === 0} onClick={() => void askApply()}>
                Apply selected improvements
              </BusyButton>
            </div>
          </>
        )}
      </Panel>
    </div>
  );
}
