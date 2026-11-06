import { useQuery } from "@tanstack/react-query";
import type { ReactNode } from "react";

import { api, ApiError } from "@/api/client";
import { EmptyState, ErrorState } from "@/blocks/layout";
import { Skeleton } from "@/ui/skeleton";

import type { ReportProps, ReportSection } from ".";
import { Cell, humanise, plain, weekLabel, weekStartOf } from "./shared";

/**
 * The weekly summary endpoint is SCHS-39. Its field list is not fixed here, so the section shows what
 * the endpoint returns: single values as a list, lists of rows as tables, groups as nested lists.
 * Derived (SCHR-OUT-02): the call is `reports/weekly?society_id&start_date` for the week that holds the day.
 */
type Json = Record<string, unknown>;

const isRows = (v: unknown): v is Json[] => Array.isArray(v) && v.length > 0 && v.every((x) => typeof x === "object" && x !== null);
const hidden = (key: string) => key === "society_id" || key === "end_date" || key === "start_date" || key === "week_start";

function Block({ data }: { data: Json }): ReactNode {
  const entries = Object.entries(data).filter(([k]) => !hidden(k));
  const scalars = entries.filter(([, v]) => !isRows(v) && (typeof v !== "object" || v === null));
  return (
    <div className="flex flex-col gap-4">
      {scalars.length > 0 && (
        <dl className="grid gap-1 text-sm sm:grid-cols-[16rem_1fr]">
          {scalars.map(([k, v]) => (
            <div key={k} className="contents"><dt className="text-muted-foreground">{humanise(k)}</dt><dd className="m-0 font-medium">{plain(v)}</dd></div>
          ))}
        </dl>
      )}
      {entries.filter(([, v]) => isRows(v)).map(([k, v]) => {
        const rows = v as Json[];
        const cols = Object.keys(rows[0]);
        return (
          <div key={k} className="flex flex-col gap-1">
            <h3 className="text-sm font-semibold">{humanise(k)}</h3>
            <div className="overflow-x-auto">
              <table className="w-full border-collapse">
                <thead><tr className="border-b">{cols.map((c) => <Cell head key={c}>{humanise(c)}</Cell>)}</tr></thead>
                <tbody>{rows.map((r, i) => <tr key={i} className="border-b last:border-0">{cols.map((c) => <Cell key={c}>{plain(r[c])}</Cell>)}</tr>)}</tbody>
              </table>
            </div>
          </div>
        );
      })}
      {entries.filter(([, v]) => typeof v === "object" && v !== null && !Array.isArray(v)).map(([k, v]) => (
        <div key={k} className="flex flex-col gap-1">
          <h3 className="text-sm font-semibold">{humanise(k)}</h3>
          <Block data={v as Json} />
        </div>
      ))}
    </div>
  );
}

const isEmpty = (d: Json): boolean => Object.entries(d).filter(([k]) => !hidden(k)).every(([, v]) =>
  v === null || v === 0 || v === "" || (Array.isArray(v) && v.length === 0) || (typeof v === "object" && !Array.isArray(v) && isEmpty(v as Json)));

/** SCHS-41: the weekly summary of the week that holds the chosen day (SCHR-OUT-02, SCHR-OUT-05). */
export function WeeklySection({ societyId, date }: ReportProps) {
  const start = weekStartOf(date);
  const q = useQuery({
    queryKey: ["report-weekly", societyId, start],
    queryFn: () => api<Json>(`/v1/admin/scheduling/reports/weekly?society_id=${societyId}&start_date=${start}`),
    retry: false,
  });
  if (q.error instanceof ApiError && q.error.status === 404) {
    return <EmptyState title="Not available yet">The weekly summary is not available on this server yet.</EmptyState>;
  }
  if (q.isError) return <ErrorState message="The weekly summary could not be loaded." onRetry={() => void q.refetch()} />;
  if (!q.data) return <Skeleton className="h-24 w-full" />;
  if (isEmpty(q.data)) return <EmptyState title="Nothing this week">{`No work to summarise for ${weekLabel(start)}.`}</EmptyState>;
  return (
    <div className="flex flex-col gap-3">
      <p className="text-sm text-muted-foreground">Week of {weekLabel(start)}.</p>
      <Block data={q.data} />
    </div>
  );
}

export const section: ReportSection = { id: "weekly", title: "Weekly summary", order: 20, component: WeeklySection };
