import type { ReactNode } from "react";

import { cn } from "@/lib/utils";
import { Skeleton } from "@/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/ui/table";

export interface DataColumn<T> {
  key: string;
  header: ReactNode;
  cell: (row: T) => ReactNode;
  /** A CSS width such as "12rem" or "20%". Without one the column takes what is left. */
  width?: string;
  align?: "left" | "right";
  /** Let the text wrap onto more lines. By default it is cut with "…" and shown in full on hover. */
  wrap?: boolean;
  className?: string;
}

/**
 * The portal's table: fixed column widths, long text cut and shown on hover,
 * row hover, an optional whole-row click, skeleton rows while loading and an
 * empty state. Paging and filters go in `footer` and `toolbar`.
 */
export function DataTable<T>({
  columns, rows, rowKey, loading, empty, onRowClick, rowLabel, toolbar, footer, className,
  skeletonRows = 6,
}: {
  columns: DataColumn<T>[];
  rows: T[] | undefined;
  rowKey: (row: T) => string;
  loading?: boolean;
  empty: ReactNode;
  onRowClick?: (row: T) => void;
  /** The accessible name of a clickable row. */
  rowLabel?: (row: T) => string;
  toolbar?: ReactNode;
  footer?: ReactNode;
  className?: string;
  skeletonRows?: number;
}) {
  const showSkeleton = loading && !rows;
  return (
    <div className={cn("flex flex-col gap-3", className)}>
      {toolbar}
      <div className="overflow-hidden rounded-lg border bg-card">
        <Table className="table-fixed">
          <colgroup>
            {columns.map((c) => <col key={c.key} style={c.width ? { width: c.width } : undefined} />)}
          </colgroup>
          <TableHeader className="bg-muted/60">
            <TableRow className="hover:bg-transparent">
              {columns.map((c) => (
                <TableHead key={c.key}
                           className={cn("h-9 px-3 text-xs font-semibold tracking-wide text-muted-foreground uppercase",
                             c.align === "right" && "text-right")}>
                  {c.header}
                </TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {showSkeleton && Array.from({ length: skeletonRows }, (_, i) => (
              <TableRow key={`s${i}`} className="hover:bg-transparent">
                {columns.map((c) => (
                  <TableCell key={c.key} className="px-3 py-3"><Skeleton className="h-4 w-3/4" /></TableCell>
                ))}
              </TableRow>
            ))}
            {!showSkeleton && rows?.map((row) => (
              <TableRow
                key={rowKey(row)}
                className={cn(onRowClick && "cursor-pointer")}
                onClick={onRowClick ? (e) => {
                  // A click on a link, button or field inside the row does its own thing.
                  if ((e.target as HTMLElement).closest("a,button,input,select,label,[role=switch],[role=checkbox]")) return;
                  onRowClick(row);
                } : undefined}
                onKeyDown={onRowClick ? (e) => {
                  if (e.key === "Enter" && e.target === e.currentTarget) onRowClick(row);
                } : undefined}
                tabIndex={onRowClick ? 0 : undefined}
                aria-label={rowLabel?.(row)}
              >
                {columns.map((c) => {
                  const v = c.cell(row);
                  return (
                    <TableCell key={c.key}
                               className={cn("px-3 py-2.5 align-top", c.align === "right" && "text-right",
                                 c.wrap ? "whitespace-normal break-words" : "truncate", c.className)}
                               title={!c.wrap && (typeof v === "string" || typeof v === "number") ? String(v) : undefined}>
                      {v}
                    </TableCell>
                  );
                })}
              </TableRow>
            ))}
          </TableBody>
        </Table>
        {!showSkeleton && rows?.length === 0 && <div className="border-t p-4">{empty}</div>}
      </div>
      {footer}
    </div>
  );
}

/** Previous / next paging for a list fetched in pages of `size`. */
export function Pager({ page, size, count, busy, onPage }: {
  page: number; size: number; count: number; busy?: boolean; onPage: (page: number) => void;
}) {
  if (page === 0 && count < size) return null;
  return (
    <nav aria-label="Pages" className="flex items-center justify-end gap-2 text-sm text-muted-foreground">
      <span>Page {page + 1}</span>
      <button type="button" disabled={page === 0 || busy} onClick={() => onPage(page - 1)}
              className="h-8 rounded-md border bg-card px-3 font-medium text-foreground hover:bg-accent disabled:opacity-50">
        Previous
      </button>
      <button type="button" disabled={busy || count < size} onClick={() => onPage(page + 1)}
              className="h-8 rounded-md border bg-card px-3 font-medium text-foreground hover:bg-accent disabled:opacity-50">
        Next
      </button>
    </nav>
  );
}
