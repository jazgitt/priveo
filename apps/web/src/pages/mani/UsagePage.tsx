import { useQuery } from "@tanstack/react-query";

import { getUsage } from "@/api/mani";
import { DataTable } from "@/blocks/DataTable";
import { EmptyState, ErrorState, PageHeader, StatRow, StatTile } from "@/blocks/layout";
import { showDate } from "@/components/format";
import { ManiGate } from "./ManiGate";

const usd = (n: number) => `$${n.toFixed(2)}`;

function Usage() {
  const q = useQuery({ queryKey: ["mani", "usage"], queryFn: getUsage });
  const u = q.data;
  return (
    <>
      <PageHeader title="Agent" description="What Mani Bond has used against the budget. Counts and cost only, never what was said." />
      {q.isError && <div className="mb-4"><ErrorState message="Could not load the usage." onRetry={() => void q.refetch()} /></div>}
      {u?.budget_exhausted && (
        <p role="alert" className="mb-4 rounded-lg border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm text-destructive">
          The budget is used up. Mani will not answer until the budget is raised.
        </p>
      )}
      <StatRow label="Usage">
        <StatTile label="Budget" value={u ? usd(u.budget_usd) : ""} loading={!u} />
        <StatTile label="Spent" value={u ? usd(u.spent_usd) : ""} loading={!u} />
        <StatTile label="Remaining" value={u ? usd(u.remaining_usd) : ""} loading={!u} hint={u?.budget_exhausted ? "Budget used up" : undefined} />
        <StatTile label="Failed calls" value={u?.failed_calls ?? 0} loading={!u} />
        <StatTile label="Average latency" value={u ? `${u.average_latency_ms} ms` : ""} loading={!u} />
      </StatRow>
      <DataTable
        rows={u?.days}
        loading={q.isLoading}
        rowKey={(d) => d.day}
        empty={<EmptyState title="No usage yet" />}
        columns={[
          { key: "day", header: "Day", cell: (d) => showDate(d.day) },
          { key: "calls", header: "Calls", align: "right", cell: (d) => d.calls },
          { key: "prompt", header: "Prompt tokens", align: "right", cell: (d) => d.prompt_tokens.toLocaleString("en-IN") },
          { key: "completion", header: "Answer tokens", align: "right", cell: (d) => d.completion_tokens.toLocaleString("en-IN") },
          { key: "cost", header: "Cost", align: "right", cell: (d) => usd(d.cost_usd) },
        ]}
      />
    </>
  );
}

/** Reports > Agent: Mani Bond's spend against the budget (Founder only). */
export function UsagePage() {
  return <ManiGate><Usage /></ManiGate>;
}
