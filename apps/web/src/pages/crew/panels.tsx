import { useState, type CSSProperties } from "react";

import { ApiError } from "../../api/client";
import { ApiErrorNote } from "../../components/ApiErrorNote";
import { showDate } from "../../components/format";
import { Button, Card, Dialog, SelectField, TextField, useToast } from "../../components";
import {
  EXCEPTION_KINDS, ROLES, useCrewActions, useCrewList, useSessions,
  type Crew, type CrewException, type CrewPassword, type DayHours, type ReleasedJob,
} from "./api";
import { HoursEditor } from "./HoursEditor";
import { PasswordDialog, ReleasedJobs } from "./shared";

const row: CSSProperties = { display: "flex", flexWrap: "wrap", gap: "0.75rem", alignItems: "flex-end" };

function useMembers(crew: Crew) {
  const list = useCrewList(crew.society_id);
  return (list.data ?? []).filter((m) => m.role === "Member" && m.active && m.id !== crew.id);
}

function fieldsOf(e: unknown): Record<string, string> {
  return e instanceof ApiError ? e.fields : {};
}

/** ADM-CRW-02: name and mobile. The society is changed in the Society panel (ADM-CRW-22). */
export function DetailsPanel({ crew }: { crew: Crew }) {
  const toast = useToast();
  const { edit, unlock } = useCrewActions(crew.id);
  const [name, setName] = useState(crew.name);
  const [mobile, setMobile] = useState(crew.mobile);
  const changed = name.trim() !== crew.name || mobile.trim() !== crew.mobile;
  const fe = fieldsOf(edit.error);
  return (
    <Card title="Details">
      <p className="muted">Society: {crew.society}. To move to another society, use the Society panel below.</p>
      <div style={row}>
        <TextField label="Name" value={name} onChange={(e) => setName(e.target.value)} error={fe.name} />
        <TextField label="Mobile number" value={mobile} onChange={(e) => setMobile(e.target.value)}
                   error={fe.mobile}
                   hint="A new number is the new login ID and signs the crew member out." />
        <Button disabled={!changed} busy={edit.isPending} onClick={() => edit.mutate(
          { name: name.trim(), mobile: mobile.trim() },
          { onSuccess: () => toast.show("Details saved.", "ok") })}>Save details</Button>
      </div>
      <ApiErrorNote error={edit.error} />
      {crew.locked && (
        <p>
          This login is locked after wrong attempts.{" "}
          <Button variant="secondary" busy={unlock.isPending}
                  onClick={() => unlock.mutate(undefined, { onSuccess: () => toast.show("Unlocked.", "ok") })}>
            Unlock
          </Button>
        </p>
      )}
      <ApiErrorNote error={unlock.error} />
    </Card>
  );
}

/** ADM-CRW-03, -16, -19: role change and Trainee pairing. */
export function RolePanel({ crew }: { crew: Crew }) {
  const toast = useToast();
  const { role: setRole, pair } = useCrewActions(crew.id);
  const members = useMembers(crew);
  const [role, setRoleValue] = useState(crew.role);
  const [mate, setMate] = useState(crew.paired_member_id ?? "");
  const [released, setReleased] = useState<ReleasedJob[]>([]);
  const needsMate = role === "Trainee";
  const roleChanged = role !== crew.role;
  const fe = fieldsOf(setRole.error ?? pair.error);

  return (
    <Card title="Role and pairing">
      <p>Role now: <strong>{crew.role}</strong>
        {crew.role === "Trainee" && crew.paired_member ? `, paired with ${crew.paired_member}` : ""}.
      </p>
      <p className="muted">A Trainee adds no capacity and gets the jobs of the paired Member.</p>
      <div style={row}>
        <SelectField label="Role" value={role} onChange={(e) => setRoleValue(e.target.value)} error={fe.role}>
          {ROLES.map((r) => <option key={r}>{r}</option>)}
        </SelectField>
        {needsMate && (
          <SelectField label="Paired Member" value={mate} onChange={(e) => setMate(e.target.value)}
                       error={fe.paired_member_id}>
            <option value="">Choose</option>
            {members.map((m) => <option key={m.id} value={m.id}>{m.name}</option>)}
          </SelectField>
        )}
        {roleChanged && (
          <Button busy={setRole.isPending} disabled={needsMate && mate === ""}
                  onClick={() => setRole.mutate(
                    { role, paired_member_id: needsMate ? mate : null },
                    { onSuccess: (r) => {
                      setReleased(r.released_jobs);
                      toast.show(`Role is now ${r.crew.role}.`, "ok");
                    } })}>
            Change role
          </Button>
        )}
        {!roleChanged && crew.role === "Trainee" && (
          <Button busy={pair.isPending} disabled={mate === "" || mate === crew.paired_member_id}
                  onClick={() => pair.mutate({ paired_member_id: mate },
                    { onSuccess: () => toast.show("Pairing saved.", "ok") })}>
            Change pairing
          </Button>
        )}
      </div>
      <ApiErrorNote error={setRole.error ?? pair.error} />
      <ReleasedJobs jobs={released} />
    </Card>
  );
}

