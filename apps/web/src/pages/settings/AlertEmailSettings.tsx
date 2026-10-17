import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { api } from "@/api/client";
import { Field } from "@/blocks/fields";
import { BusyButton } from "@/blocks/FormDialog";
import { ErrorState, Panel } from "@/blocks/layout";
import { errorMessage, useAppMutation } from "@/blocks/mutation";
import { Input } from "@/ui/input";
import { Switch } from "@/ui/switch";

interface Preferences { enabled: boolean; email: string }
const path = "/v1/admin/alerts/email-preferences";

/** Where the signed-in admin's alert emails go, and whether they are sent (ADM-ACC-09). */
export function AlertEmailSettings() {
  const qc = useQueryClient();
  const current = useQuery({ queryKey: ["alert-email-preferences"], queryFn: () => api<Preferences>(path) });
  const [email, setEmail] = useState<string>();
  const [enabled, setEnabled] = useState<boolean>();
  const save = useAppMutation<Preferences, Preferences>({
    mutationFn: (value) => api(path, { method: "PUT", body: value }),
    success: "Alert email preferences saved.",
    onSuccess: (value) => { qc.setQueryData(["alert-email-preferences"], value); setEmail(undefined); setEnabled(undefined); },
  });
  const d = current.data;
  return (
    <Panel title="My alert emails" description="The bell and phone alerts cannot be switched off. Emails can.">
      {current.error ? <ErrorState message={errorMessage(current.error)} /> : null}
      {d && (
        <form className="flex flex-col gap-4" onSubmit={(e) => { e.preventDefault(); save.mutate({ email: email ?? d.email, enabled: enabled ?? d.enabled }); }}>
          <Field label="Alert email address">{(p) => <Input {...p} type="email" value={email ?? d.email} onChange={(e) => setEmail(e.target.value)} />}</Field>
          <label className="flex items-center justify-between gap-3 text-sm">
            Email me admin alerts
            <Switch aria-label="Email me admin alerts" checked={enabled ?? d.enabled} onCheckedChange={setEnabled} />
          </label>
          <p className="m-0 text-xs text-muted-foreground">Alerts remain in the inbox when email is off.</p>
          <BusyButton type="submit" variant="outline" busy={save.isPending} className="self-start">Save alert email preferences</BusyButton>
          {save.isSuccess && <p role="status" className="m-0 text-xs text-ok">Alert email preferences saved.</p>}
        </form>
      )}
    </Panel>
  );
}
