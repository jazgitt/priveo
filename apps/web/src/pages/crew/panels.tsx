import { LockOpen, Pencil, Trash2 } from "lucide-react";
import { useState } from "react";

import { ApiError } from "@/api/client";
import { useConfirm } from "@/blocks/confirm";
import { Field, SelectBox } from "@/blocks/fields";
import { BusyButton, FormDialog } from "@/blocks/FormDialog";
import { DetailList, ErrorState, Panel } from "@/blocks/layout";
import { errorMessage, useAppMutation } from "@/blocks/mutation";
import { StatusBadge } from "@/blocks/status";
import { showDate, showDateTime } from "@/components/format";
import { Button } from "@/ui/button";
import { Input } from "@/ui/input";
import { Skeleton } from "@/ui/skeleton";

import {
  EXCEPTION_KINDS, ROLES, useCrewActions, useCrewList, useDefaultHours, useSessions,
  type Crew, type CrewException, type CrewPassword, type DayHours, type ReleasedJob,
} from "./api";
import { HoursEditor } from "./HoursEditor";
import { PasswordDialog, ReleasedJobs } from "./shared";

function useMembers(crew: Crew) {
  const list = useCrewList(crew.society_id);
  return (list.data ?? []).filter((m) => m.role === "Member" && m.active && m.id !== crew.id);
}

function fieldsOf(e: unknown): Record<string, string> {
  return e instanceof ApiError ? e.fields : {};
}

/** Runs one crew action with the Saving / Saved toast, and keeps the jobs it released. */
function useCrewRun(setReleased?: (j: ReleasedJob[]) => void) {
  return useAppMutation<{ go: () => Promise<unknown>; done: string }, unknown>({
    mutationFn: (v) => v.go(),
    success: (_d, v) => v.done,
    onSuccess: (r) => {
      const jobs = (r as { released_jobs?: ReleasedJob[] } | undefined)?.released_jobs;
      if (jobs && setReleased) setReleased(jobs);
    },
  });
}

const kindChoices = EXCEPTION_KINDS.map((k) => ({ value: k, label: k }));

/** ADM-CRW-02: name and mobile. The society is changed in the Society panel (ADM-CRW-22). */
export function DetailsPanel({ crew }: { crew: Crew }) {
  const confirm = useConfirm();
  const { edit, unlock } = useCrewActions(crew.id);
  const run = useCrewRun();
  const [name, setName] = useState(crew.name);
  const [mobile, setMobile] = useState(crew.mobile);
  const changed = name.trim() !== crew.name || mobile.trim() !== crew.mobile;
  const mobileChanged = mobile.trim() !== crew.mobile;
  const fe = fieldsOf(edit.error);
  const save = async () => {
    if (mobileChanged && !await confirm({
      title: "Change the mobile number?",
      description: `${mobile.trim()} becomes ${crew.name}'s login ID, and they are signed out on every phone.`,
      confirmLabel: "Save details",
    })) return;
    run.mutate({ go: () => edit.mutateAsync({ name: name.trim(), mobile: mobile.trim() }), done: "Details saved." });
  };
  return (
    <div className="flex flex-col gap-6">
      <Panel title="Details" description={`Society: ${crew.society}. To move to another society, open the Society tab.`}>
        <form className="grid grid-cols-1 items-end gap-4 sm:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_auto]"
              onSubmit={(e) => { e.preventDefault(); if (changed) void save(); }}>
          <Field label="Name" error={fe.name}>{(p) => <Input {...p} value={name} onChange={(e) => setName(e.target.value)} />}</Field>
          <Field label="Mobile number" error={fe.mobile} hint="A new number is the new login ID and signs the crew member out.">
            {(p) => <Input {...p} inputMode="numeric" value={mobile} onChange={(e) => setMobile(e.target.value)} />}
          </Field>
          <BusyButton type="submit" className="sm:mb-5" disabled={!changed} busy={run.isPending}>Save details</BusyButton>
        </form>
      </Panel>
      {crew.locked && (
        <Panel title="Locked login" description="This login is locked after wrong password attempts.">
          <BusyButton variant="outline" busy={run.isPending} onClick={async () => {
            if (await confirm({ title: `Unlock ${crew.name}?`, description: "They can sign in again with their password.", confirmLabel: "Unlock" })) {
              run.mutate({ go: () => unlock.mutateAsync(), done: "Unlocked." });
            }
          }}><LockOpen aria-hidden /> Unlock</BusyButton>
        </Panel>
      )}
    </div>
  );
}

