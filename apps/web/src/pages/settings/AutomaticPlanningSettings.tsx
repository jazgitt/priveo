import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { api } from "@/api/client";
import { Field } from "@/blocks/fields";
import { BusyButton } from "@/blocks/FormDialog";
import { ErrorState, Panel } from "@/blocks/layout";
import { errorMessage, useAppMutation } from "@/blocks/mutation";
import { Input } from "@/ui/input";
import { Switch } from "@/ui/switch";

interface Settings { enabled: boolean; time_ist: string }
const path = "/v1/admin/scheduling/automatic-planning";

/** Whether the next schedule draft is made automatically, and when (IST). */
export function AutomaticPlanningSettings() {
  const qc = useQueryClient();
  const current = useQuery({ queryKey: ["automatic-planning"], queryFn: () => api<Settings>(path) });
  const [draft, setDraft] = useState<Settings>();
  const value = draft ?? current.data;
  const save = useAppMutation<Settings, Settings>({
    mutationFn: (settings) => api(path, { method: "PUT", body: settings }),
    success: (r) => (r.enabled ? `Automatic planning is on at ${r.time_ist} IST.` : "Automatic planning is off."),
    onSuccess: (result) => { qc.setQueryData(["automatic-planning"], result); setDraft(undefined); void qc.invalidateQueries({ queryKey: ["admin-settings"] }); },
  });
  return (
    <Panel title="Automatic schedule planning"
           description="Creates the next Daily, Weekly or Monthly draft for active societies. Existing schedules stay intact. Errors appear in admin alerts.">
      {current.error ? <ErrorState message={errorMessage(current.error)} /> : null}
      {value && (
        <form className="flex flex-col gap-4" onSubmit={(e) => { e.preventDefault(); save.mutate(value); }}>
          <label className="flex items-center justify-between gap-3 text-sm">
            Enable automatic planning
            <Switch aria-label="Enable automatic planning" checked={value.enabled} onCheckedChange={(on) => setDraft({ ...value, enabled: on })} />
          </label>
          <Field label="Planning time (IST)" hint={value.enabled && !value.time_ist ? "Set a time to turn it on." : undefined}>
            {(p) => <Input {...p} type="time" className="w-40" value={value.time_ist} onChange={(e) => setDraft({ ...value, time_ist: e.target.value })} />}
          </Field>
          <BusyButton type="submit" variant="outline" className="self-start" busy={save.isPending} disabled={value.enabled && !value.time_ist}>Save automatic planning</BusyButton>
          {save.isSuccess && <p role="status" className="m-0 text-xs text-ok">Automatic planning settings saved.</p>}
        </form>
      )}
    </Panel>
  );
}
