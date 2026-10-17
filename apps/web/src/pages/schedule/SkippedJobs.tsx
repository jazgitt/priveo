import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { api } from "@/api/client";
import { DataTable } from "@/blocks/DataTable";
import { Field, SelectBox } from "@/blocks/fields";
import { ErrorState, Panel } from "@/blocks/layout";
import { errorMessage } from "@/blocks/mutation";
import { StatusBadge } from "@/blocks/status";
import { Input } from "@/ui/input";

import { JobLabel } from "./Board";
import { fmtDate, weekday, type AdminJob } from "./api";

const KINDS = [
  { value: "all", label: "Skipped and paused" },
  { value: "Skipped", label: "Skipped only" },
  { value: "Paused", label: "Paused only" },
];

function plusDays(iso: string, n: number): string {
  const d = new Date(`${iso}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() + n);
  return d.toISOString().slice(0, 10);
}

/**
 * Jobs that will not be done because they were skipped or paused, with who
 * did it. They are kept off the Board so it shows only work to do (ADM-SCH-36).
 */
export function SkippedJobs({ societyId, from: initialFrom }: { societyId: string; from: string }) {
  const [from, setFrom] = useState(initialFrom);
  const [to, setTo] = useState(plusDays(initialFrom, 6));
  const [kind, setKind] = useState("all");
  const valid = Boolean(from && to && to >= from);
  const q = useQuery({
    queryKey: ["skipped", societyId, from, to],
    enabled: Boolean(societyId) && valid,
    queryFn: () => api<AdminJob[]>(`/v1/admin/scheduling/skipped?${new URLSearchParams({
      society_id: societyId, date_from: from, date_to: to })}`),
  });
  const rows = (q.data ?? []).filter((j) => kind === "all" || j.skip_kind === kind);
  return (
    <Panel title="Skipped and paused"
           description="Jobs that will not be done on these dates, and who skipped or paused them. They are not on the Board."
           bodyClassName="p-0">
      <div className="grid grid-cols-1 items-end gap-4 border-b p-4 sm:grid-cols-[11rem_11rem_13rem]">
        <Field label="From">{(p) => <Input {...p} type="date" value={from} onChange={(e) => setFrom(e.target.value)} />}</Field>
        <Field label="To" error={valid ? undefined : "Choose a date on or after From."}>
          {(p) => <Input {...p} type="date" value={to} onChange={(e) => setTo(e.target.value)} />}
        </Field>
        <Field label="Show">{(p) => <SelectBox {...p} value={kind} onChange={setKind} choices={KINDS} />}</Field>
      </div>
      {q.isError ? <div className="p-4"><ErrorState message={errorMessage(q.error)} onRetry={() => void q.refetch()} /></div> : (
        <DataTable
          className="[&>div]:rounded-none [&>div]:border-0"
          rows={valid ? rows : []}
          loading={valid && q.isPending}
          rowKey={(j) => j.id}
          empty={<p className="text-sm text-muted-foreground">Nothing was skipped or paused on these dates.</p>}
          columns={[
            { key: "d", header: "Date", width: "8rem", cell: (j) => `${weekday(j.date)} ${fmtDate(j.date)}` },
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
