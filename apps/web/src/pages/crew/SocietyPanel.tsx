import { useState } from "react";

import { ApiError } from "../../api/client";
import { ApiErrorNote } from "../../components/ApiErrorNote";
import { showDate } from "../../components/format";
import { Button, Card, SelectField, StatusChip, Table, TextField, useToast } from "../../components";
import {
  useCrewActions, useCrewList, useSocieties, useSocietyHistory,
  type Crew, type ReleasedJob,
} from "./api";
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
  const toast = useToast();
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

  return (
    <Card title="Society">
      <p>Society now: <strong>{crew.society}</strong>.</p>
      <p className="muted">
        A move starts on the date you choose and earlier stays are never changed. From that
        date the crew member's open jobs in the old society go to Needs scheduling.
      </p>
      {crew.role === "Member" && (
        <p className="muted" role="note">
          If Trainees are assigned to this Member, their society is updated too: they move to
          the new society on the same date and stay paired with this Member.
          {trainees.length > 0 && <> Trainees who will move: {trainees.map((t) => t.name).join(", ")}.</>}
        </p>
      )}
      <Table rows={stays} rowKey={(s) => s.id} empty="No history yet." columns={[
        { key: "society", header: "Society", render: (s) => s.society },
        { key: "from", header: "From", render: (s) => showDate(s.effective_from) },
        { key: "to", header: "To", render: (s) => (s.effective_to ? showDate(s.effective_to) : "now") },
        { key: "st", header: "", render: (s) => (s.pending
          ? (
            <>
              <StatusChip tone="warn">Starts later</StatusChip>{" "}
              <Button variant="ghost" busy={cancelMove.isPending}
                      aria-label={`Cancel the move to ${s.society}`}
                      onClick={() => cancelMove.mutate(s.id, {
                        onSuccess: () => toast.show("The move is cancelled.", "ok"),
                      })}>
                Cancel move
              </Button>
            </>
          )
          : null) },
      ]} />
      <ApiErrorNote error={cancelMove.error} />
      {pending ? (
        <p className="muted">
          A move to {pending.society} starts on {showDate(pending.effective_from)}. Cancel it to
          set a different one.
        </p>
      ) : (
        <div style={{ display: "flex", flexWrap: "wrap", gap: "0.75rem", alignItems: "flex-end" }}>
          <SelectField label="Move to society" value={target} error={fe.society_id}
                       onChange={(e) => { setTarget(e.target.value); setMate(""); }}>
            <option value="">Choose</option>
            {(societies.data ?? [])
              .filter((s) => s.active && s.id !== crew.society_id)
              .map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
          </SelectField>
          <TextField label="Starts on" type="date" value={from} min={today()}
                     onChange={(e) => setFrom(e.target.value)} error={fe.effective_from} />
          {needsMate && target !== "" && (
            <SelectField label="Paired Member in the new society" value={mate}
                         error={fe.paired_member_id} onChange={(e) => setMate(e.target.value)}>
              <option value="">Choose</option>
              {members.map((m) => <option key={m.id} value={m.id}>{m.name}</option>)}
            </SelectField>
          )}
          <Button busy={moveSociety.isPending}
                  disabled={target === "" || from === "" || (needsMate && mate === "")}
                  onClick={() => moveSociety.mutate(
                    { society_id: target, effective_from: from, paired_member_id: needsMate ? mate : null },
                    { onSuccess: (r) => {
                      setReleased(r.released_jobs);
                      setTarget("");
                      toast.show(from === today() ? "Moved." : "The move is set.", "ok");
                    } })}>
            Move crew member
          </Button>
        </div>
      )}
      <ApiErrorNote error={moveSociety.error} />
      <ReleasedJobs jobs={released} />
    </Card>
  );
}
