import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { api } from "@/api/client";
import { DataTable } from "@/blocks/DataTable";
import { Field, SelectBox } from "@/blocks/fields";
import { ErrorState, Panel } from "@/blocks/layout";
import { errorMessage } from "@/blocks/mutation";
import { StatusBadge } from "@/blocks/status";

import { JobLabel } from "./Board";
import { fmtDate, weekday, type AdminJob } from "./api";

const KINDS = [
  { value: "all", label: "Skipped and paused" },
  { value: "Skipped", label: "Skipped only" },
  { value: "Paused", label: "Paused only" },
];

/**
 * The jobs of the chosen day that will not be done because they were skipped
 * or paused, with who did it. They are kept off the Board so it shows only
 * work to do (ADM-SCH-36).
 */
export function SkippedJobs({ societyId, date }: { societyId: string; date: string }) {
  const [kind, setKind] = useState("all");
  const q = useQuery({
    queryKey: ["skipped", societyId, date, date],
    enabled: Boolean(societyId && date),
    queryFn: () => api<AdminJob[]>(`/v1/admin/scheduling/skipped?${new URLSearchParams({
      society_id: societyId, date_from: date, date_to: date })}`),
  });
  const rows = (q.data ?? []).filter((j) => kind === "all" || j.skip_kind === kind);
  return (
    <Panel title={`Skipped and paused on ${weekday(date)} ${fmtDate(date)}`}
           description="Jobs of this day that will not be done, and who skipped or paused them. They are not on the Board."
           actions={<div className="w-48"><Field label="Show">{(p) => <SelectBox {...p} value={kind} onChange={setKind} choices={KINDS} />}</Field></div>}
           bodyClassName="p-0">
      {q.isError ? <div className="p-4"><ErrorState message={errorMessage(q.error)} onRetry={() => void q.refetch()} /></div> : (
        <DataTable
          className="[&>div]:rounded-none [&>div]:border-0"
          rows={rows}
          loading={q.isPending}
          rowKey={(j) => j.id}
          empty={<p className="text-sm text-muted-foreground">Nothing was skipped or paused on this day.</p>}
          columns={[
            { key: "v", header: "Vehicle", width: "14rem", cell: (j) => <JobLabel job={j} /> },
            { key: "c", header: "Customer", width: "12rem", cell: (j) => j.customer_name },
            { key: "k", header: "Type", width: "7rem",
              cell: (j) => <StatusBadge status={j.skip_kind || "Skipped"} tone={j.skip_kind === "Paused" ? "info" : "neutral"} /> },
            { key: "w", header: "Why", wrap: true, cell: (j) => j.skip_reason || "-" },
          ]}
        />
      )}
    </Panel>
  );
}