/** ADM-CRW-04, -05: hours for each weekday, applied from today on. */
export function HoursPanel({ crew }: { crew: Crew }) {
  const toast = useToast();
  const { hours: save } = useCrewActions(crew.id);
  const [hours, setHours] = useState<DayHours[]>(crew.working_hours);
  const [released, setReleased] = useState<ReleasedJob[]>([]);
  return (
    <Card title="Working hours">
      <HoursEditor value={hours} onChange={setHours} error={fieldsOf(save.error).working_hours} />
      <p className="muted">A change applies from today on. Jobs that no longer fit go to Needs scheduling.</p>
      <Button busy={save.isPending} onClick={() => save.mutate(hours, {
        onSuccess: (r) => {
          setReleased(r.released_jobs);
          toast.show("Working hours saved.", "ok");
        } })}>Save working hours</Button>
      <ApiErrorNote error={save.error} />
      <ReleasedJobs jobs={released} />
    </Card>
  );
}

/** ADM-CRW-08 to -12: Sick, Leave and Late start, one date or a range. */
export function ExceptionsPanel({ crew }: { crew: Crew }) {
  const toast = useToast();
  const act = useCrewActions(crew.id);
  const [kind, setKind] = useState<string>("Sick");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [start, setStart] = useState("");
  const [released, setReleased] = useState<ReleasedJob[]>([]);
  const [editing, setEditing] = useState<CrewException | null>(null);
  const [eKind, setEKind] = useState("Sick");
  const [eStart, setEStart] = useState("");
  const fe = fieldsOf(act.addException.error);
  const after = (m: string) => ({
    onSuccess: (r: { released_jobs: ReleasedJob[] }) => {
      setReleased(r.released_jobs);
      toast.show(m, "ok");
    },
  });
  const upcoming = crew.exceptions;

  return (
    <Card title="Exceptions">
      {upcoming.length === 0 ? <p className="muted">No upcoming exceptions.</p> : (
        <ul>
          {upcoming.map((x) => (
            <li key={x.id}>
              {showDate(x.date)}: {x.kind}{x.kind === "Late start" ? ` from ${x.start}` : ""}{" "}
              <Button variant="ghost" aria-label={`Edit ${x.date}`}
                      onClick={() => { setEditing(x); setEKind(x.kind); setEStart(x.start); }}>
                Edit
              </Button>
              <Button variant="ghost" aria-label={`Remove ${x.date}`}
                      onClick={() => act.removeException.mutate(x.id, after("Exception removed."))}>
                Remove
              </Button>
            </li>
          ))}
        </ul>
      )}

      <h3>Add an exception</h3>
      <div style={row}>
        <SelectField label="Type" value={kind} onChange={(e) => setKind(e.target.value)} error={fe.kind}>
          {EXCEPTION_KINDS.map((k) => <option key={k}>{k}</option>)}
        </SelectField>
        <TextField label="From date" type="date" value={from} onChange={(e) => setFrom(e.target.value)}
                   error={fe.from_date} />
        <TextField label="To date" type="date" value={to} onChange={(e) => setTo(e.target.value)}
                   error={fe.to_date} hint="Leave empty for one day." />
        {kind === "Late start" && (
          <TextField label="Can start at" type="time" value={start}
                     onChange={(e) => setStart(e.target.value)} error={fe.start} />
        )}
        <Button busy={act.addException.isPending} disabled={!from || (kind === "Late start" && !start)}
                onClick={() => act.addException.mutate(
                  { kind, from_date: from, to_date: to || null, start: kind === "Late start" ? start : "" },
                  { onSuccess: (r) => {
                    setReleased(r.released_jobs);
                    setFrom("");
                    setTo("");
                    toast.show("Exception saved.", "ok");
                  } })}>
          Add exception
        </Button>
      </div>
      <ApiErrorNote error={act.addException.error ?? act.removeException.error} />
      <ReleasedJobs jobs={released} />

      {editing && (
        <Dialog open title={`Edit exception on ${showDate(editing.date)}`}
                onClose={() => setEditing(null)}
                footer={<>
                  <Button variant="secondary" onClick={() => setEditing(null)}>Cancel</Button>
                  <Button busy={act.editException.isPending}
                          disabled={eKind === "Late start" && !eStart}
                          onClick={() => act.editException.mutate(
                            { exId: editing.id, kind: eKind, start: eKind === "Late start" ? eStart : "" },
                            { onSuccess: (r) => {
                              setReleased(r.released_jobs);
                              setEditing(null);
                              toast.show("Exception saved.", "ok");
                            } })}>Save</Button>
                </>}>
          <SelectField label="Edit type" value={eKind} onChange={(e) => setEKind(e.target.value)}>
            {EXCEPTION_KINDS.map((k) => <option key={k}>{k}</option>)}
          </SelectField>
          {eKind === "Late start" && (
            <TextField label="Edit start time" type="time" value={eStart}
                       onChange={(e) => setEStart(e.target.value)} />
          )}
          <ApiErrorNote error={act.editException.error} />
        </Dialog>
      )}
    </Card>
  );
}

