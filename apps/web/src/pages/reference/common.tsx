import type { UseQueryResult } from "@tanstack/react-query";
import { Pencil } from "lucide-react";
import type { ReactNode } from "react";

import { useConfirm } from "@/blocks/confirm";
import { ErrorState } from "@/blocks/layout";
import { StatusBadge } from "@/blocks/status";
import { Button } from "@/ui/button";
import { Skeleton } from "@/ui/skeleton";

import { errorText, useDirSave } from "./api";

/** Loading and error states around a query, then the data. */
export function QueryState<T>({ query, children }: {
  query: UseQueryResult<T>;
  children: (data: T) => ReactNode;
}) {
  if (query.isLoading) return <div className="flex flex-col gap-2 p-1"><Skeleton className="h-9" /><Skeleton className="h-9" /><Skeleton className="h-9" /></div>;
  if (query.isError || query.data === undefined) return <ErrorState message={errorText(query.error)} onRetry={() => void query.refetch()} />;
  return <>{children(query.data)}</>;
}

export function ActiveChip({ active }: { active: boolean }) {
  return <StatusBadge status={active ? "Active" : "Inactive"} tone={active ? "ok" : "neutral"} />;
}

/** A failed action that has no field beside it, such as a blocked deactivation. */
export function Notice({ error }: { error: unknown }) {
  if (!error) return null;
  return <div className="mb-4"><ErrorState message={errorText(error)} /></div>;
}

/**
 * Edit plus Deactivate or Reactivate for a directory row. Deactivating asks
 * first; a blocked deactivation is shown by the page's Notice.
 */
export function RowActions({ name, active, path, onEdit, toggle, what }: {
  name: string; active: boolean; path: string; onEdit: () => void;
  toggle: ReturnType<typeof useDirSave>; what: string;
}) {
  const confirm = useConfirm();
  return (
    <div className="flex justify-end gap-1">
      <Button size="sm" variant="ghost" aria-label={`Edit ${name}`} onClick={onEdit}><Pencil aria-hidden /> Edit</Button>
      <Button size="sm" variant="ghost" className={active ? "text-destructive" : undefined} disabled={toggle.isPending}
              aria-label={`${active ? "Deactivate" : "Reactivate"} ${name}`}
              onClick={async () => {
                if (!active) toggle.mutate({ path: `${path}/reactivate`, done: `${name} reactivated.` });
                else if (await confirm({ title: `Deactivate ${name}?`, description: what, confirmLabel: "Deactivate", tone: "danger" })) {
                  toggle.mutate({ path: `${path}/deactivate`, done: `${name} deactivated.` });
                }
              }}>
        {active ? "Deactivate" : "Reactivate"}
      </Button>
    </div>
  );
}