/** ADM-CRW-03, -16, -19: role change and Trainee pairing. */
export function RolePanel({ crew }: { crew: Crew }) {
  const confirm = useConfirm();
  const { role: setRole, pair } = useCrewActions(crew.id);
  const members = useMembers(crew);
  const [role, setRoleValue] = useState(crew.role);
  const [mate, setMate] = useState(crew.paired_member_id ?? "");
  const [released, setReleased] = useState<ReleasedJob[]>([]);
  const run = useCrewRun(setReleased);
  const needsMate = role === "Trainee";
  const roleChanged = role !== crew.role;
  const fe = fieldsOf(setRole.error ?? pair.error);
  const mateName = members.find((m) => m.id === mate)?.name;

  const changeRole = async () => {
    if (await confirm({
      title: `Make ${crew.name} a ${role}?`,
      description: role === "Trainee"
        ? `A Trainee adds no capacity and gets ${mateName ?? "the paired Member"}'s jobs. ${crew.name}'s own jobs go to Needs scheduling.`
        : "Jobs that no longer fit go to Needs scheduling.",
      confirmLabel: "Change role",
    })) run.mutate({ go: () => setRole.mutateAsync({ role, paired_member_id: needsMate ? mate : null }), done: `Role is now ${role}.` });
  };

  return (
    <Panel title="Role and pairing" description="A Trainee adds no capacity and gets the jobs of the paired Member.">
      <DetailList columns={2} className="mb-5" items={[
        { label: "Role now", value: crew.role },
        { label: "Paired with", value: crew.role === "Trainee" ? crew.paired_member : "Not a Trainee" },
      ]} />
      <div className="grid grid-cols-1 items-end gap-4 sm:grid-cols-[12rem_minmax(0,16rem)_auto]">
        <Field label="Role" error={fe.role}>
          {(p) => <SelectBox {...p} value={role} onChange={setRoleValue} choices={ROLES.map((r) => ({ value: r, label: r }))} />}
        </Field>
        {needsMate ? (
          <Field label="Paired Member" error={fe.paired_member_id} hint={members.length === 0 ? "No active Member in this society." : undefined}>
            {(p) => <SelectBox {...p} value={mate} onChange={setMate} choices={members.map((m) => ({ value: m.id, label: m.name }))} />}
          </Field>
        ) : <span />}
        {roleChanged && (
          <BusyButton busy={run.isPending} disabled={needsMate && mate === ""} onClick={() => void changeRole()}>Change role</BusyButton>
        )}
        {!roleChanged && crew.role === "Trainee" && (
          <BusyButton busy={run.isPending} disabled={mate === "" || mate === crew.paired_member_id}
                      onClick={() => run.mutate({ go: () => pair.mutateAsync({ paired_member_id: mate }), done: "Pairing saved." })}>
            Change pairing
          </BusyButton>
        )}
      </div>
      <ReleasedJobs jobs={released} />
    </Panel>
  );
}

