import { Pencil, Plus, Search } from "lucide-react";
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { DataTable } from "@/blocks/DataTable";
import { Field, NONE, SelectBox } from "@/blocks/fields";
import { EmptyState, ErrorState, PageHeader } from "@/blocks/layout";
import { errorMessage } from "@/blocks/mutation";
import { StatusBadge } from "@/blocks/status";
import { useSite } from "@/site/SiteContext";
import { Button } from "@/ui/button";
import { Input } from "@/ui/input";

import { ROLES, useCrewList } from "./api";
import { OnboardDialog } from "./OnboardDialog";
import { WorkingDaysCell } from "./WorkingDaysCell";

/** The site's crew: roles, this week's working days and exceptions (ADM-CRW-*). */
export function CrewListPage() {
  const site = useSite();
  const navigate = useNavigate();
  const [role, setRole] = useState("");
  const [active, setActive] = useState("");
  const [search, setSearch] = useState("");
  const [onboarding, setOnboarding] = useState(false);
  const list = useCrewList(site.id);

  const q = search.trim().toLowerCase();
  const rows = list.data?.filter((c) =>
    (role === "" || c.role === role)
    && (active === "" || c.active === (active === "yes"))
    && (q === "" || c.name.toLowerCase().includes(q) || c.mobile.includes(q)));

  return (
    <>
      <PageHeader title="Crew" site={site.name || undefined}
                  description="Members, Managers and Trainees, their hours this week and their exceptions."
                  actions={<Button onClick={() => setOnboarding(true)}><Plus aria-hidden /> Onboard crew</Button>} />
      {list.isError && <div className="mb-4"><ErrorState message={errorMessage(list.error)} onRetry={() => void list.refetch()} /></div>}
      <DataTable
        rows={rows}
        loading={list.isPending}
        rowKey={(c) => c.id}
        onRowClick={(c) => navigate(`/crew/${c.id}`)}
        toolbar={(
          <div className="flex flex-wrap items-end gap-3">
            <div className="relative w-full max-w-xs">
              <Search className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" aria-hidden />
              <Input aria-label="Search" placeholder="Name or mobile" className="bg-card pl-9" value={search} onChange={(e) => setSearch(e.target.value)} />
            </div>
            <Field label="Role" className="w-40">
              {(p) => <SelectBox {...p} value={role || NONE} onChange={(v) => setRole(v === NONE ? "" : v)}
                                 choices={[{ value: NONE, label: "All" }, ...ROLES.map((r) => ({ value: r, label: r }))]} />}
            </Field>
            <Field label="Active" className="w-40">
              {(p) => <SelectBox {...p} value={active || NONE} onChange={(v) => setActive(v === NONE ? "" : v)}
                                 choices={[{ value: NONE, label: "All" }, { value: "yes", label: "Active" }, { value: "no", label: "Inactive" }]} />}
            </Field>
          </div>
        )}
        empty={<EmptyState title="No crew members match" action={<Button variant="outline" onClick={() => setOnboarding(true)}>Onboard crew</Button>}>Change the filters, or onboard a crew member.</EmptyState>}
        columns={[
          { key: "name", header: "Name", width: "20%", cell: (c) => <Link to={`/crew/${c.id}`} className="font-medium text-foreground">{c.name}</Link> },
          { key: "mobile", header: "Mobile", width: "9rem", cell: (c) => <span className="tabular-nums">{c.mobile}</span> },
          { key: "role", header: "Role", wrap: true, cell: (c) => (c.paired_member
            ? <span>{c.role} <span className="text-muted-foreground">(with {c.paired_member})</span></span> : c.role) },
          { key: "hours", header: "Working days/hrs", width: "11rem", cell: (c) => <WorkingDaysCell crew={c} /> },
          { key: "ex", header: "Exceptions", width: "7rem", align: "right", cell: (c) => String(c.exceptions.length) },
          { key: "status", header: "Status", width: "9rem", cell: (c) => (
            <span className="flex gap-1.5"><StatusBadge status={c.active ? "Active" : "Inactive"} tone={c.active ? "ok" : "neutral"} />
              {c.locked && <StatusBadge status="Locked" tone="warn" />}</span>) },
          { key: "edit", header: "", width: "3.5rem", align: "right", cell: (c) => (
            <Button asChild size="icon-sm" variant="ghost">
              <Link to={`/crew/${c.id}`} aria-label={`Edit ${c.name}`} title="Edit"><Pencil /></Link>
            </Button>) },
        ]}
      />
      {onboarding && <OnboardDialog onClose={() => setOnboarding(false)} />}
    </>
  );
}
