import { useState } from "react";

import { useSite } from "../../site/SiteContext";
import { Card, HoverTip, StatusChip, Table, TextField, TipRows, type TipRow } from "../../components";
import {
  errorText, fmtDate, fmtHours, nextSunday, useCapacity, useCrewList, weekday,
  type DayCapacity,
} from "../schedule/api";
import "../schedule/schedule.css";

/** A capacity figure with its breakup on hover. */
function Tip({ label, title, rows, empty }: {
  label: string; title: string; rows: TipRow[]; empty: string;
}) {
  return (
    <HoverTip label={label} ariaLabel={`${title} ${label}. Hover for the breakup.`}>
      <TipRows title={title} rows={rows} empty={empty} />
    </HoverTip>
  );
}

export function CapacityPage() {
  const crewQ = useCrewList();
  const site = useSite();
  const societyId = site.id;
  const [startDate, setStartDate] = useState(nextSunday());
  const [days, setDays] = useState("7");

  const count = Math.min(31, Math.max(1, Number(days) || 7));
  const capQ = useCapacity(societyId, startDate, count);
  const crew = (crewQ.data ?? []).filter((c) => c.society_id === societyId);

  return (
    <>
      <h1 className="page-title">Capacity</h1>
      <Card title={`Period, ${site.name || "no site chosen"}`}>
        <div className="sch-controls">
          <TextField label="From" type="date" value={startDate}
                     onChange={(e) => setStartDate(e.target.value)} />
          <TextField label="Days" type="number" min={1} max={31} value={days}
                     onChange={(e) => setDays(e.target.value)} />
        </div>
      </Card>

      {!societyId && <p className="muted" style={{ marginTop: "1rem" }}>Choose a site.</p>}

      {societyId && (
        <div className="sch-stack" style={{ marginTop: "1rem" }}>
          <Card title="Demand against capacity">
            {capQ.isLoading && <p className="loading">Loading...</p>}
            {capQ.isError && <p className="form-error" role="alert">{errorText(capQ.error)}</p>}
            {capQ.data && (
              <Table<DayCapacity>
                rows={capQ.data}
                rowKey={(d) => d.date}
                columns={[
                  { key: "d", header: "Date", render: (d) => `${weekday(d.date)} ${fmtDate(d.date)}` },
                  { key: "c", header: "Crew available", align: "right", render: (d) => (
                    <Tip label={fmtHours(d.capacity_minutes)} title="Crew available"
                         empty="No crew available" rows={(d.crew ?? []).map((c) => ({
                           key: c.name + c.slots, left: `${c.name} (${c.role})`,
                           right: fmtHours(c.minutes), note: c.slots }))} />) },
                  { key: "n", header: "Demand", align: "right", render: (d) => (
                    <Tip label={fmtHours(d.demand_minutes)} title="Demand"
                         empty="Nothing due" rows={(d.demand ?? []).map((l) => ({
                           key: l.service + l.source,
                           left: `${l.service}${l.source === "Add-on" ? " (add-on)" : ""}`,
                           right: fmtHours(l.minutes),
                           note: `${l.jobs} ${l.jobs === 1 ? "job" : "jobs"}` }))} />) },
                  { key: "s", header: "Scheduled", align: "right",
                    render: (d) => fmtHours(d.scheduled_minutes) },
                  { key: "u", header: "Use", render: (d) => {
                    const pct = d.capacity_minutes > 0
                      ? Math.min(100, Math.round((d.demand_minutes / d.capacity_minutes) * 100))
                      : d.demand_minutes > 0 ? 100 : 0;
                    return (
                      <div className={`sch-bar${d.over_capacity ? " over" : ""}`}
                           role="img" aria-label={`Demand is ${pct} percent of capacity`}>
                        <span style={{ width: `${pct}%` }} />
                      </div>
                    );
                  } },
                  { key: "o", header: "", render: (d) => d.over_capacity
                    ? <StatusChip tone="error">Over capacity</StatusChip> : null },
                ]}
              />
            )}
          </Card>

          <Card title="Crew">
            <Table
              rows={crew}
              rowKey={(c) => c.id}
              empty="No crew in this society."
              columns={[
                { key: "n", header: "Name", render: (c) => c.name },
                { key: "r", header: "Role", render: (c) => c.role },
                { key: "a", header: "Status", render: (c) => c.active
                  ? <StatusChip tone="ok">Active</StatusChip>
                  : <StatusChip tone="neutral">Inactive</StatusChip> },
              ]}
            />
            <p className="muted">
              Trainees add no capacity. Working hours and exceptions are on the Crew page.
            </p>
          </Card>
        </div>
      )}
    </>
  );
}
