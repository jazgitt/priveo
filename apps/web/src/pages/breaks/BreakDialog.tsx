import { useState } from "react";

import { api, ApiError } from "@/api/client";
import { Field } from "@/blocks/fields";
import { FormDialog } from "@/blocks/FormDialog";
import { useAppMutation } from "@/blocks/mutation";
import { Button } from "@/ui/button";
import { Input } from "@/ui/input";
import { Switch } from "@/ui/switch";

import { addDays } from "../schedule/DateBar";
import { hhmm, minuteOf, toIso } from "../schedule/api";

/** BreakRuleOut. Dates are null for a rule that has no date range. */
export interface BreakRule {
  id: string;
  society_id: string;
  crew_id: string | null;
  start_date: string | null;
  end_date: string | null;
  start_minute: number | null;
  end_minute: number | null;
  enabled: boolean;
}

/** The site break the dialog starts from, in minutes after midnight. */
export interface SiteBreak { start: number; end: number }

export type Cue = "today" | "tomorrow" | "range";
const CUES: { id: Cue; label: string }[] = [
  { id: "today", label: "Today" }, { id: "tomorrow", label: "Tomorrow" }, { id: "range", label: "Date range" },
];

/** The dates a cue fills in. A date range keeps what the admin typed. */
export function cueDates(cue: Cue, today: string, typed: { from: string; to: string }): { from: string; to: string } {
  if (cue === "today") return { from: today, to: today };
  if (cue === "tomorrow") { const t = addDays(today, 1); return { from: t, to: t }; }
  return typed;
}

interface Body {
  society_id: string;
  crew_id: string | null;
  start_date: string;
  end_date: string;
  start_minute: number | null;
  end_minute: number | null;
  enabled: boolean;
}

/**
 * SCHS-28: sets a break for a date range, for the whole site or for one cleaner (SCHR-BRK-05).
 * Today, Tomorrow and Date range only fill in the dates; the API takes dates.
 * `crewId` is the scheduling id of the cleaner, absent for the whole site.
 */
export function BreakDialog({ open, onOpenChange, societyId, crewId, siteBreak, invalidate, today = toIso(new Date()) }: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  societyId: string;
  crewId?: string;
  siteBreak: SiteBreak;
  invalidate: unknown[][];
  today?: string;
}) {
  const [cue, setCue] = useState<Cue>("today");
  const [typed, setTyped] = useState({ from: today, to: today });
  const [noBreak, setNoBreak] = useState(false);
  const [times, setTimes] = useState<SiteBreak>(siteBreak);
  const dates = cueDates(cue, today, typed);

  const save = useAppMutation<Body, BreakRule>({
    mutationFn: (body) => api<BreakRule>("/v1/admin/scheduling/break-rules", { method: "POST", body }),
    success: noBreak ? "No break set." : "Break saved.",
    invalidate: invalidate as never,
    onSuccess: () => onOpenChange(false),
  });
  const err = save.error instanceof ApiError ? save.error.fields : {};
  const sameAsSite = times.start === siteBreak.start && times.end === siteBreak.end;
  const timeError = !noBreak && times.end <= times.start ? "The break must end after it starts." : "";
  const dateError = cue === "range" && dates.to < dates.from ? "The end date cannot be before the start date." : "";

  const submit = () => save.mutate({
    society_id: societyId, crew_id: crewId ?? null, start_date: dates.from, end_date: dates.to,
    // Times equal to the site break are left out, so the rule follows the site break.
    start_minute: noBreak || sameAsSite ? null : times.start,
    end_minute: noBreak || sameAsSite ? null : times.end,
    enabled: !noBreak,
  });

  const timeInput = (key: keyof SiteBreak, label: string) => (
    <Field label={label} error={key === "end" ? timeError || err.end_minute : ""}>
      {(p) => (
        <Input {...p} type="time" className="h-8 w-28" value={hhmm(times[key])}
          onChange={(e) => { const m = minuteOf(e.target.value); if (m !== null) setTimes({ ...times, [key]: m }); }} />
      )}
    </Field>
  );

  return (
    <FormDialog open={open} onOpenChange={onOpenChange} size="md" submitLabel="Save break"
      title={crewId ? "Change this cleaner's break" : "Change the break for the site"}
      description="The most specific rule wins: a date for this cleaner, then a date for the site, then this cleaner, then the site."
      onSubmit={submit} busy={save.isPending} disabled={!!timeError || !!dateError}>
      <div role="group" aria-label="When" className="flex flex-wrap gap-2">
        {CUES.map((c) => (
          <Button key={c.id} type="button" size="sm" variant={cue === c.id ? "default" : "outline"}
            aria-pressed={cue === c.id} onClick={() => setCue(c.id)}>
            {c.label}
          </Button>
        ))}
      </div>
      <div className="flex flex-wrap gap-4">
        <Field label="From date" error={err.start_date}>
          {(p) => (
            <Input {...p} type="date" className="h-8 w-40" value={dates.from} disabled={cue !== "range"}
              onChange={(e) => setTyped({ ...typed, from: e.target.value })} />
          )}
        </Field>
        <Field label="To date" error={dateError || err.end_date}>
          {(p) => (
            <Input {...p} type="date" className="h-8 w-40" value={dates.to} disabled={cue !== "range"}
              onChange={(e) => setTyped({ ...typed, to: e.target.value })} />
          )}
        </Field>
      </div>
      <Field label="No break on these dates">
        {(p) => <Switch {...p} checked={noBreak} onCheckedChange={setNoBreak} />}
      </Field>
      {!noBreak && (
        <div className="flex flex-wrap gap-4">
          {timeInput("start", "Break starts")}
          {timeInput("end", "Break ends")}
        </div>
      )}
    </FormDialog>
  );
}