/** ADM-CRW-15, -18: deactivate, reactivate and reset the password. */
export function AccountPanel({ crew }: { crew: Crew }) {
  const toast = useToast();
  const act = useCrewActions(crew.id);
  const [released, setReleased] = useState<ReleasedJob[]>([]);
  const [issued, setIssued] = useState<CrewPassword | null>(null);
  const [confirmReset, setConfirmReset] = useState(false);
  const [needsRelease, setNeedsRelease] = useState("");
  const done = (r: { released_jobs: ReleasedJob[] }) => {
    setReleased(r.released_jobs);
    setNeedsRelease("");
    toast.show("Crew member deactivated.", "ok");
  };
  const deactivate = (release_jobs: boolean) => act.deactivate.mutate({ release_jobs }, {
    onSuccess: done,
    onError: (e) => {
      if (e instanceof ApiError && e.status === 409 && e.code === "has_open_jobs") {
        setNeedsRelease(e.message);
      }
    },
  });
  const blocking = act.deactivate.error instanceof ApiError
    && act.deactivate.error.code === "has_open_jobs";

  return (
    <Card title="Account">
      <div style={row}>
        {crew.active ? (
          <Button variant="danger" busy={act.deactivate.isPending} onClick={() => deactivate(false)}>
            Deactivate
          </Button>
        ) : (
          <Button busy={act.reactivate.isPending}
                  onClick={() => act.reactivate.mutate(undefined,
                    { onSuccess: () => toast.show("Crew member reactivated.", "ok") })}>
            Reactivate
          </Button>
        )}
        <Button variant="secondary" onClick={() => setConfirmReset(true)}>Reset password</Button>
      </div>
      {!blocking && <ApiErrorNote error={act.deactivate.error} />}
      <ApiErrorNote error={act.reactivate.error ?? act.resetPassword.error} />
      <ReleasedJobs jobs={released} />

      {needsRelease && (
        <Dialog open title="Open jobs need to be released" onClose={() => setNeedsRelease("")}
                footer={<>
                  <Button variant="secondary" onClick={() => setNeedsRelease("")}>Cancel</Button>
                  <Button variant="danger" busy={act.deactivate.isPending}
                          onClick={() => deactivate(true)}>
                    Send jobs to Needs scheduling and deactivate
                  </Button>
                </>}>
          <p>{needsRelease}</p>
        </Dialog>
      )}

      {confirmReset && (
        <Dialog open title="Reset password" onClose={() => setConfirmReset(false)}
                footer={<>
                  <Button variant="secondary" onClick={() => setConfirmReset(false)}>Cancel</Button>
                  <Button busy={act.resetPassword.isPending}
                          onClick={() => act.resetPassword.mutate(undefined, {
                            onSuccess: (r) => { setConfirmReset(false); setIssued(r); },
                          })}>
                    Reset password
                  </Button>
                </>}>
          <p>The old password stops working at once and every signed-in phone is signed out.</p>
        </Dialog>
      )}
      {issued && <PasswordDialog issued={issued} onDone={() => setIssued(null)} />}
    </Card>
  );
}

/** ADM-CRW-21: signed-in devices. */
export function SessionsPanel({ crew }: { crew: Crew }) {
  const toast = useToast();
  const sessions = useSessions(crew.id);
  const act = useCrewActions(crew.id);
  const when = (iso: string) => `${showDate(iso)} ${iso.slice(11, 16)}`;
  return (
    <Card title="Signed-in devices"
          actions={<Button variant="secondary" disabled={!sessions.data?.length}
                           busy={act.endAll.isPending}
                           onClick={() => act.endAll.mutate(undefined,
                             { onSuccess: (r) => toast.show(`Signed out ${r.ended}.`, "ok") })}>
            Sign out all
          </Button>}>
      {sessions.isPending && <p className="loading">Loading...</p>}
      {sessions.isError && <ApiErrorNote error={sessions.error} />}
      {sessions.data && (sessions.data.length === 0
        ? <p className="muted">No signed-in devices.</p>
        : <ul>{sessions.data.map((s) => (
            <li key={s.id}>
              <strong>{s.device_name || "Unknown device"}</strong> {s.platform || "Unknown platform"} · App {s.app_version || "Unknown version"}<br />
              {s.channel === "web" ? "Web" : "Mobile app"}, signed in {when(s.signed_in_at)},
              last active {when(s.last_active_at)}{" "}
              <Button variant="ghost" busy={act.endSession.isPending}
                      onClick={() => act.endSession.mutate(s.id,
                        { onSuccess: () => toast.show("Signed out.", "ok") })}>
                Sign out
              </Button>
            </li>))}
          </ul>)}
      <ApiErrorNote error={act.endSession.error ?? act.endAll.error} />
    </Card>
  );
}
