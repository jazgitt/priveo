import { useQuery } from "@tanstack/react-query";

import { getSources, type Source } from "@/api/mani";
import { DataTable } from "@/blocks/DataTable";
import { DetailList, EmptyState, ErrorState } from "@/blocks/layout";
import { showDate } from "@/components/format";

const CATEGORY: Record<string, string> = { doc: "Documents", code: "Code", config: "Configuration", data: "Data" };

interface Category { kind: string; name: string; sources: number; chunks: number; failed: number; indexed: string | null }

/** One row per kind of source: how many are indexed, their chunks, and the latest index date. */
function categories(items: Source[]): Category[] {
  const by = new Map<string, Category>();
  for (const s of items) {
    if (s.status === "deleted") continue;
    const row = by.get(s.kind) ?? { kind: s.kind, name: CATEGORY[s.kind] ?? s.kind, sources: 0, chunks: 0, failed: 0, indexed: null };
    if (s.status === "failed") row.failed += 1;
    else { row.sources += 1; row.chunks += s.chunks; }
    if (s.indexed_at && (!row.indexed || s.indexed_at > row.indexed)) row.indexed = s.indexed_at;
    by.set(s.kind, row);
  }
  return [...by.values()].sort((a, b) => a.name.localeCompare(b.name));
}

/** What Mani reads, by kind of source. The full file list is not shown. */
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
        rows={list.data ? categories(list.data.items) : undefined}
        loading={list.isLoading}
        rowKey={(c) => c.kind}
        empty={<EmptyState title="No sources indexed yet" />}
        columns={[
          { key: "category", header: "Category", wrap: true, cell: (c) => <span className="font-medium">{c.name}</span> },
          { key: "sources", header: "Sources", width: "7rem", align: "right", cell: (c) => c.sources },
          { key: "chunks", header: "Chunks", width: "7rem", align: "right", cell: (c) => c.chunks },
          { key: "failed", header: "Failed", width: "7rem", align: "right", cell: (c) => c.failed },
          { key: "indexed", header: "Last indexed", width: "9rem", cell: (c) => (c.indexed ? showDate(c.indexed) : "") },
        ]}
      />
    </div>
  );
}
