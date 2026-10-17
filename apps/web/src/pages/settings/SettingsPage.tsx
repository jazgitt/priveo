import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { api, ApiError } from "@/api/client";
import { BusyButton } from "@/blocks/FormDialog";
import { ErrorState, PageHeader, Panel } from "@/blocks/layout";
import { useAppMutation } from "@/blocks/mutation";
import { StatusBadge } from "@/blocks/status";
import { showDateTime } from "@/components/format";
import { Input } from "@/ui/input";
import { Skeleton } from "@/ui/skeleton";

import { AlertEmailSettings } from "./AlertEmailSettings";
import { AutomaticPlanningSettings } from "./AutomaticPlanningSettings";

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

function SettingRow({ setting }: { setting: Setting }) {
  const qc = useQueryClient();
  const [draft, setValue] = useState<string>();
  const value = draft ?? String(setting.value ?? "");
  const save = useAppMutation<void>({
    mutationFn: () => api(`${PATH}/${setting.key}`, { method: "PUT", body: { value: setting.kind === "int" ? Number(value) : value } }),
    success: `${setting.label} saved.`,
    onSuccess: () => { setValue(undefined); void qc.invalidateQueries({ queryKey: ["admin-settings"] }); },
  });
  const err = save.error instanceof ApiError ? (save.error.fields.value ?? save.error.message)
    : save.error ? "Could not save. Please try again." : undefined;
  const changed = value !== String(setting.value ?? "");
  const id = `setting-${setting.key}`;

  if (setting.group === "invoice") {
    return (
      <div className="grid grid-cols-1 gap-1 py-3 sm:grid-cols-[14rem_minmax(0,1fr)] sm:gap-4">
        <span className="text-sm font-medium">{setting.label}</span>
        <span className="text-sm">{String(setting.value ?? "") || "-"} <span className="block text-xs text-muted-foreground">Seeded from environment configuration.</span></span>
      </div>
    );
  }

  return (
    <form className="grid grid-cols-1 items-start gap-2 py-3 sm:grid-cols-[14rem_minmax(0,1fr)_auto] sm:gap-4"
          onSubmit={(e) => { e.preventDefault(); if (changed) save.mutate(); }}>
      <label htmlFor={id} className="pt-2 text-sm font-medium">{setting.label}</label>
      <div className="flex min-w-0 flex-col gap-1">
        <Input id={id} type={setting.kind === "int" ? "number" : "text"} value={value} aria-invalid={err ? true : undefined}
               onChange={(e) => setValue(e.target.value)} className="max-w-md" />
        {err ? <p role="alert" className="m-0 text-xs text-destructive">{err}</p>
          : <p className="m-0 text-xs text-muted-foreground">
              {HINTS[setting.kind] ? `${HINTS[setting.kind]} ` : ""}
              {setting.updated_at ? `Updated ${showDateTime(setting.updated_at)}${setting.updated_by ? ` by ${setting.updated_by}` : ""}.` : ""}
            </p>}
      </div>
      <div className="flex items-center gap-2 sm:pt-1">
        <StatusBadge status={setting.is_default ? "Default" : "Set"} tone={setting.is_default ? "neutral" : "ok"} />
        <BusyButton type="submit" size="sm" variant={changed ? "default" : "outline"} busy={save.isPending} disabled={!changed} aria-label={`Save ${setting.label}`}>Save</BusyButton>
      </div>
    </form>
  );
}

/** Settings by group, each saved on its own (ADM-SET-01 to -04, ADM-SCH-18, -25). */
export function SettingsPage() {
  const list = useQuery({ queryKey: ["admin-settings"], queryFn: () => api<Setting[]>(PATH) });
  return (
    <>
      <PageHeader title="Settings" description="Portal-wide settings. Each one is saved on its own and recorded in the Audit log." />
      <div className="grid grid-cols-1 items-start gap-6 xl:grid-cols-[minmax(0,1fr)_24rem]">
        <div className="flex min-w-0 flex-col gap-6">
          {list.isLoading && <Skeleton className="h-64" />}
          {list.isError && <ErrorState message="Could not load the settings." onRetry={() => void list.refetch()} />}
          {Object.entries(GROUPS).map(([group, title]) => {
            const rows = (list.data ?? []).filter((s) => s.group === group);
            if (rows.length === 0) return null;
            return (
              <Panel key={group} title={title} bodyClassName="divide-y py-1">
                {/* Keep drafts while another client changes the server value. */}
                {rows.map((s) => <SettingRow key={s.key} setting={s} />)}
              </Panel>
            );
          })}
        </div>
        <div className="flex flex-col gap-6">
          <AlertEmailSettings />
          <AutomaticPlanningSettings />
        </div>
      </div>
    </>
  );
}