/** ADM-CRW-04, -05: hours for each weekday, applied from today on. */
export function HoursPanel({ crew }: { crew: Crew }) {
  const { hours: save } = useCrewActions(crew.id);
  const [hours, setHours] = useState<DayHours[]>(crew.working_hours);
  const [released, setReleased] = useState<ReleasedJob[]>([]);
  const run = useCrewRun(setReleased);
  const defaults = useDefaultHours(crew.society_id);
  return (
    <Panel title="Working hours"
           description="A day can have several slots, for example 05:00 to 13:00 and 17:00 to 19:00. A change applies from today on; jobs that no longer fit go to Needs scheduling."
           actions={<Button size="sm" variant="outline" disabled={!defaults.data} onClick={() => defaults.data && setHours(defaults.data)}>
             Use {crew.society} working slots
           </Button>}>
      <HoursEditor value={hours} onChange={setHours} error={fieldsOf(save.error).working_hours} />
      <div className="mt-4 flex justify-end">
        <BusyButton busy={run.isPending} onClick={() => run.mutate({ go: () => save.mutateAsync(hours), done: "Working hours saved." })}>
          Save working hours
        </BusyButton>
      </div>
      <ReleasedJobs jobs={released} />
    </Panel>
  );
}

/** ADM-CRW-08 to -12: Sick, Leave and Late start, one date or a range. */
export function ExceptionsPanel({ crew }: { crew: Crew }) {
  const confirm = useConfirm();
  const act = useCrewActions(crew.id);
  const [kind, setKind] = useState<string>("Sick");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [start, setStart] = useState("");
  const [released, setReleased] = useState<ReleasedJob[]>([]);
  const [editing, setEditing] = useState<CrewException | null>(null);
  const run = useCrewRun(setReleased);
  const fe = fieldsOf(act.addException.error);
  const order = from && to && to < from ? "The last day must be on or after the first." : undefined;
  const label = (x: CrewException) => `${x.kind}${x.kind === "Late start" ? ` from ${x.start}` : ""}`;

  const add = () => run.mutate({
    go: async () => {
      const r = await act.addException.mutateAsync({ kind, from_date: from, to_date: to || null, start: kind === "Late start" ? start : "" });
      setFrom(""); setTo("");
      return r;
    },
    done: "Exception saved.",
  });

  return (
    <div className="flex flex-col gap-6">
      <Panel title="Upcoming exceptions" bodyClassName="p-0">
        {crew.exceptions.length === 0 ? <p className="m-0 px-5 py-4 text-sm text-muted-foreground">No upcoming exceptions.</p> : (
          <ul className="m-0 list-none divide-y p-0">
            {crew.exceptions.map((x) => (
              <li key={x.id} className="flex items-center justify-between gap-3 px-5 py-2.5 text-sm">
                <span className="flex items-center gap-3"><span className="w-24">{showDate(x.date)}</span>
                  <StatusBadge status={label(x)} tone={x.kind === "Late start" ? "warn" : "neutral"} /></span>
                <span className="flex gap-1">
                  <Button size="sm" variant="ghost" aria-label={`Edit ${x.date}`} onClick={() => setEditing(x)}><Pencil aria-hidden /> Edit</Button>
                  <Button size="sm" variant="ghost" className="text-destructive" aria-label={`Remove ${x.date}`} onClick={async () => {
                    if (await confirm({ title: `Remove the exception on ${showDate(x.date)}?`, description: `${crew.name} counts as working that day again.`, confirmLabel: "Remove", tone: "danger" })) {
                      run.mutate({ go: () => act.removeException.mutateAsync(x.id), done: "Exception removed." });
                    }
                  }}><Trash2 aria-hidden /> Remove</Button>
                </span>
              </li>
            ))}
          </ul>
        )}
      </Panel>

      <Panel title="Add an exception" description="Jobs the crew member can no longer do go to Needs scheduling.">
        <form className="grid grid-cols-2 items-end gap-4 lg:grid-cols-[10rem_10rem_10rem_8rem_auto]" onSubmit={(e) => { e.preventDefault(); add(); }}>
          <Field label="Type" error={fe.kind}>{(p) => <SelectBox {...p} value={kind} onChange={setKind} choices={kindChoices} />}</Field>
          <Field label="From date" error={fe.from_date}>{(p) => <Input {...p} type="date" value={from} onChange={(e) => setFrom(e.target.value)} />}</Field>
          <Field label="To date" error={fe.to_date ?? order} hint="Empty for one day.">{(p) => <Input {...p} type="date" value={to} onChange={(e) => setTo(e.target.value)} />}</Field>
          {kind === "Late start"
            ? <Field label="Can start at" error={fe.start}>{(p) => <Input {...p} type="time" value={start} onChange={(e) => setStart(e.target.value)} />}</Field>
            : <span />}
          <BusyButton type="submit" className="lg:mb-5" busy={run.isPending} disabled={!from || Boolean(order) || (kind === "Late start" && !start)}>Add exception</BusyButton>
        </form>
        <ReleasedJobs jobs={released} />
      </Panel>

      {editing && <ExceptionDialog key={editing.id} x={editing} onClose={() => setEditing(null)}
        onSave={(k, s) => run.mutate({
          go: async () => { const r = await act.editException.mutateAsync({ exId: editing.id, kind: k, start: k === "Late start" ? s : "" }); setEditing(null); return r; },
          done: "Exception saved.",
        })} busy={run.isPending} />}
    </div>
  );
}

