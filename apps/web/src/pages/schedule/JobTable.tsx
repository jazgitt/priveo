import { ArrowDown, ArrowUp, Download } from "lucide-react";
import { useState, type ReactNode } from "react";

import { StatusBadge } from "@/blocks/status";
import { cn } from "@/lib/utils";
import { Button } from "@/ui/button";
import { TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/ui/table";

import { JobFlags, serviceCode, typeClass, zoneShort, zonesOf, zoneStyle } from "./Board";
import type { Density } from "./CardBoard";
import { Scroller } from "./Scroller";
import type { AdminJob } from "./api";

type SortKey = "time" | "crew" | "vehicle" | "customer" | "parking" | "service" | "duration" | "finish" | "status";

const UNASSIGNED = "Unassigned";

/** What a column sorts by. Unplaced jobs have no time, so they come first. */
const sortValue = (j: AdminJob, key: SortKey): string | number => {
  switch (key) {
    case "time": return j.start_minute ?? -1;
    case "crew": return (j.crew_name ?? "").toLowerCase();
    case "vehicle": return j.registration.toLowerCase();
    case "customer": return j.customer_name.toLowerCase();
    case "parking": return (j.parking ?? "").toLowerCase();
    case "service": return j.service.toLowerCase();
    case "duration": return j.duration_minutes;
    case "finish": return j.finish_by ?? "";
    case "status": return j.status.toLowerCase();
  }
};

function compare(a: AdminJob, b: AdminJob, key: SortKey): number {
  const x = sortValue(a, key);
  const y = sortValue(b, key);
  const c = typeof x === "number" && typeof y === "number" ? x - y : String(x).localeCompare(String(y));
  // Ties keep the day's order: by crew member, then by time.
  return c || (a.crew_name ?? "").localeCompare(b.crew_name ?? "") || (a.start_minute ?? -1) - (b.start_minute ?? -1);
}

/** One CSV cell. A value a spreadsheet could run as a formula gets a leading quote. */
export function csvCell(value: string | number | null | undefined): string {
  let v = value === null || value === undefined ? "" : String(value);
  if (/^[=+\-@\t\r]/.test(v)) v = `'${v}`;
  return /[",\n\r]/.test(v) ? `"${v.replace(/"/g, '""')}"` : v;
}

const timeOf = (j: AdminJob) => (j.start_time ? `${j.start_time}-${j.end_time}` : "Unscheduled");

/** The CSV of the jobs shown, in the order shown. */
export function jobsCsv(jobs: AdminJob[]): string {
  const head = ["Time", "Crew", "Registration", "Vehicle", "Customer", "Parking", "Service", "Duration (min)", "Finish by", "Status", "Late", "By hand", "Reason"];
  const rows = jobs.map((j) => [timeOf(j), j.crew_name ?? UNASSIGNED, j.registration, j.vehicle, j.customer_name, j.parking ?? "",
    j.service, j.duration_minutes, j.finish_by ?? "", j.status, j.late ? "Yes" : "", j.manual ? "Yes" : "", j.reason ?? ""]);
  return [head, ...rows].map((r) => r.map(csvCell).join(",")).join("\r\n");
}

/**
 * The chosen day's jobs as a table: every job with its crew member and card
 * details, sorted by any column. Opening a row opens the job's dialog, where it
 * can be moved; the table itself changes nothing (ADM-SCH-33).
 */
export function JobTable({ jobs, total, fileName, onOpen, density = "standard", faded }: {
  /** The jobs to show, already filtered by the search and the chips (or all of them with "Show all"). */
  jobs: AdminJob[];
  /** With "Show all" on: a row the filters do not keep, shown in disabled form (P1-4). */
  faded?: (job: AdminJob) => boolean;
  /** All jobs of the day, to say how many are hidden by the filters. */
  total: number;
  fileName: string;
  onOpen: (job: AdminJob) => void;
  /** Compact hides the customer, parking and notes columns; detailed adds each job's zone. */
  density?: Density;
}) {
  const [sort, setSort] = useState<{ key: SortKey; dir: 1 | -1 }>({ key: "crew", dir: 1 });
  const zones = zonesOf(jobs);
  const wide = density !== "compact";
  const rows = [...jobs].sort((a, b) => sort.dir * compare(a, b, sort.key));
  const choose = (key: SortKey) => setSort((s) => (s.key === key ? { key, dir: s.dir === 1 ? -1 : 1 } : { key, dir: 1 }));

  const download = () => {
    const url = URL.createObjectURL(new Blob(["\uFEFF", jobsCsv(rows)], { type: "text/csv;charset=utf-8" }));
    const a = document.createElement("a");
    a.href = url;
    a.download = fileName;
    a.click();
    URL.revokeObjectURL(url);
  };

  const head = (key: SortKey, label: string, className?: string) => (
    <TableHead scope="col" aria-sort={sort.key === key ? (sort.dir === 1 ? "ascending" : "descending") : "none"}
               className={cn("sticky top-0 z-10 h-9 bg-muted px-3 text-xs font-semibold tracking-wide whitespace-nowrap text-muted-foreground uppercase", className)}>
      <button type="button" onClick={() => choose(key)} className="inline-flex items-center gap-1 uppercase hover:text-foreground">
        {label}
        {sort.key === key && (sort.dir === 1 ? <ArrowUp className="size-3" aria-hidden /> : <ArrowDown className="size-3" aria-hidden />)}
      </button>
    </TableHead>
  );
  const cell = (children: ReactNode, className?: string) => (
    <TableCell className={cn("px-3 py-1.5 align-middle whitespace-nowrap", className)}>{children}</TableCell>
  );

  return (
    <div className="sch-fill">
      <Scroller axis="y" wrapClassName="sch-table-wrap" className="sch-table" role="region" aria-label="Jobs of the day">
        <table className={cn("w-full caption-bottom text-sm", wide ? "min-w-[64rem]" : "min-w-[40rem]")}>
          <TableHeader>
            <TableRow className="hover:bg-transparent">
              {head("time", "Time")}
              {head("crew", "Crew")}
              {head("vehicle", "Vehicle")}
              {wide && head("customer", "Customer")}
              {wide && head("parking", "Parking")}
              {head("service", "Service")}
              {head("duration", "Min", "text-right")}
              {head("finish", "Finish by")}
              {head("status", "Status")}
              {wide && <TableHead scope="col" className="sticky top-0 z-10 h-9 bg-muted px-3 text-xs font-semibold tracking-wide text-muted-foreground uppercase">Notes</TableHead>}
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.map((j) => {
              const off = faded?.(j) ?? false;
              return (
              <TableRow key={j.id} tabIndex={0} className={cn("cursor-pointer", off && "sch-row-dim")} aria-label={`${j.registration}, ${j.crew_name ?? UNASSIGNED}`}
                        aria-disabled={off || undefined}
                        onClick={() => { if (!off) onOpen(j); }}
                        onKeyDown={(e) => { if (!off && e.key === "Enter" && e.target === e.currentTarget) onOpen(j); }}>
                {cell(<span className="tabular-nums font-medium">{timeOf(j)}</span>)}
                {cell(j.crew_name ?? <span className="text-muted-foreground italic">{UNASSIGNED}</span>)}
                {cell(
                  <span className="flex flex-col leading-tight">
                    <strong className="reg inline-flex items-center gap-1.5">
                      {density === "detailed" && j.zone && (
                        <span className="sch-zone" style={zoneStyle(j.zone, zones)}>{zoneShort(j.zone)}</span>
                      )}
                      {j.registration}
                    </strong>
                    <span className="text-xs text-muted-foreground">{j.vehicle}</span>
                  </span>)}
                {wide && cell(j.customer_name, "max-w-[12rem] truncate")}
                {wide && cell(j.parking || "-")}
                {cell(<span className={cn("sch-kind", typeClass(j))}><i aria-hidden />{serviceCode(j.service)}<span className="sr-only"> {j.service}</span></span>)}
                {cell(j.duration_minutes, "text-right tabular-nums")}
                {cell(j.finish_by ?? "-")}
                {cell(<StatusBadge status={j.status} />)}
                {wide && cell(
                  <span className="flex items-center gap-1.5">
                    <JobFlags job={j} />
                    {j.reason && <span className="max-w-[16rem] truncate text-xs text-muted-foreground" title={j.reason}>{j.reason}</span>}
                  </span>)}
              </TableRow>
              );
            })}
            {rows.length === 0 && (
              <TableRow className="hover:bg-transparent">
                <TableCell colSpan={wide ? 10 : 7} className="px-3 py-6 text-center text-sm text-muted-foreground">
                  {total === 0 ? "No jobs on this day." : "No job matches the search and filters."}
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </table>
      </Scroller>
      <div className="flex flex-wrap items-center justify-between gap-2 pt-2 text-sm text-muted-foreground">
        <span role="status">{rows.length === total ? `${total} ${total === 1 ? "job" : "jobs"}` : `${rows.length} of ${total} jobs`}</span>
        <Button size="sm" variant="outline" className="h-8" disabled={rows.length === 0} onClick={download}>
          <Download aria-hidden /> Export CSV
        </Button>
      </div>
    </div>
  );
}
