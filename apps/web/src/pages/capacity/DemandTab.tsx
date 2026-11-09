import { useState } from "react";

import { DataTable } from "@/blocks/DataTable";
import { Field, SelectBox } from "@/blocks/fields";
import { EmptyState, ErrorState } from "@/blocks/layout";
import { Input } from "@/ui/input";

import { errorText, fmtDate, weekday } from "../schedule/api";
import { useDemandList } from "./demandApi";

const SERVICES = [
  { value: "All", label: "All services" },
  { value: "Cleaning-External", label: "Exterior" },
  { value: "Cleaning-Internal", label: "Interior" },
  { value: "Deep Spa", label: "Deep Spa" },
];

/**
 * The jobs due on one date (P3-2.2). The list keeps the server's order:
 * Exteriors by cutoff, then Interiors by cutoff, then the other services by cutoff.
 * Search matches the registration and the car; the service filter asks the server.
 */
export function DemandTab({ societyId, date, onDateChange }: {
  societyId: string; date: string; onDateChange: (iso: string) => void;
}) {
  const [service, setService] = useState("All");
  const [query, setQuery] = useState("");
  const listQ = useDemandList(societyId, date, service);
  const needle = query.trim().toLowerCase();
  // The number is the job's place in the day's order, so it stays put while the search narrows the list.
  const numbered = (listQ.data ?? []).map((item, i) => ({ item, n: i + 1 }));
  const rows = needle
    ? numbered.filter(({ item }) => `${item.registration} ${item.vehicle}`.toLowerCase().includes(needle))
    : numbered;

  return (
    <DataTable
      rows={rows}
      loading={listQ.isLoading}
      rowKey={(r) => `${r.n}-${r.item.vehicle_id}-${r.item.service}`}
      toolbar={(
        <div className="flex flex-wrap items-end gap-3">
          <Field label="Date" className="w-44">{(p) => <Input {...p} type="date" value={date} onChange={(e) => onDateChange(e.target.value)} />}</Field>
          <Field label="Service" className="w-44">{(p) => <SelectBox {...p} value={service} onChange={setService} choices={SERVICES} />}</Field>
          <Field label="Search" className="w-56">{(p) => (
            <Input {...p} type="search" value={query} placeholder="Registration or car" onChange={(e) => setQuery(e.target.value)} />
          )}</Field>
          {listQ.isError && <ErrorState message={errorText(listQ.error)} onRetry={() => void listQ.refetch()} />}
          {listQ.data && (
            <p className="m-0 pb-2 text-sm text-muted-foreground">
              {`${rows.length} of ${numbered.length} ${numbered.length === 1 ? "job" : "jobs"} on ${weekday(date)} ${fmtDate(date)}`}
            </p>
          )}
        </div>
      )}
      empty={<EmptyState title="No jobs due">Nothing is due on this date for the chosen service.</EmptyState>}
      columns={[
        { key: "n", header: "#", width: "3.5rem", align: "right", cell: (r) => r.n },
        { key: "s", header: "Service", width: "10rem", cell: (r) => <span className="font-medium">{r.item.service_label}</span> },
        { key: "c", header: "Car", cell: (r) => r.item.vehicle || "-" },
        { key: "r", header: "Registration", width: "10rem", cell: (r) => r.item.registration || "-" },
        { key: "k", header: "Cutoff", width: "8rem", align: "right", cell: (r) => r.item.cutoff ?? "-" },
        { key: "src", header: "Source", width: "9rem", cell: (r) => r.item.source },
      ]}
    />
  );
}
