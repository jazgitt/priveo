import { useState } from "react";

import { ApiError } from "@/api/client";
import { useConfirm } from "@/blocks/confirm";
import { DataTable } from "@/blocks/DataTable";
import { Field, SelectBox } from "@/blocks/fields";
import { BusyButton } from "@/blocks/FormDialog";
import { Panel } from "@/blocks/layout";
import { useAppMutation } from "@/blocks/mutation";
import { StatusBadge } from "@/blocks/status";
import { showDate } from "@/components/format";
import { Button } from "@/ui/button";
import { Input } from "@/ui/input";

import { useCrewActions, useCrewList, useSocieties, useSocietyHistory, type Crew, type ReleasedJob } from "./api";
import { ReleasedJobs } from "./shared";

function fieldsOf(e: unknown): Record<string, string> {
  return e instanceof ApiError ? e.fields : {};
}

const today = () => new Date().toISOString().slice(0, 10);

/**
 * ADM-CRW-13, ADM-CRW-22: the crew member's society over time. A move starts on
 * a date the admin picks (today or later). Earlier stays are kept exactly as
 * they were. A move that has not happened yet can be cancelled.
 */
export function SocietyPanel({ crew }: { crew: Crew }) {
  const confirm = useConfirm();
  const { moveSociety, cancelMove } = useCrewActions(crew.id);
  const history = useSocietyHistory(crew.id);
  const societies = useSocieties();
  const [target, setTarget] = useState("");
  const [from, setFrom] = useState(today());
  const [mate, setMate] = useState("");
  const [released, setReleased] = useState<ReleasedJob[]>([]);
  const newSociety = useCrewList(target);
  const members = (newSociety.data ?? []).filter((m) => m.role === "Member" && m.active);
  const fe = fieldsOf(moveSociety.error);
  const stays = history.data ?? [];
  // The Trainees paired with this Member move to the new society with them.
  const mates = useCrewList(crew.society_id);
  const trainees = crew.role === "Member"
    ? (mates.data ?? []).filter((m) => m.role === "Trainee" && m.paired_member_id === crew.id)
    : [];
  const pending = stays.find((s) => s.pending);
  const needsMate = crew.role === "Trainee";
  const targetName = societies.data?.find((s) => s.id === target)?.name ?? "";

  const move = useAppMutation<void, { released_jobs: ReleasedJob[] }>({
    mutationFn: () => moveSociety.mutateAsync({ society_id: target, effective_from: from, paired_member_id: needsMate ? mate : null }),
    pending: "Moving…", success: from === today() ? "Moved." : "The move is set.",
    onSuccess: (r) => { setReleased(r.released_jobs); setTarget(""); },
  });
  const cancel = useAppMutation<string>({
    mutationFn: (id) => cancelMove.mutateAsync(id), pending: "Cancelling the move…", success: "The move is cancelled.",
  });

  return (
    <div className="flex flex-col gap-6">
      <Panel title="Society over time" bodyClassName="p-0"
             description={`Now in ${crew.society}. A move starts on the date you choose and earlier stays are never changed.`}>
        <DataTable
          className="[&>div]:rounded-none [&>div]:border-0"
          rows={stays}
          loading={history.isPending}
          rowKey={(s) => s.id}
          empty={<p className="text-sm text-muted-foreground">No history yet.</p>}
          columns={[
            { key: "society", header: "Society", cell: (s) => s.society },
            { key: "from", header: "From", width: "9rem", cell: (s) => showDate(s.effective_from) },
            { key: "to", header: "To", width: "9rem", cell: (s) => (s.effective_to ? showDate(s.effective_to) : "now") },
            { key: "st", header: "", width: "16rem", align: "right", cell: (s) => (s.pending ? (
              <span className="flex items-center justify-end gap-2">
                <StatusBadge status="Starts later" tone="warn" />
                <Button size="sm" variant="ghost" className="text-destructive" disabled={cancel.isPending} aria-label={`Cancel the move to ${s.society}`}
                        onClick={async () => {
                          if (await confirm({ title: `Cancel the move to ${s.society}?`, description: `${crew.name} stays in ${crew.society}.`, confirmLabel: "Cancel move", tone: "danger" })) cancel.mutate(s.id);
                        }}>Cancel move</Button>
              </span>) : null) },
          ]}
        />
      </Panel>

      <Panel title="Move to another society" description="From the start date the crew member's open jobs in the old society go to Needs scheduling.">
        {crew.role === "Member" && (
          <p role="note" className="mt-0 mb-4 rounded-md bg-muted px-3 py-2 text-sm">
            If Trainees are assigned to this Member, their society is updated too: they move to the new society on the same date and stay paired with this Member.
            {trainees.length > 0 && <> Trainees who will move: {trainees.map((t) => t.name).join(", ")}.</>}
          </p>
        )}
        {pending ? (
          <p className="m-0 text-sm text-muted-foreground">A move to {pending.society} starts on {showDate(pending.effective_from)}. Cancel it to set a different one.</p>
        ) : (
          <form className="grid grid-cols-1 items-end gap-4 sm:grid-cols-[minmax(0,14rem)_11rem_minmax(0,14rem)_auto]"
                onSubmit={async (e) => {
                  e.preventDefault();
                  if (await confirm({
                    title: `Move ${crew.name} to ${targetName}?`,
                    description: `From ${showDate(from)}. Open jobs in ${crew.society} from that date go to Needs scheduling.`,
                    confirmLabel: "Move crew member",
                  })) move.mutate();
                }}>
            <Field label="Move to society" error={fe.society_id}>
              {(p) => <SelectBox {...p} value={target} onChange={(v) => { setTarget(v); setMate(""); }}
                                 choices={(societies.data ?? []).filter((s) => s.active && s.id !== crew.society_id).map((s) => ({ value: s.id, label: s.name }))} />}
            </Field>
            <Field label="Starts on" error={fe.effective_from}>
              {(p) => <Input {...p} type="date" value={from} min={today()} onChange={(e) => setFrom(e.target.value)} />}
            </Field>
            {needsMate && target !== "" ? (
              <Field label="Paired Member in the new society" error={fe.paired_member_id}>
                {(p) => <SelectBox {...p} value={mate} onChange={setMate} choices={members.map((m) => ({ value: m.id, label: m.name }))} />}
              </Field>
            ) : <span />}
            <BusyButton type="submit" busy={move.isPending} disabled={target === "" || from === "" || (needsMate && mate === "")}>Move crew member</BusyButton>
          </form>
        )}
        <ReleasedJobs jobs={released} />
      </Panel>
    </div>
  );
}
