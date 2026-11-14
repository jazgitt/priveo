import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { api } from "@/api/client";
import { Pager } from "@/blocks/DataTable";
import { Field, NONE, SelectBox } from "@/blocks/fields";
import { EmptyState, ErrorState } from "@/blocks/layout";
import { errorMessage } from "@/blocks/mutation";
import { showDate } from "@/components/format";
import { useSite } from "@/site/SiteContext";
import { Input } from "@/ui/input";
import { currentMonth } from "./monthRange";

interface Row { vehicle_id: string; registration: string; customer_name: string; cells: Record<string, string> }
interface Report { dates: string[]; rows: Row[] }

const PAGE_SIZE = 20;
/** Service filter: which cell marks count. Exterior done is EXT or Both; Interior done is INT or Both. */
const SERVICE_FILTERS: { value: string; label: string; test: (mark: string) => boolean }[] = [
  { value: "ext", label: "Exterior done", test: (m) => m.startsWith("EXT") || m.startsWith("Both") },
  { value: "int", label: "Interior done", test: (m) => m.startsWith("INT") || m.startsWith("Both") },
  { value: "both", label: "Exterior and Interior both done", test: (m) => m.startsWith("Both") },
  { value: "spa", label: "Deep Spa done", test: (m) => m.includes("SPA") },
];
const dayHead = (d: string) => showDate(d).slice(0, 6);

/** Operations > Reports: the service completed for each vehicle on each day of the period. */
export function StatusReport() {
  const site = useSite();
  const [month] = useState(currentMonth);
  const [from, setFrom] = useState(month.from);
  const [to, setTo] = useState(month.to);
  const [search, setSearch] = useState("");
  const [service, setService] = useState("");
  const [page, setPage] = useState(0);
  const valid = !!from && !!to && from <= to;
  const params = new URLSearchParams({ date_from: from, date_to: to });
  if (site.id) params.set("society_id", site.id);
  const report = useQuery({
    queryKey: ["operations-status-report", params.toString()], enabled: valid,
    queryFn: () => api<Report>(`/v1/admin/operations/job-status-report?${params}`),
  });

  const filter = SERVICE_FILTERS.find((f) => f.value === service);
  const needle = search.trim().toLowerCase().replace(/\s+/g, " ");
  const matching = (report.data?.rows ?? []).filter((r) =>
    (!needle || r.registration.toLowerCase().includes(needle) || r.customer_name.toLowerCase().includes(needle))
    && (!filter || Object.values(r.cells).some(filter.test)));
  const lastPage = Math.max(0, Math.ceil(matching.length / PAGE_SIZE) - 1);
  const current = Math.min(page, lastPage);
  const rows = matching.slice(current * PAGE_SIZE, (current + 1) * PAGE_SIZE);
  // With a service filter on, a cell shows only when it matches, so the grid reads as that service.
  const mark = (r: Row, d: string) => (r.cells[d] && (!filter || filter.test(r.cells[d])) ? r.cells[d] : "");

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-end gap-3">
        <Field label="From date" className="w-44">{(p) => <Input {...p} type="date" value={from} onChange={(e) => { setFrom(e.target.value); setPage(0); }} />}</Field>
        <Field label="To date" className="w-44">{(p) => <Input {...p} type="date" value={to} onChange={(e) => { setTo(e.target.value); setPage(0); }} />}</Field>
        <Field label="Search" className="w-64">
          {(p) => <Input {...p} type="search" placeholder="Customer name or vehicle number" value={search} onChange={(e) => { setSearch(e.target.value); setPage(0); }} />}
        </Field>
        <Field label="Service done" className="w-56">
          {(p) => <SelectBox {...p} value={service || NONE} onChange={(v) => { setService(v === NONE ? "" : v); setPage(0); }}
                             choices={[{ value: NONE, label: "All services" }, ...SERVICE_FILTERS.map((f) => ({ value: f.value, label: f.label }))]} />}
        </Field>
        <p className="m-0 pb-2 text-sm text-muted-foreground">
          EXT: Exterior done. INT: Interior done. Both: Exterior and Interior done. SPA: Deep Spa done. Up to 31 days.
        </p>
      </div>
      {!valid && <ErrorState message="Choose a first date that is not after the last date." />}
      {report.isError && <ErrorState message={errorMessage(report.error)} />}
      {report.isPending && valid && <p className="text-sm text-muted-foreground">Loading…</p>}
      {report.data && matching.length === 0 && <EmptyState title={report.data.rows.length === 0 ? "No jobs in this period" : "No vehicles match these filters"} />}
      {report.data && rows.length > 0 && (
        <div className="soft-scrollbar overflow-x-auto rounded-lg border">
          <table className="w-max min-w-full border-collapse text-sm" aria-label="Job completion by day">
            <thead className="bg-muted">
              <tr>
                <th scope="col" className="px-3 py-2 text-left font-medium">Vehicle</th>
                <th scope="col" className="px-3 py-2 text-left font-medium">Customer</th>
                {report.data.dates.map((d) => <th key={d} scope="col" className="whitespace-nowrap px-2 py-2 text-center font-medium">{dayHead(d)}</th>)}
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.vehicle_id} className="border-t">
                  <th scope="row" className="reg whitespace-nowrap px-3 py-2 text-left font-medium">{r.registration || "-"}</th>
                  <td className="whitespace-nowrap px-3 py-2">{r.customer_name}</td>
                  {report.data.dates.map((d) => (
                    <td key={d} className="px-2 py-2 text-center">
                      {mark(r, d) ? <span className="rounded bg-ok/10 px-1.5 py-0.5 text-xs font-medium">{mark(r, d)}</span> : ""}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {report.data && matching.length > 0 && (
        <Pager page={current} size={PAGE_SIZE} count={rows.length} total={matching.length} onPage={setPage} />
      )}
    </div>
  );
}
