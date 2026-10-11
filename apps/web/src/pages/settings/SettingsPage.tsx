import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { api, ApiError } from "../../api/client";
import { Button, Card, StatusChip, TextField, useToast } from "../../components";

const PATH = "/v1/admin/directory/settings";

export interface Setting {
  key: string;
  label: string;
  group: string;
  kind: string;
  value: string | number | null;
  is_default: boolean;
  updated_at: string | null;
  updated_by: string | null;
}

const GROUPS: Record<string, string> = {
  support: "Support",
  payment: "Payment",
  invoice: "Invoice",
  schedule: "Schedule",
  billing: "Billing",
};

const HINTS: Record<string, string> = {
  phone: "Digits only, 10 to 15, with an optional leading +.",
  upi: "For example name@bank.",
  url: "A full web address starting with https://.",
  gstin: "The 15 character GSTIN.",
  int: "A whole number.",
  time: "24-hour time as HH:MM.",
};

/** Date and time in the admin's locale, for the updated-at line. */
function when(iso: string): string {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleString("en-IN");
}

function SettingRow({ setting }: { setting: Setting }) {
  const qc = useQueryClient();
  const toast = useToast();
  const [value, setValue] = useState(String(setting.value ?? ""));
  const save = useMutation({
    mutationFn: () => api<Setting>(`${PATH}/${setting.key}`, {
      method: "PUT",
      body: { value: setting.kind === "int" ? Number(value) : value },
    }),
    onSuccess: () => {
      toast.show(`${setting.label} saved.`, "ok");
      void qc.invalidateQueries({ queryKey: ["admin-settings"] });
    },
  });
  const err = save.error instanceof ApiError
    ? (save.error.fields.value ?? save.error.message)
    : save.error ? "Could not save. Please try again." : undefined;
  const changed = value !== String(setting.value ?? "");

  return (
    <div className="set-row">
      <TextField label={setting.label} value={value} error={err}
                 type={setting.kind === "int" ? "number" : "text"}
                 hint={HINTS[setting.kind]} onChange={(e) => setValue(e.target.value)} />
      <div className="set-meta">
        {setting.is_default
          ? <StatusChip tone="neutral">Default</StatusChip>
          : <StatusChip tone="ok">Set</StatusChip>}
        {setting.updated_at && (
          <span className="muted">
            Updated {when(setting.updated_at)}{setting.updated_by ? ` by ${setting.updated_by}` : ""}
          </span>
        )}
        <Button busy={save.isPending} disabled={!changed}
                aria-label={`Save ${setting.label}`} onClick={() => save.mutate()}>Save</Button>
      </div>
    </div>
  );
}

/** Settings by group, each saved on its own (ADM-SET-01 to -04, ADM-SCH-18, -25). */
export function SettingsPage() {
  const list = useQuery({ queryKey: ["admin-settings"], queryFn: () => api<Setting[]>(PATH) });
  return (
    <>
      <h1 className="page-title">Settings</h1>
      {list.isLoading && <p className="muted">Loading...</p>}
      {list.isError && <p role="alert" className="form-error">Could not load the settings.</p>}
      <div className="set-stack">
        {Object.entries(GROUPS).map(([group, title]) => {
          const rows = (list.data ?? []).filter((s) => s.group === group);
          if (rows.length === 0) return null;
          return (
            <Card key={group} title={title}>
              {rows.map((s) => (
                // The value is part of the key so a saved value resets the draft.
                <SettingRow key={`${s.key}-${String(s.value)}`} setting={s} />
              ))}
            </Card>
          );
        })}
      </div>
    </>
  );
}
