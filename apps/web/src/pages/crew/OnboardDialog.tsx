import { useState } from "react";

import { ApiError } from "../../api/client";
import { ApiErrorNote } from "../../components/ApiErrorNote";
import { Button, Dialog, SelectField, TextField, useToast } from "../../components";
import {
  ROLES, defaultHours, hoursBody, useCreateCrew, useCrewList, useSocieties,
  type CrewPassword, type DayHours,
} from "./api";
import { HoursEditor } from "./HoursEditor";
import { PasswordDialog } from "./shared";

/** ADM-CRW-01: several crew members can be added one after another. The
 *  society, role and hours stay between members; the name and mobile clear. */
export function OnboardDialog({ onClose }: { onClose: () => void }) {
  const toast = useToast();
  const societies = useSocieties();
  const crew = useCrewList("");
  const create = useCreateCrew();
  const [name, setName] = useState("");
  const [mobile, setMobile] = useState("");
  const [societyId, setSocietyId] = useState("");
  const [role, setRole] = useState("Member");
  const [mate, setMate] = useState("");
  const [hours, setHours] = useState<DayHours[]>(defaultHours());
  const [issued, setIssued] = useState<CrewPassword | null>(null);

  const members = (crew.data ?? []).filter(
    (c) => c.role === "Member" && c.active && c.society_id === societyId);
  const fe = create.error instanceof ApiError ? create.error.fields : {};
  const valid = name.trim() !== "" && /^\d{10}$/.test(mobile.trim()) && societyId !== ""
    && (role !== "Trainee" || mate !== "");

  const submit = () => create.mutate(
    { name: name.trim(), mobile: mobile.trim(), society_id: societyId, role,
      working_hours: hoursBody(hours),
      paired_member_id: role === "Trainee" ? mate : null },
    { onSuccess: (r) => {
      setIssued(r);
      setName("");
      setMobile("");
    } });

  return (
    <>
      <Dialog open title="Onboard crew" onClose={onClose}
              footer={<>
                <Button variant="secondary" onClick={onClose}>Done</Button>
                <Button busy={create.isPending} disabled={!valid} onClick={submit}>
                  Onboard
                </Button>
              </>}>
        <TextField label="Name" value={name} onChange={(e) => setName(e.target.value)} error={fe.name} />
        <TextField label="Mobile number" inputMode="numeric" value={mobile}
                   onChange={(e) => setMobile(e.target.value)} error={fe.mobile}
                   hint="10 digits. This is the login ID." />
        <SelectField label="Society" value={societyId} error={fe.society_id}
                     onChange={(e) => { setSocietyId(e.target.value); setMate(""); }}>
          <option value="">Choose</option>
          {(societies.data ?? []).filter((s) => s.active).map((s) => (
            <option key={s.id} value={s.id}>{s.name}</option>))}
        </SelectField>
        <SelectField label="Role" value={role} onChange={(e) => setRole(e.target.value)} error={fe.role}>
          {ROLES.map((r) => <option key={r}>{r}</option>)}
        </SelectField>
        {role === "Trainee" && (
          <SelectField label="Paired Member" value={mate} error={fe.paired_member_id}
                       onChange={(e) => setMate(e.target.value)}
                       hint={societyId && members.length === 0
                         ? "This society has no active Member yet. Onboard a Member first." : undefined}>
            <option value="">Choose</option>
            {members.map((m) => <option key={m.id} value={m.id}>{m.name}</option>)}
          </SelectField>
        )}
        <HoursEditor value={hours} onChange={setHours} error={fe.working_hours} />
        <ApiErrorNote error={create.error} />
      </Dialog>
      {issued && (
        <PasswordDialog issued={issued} onDone={() => {
          toast.show(`${issued.crew.name} is onboarded.`, "ok");
          setIssued(null);
        }} />
      )}
    </>
  );
}
