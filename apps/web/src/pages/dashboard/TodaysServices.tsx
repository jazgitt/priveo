import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";

import { api } from "@/api/client";
import { Field, NONE, SelectBox } from "@/blocks/fields";
import { ErrorState } from "@/blocks/layout";
import { errorMessage } from "@/blocks/mutation";
import { StatusBadge, type Tone } from "@/blocks/status";
import { Input } from "@/ui/input";
import { Skeleton } from "@/ui/skeleton";

import { type CrewRow, toIso } from "../schedule/api";
import { formatDate } from "../support/format";

export interface SummaryItem { id: string; registration: string; crew: string; reason: string; time: string | null }
export interface SummaryState { count: number; items: SummaryItem[]; more: number }
export const STATES = ["pending", "completed", "missed", "partially_completed", "skipped", "rescheduled", "cancelled"] as const;
export type StateKey = (typeof STATES)[number];
export type DaySummary = { date: string; total: number } & Record<StateKey, SummaryState>;

const LABEL: Record<StateKey, string> = {
  pending: "Pending", completed: "Completed", missed: "Missed", partially_completed: "Partially completed",
  skipped: "Skipped", rescheduled: "Rescheduled", cancelled: "Cancelled",
};
const TONE: Record<StateKey, Tone> = {
  pending: "info", completed: "ok", missed: "error", partially_completed: "warn",
  skipped: "neutral", rescheduled: "warn", cancelled: "neutral",
};
/** Operations holds the follow-up of missed and partial visits; the Schedule board shows the rest. */
function linkOf(state: StateKey, date: string): string {
  const day = `date_from=${date}&date_to=${date}`;
  if (state === "missed" || state === "partially_completed") return `/operations?queue=missed&${day}`;
  if (state === "rescheduled" || state === "skipped" || state === "cancelled") return `/operations?queue=history&${day}`;
  return `/schedule?date=${date}`;
}

/** A-02: the day's visits by outcome, with a date, crew and vehicle filter. */
export function TodaysServices() {
  const [date, setDate] = useState(toIso(new Date()));
  const [crew, setCrew] = useState("");
  const [registration, setRegistration] = useState("");
  const crews = useQuery({ queryKey: ["admin-crew"], queryFn: () => api<CrewRow[]>("/v1/admin/crew") });
  const q = new URLSearchParams({ date });
  if (crew) q.set("crew_id", crew);
  if (registration.trim()) q.set("registration", registration.trim());
  const summary = useQuery({
    queryKey: ["day-summary", q.toString()],
    queryFn: () => api<DaySummary>(`/v1/admin/home/day-summary?${q}`),
  });
  const data = summary.data;

  return (
    <section aria-label="Today's services" className="mb-5 rounded-xl border bg-card shadow-xs">
      <header className="flex flex-wrap items-end justify-between gap-3 px-5 pt-4">
        <h2 className="m-0 text-base font-semibold">Today's services{date ? <span className="ml-2 text-sm font-normal text-muted-foreground">{formatDate(date)}</span> : null}</h2>
        <div className="flex flex-wrap items-end gap-3">
          <Field label="Date" className="w-40">{(p) => <Input {...p} type="date" value={date} onChange={(e) => e.target.value && setDate(e.target.value)} />}</Field>
          <Field label="Crew" className="w-44">
            {(p) => <SelectBox {...p} value={crew || NONE} onChange={(v) => setCrew(v === NONE ? "" : v)}
                               choices={[{ value: NONE, label: "All crew" }, ...(crews.data ?? []).map((c) => ({ value: c.id, label: c.name }))]} />}
          </Field>
          <Field label="Vehicle" className="w-40">{(p) => <Input {...p} placeholder="Registration" value={registration} onChange={(e) => setRegistration(e.target.value)} />}</Field>
        </div>
      </header>
      <div className="px-5 py-4">
        {summary.isError ? <ErrorState message={errorMessage(summary.error)} onRetry={() => void summary.refetch()} />
          : summary.isPending ? <Skeleton className="h-20 w-full" />
          : data && data.total === 0 ? <p className="m-0 text-sm text-muted-foreground">No services on this day.</p>
          : data && (
            <>
              <p className="m-0 mb-3 text-sm text-muted-foreground">{data.total} visits</p>
              <ul className="m-0 grid list-none grid-cols-2 gap-3 p-0 md:grid-cols-4 2xl:grid-cols-7">
                {STATES.map((k) => (
                  <li key={k} className="min-w-0 rounded-lg border p-3">
                    <Link to={linkOf(k, data.date)} aria-label={`${LABEL[k]}: ${data[k].count}`} className="block no-underline">
                      <StatusBadge status={LABEL[k]} tone={TONE[k]} />
                      <span className="mt-2 block text-2xl font-semibold tabular-nums">{data[k].count}</span>
                    </Link>
                    <ul className="m-0 mt-2 list-none space-y-1 p-0 text-xs text-muted-foreground">
                      {data[k].items.slice(0, 3).map((i) => (
                        <li key={i.id} className="truncate"><span className="reg">{i.registration}</span> · {i.crew}{i.reason ? ` · ${i.reason}` : ""}</li>
                      ))}
                      {data[k].count > 3 && <li>+{data[k].count - 3} more</li>}
                    </ul>
                  </li>
                ))}
              </ul>
            </>
          )}
      </div>
    </section>
  );
}