function ExceptionDialog({ x, onClose, onSave, busy }: { x: CrewException; onClose: () => void; onSave: (kind: string, start: string) => void; busy: boolean }) {
  const [kind, setKind] = useState(x.kind);
  const [start, setStart] = useState(x.start);
  return (
    <FormDialog open onOpenChange={(o) => !o && onClose()} title={`Edit exception on ${showDate(x.date)}`} size="sm"
                submitLabel="Save" busy={busy} disabled={kind === "Late start" && !start} onSubmit={() => onSave(kind, start)}>
      <Field label="Edit type">{(p) => <SelectBox {...p} value={kind} onChange={setKind} choices={kindChoices} />}</Field>
      {kind === "Late start" && <Field label="Edit start time">{(p) => <Input {...p} type="time" value={start} onChange={(e) => setStart(e.target.value)} />}</Field>}
    </FormDialog>
  );
}

/** ADM-CRW-15, -18: deactivate, reactivate and reset the password. */
export function AccountPanel({ crew }: { crew: Crew }) {
  const confirm = useConfirm();
  const act = useCrewActions(crew.id);
  const [released, setReleased] = useState<ReleasedJob[]>([]);
  const [issued, setIssued] = useState<CrewPassword | null>(null);
  const [needsRelease, setNeedsRelease] = useState("");
  const deactivate = useAppMutation<boolean, { released_jobs: ReleasedJob[] }>({
    mutationFn: (release_jobs) => act.deactivate.mutateAsync({ release_jobs }),
    pending: "Deactivating…", success: "Crew member deactivated.",
    onSuccess: (r) => { setReleased(r.released_jobs); setNeedsRelease(""); },
    onError: (e) => { if (e instanceof ApiError && e.status === 409 && e.code === "has_open_jobs") setNeedsRelease(e.message); },
  });
  const run = useCrewRun();
  const reset = useAppMutation<void, CrewPassword>({
    mutationFn: () => act.resetPassword.mutateAsync(), pending: "Resetting the password…",
    success: "New password made. Note it now.", onSuccess: setIssued,
  });

  return (
    <Panel title="Account" bodyClassName="flex flex-col gap-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="m-0 text-sm font-medium">{crew.active ? "Deactivate" : "Reactivate"}</p>
          <p className="m-0 text-sm text-muted-foreground">{crew.active
            ? "The crew member can no longer sign in or be scheduled."
            : "The crew member can sign in and be scheduled again."}</p>
        </div>
        {crew.active ? (
          <BusyButton variant="destructive" busy={deactivate.isPending} onClick={async () => {
            if (await confirm({ title: `Deactivate ${crew.name}?`, description: "They are signed out and no longer scheduled.", confirmLabel: "Deactivate", tone: "danger" })) deactivate.mutate(false);
          }}>Deactivate</BusyButton>
        ) : (
          <BusyButton busy={run.isPending} onClick={async () => {
            if (await confirm({ title: `Reactivate ${crew.name}?`, description: "They can sign in and be scheduled again.", confirmLabel: "Reactivate" })) {
              run.mutate({ go: () => act.reactivate.mutateAsync(), done: "Crew member reactivated." });
            }
          }}>Reactivate</BusyButton>
        )}
      </div>
      <div className="flex flex-col gap-3 border-t pt-5 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="m-0 text-sm font-medium">Reset password</p>
          <p className="m-0 text-sm text-muted-foreground">A new password is shown once. Hand it over yourself.</p>
        </div>
        <BusyButton variant="outline" busy={reset.isPending} onClick={async () => {
          if (await confirm({ title: "Reset password", description: "The old password stops working at once and every signed-in phone is signed out.", confirmLabel: "Reset password" })) reset.mutate();
        }}>Reset password</BusyButton>
      </div>
      <ReleasedJobs jobs={released} />

      {needsRelease && (
        <FormDialog open onOpenChange={(o) => !o && setNeedsRelease("")} title="Open jobs need to be released" danger
                    submitLabel="Send jobs to Needs scheduling and deactivate" busy={deactivate.isPending}
                    onSubmit={() => deactivate.mutate(true)}>
          <p className="m-0 text-sm">{needsRelease}</p>
        </FormDialog>
      )}
      {issued && <PasswordDialog issued={issued} onDone={() => setIssued(null)} />}
    </Panel>
  );
}

