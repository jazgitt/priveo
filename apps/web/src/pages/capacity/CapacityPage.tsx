import { useState } from "react";

import { Card, SelectField, StatusChip, Table, TextField } from "../../components";
import {
  errorText, fmtDate, fmtHours, nextSunday, societiesOf, useCapacity, useCrewList, weekday,
  type DayCapacity,
} from "../schedule/api";
import "../schedule/schedule.css";

export function CapacityPage() {
  const crewQ = useCrewList();
  const societies = societiesOf(crewQ.data);
  const [societyId, setSocietyId] = useState("");
  const [startDate, setStartDate] = useState(nextSunday());
  const [days, setDays] = useState("7");

  const count = Math.min(31, Math.max(1, Number(days) || 7));
  const capQ = useCapacity(societyId, startDate, count);
  const crew = (crewQ.data ?? []).filter((c) => c.society_id === societyId);

  return (
    <>
      <h1 className="page-title">Capacity</h1>
      <Card title="Society and period">
        <div className="sch-controls">
          {societies.length > 0 ? (
            <SelectField label="Society" value={societyId}
                         onChange={(e) => setSocietyId(e.target.value)}>
              <option value="">Choose a society</option>
              {societies.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
            </SelectField>
          ) : (
            <TextField label="Society ID" value={societyId}
                       onChange={(e) => setSocietyId(e.target.value.trim())} />
          )}
          <TextField label="From" type="date" value={startDate}
                     onChange={(e) => setStartDate(e.target.value)} />
          <TextField label="Days" type="number" min={1} max={31} value={days}
                     onChange={(e) => setDays(e.target.value)} />
        </div>
      </Card>

      {!societyId && <p className="muted" style={{ marginTop: "1rem" }}>Choose a society.</p>}

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
                  { key: "c", header: "Crew available", align: "right",
                    render: (d) => fmtHours(d.capacity_minutes) },
                  { key: "n", header: "Demand", align: "right",
                    render: (d) => fmtHours(d.demand_minutes) },
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
