import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "../../api/client";
import { ApiErrorNote } from "../../components/ApiErrorNote";
import { Button, Card, TextField } from "../../components";

interface Settings { enabled: boolean; time_ist: string }
const path = "/v1/admin/scheduling/automatic-planning";

export function AutomaticPlanningSettings() {
  const qc = useQueryClient();
  const current = useQuery({ queryKey: ["automatic-planning"], queryFn: () => api<Settings>(path) });
  const [draft, setDraft] = useState<Settings>();
  const value = draft ?? current.data;
  const save = useMutation({ mutationFn: (settings: Settings) => api<Settings>(path, { method: "PUT", body: settings }),
    onSuccess: result => { qc.setQueryData(["automatic-planning"], result); setDraft(undefined); void qc.invalidateQueries({ queryKey: ["admin-settings"] }); } });
  return <Card title="Automatic schedule planning">
    <ApiErrorNote error={current.error ?? save.error} />
    {value && <>
      <label><input type="checkbox" checked={value.enabled} onChange={e => setDraft({ ...value, enabled: e.target.checked })} />Enable automatic planning</label>
      <TextField label="Planning time (IST)" type="time" value={value.time_ist} onChange={e => setDraft({ ...value, time_ist: e.target.value })} />
      <p>Creates the next Daily/Weekly/Monthly draft for active societies using the scheduling settings. Existing schedules stay intact. Errors appear in admin alerts.</p>
      <Button busy={save.isPending} disabled={value.enabled && !value.time_ist} onClick={() => save.mutate(value)}>Save automatic planning</Button>
      {save.isSuccess && <p role="status">Automatic planning settings saved.</p>}
    </>}
  </Card>;
}
