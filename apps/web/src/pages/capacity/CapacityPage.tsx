import { useState } from "react";

import { DataTable } from "@/blocks/DataTable";
import { Field, SelectBox } from "@/blocks/fields";
import { EmptyState, ErrorState, PageHeader, StatRow, StatTile } from "@/blocks/layout";
import { StatusBadge } from "@/blocks/status";
import { HoverTip, TipRows, type TipRow } from "@/components";
import { cn } from "@/lib/utils";
import { useSite } from "@/site/SiteContext";
import { Input } from "@/ui/input";

import {
  errorText, fmtDate, fmtHours, nextSunday, useCapacity, weekday,
} from "../schedule/api";

/** A capacity figure with its breakup on hover (ADM-CAP-06). */
function Tip({ label, title, rows, empty }: { label: string; title: string; rows: TipRow[]; empty: string }) {
  return (
    <HoverTip label={label} ariaLabel={`${title} ${label}. Hover for the breakup.`}>
      <TipRows title={title} rows={rows} empty={empty} />
    </HoverTip>
  );
}

const SPANS = [{ value: "1", label: "1 day" }, { value: "7", label: "7 days" }, { value: "14", label: "14 days" }, { value: "31", label: "31 days" }];

/** Crew hours against the work due, by date, for the chosen site (ADM-CAP-01 to -06). */
export function CapacityPage() {
  const site = useSite();
  const societyId = site.id;
  const [startDate, setStartDate] = useState(nextSunday());
  const [days, setDays] = useState("7");
  const capQ = useCapacity(societyId, startDate, Number(days));
  const days_ = capQ.data;
  const over = days_?.filter((d) => d.over_capacity).length ?? 0;
  const sum = (f: (d: NonNullable<typeof days_>[number]) => number) => days_?.reduce((t, d) => t + f(d), 0) ?? 0;
  const use = (d: NonNullable<typeof days_>[number]) =>
    d.capacity_minutes > 0 ? Math.round((d.demand_minutes / d.capacity_minutes) * 100) : d.demand_minutes > 0 ? 100 : 0;
  const capacity = sum((d) => d.capacity_minutes);
  const demand = sum((d) => d.demand_minutes);
  const peak = days_?.reduce((m, d) => Math.max(m, use(d)), 0) ?? 0;
  const loading = capQ.isLoading;

  return (
    <>
      <PageHeader title="Capacity Utilisation" site={site.name || undefined}
                  description="Crew hours available against the work due. Act on red days before scheduling." />
      {!societyId ? <EmptyState title="Choose a site">Pick a site at the top left.</EmptyState> : (
        <>
          <StatRow label="Capacity summary">
            <StatTile label="Days shown" value={days_?.length} loading={loading} />
            <StatTile label="Days over capacity" value={over} loading={loading} hint={over > 0 ? "Act before scheduling" : "None"} />
            <StatTile label="Crew available" value={fmtHours(capacity)} loading={loading} />
            <StatTile label="Demand" value={fmtHours(demand)} loading={loading} />
            <StatTile label="Scheduled" value={fmtHours(sum((d) => d.scheduled_minutes))} loading={loading} />
            <StatTile label="Overall use" value={`${capacity > 0 ? Math.round((demand / capacity) * 100) : demand > 0 ? 100 : 0}%`}
                      loading={loading} hint={`Busiest day ${peak}%`} />
          </StatRow>
          <DataTable
            rows={capQ.data}
            loading={capQ.isLoading}
            rowKey={(d) => d.date}
            toolbar={(
              <div className="flex flex-wrap items-end gap-3">
                <Field label="From" className="w-44">{(p) => <Input {...p} type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} />}</Field>
                <Field label="Days" className="w-36">{(p) => <SelectBox {...p} value={days} onChange={setDays} choices={SPANS} />}</Field>
                {capQ.isError && <ErrorState message={errorText(capQ.error)} onRetry={() => void capQ.refetch()} />}
                {capQ.data && (
                  <p className={cn("m-0 pb-2 text-sm", over > 0 ? "font-medium text-destructive" : "text-muted-foreground")}>
                    {over > 0 ? `${over} ${over === 1 ? "day is" : "days are"} over capacity.` : "No day is over capacity."}
                  </p>
                )}
              </div>
            )}
            empty={<EmptyState title="No dates">Choose a start date.</EmptyState>}
            columns={[
              { key: "d", header: "Date", width: "9rem", cell: (d) => `${weekday(d.date)} ${fmtDate(d.date)}` },
              { key: "c", header: "Crew available", width: "9rem", align: "right", className: "overflow-visible", cell: (d) => (
                <Tip label={fmtHours(d.capacity_minutes)} title="Crew available" empty="No crew available"
                     rows={(d.crew ?? []).map((c) => ({ key: c.name + c.slots, left: `${c.name} (${c.role})`, right: fmtHours(c.minutes), note: c.slots }))} />) },
              { key: "n", header: "Demand", width: "8rem", align: "right", className: "overflow-visible", cell: (d) => (
                <Tip label={fmtHours(d.demand_minutes)} title="Demand" empty="Nothing due"
                     rows={(d.demand ?? []).map((l) => ({
                       key: l.service + l.source, left: `${l.service}${l.source === "Add-on" ? " (add-on)" : ""}`,
                       right: fmtHours(l.minutes), note: `${l.jobs} ${l.jobs === 1 ? "job" : "jobs"}` }))} />) },
              { key: "s", header: "Scheduled", width: "8rem", align: "right", cell: (d) => fmtHours(d.scheduled_minutes) },
              { key: "u", header: "Use", cell: (d) => {
                const pct = d.capacity_minutes > 0 ? Math.min(100, Math.round((d.demand_minutes / d.capacity_minutes) * 100)) : d.demand_minutes > 0 ? 100 : 0;
                return (
                  <div className="flex items-center gap-3">
                    <div className="h-2 min-w-24 flex-1 overflow-hidden rounded-full bg-muted" role="img" aria-label={`Demand is ${pct} percent of capacity`}>
                      <span className={cn("block h-full rounded-full", d.over_capacity ? "bg-destructive" : "bg-gold")} style={{ width: `${pct}%` }} />
                    </div>
                    <span className="w-10 text-right text-xs tabular-nums text-muted-foreground">{pct}%</span>
                  </div>
                );
              } },
              { key: "o", header: "", width: "8.5rem", cell: (d) => (d.over_capacity ? <StatusBadge status="Over capacity" tone="error" /> : null) },
            ]}
          />
        </>
      )}
    </>
  );
}
