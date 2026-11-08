import { useEffect, useState } from "react";

import { api, ApiError } from "@/api/client";
import { Field, SelectBox } from "@/blocks/fields";
import { FormDialog } from "@/blocks/FormDialog";
import { EVENTS } from "@/analytics/events";
import { useAppMutation } from "@/blocks/mutation";
import { useToast } from "@/components";
import { useSite } from "@/site/SiteContext";
import { phoneDigits } from "@/lib/utils";
import { Input } from "@/ui/input";

import {
  ROLES, defaultHours, hoursBody, useCreateCrew, useCrewList, useDefaultHours, useSocieties,
  type CrewPassword, type DayHours,
} from "./api";
import { useDirectory } from "../reference/api";
import type { Zone } from "../reference/types";
import { HoursEditor } from "./HoursEditor";
import { HomeZonePicker, homeZoneHint } from "./rules/HomeZoneSection";
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
  const [societyId, setSocietyId] = useState(useSite().id);
  const [role, setRole] = useState("Member");
  const [mate, setMate] = useState("");
  const [hours, setHours] = useState<DayHours[]>(defaultHours());
  const [zoneIds, setZoneIds] = useState<string[]>([]);
  const [issued, setIssued] = useState<CrewPassword | null>(null);

  // The hours start as the society's working slots; the admin can still change them.
  const defaults = useDefaultHours(societyId);
  useEffect(() => {
    if (defaults.data) setHours(defaults.data);
  }, [defaults.data]);

  // Home zones are picked from the society's active zones (SCHS-29); the crew is saved first, then its zones.
  const zones = useDirectory<Zone[]>(`/societies/${societyId}/zones`, societyId !== "");
  const zoneChoices = (zones.data ?? []).filter((z) => z.active).map(({ id, name: zoneName }) => ({ id, name: zoneName }));

  const members = (crew.data ?? []).filter((c) => c.role === "Member" && c.active && c.society_id === societyId);
  const fe = create.error instanceof ApiError ? create.error.fields : {};
  const mobileOk = /^\d{10}$/.test(mobile.trim());
  const valid = name.trim() !== "" && mobileOk && societyId !== "" && (role !== "Trainee" || mate !== "");

  const save = useAppMutation<void, CrewPassword>({
    event: EVENTS.crewOnboarded,
    mutationFn: async () => {
      const r = await create.mutateAsync({
        name: name.trim(), mobile: mobile.trim(), society_id: societyId, role,
        working_hours: hoursBody(hours), paired_member_id: role === "Trainee" ? mate : null,
      });
      // A Trainee follows the Member's zones, so only a Member or Manager gets zones here.
      if (role !== "Trainee" && zoneIds.length > 0) {
        try {
          await api(`/v1/admin/crew/${r.crew.id}/home-zone`, { method: "PUT", body: { home_zone_ids: zoneIds } });
        } catch {
          // The crew exists already, so the password is still shown; the zones are set on the crew later.
          toast.show(`${r.crew.name} is onboarded, but the home zones could not be saved. Set them on the crew's Scheduling tab.`, "error");
        }
      }
      return r;
    },
    pending: "Onboarding…", success: (r) => `${r.crew.name} is onboarded. Note the password now.`,
    onSuccess: (r) => { setIssued(r); setName(""); setMobile(""); setZoneIds([]); },
  });

  return (
    <>
      <FormDialog open={!issued} onOpenChange={(o) => !o && onClose()} title="Onboard crew" size="xl"
                  description="Add crew members one after another. The society, role and hours stay for the next one."
                  submitLabel="Onboard" cancelLabel="Done" busy={save.isPending} disabled={!valid} onSubmit={() => save.mutate()}>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <Field label="Name" error={fe.name}>{(p) => <Input {...p} value={name} onChange={(e) => setName(e.target.value)} />}</Field>
          <Field label="Mobile number" error={fe.mobile ?? (mobile && !mobileOk ? "Enter 10 digits." : undefined)} hint="10 digits. This is the login ID.">
            {(p) => <Input {...p} inputMode="numeric" maxLength={10} value={mobile} onChange={(e) => setMobile(phoneDigits(e.target.value))} />}
          </Field>
          <Field label="Society" error={fe.society_id}>
            {(p) => <SelectBox {...p} value={societyId} onChange={(v) => { setSocietyId(v); setMate(""); setZoneIds([]); }}
                               choices={(societies.data ?? []).filter((s) => s.active).map((s) => ({ value: s.id, label: s.name }))} />}
          </Field>
          <Field label="Role" error={fe.role}>
            {(p) => <SelectBox {...p} value={role} onChange={setRole} choices={ROLES.map((r) => ({ value: r, label: r }))} />}
          </Field>
          {role === "Trainee" && (
            <Field label="Paired Member" error={fe.paired_member_id} className="sm:col-span-2"
                   hint={societyId && members.length === 0 ? "This society has no active Member yet. Onboard a Member first." : "The Trainee gets this Member's jobs."}>
              {(p) => <SelectBox {...p} value={mate} onChange={setMate} choices={members.map((m) => ({ value: m.id, label: m.name }))} />}
            </Field>
          )}
          {role !== "Trainee" && societyId !== "" && (
            <fieldset className="m-0 flex min-w-0 flex-col gap-2 border-0 p-0 sm:col-span-2">
              <legend className="mb-1.5 text-[0.8125rem] font-medium">Home zones <span className="font-normal text-muted-foreground">(optional)</span></legend>
              <HomeZonePicker zones={zoneChoices} value={zoneIds} onChange={setZoneIds} />
              <p className="m-0 text-xs text-muted-foreground">{homeZoneHint(null)}</p>
            </fieldset>
          )}
        </div>
        {societyId !== "" && <p className="m-0 text-xs text-muted-foreground">These hours come from the society's working slots. You can change them.</p>}
        <HoursEditor value={hours} onChange={setHours} error={fe.working_hours} />
      </FormDialog>
      {issued && (
        <PasswordDialog issued={issued} onDone={() => {
          toast.show(`${issued.crew.name} is onboarded.`, "ok");
          setIssued(null);
        }} />
      )}
    </>
  );
}
