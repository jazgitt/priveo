import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "../../api/client";
import { Button, Card, TextField } from "../../components";
import { ApiErrorNote } from "../../components/ApiErrorNote";

interface Preferences { enabled: boolean; email: string }
const path = "/v1/admin/alerts/email-preferences";

export function AlertEmailSettings() {
  const qc = useQueryClient();
  const current = useQuery({ queryKey: ["alert-email-preferences"], queryFn: () => api<Preferences>(path) });
  const [email, setEmail] = useState<string>();
  const [enabled, setEnabled] = useState<boolean>();
  const save = useMutation({ mutationFn: (value: Preferences) => api<Preferences>(path, { method: "PUT", body: value }),
    onSuccess: (value) => { qc.setQueryData(["alert-email-preferences"], value); setEmail(undefined); setEnabled(undefined); } });
  return <Card title="My alert emails">
    <ApiErrorNote error={current.error ?? save.error} />
    {current.data && <>
      <TextField label="Alert email address" type="email" value={email ?? current.data.email} onChange={e => setEmail(e.target.value)} />
      <label><input type="checkbox" checked={enabled ?? current.data.enabled} onChange={e => setEnabled(e.target.checked)} /> Email me admin alerts</label>
      <p className="muted">Alerts remain in the inbox when email is off.</p>
      <Button busy={save.isPending} onClick={() => save.mutate({ email: email ?? current.data!.email, enabled: enabled ?? current.data!.enabled })}>Save alert email preferences</Button>
      {save.isSuccess && <p role="status">Alert email preferences saved.</p>}
    </>}
  </Card>;
}
