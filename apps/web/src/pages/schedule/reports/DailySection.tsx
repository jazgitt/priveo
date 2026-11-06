import { useQuery } from "@tanstack/react-query";

import { api } from "@/api/client";
import { EmptyState, ErrorState } from "@/blocks/layout";
import { Skeleton } from "@/ui/skeleton";

import { showDate } from "../../../components/format";
import type { ReportProps, ReportSection } from ".";
import { breakText, Cell, humanise } from "./shared";

/** DailyView (SCHS-26): the day, cleaner by cleaner. */
interface Daily {
  cleaners: {
    cleaner_id: string;
    name: string;
    break_window: Record<string, unknown> | null;
    free_slots: Record<string, unknown>[] | null;
    jobs: {
      job_id: string; registration: string; zone: string; type: string; start_time: string; end_time: string;
      cutoff: string; exceptions: { code: string; detail: string }[]; cross_zone_reason: string | null;
    }[];
  }[];
}

/** SCHS-41: the cleaner-wise view of one day (SCHR-OUT-01, SCHR-OUT-05). */
export function DailySection({ societyId, date }: ReportProps) {
  const q = useQuery({
    queryKey: ["report-daily", societyId, date],
    queryFn: () => api<Daily>(`/v1/admin/scheduling/reports/daily?society_id=${societyId}&date=${date}`),
  });
  if (q.isError) return <ErrorState message="The daily view could not be loaded." onRetry={() => void q.refetch()} />;
  if (!q.data) return <Skeleton className="h-24 w-full" />;
  if (q.data.cleaners.length === 0) {
    return <EmptyState title="No jobs planned">{`No cleaner has a job on ${showDate(date)}.`}</EmptyState>;
  }
  return (
    <div className="flex flex-col gap-5">
      {q.data.cleaners.map((c) => (
        <div key={c.cleaner_id} className="flex flex-col gap-1">
          <h3 className="text-sm font-semibold">
            {c.name || "Cleaner"}
            <span className="ml-2 font-normal text-muted-foreground">
              {c.jobs.length} {c.jobs.length === 1 ? "job" : "jobs"}{breakText(c.break_window) ? ` · Break ${breakText(c.break_window)}` : ""}
            </span>
          </h3>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[40rem] border-collapse">
              <thead><tr className="border-b">
                <Cell head>Car</Cell><Cell head>Zone</Cell><Cell head>Type</Cell><Cell head>Start</Cell>
                <Cell head>End</Cell><Cell head>Cutoff</Cell><Cell head>Notes</Cell>
              </tr></thead>
              <tbody>
                {c.jobs.map((j) => (
                  <tr key={j.job_id} className="border-b last:border-0">
                    <Cell>{j.registration}</Cell><Cell>{j.zone || "-"}</Cell><Cell>{j.type}</Cell>
                    <Cell>{j.start_time}</Cell><Cell>{j.end_time}</Cell><Cell>{j.cutoff || "-"}</Cell>
                    <Cell>
                      {[...j.exceptions.map((e) => humanise(e.code)), ...(j.cross_zone_reason ? [`Cross-zone: ${j.cross_zone_reason}`] : [])].join(", ") || "-"}
                    </Cell>
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

export const section: ReportSection = { id: "daily", title: "Daily cleaner view", order: 10, component: DailySection };
