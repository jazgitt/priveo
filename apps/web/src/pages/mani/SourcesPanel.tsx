import { useQuery } from "@tanstack/react-query";

import { getSources, type Source } from "@/api/mani";
import { DataTable } from "@/blocks/DataTable";
import { DetailList, EmptyState, ErrorState } from "@/blocks/layout";
import { StatusBadge } from "@/blocks/status";
import { showDate } from "@/components/format";

const STATUS: Record<Source["status"], { label: string; tone: "ok" | "neutral" | "error" }> = {
  active: { label: "Active", tone: "ok" },
  deleted: { label: "Deleted", tone: "neutral" },
  failed: { label: "Failed", tone: "error" },
};

/** The files Mani reads, with when each was last indexed. */
export function SourcesPanel() {
  const list = useQuery({ queryKey: ["mani", "sources"], queryFn: getSources });
  return (
    <div className="flex flex-col gap-4">
      {list.isError && <ErrorState message="Could not load the sources." onRetry={() => void list.refetch()} />}
      {list.data && (
        <DetailList columns={2} items={[
          { label: "Embedding model", value: list.data.embedding_model },
          { label: "Last indexed", value: list.data.last_indexed_at ? showDate(list.data.last_indexed_at) : "" },
        ]} />
      )}
      <DataTable
        rows={list.data?.items}
        loading={list.isLoading}
        rowKey={(s) => s.path}
        empty={<EmptyState title="No sources indexed yet" />}
        columns={[
          { key: "title", header: "Source", wrap: true, cell: (s) => (<><span className="font-medium">{s.title}</span><br /><span className="text-xs text-muted-foreground">{s.path}</span></>) },
          { key: "kind", header: "Kind", width: "6rem", cell: (s) => s.kind },
          { key: "status", header: "Status", width: "7rem", cell: (s) => <StatusBadge status={STATUS[s.status].label} tone={STATUS[s.status].tone} /> },
          { key: "indexed", header: "Indexed", width: "8rem", cell: (s) => showDate(s.indexed_at) },
          { key: "chunks", header: "Chunks", width: "6rem", align: "right", cell: (s) => s.chunks },
        ]}
      />
    </div>
  );
}
