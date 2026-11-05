import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";

import { api } from "@/api/client";
import { Field } from "@/blocks/fields";
import { BusyButton } from "@/blocks/FormDialog";
import { ErrorState, Panel } from "@/blocks/layout";
import { errorMessage, useAppMutation } from "@/blocks/mutation";
import { Input } from "@/ui/input";

interface Settings { time_ist: string }
const path = "/v1/admin/scheduling/automatic-planning";

/**
 * The time (IST) the next schedule draft is made. Whether automatic planning runs
 * at all is the "Automatic planning" switch on the Scheduled jobs page (ADM-OPS-05).
 */
export function AutomaticPlanningSettings() {
  const qc = useQueryClient();
  const current = useQuery({ queryKey: ["automatic-planning"], queryFn: () => api<Settings>(path) });
  const [draft, setDraft] = useState<Settings>();
  const value = draft ?? current.data;
  const save = useAppMutation<Settings, Settings>({
    mutationFn: (settings) => api(path, { method: "PUT", body: settings }),
    success: (r) => (r.time_ist ? `Automatic planning time is ${r.time_ist} IST.` : "Automatic planning time is cleared."),
    onSuccess: (result) => { qc.setQueryData(["automatic-planning"], result); setDraft(undefined); void qc.invalidateQueries({ queryKey: ["admin-settings"] }); },
  });
  return (
    <Panel title="Automatic schedule planning"
           description="Creates the next Daily, Weekly or Monthly draft for active societies. Existing schedules stay intact. Errors appear in admin alerts.">
      {current.error ? <ErrorState message={errorMessage(current.error)} /> : null}
      {value && (
        <form className="flex flex-col gap-4" onSubmit={(e) => { e.preventDefault(); save.mutate(value); }}>
          <p className="m-0 text-sm text-muted-foreground">
            Switch automatic planning on or off in <Link className="underline" to="/scheduled-jobs">Scheduled jobs</Link>.
          </p>
          <Field label="Planning time (IST)" hint="The job runs once a day at about 9 PM IST. Choose 9 PM or earlier, and set a time before it is switched on.">
            {(p) => <Input {...p} type="time" className="w-40" value={value.time_ist} onChange={(e) => setDraft({ ...value, time_ist: e.target.value })} />}
          </Field>
          <BusyButton type="submit" variant="outline" className="self-start" busy={save.isPending}>Save automatic planning</BusyButton>
          {save.isSuccess && <p role="status" className="m-0 text-xs text-ok">Automatic planning settings saved.</p>}
        </form>
      )}
    </Panel>
  );
}
