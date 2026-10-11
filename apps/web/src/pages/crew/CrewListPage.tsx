import { useState } from "react";
import { Link } from "react-router-dom";

import { ApiErrorNote } from "../../components/ApiErrorNote";
import {
  Button, Card, SelectField, StatusChip, Table, TextField, type Column,
} from "../../components";
import { ROLES, useCrewList, useSocieties, type Crew } from "./api";
import { OnboardDialog } from "./OnboardDialog";

/** "Mon 06:00-12:00, ..." for the days that work. */
function hoursText(c: Crew): string {
  const w = c.working_hours.filter((h) => h.working);
  if (w.length === 0) return "No working days";
  return w.map((h) => `${h.day.slice(0, 3)} ${h.start}-${h.end}`).join(", ");
}

export function CrewListPage() {
  const [society, setSociety] = useState("");
  const [role, setRole] = useState("");
  const [active, setActive] = useState("");
  const [search, setSearch] = useState("");
  const [onboarding, setOnboarding] = useState(false);
  const societies = useSocieties();
  const list = useCrewList(society);

  const q = search.trim().toLowerCase();
  const rows = (list.data ?? []).filter((c) =>
    (role === "" || c.role === role)
    && (active === "" || c.active === (active === "yes"))
    && (q === "" || c.name.toLowerCase().includes(q) || c.mobile.includes(q)));

  const columns: Column<Crew>[] = [
    { key: "name", header: "Name", render: (c) => <Link className="sp-link" to={`/crew/${c.id}`}>{c.name}</Link> },
    { key: "mobile", header: "Mobile", render: (c) => c.mobile },
    { key: "society", header: "Society", render: (c) => c.society },
    { key: "role", header: "Role", render: (c) => c.paired_member
      ? `${c.role} (with ${c.paired_member})` : c.role },
    { key: "hours", header: "Working hours", render: hoursText },
    { key: "ex", header: "Exceptions", render: (c) => String(c.exceptions.length) },
    { key: "status", header: "Status", render: (c) => (
      <>
        <StatusChip tone={c.active ? "ok" : "neutral"}>{c.active ? "Active" : "Inactive"}</StatusChip>
        {c.locked && <> <StatusChip tone="warn">Locked</StatusChip></>}
      </>) },
  ];

  return (
    <>
      <h1 className="page-title">Crew</h1>
      <Card title="Crew" actions={<Button onClick={() => setOnboarding(true)}>Onboard crew</Button>}>
        <div style={{ display: "flex", flexWrap: "wrap", gap: "0.75rem", alignItems: "flex-end" }}>
          <TextField label="Search" value={search} placeholder="Name or mobile"
                     onChange={(e) => setSearch(e.target.value)} />
          <SelectField label="Society" value={society} onChange={(e) => setSociety(e.target.value)}>
            <option value="">All</option>
            {(societies.data ?? []).map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
          </SelectField>
          <SelectField label="Role" value={role} onChange={(e) => setRole(e.target.value)}>
            <option value="">All</option>
            {ROLES.map((r) => <option key={r}>{r}</option>)}
          </SelectField>
          <SelectField label="Active" value={active} onChange={(e) => setActive(e.target.value)}>
            <option value="">All</option>
            <option value="yes">Active</option>
            <option value="no">Inactive</option>
          </SelectField>
        </div>
        {list.isPending && <p className="loading">Loading...</p>}
        {list.isError && <ApiErrorNote error={list.error} />}
        {list.data && <Table columns={columns} rows={rows} rowKey={(c) => c.id}
                             empty="No crew members match." />}
      </Card>
      {onboarding && <OnboardDialog onClose={() => setOnboarding(false)} />}
    </>
  );
}
