import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { api } from "@/api/client";
import { Field } from "@/blocks/fields";
import { ErrorState } from "@/blocks/layout";
import { useAppMutation } from "@/blocks/mutation";
import { cn } from "@/lib/utils";
import { Button } from "@/ui/button";
import { Input } from "@/ui/input";
import { Skeleton } from "@/ui/skeleton";

import type { Crew } from "../api";
import type { CrewRulesSection } from ".";

/** CrewTimesOut: the cleaner's overrides (null: none) and the site values behind them, in minutes. */
interface Times {
  reporting_minute: number | null;
  first_job_minute: number | null;
  site_reporting_minute: number;
  site_first_job_minute: number;
}
type Override = Pick<Times, "reporting_minute" | "first_job_minute">;

const pad = (n: number) => String(n).padStart(2, "0");
const show = (m: number) => `${pad(Math.floor(m / 60))}:${pad(m % 60)}`;
const minutes = (t: string) => {
  const [h, m] = t.split(":").map(Number);
  return Number.isFinite(h) && Number.isFinite(m) ? h * 60 + m : null;
};

function TimesForm({ crewId, times }: { crewId: string; times: Times }) {
  const [draft, setDraft] = useState<Override>({
    reporting_minute: times.reporting_minute, first_job_minute: times.first_job_minute,
  });
  const save = useAppMutation<Override, Times>({
    mutationFn: (body) => api<Times>(`/v1/admin/crew/${crewId}/times`, { method: "PUT", body }),
    success: "Times saved.",
    invalidate: [["crew", crewId, "times"]],
  });

  const reporting = draft.reporting_minute ?? times.site_reporting_minute;
  const firstJob = draft.first_job_minute ?? times.site_first_job_minute;
  const error = firstJob < reporting ? "The first job time must not be before the reporting time." : "";
  const changed = draft.reporting_minute !== times.reporting_minute
    || draft.first_job_minute !== times.first_job_minute;

  const row = (key: keyof Override, label: string, siteMinute: number) => {
    const own = draft[key];
    return (
      <Field label={label} hint={`Site default ${show(siteMinute)}`} error={key === "first_job_minute" ? error : ""}>
        {(p) => (
          <div className="flex items-center gap-2">
            <Input
              {...p} type="time" className={cn("h-8 w-28", own === null && "text-muted-foreground")}
              value={show(own ?? siteMinute)}
              onChange={(e) => { const m = minutes(e.target.value); if (m !== null) setDraft({ ...draft, [key]: m }); }}
            />
            {own !== null && (
              <Button type="button" variant="ghost" size="sm" aria-label={`Clear ${label.toLowerCase()}`}
                onClick={() => setDraft({ ...draft, [key]: null })}>Clear</Button>
            )}
          </div>
        )}
      </Field>
    );
  };

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap gap-6">
        {row("reporting_minute", "Reporting time", times.site_reporting_minute)}
        {row("first_job_minute", "First job time", times.site_first_job_minute)}
      </div>
      <div>
        <Button type="button" disabled={!changed || !!error || save.isPending} onClick={() => save.mutate(draft)}>
          Save
        </Button>
      </div>
    </div>
  );
}

/** SCHS-16: when the cleaner reports and the earliest first job. Grey is the site default. */
export function TimesSection({ crew }: { crew: Crew }) {
  const q = useQuery({
    queryKey: ["crew", crew.id, "times"],
    queryFn: () => api<Times>(`/v1/admin/crew/${crew.id}/times`),
  });
  if (q.isError) return <ErrorState message="The times could not be loaded." onRetry={() => void q.refetch()} />;
  if (!q.data) return <Skeleton className="h-24 w-full" />;
  // The key resets the form when the saved values change.
  return <TimesForm key={JSON.stringify(q.data)} crewId={crew.id} times={q.data} />;
}

export const section: CrewRulesSection = {
  id: "times", title: "Reporting and first job", order: 10, component: TimesSection,
};