/** ADM-CRW-21: signed-in devices. */
export function SessionsPanel({ crew }: { crew: Crew }) {
  const confirm = useConfirm();
  const sessions = useSessions(crew.id);
  const act = useCrewActions(crew.id);
  const run = useCrewRun();
  return (
    <Panel title="Signed-in devices" bodyClassName="p-0"
           actions={<BusyButton size="sm" variant="outline" disabled={!sessions.data?.length} busy={act.endAll.isPending} onClick={async () => {
             if (await confirm({ title: `Sign ${crew.name} out everywhere?`, description: "Every phone is signed out now.", confirmLabel: "Sign out all", tone: "danger" })) {
               run.mutate({ go: () => act.endAll.mutateAsync(), done: "Signed out of every device." });
             }
           }}>Sign out all</BusyButton>}>
      {sessions.isPending && <div className="p-5"><Skeleton className="h-12" /></div>}
      {sessions.isError && <div className="p-5"><ErrorState message={errorMessage(sessions.error)} /></div>}
      {sessions.data?.length === 0 && <p className="m-0 px-5 py-4 text-sm text-muted-foreground">No signed-in devices.</p>}
      <ul className="m-0 list-none divide-y p-0">
        {sessions.data?.map((s) => (
          <li key={s.id} className="flex items-center justify-between gap-3 px-5 py-3">
            <div className="min-w-0 text-sm">
              <p className="m-0 font-medium">{s.device_name || "Unknown device"}</p>
              <p className="m-0 text-muted-foreground">{s.platform || "Unknown platform"} · App {s.app_version || "Unknown version"} · {s.channel === "web" ? "Web" : "Mobile app"}</p>
              <p className="m-0 text-xs text-muted-foreground">Signed in {showDateTime(s.signed_in_at)} · last active {showDateTime(s.last_active_at)}</p>
            </div>
            <Button size="sm" variant="outline" disabled={run.isPending} onClick={async () => {
              if (await confirm({ title: "Sign out this device?", description: `${s.device_name || "The device"} is signed out now.`, confirmLabel: "Sign out", tone: "danger" })) {
                run.mutate({ go: () => act.endSession.mutateAsync(s.id), done: "Signed out." });
              }
            }}>Sign out</Button>
          </li>
        ))}
      </ul>
    </Panel>
  );
}
