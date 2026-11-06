import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { api, ApiError } from "@/api/client";
import { Field } from "@/blocks/fields";
import { ErrorState } from "@/blocks/layout";
import { useAppMutation } from "@/blocks/mutation";
import { Button } from "@/ui/button";
import { Input } from "@/ui/input";
import { Skeleton } from "@/ui/skeleton";
import { Switch } from "@/ui/switch";
import { useSite } from "../../../site/SiteContext";
import type { RulesSection } from ".";
import { CUTOFF_NAMES, WEEKDAY_NAMES, clock, isMinuteKey, labelOf, minutesOf } from "./labels";

/** SiteSettingOut: values travel as the stored text ("300", "true", "5,6"). */
interface SiteSetting {
  key: string;
  label: string;
  kind: string;
  default_value: string;
  site_value: string | null;
  value: string;
  minimum: number | null;
  maximum: number | null;
}

const shown = (s: SiteSetting, text: string) => {
  if (s.kind === "bool") return text === "true" ? "On" : "Off";
  if (s.kind === "weekdays") return text.split(",").filter(Boolean).map((d) => WEEKDAY_NAMES[Number(d)]).join(", ") || "None";
  if (s.kind === "int" && isMinuteKey(s.key)) return clock(Number(text));
  return text;
};

const rangeOf = (s: SiteSetting) => {
  if (s.kind !== "int" || s.minimum === null || s.maximum === null) return "";
  return isMinuteKey(s.key) ? `Range ${clock(s.minimum)} to ${clock(s.maximum)}.` : `Range ${s.minimum} to ${s.maximum}.`;
};

function Control({ s, draft, setDraft, p }: {
  s: SiteSetting; draft: string; setDraft: (v: string) => void; p: object;
}) {
  if (s.kind === "bool") {
    return <Switch {...p} checked={draft === "true"} onCheckedChange={(on) => setDraft(on ? "true" : "false")} />;
  }
  if (s.kind === "weekdays") {
    const days = new Set(draft.split(",").filter(Boolean));
    return (
      <div className="flex flex-wrap gap-1" role="group" aria-label={labelOf(s.key, s.label)}>
        {WEEKDAY_NAMES.map((name, i) => (
          <Button key={name} type="button" size="sm" variant={days.has(String(i)) ? "default" : "outline"}
            aria-pressed={days.has(String(i))}
            onClick={() => { const next = new Set(days); if (!next.delete(String(i))) next.add(String(i)); setDraft([...next].sort().join(",")); }}>
            {name}
          </Button>
        ))}
      </div>
    );
  }
  if (isMinuteKey(s.key)) {
    return <Input {...p} type="time" className="h-8 w-28" value={clock(Number(draft))}
      onChange={(e) => { const m = minutesOf(e.target.value); if (m !== null) setDraft(String(m)); }} />;
  }
  return <Input {...p} className="h-8 w-28" inputMode="numeric" value={draft} onChange={(e) => setDraft(e.target.value)} />;
}

function Row({ s, societyId }: { s: SiteSetting; societyId: string }) {
  const [draft, setDraft] = useState(s.value);
  const save = useAppMutation<string, SiteSetting>({
    mutationFn: (value) => api<SiteSetting>(`/v1/admin/scheduling/site-settings/${s.key}`,
      { method: "PUT", body: { society_id: societyId, value } }),
    success: "Saved.",
    invalidate: [["site-settings", societyId]],
  });
  const error = save.error instanceof ApiError ? (save.error.fields.value ?? save.error.message) : "";
  const label = labelOf(s.key, s.label);
  const hint = [`Default ${shown(s, s.default_value)}.`,
    s.site_value === null ? "This site uses the default." : `This site: ${shown(s, s.site_value)}.`,
    rangeOf(s)].filter(Boolean).join(" ");
  return (
    <div className="flex flex-wrap items-end gap-3">
      <Field label={label} hint={hint} error={error}>
        {(p) => <Control s={s} draft={draft} setDraft={setDraft} p={p} />}
      </Field>
      <Button type="button" size="sm" disabled={draft === s.value || save.isPending}
        aria-label={`Save ${label}`} onClick={() => save.mutate(draft)}>Save</Button>
    </div>
  );
}

/** SCHS-18: the per-site scheduling values, with the default, the site value and the range of each. */
export function GeneralSection() {
  const { id } = useSite();
  const q = useQuery({
    queryKey: ["site-settings", id],
    queryFn: () => api<SiteSetting[]>(`/v1/admin/scheduling/site-settings?society_id=${id}`),
    enabled: !!id,
  });
  if (!id) return <p className="text-sm text-muted-foreground">Choose a site to see its scheduling rules.</p>;
  if (q.isError) return <ErrorState message="The scheduling rules could not be loaded." onRetry={() => void q.refetch()} />;
  if (!q.data) return <Skeleton className="h-32 w-full" />;
  return (
    <div className="flex flex-col gap-5">
      <dl className="grid gap-1 text-sm sm:grid-cols-[10rem_1fr]">
        {CUTOFF_NAMES.map((c) => (
          <div key={c.name} className="contents"><dt className="font-medium">{c.name}</dt><dd className="text-muted-foreground">{c.meaning}</dd></div>
        ))}
      </dl>
      {/* The key resets a row when its saved value changes. */}
      {q.data.map((s) => <Row key={`${s.key}:${s.value}`} s={s} societyId={id} />)}
    </div>
  );
}

export const section: RulesSection = {
  id: "general", title: "Site rules", order: 10, component: GeneralSection,
};
