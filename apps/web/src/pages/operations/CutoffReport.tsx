import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { api } from "@/api/client";
import { Pager } from "@/blocks/DataTable";
import { Field } from "@/blocks/fields";
import { EmptyState, ErrorState } from "@/blocks/layout";
import { errorMessage } from "@/blocks/mutation";
import { showDate } from "@/components/format";
import { useSite } from "@/site/SiteContext";
import { Input } from "@/ui/input";

interface Row { vehicle_id: string; customer_name: string; model: string; registration: string; exterior_cutoff: string; interior_preferred_day: string }
interface Report { as_of: string; rows: Row[] }

const PAGE_SIZE = 20;

/** Operations > Cutoff reports: each active vehicle's Exterior cutoff and Interior preferred day, as of the day the report is run. */
export function CutoffReport() {
  const site = useSite();
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(0);
  const params = new URLSearchParams();
  if (site.id) params.set("society_id", site.id);
  const report = useQuery({
    queryKey: ["operations-cutoff-report", params.toString()],
    queryFn: () => api<Report>(`/v1/admin/operations/cutoff-report?${params}`),
  });
  const needle = search.trim().toLowerCase().replace(/\s+/g, " ");
  const matching = (report.data?.rows ?? []).filter((r) =>
    !needle || [r.registration, r.customer_name, r.model].some((t) => t.toLowerCase().includes(needle)));
  const current = Math.min(page, Math.max(0, Math.ceil(matching.length / PAGE_SIZE) - 1));
  const rows = matching.slice(current * PAGE_SIZE, (current + 1) * PAGE_SIZE);

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-end gap-3">
        <Field label="Search" className="w-72">
          {(p) => <Input {...p} type="search" placeholder="Customer, model or vehicle number" value={search} onChange={(e) => { setSearch(e.target.value); setPage(0); }} />}
        </Field>
        {report.data && <p className="m-0 pb-2 text-sm text-muted-foreground">As of {showDate(report.data.as_of)}. Active subscriptions only.</p>}
      </div>
      {report.isError && <ErrorState message={errorMessage(report.error)} />}
      {report.isPending && <p className="text-sm text-muted-foreground">Loading…</p>}
      {report.data && matching.length === 0 && <EmptyState title={report.data.rows.length === 0 ? "No active vehicles" : "No vehicles match this search"} />}
      {report.data && rows.length > 0 && (
        <div className="soft-scrollbar overflow-x-auto rounded-lg border">
          <table className="w-max min-w-full border-collapse text-sm" aria-label="Cutoff report">
            <thead className="bg-muted">
              <tr>
                {["Customer", "Model", "Vehicle no.", "Ext cutoff time", "INT preferred day"].map((h) =>
                  <th key={h} scope="col" className="px-3 py-2 text-left font-medium">{h}</th>)}
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.vehicle_id} className="border-t">
                  <td className="whitespace-nowrap px-3 py-2">{r.customer_name}</td>
                  <td className="whitespace-nowrap px-3 py-2">{r.model || "-"}</td>
                  <td className="reg whitespace-nowrap px-3 py-2 font-medium">{r.registration || "-"}</td>
                  <td className="whitespace-nowrap px-3 py-2">{r.exterior_cutoff || "-"}</td>
                  <td className="whitespace-nowrap px-3 py-2">{r.interior_preferred_day || "-"}</td>
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
