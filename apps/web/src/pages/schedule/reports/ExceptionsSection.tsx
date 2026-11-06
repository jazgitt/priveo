import { useQuery } from "@tanstack/react-query";

import { api } from "@/api/client";
import { EmptyState, ErrorState } from "@/blocks/layout";
import { Skeleton } from "@/ui/skeleton";

import { showDate } from "../../../components/format";
import type { ReportProps, ReportSection } from ".";
import { Cell, humanise, weekEndOf, weekLabel, weekStartOf } from "./shared";

/** ExceptionReport (SCHS-27). Every kind is present, and empty when there is nothing to report. */
interface Report {
  kinds: {
    kind: string; label: string;
    rows: { date: string | null; registration: string; cleaner_name: string; code: string; detail: string }[];
  }[];
}

/** SCHS-41: the exceptions of the week that holds the chosen day (SCHR-OUT-03, SCHR-OUT-05). */
export function ExceptionsSection({ societyId, date }: ReportProps) {
  const start = weekStartOf(date), end = weekEndOf(start);
  const q = useQuery({
    queryKey: ["report-exceptions", societyId, start],
    queryFn: () => api<Report>(`/v1/admin/scheduling/reports/exceptions?society_id=${societyId}&start_date=${start}&end_date=${end}`),
  });
  if (q.isError) return <ErrorState message="The exception report could not be loaded." onRetry={() => void q.refetch()} />;
  if (!q.data) return <Skeleton className="h-24 w-full" />;
  const shown = q.data.kinds.filter((k) => k.rows.length > 0);
  if (shown.length === 0) {
    return <EmptyState title="No exceptions">{`Nothing to report for ${weekLabel(start)}.`}</EmptyState>;
  }
  return (
    <div className="flex flex-col gap-5">
      <p className="text-sm text-muted-foreground">Week of {weekLabel(start)}.</p>
      {shown.map((k) => (
        <div key={k.kind} className="flex flex-col gap-1">
          <h3 className="text-sm font-semibold">{k.label} <span className="font-normal text-muted-foreground">({k.rows.length})</span></h3>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[36rem] border-collapse">
              <thead><tr className="border-b"><Cell head>Date</Cell><Cell head>Car</Cell><Cell head>Cleaner</Cell><Cell head>Reason</Cell><Cell head>Detail</Cell></tr></thead>
              <tbody>
                {k.rows.map((r, i) => (
                  <tr key={`${r.code}-${i}`} className="border-b last:border-0">
                    <Cell>{showDate(r.date)}</Cell><Cell>{r.registration || "-"}</Cell><Cell>{r.cleaner_name || "-"}</Cell>
                    <Cell>{humanise(r.code)}</Cell><Cell>{r.detail || "-"}</Cell>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ))}
    </div>
  );
}

export const section: ReportSection = { id: "exceptions", title: "Exceptions", order: 30, component: ExceptionsSection };
