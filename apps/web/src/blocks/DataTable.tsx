import type { ReactNode } from "react";

import { cn } from "@/lib/utils";
import { Skeleton } from "@/ui/skeleton";
import { TileGrid, type ViewMode } from "./view";
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

const COLUMN_MIN_REM = 8;

/**
 * How wide the table must be, in rem, for every column to keep a readable
 * width. A column with a rem or px width needs that; one with no width needs
 * 8 rem; a percentage column takes its share of the whole, so the others must
 * fit in what is left (and the share itself must come to at least 8 rem).
 */
export function tableMinRem(widths: (string | undefined)[]): number {
  let fixed = 0;
  let share = 0;
  let widest = 0;
  for (const w of widths) {
    const px = /^(\d*\.?\d+)(rem|px)$/.exec(w ?? "");
    const pct = /^(\d*\.?\d+)%$/.exec(w ?? "");
    if (px) fixed += px[2] === "px" ? Number(px[1]) / 16 : Number(px[1]);
    else if (pct) { share += Number(pct[1]) / 100; widest = Math.max(widest, COLUMN_MIN_REM / (Number(pct[1]) / 100)); }
    else fixed += COLUMN_MIN_REM;
  }
  return share >= 1 ? widest : Math.max(fixed / (1 - share), widest);
}

/**
 * The portal's table: fixed column widths (on a narrow screen it scrolls
 * sideways instead of squeezing a column), long text cut and shown on hover, row hover, an optional whole-row click, skeleton rows while loading and an
 * empty state. Paging and filters go in `footer` and `toolbar`.
 */
export function DataTable<T>({
  columns, rows, rowKey, loading, empty, onRowClick, rowLabel, toolbar, footer, className,
  skeletonRows = 6, view = "list", renderTile,
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
  /** "tiles" shows each row as the tile `renderTile` draws, in a grid that follows the screen width. */
  view?: ViewMode;
  renderTile?: (row: T) => ReactNode;
}) {
  const showSkeleton = loading && !rows;
  if (view === "tiles" && renderTile) {
    return (
      <div className={cn("flex flex-col gap-3", className)}>
        {toolbar}
        <TileGrid>
          {showSkeleton && Array.from({ length: skeletonRows }, (_, i) => <Skeleton key={`s${i}`} className="h-28 rounded-xl" />)}
          {!showSkeleton && rows?.map((row) => {
            const tile = (
              <div className="h-full rounded-xl border bg-card p-4 text-left shadow-xs transition-colors hover:bg-accent/50">
                {renderTile(row)}
              </div>
            );
            return onRowClick ? (
              <button key={rowKey(row)} type="button" aria-label={rowLabel?.(row)} onClick={() => onRowClick(row)}
                      className="block h-full w-full cursor-pointer rounded-xl text-left focus-visible:ring-[3px] focus-visible:ring-ring/50 focus-visible:outline-none">
                {tile}
              </button>
            ) : <div key={rowKey(row)}>{tile}</div>;
          })}
        </TileGrid>
        {!showSkeleton && rows?.length === 0 && <div>{empty}</div>}
        {footer}
      </div>
    );
  }
  return (
    <div className={cn("flex flex-col gap-3", className)}>
      {toolbar}
      <div className="overflow-hidden rounded-lg border bg-card">
        <Table className="table-fixed" style={{ minWidth: `${tableMinRem(columns.map((c) => c.width))}rem` }}>
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

/**
 * Previous / next paging for a list fetched in pages of `size`. Give `total`
 * when the API can count the list: the pager then says "1-50 of 123" and stops
 * at the last page.
 */
export function Pager({ page, size, count, total, busy, onPage }: {
  page: number; size: number; count: number; total?: number; busy?: boolean; onPage: (page: number) => void;
}) {
  const known = total !== undefined;
  const last = known ? Math.max(0, Math.ceil(total / size) - 1) : undefined;
  if (known ? total === 0 : page === 0 && count < size) return null;
  const hasNext = known ? page < last! : count >= size;
  return (
    <nav aria-label="Pages" className="flex flex-wrap items-center justify-end gap-2 text-sm text-muted-foreground">
      <span>
        {known
          ? `${page * size + 1}-${page * size + count} of ${total} · Page ${page + 1} of ${last! + 1}`
          : `Page ${page + 1}`}
      </span>
      <button type="button" disabled={page === 0 || busy} onClick={() => onPage(page - 1)}
              className="h-8 rounded-md border bg-card px-3 font-medium text-foreground hover:bg-accent disabled:opacity-50">
        Previous
      </button>
      <button type="button" disabled={busy || !hasNext} onClick={() => onPage(page + 1)}
              className="h-8 rounded-md border bg-card px-3 font-medium text-foreground hover:bg-accent disabled:opacity-50">
        Next
      </button>
    </nav>
  );
}
