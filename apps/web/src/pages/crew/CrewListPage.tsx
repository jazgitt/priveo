import { Pencil, Plus, Search } from "lucide-react";
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { DataTable } from "@/blocks/DataTable";
import { EmptyState, ErrorState, PageHeader, StatRow, StatTile } from "@/blocks/layout";
import { errorMessage } from "@/blocks/mutation";
import { StatusBadge } from "@/blocks/status";
import { useViewMode, ViewToggle } from "@/blocks/view";
import { useSite } from "@/site/SiteContext";
import { Button } from "@/ui/button";
import { Input } from "@/ui/input";
import { Tabs, TabsList, TabsTrigger } from "@/ui/tabs";

import { ROLES, useCrewList, type Crew } from "./api";
import { OnboardDialog } from "./OnboardDialog";
import { WorkingDaysCell } from "./WorkingDaysCell";

/** What a tile can narrow the list to, besides the role tabs. */
type Only = "" | "active" | "inactive" | "locked" | "exceptions";
const ONLY: Record<Exclude<Only, "">, (c: Crew) => boolean> = {
  active: (c) => c.active,
  inactive: (c) => !c.active,
  locked: (c) => c.locked,
  exceptions: (c) => c.exceptions.length > 0,
};
const ONLY_LABEL: Record<Exclude<Only, "">, string> = {
  active: "Active", inactive: "Inactive", locked: "Locked", exceptions: "With exceptions",
};

/** One crew member as a tile. */
function CrewTile({ c }: { c: Crew }) {
  return (
    <div className="flex h-full flex-col gap-2">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="m-0 truncate font-medium">{c.name}</p>
          <p className="m-0 truncate text-xs tabular-nums text-muted-foreground">{c.mobile}</p>
        </div>
        <span className="flex shrink-0 gap-1.5">
          <StatusBadge status={c.active ? "Active" : "Inactive"} tone={c.active ? "ok" : "neutral"} />
          {c.locked && <StatusBadge status="Locked" tone="warn" />}
        </span>
      </div>
      <p className="m-0 text-sm">{c.role}{c.paired_member && <span className="text-muted-foreground"> (with {c.paired_member})</span>}</p>
      <p className="m-0 mt-auto pt-1 text-xs text-muted-foreground">
        {c.exceptions.length === 0 ? "No exceptions" : `${c.exceptions.length} ${c.exceptions.length === 1 ? "exception" : "exceptions"}`}
      </p>
    </div>
  );
}

/** The site's crew: roles, this week's working days and exceptions (ADM-CRW-*). */
export function CrewListPage() {
  const site = useSite();
  const navigate = useNavigate();
  const [role, setRole] = useState("");
  const [only, setOnly] = useState<Only>("");
  const [view, setView] = useViewMode("crew");
  const [search, setSearch] = useState("");
  const [onboarding, setOnboarding] = useState(false);
  const list = useCrewList(site.id);

  const q = search.trim().toLowerCase();
  const all = list.data;
  const count = (f: (c: Crew) => boolean) => all?.filter(f).length;
  const rows = all?.filter((c) =>
    (role === "" || c.role === role)
    && (only === "" || ONLY[only](c))
    && (q === "" || c.name.toLowerCase().includes(q) || c.mobile.includes(q)));
  const loading = list.isPending;
  const clear = () => { setRole(""); setOnly(""); };

  return (
    <>
      <PageHeader title="Crew" site={site.name || undefined}
                  description="Members, Managers and Trainees, their hours this week and their exceptions."
                  actions={<Button onClick={() => setOnboarding(true)}><Plus aria-hidden /> Onboard crew</Button>} />
      {list.isError && <div className="mb-4"><ErrorState message={errorMessage(list.error)} onRetry={() => void list.refetch()} /></div>}
      <StatRow label="Crew summary">
        <StatTile label="Total crew" value={all?.length} loading={loading} selected={!role && !only} onSelect={clear} />
        {(Object.keys(ONLY) as Exclude<Only, "">[]).map((k) => (
          <StatTile key={k} label={ONLY_LABEL[k]} value={count(ONLY[k])} loading={loading}
                    selected={only === k} onSelect={() => setOnly(only === k ? "" : k)} />
        ))}
        {ROLES.map((r) => (
          <StatTile key={r} label={`${r}s`} value={count((c) => c.role === r)} loading={loading}
                    selected={role === r} onSelect={() => setRole(role === r ? "" : r)} />
        ))}
      </StatRow>
      <DataTable
        view={view}
        renderTile={(c) => <CrewTile c={c} />}
        rows={rows}
        loading={list.isPending}
        rowKey={(c) => c.id}
        onRowClick={(c) => navigate(`/crew/${c.id}`)}
        toolbar={(
          <div className="flex flex-col gap-3">
            <Tabs value={role || "All"} onValueChange={(t) => setRole(t === "All" ? "" : t)}>
              <TabsList variant="line" aria-label="Crew role" className="h-auto flex-wrap justify-start">
                {["All", ...ROLES].map((t) => (
                  <TabsTrigger key={t} value={t} className="flex-none px-3">
                    {t === "All" ? "All" : `${t}s`}
                    {all && <span className="ml-1.5 text-xs text-muted-foreground tabular-nums">
                      {t === "All" ? all.length : count((c) => c.role === t)}
                    </span>}
                  </TabsTrigger>
                ))}
              </TabsList>
            </Tabs>
            <div className="flex flex-wrap items-center gap-3">
              <div className="relative w-full max-w-xs">
                <Search className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" aria-hidden />
                <Input aria-label="Search" placeholder="Name or mobile" className="bg-card pl-9" value={search} onChange={(e) => setSearch(e.target.value)} />
              </div>
              {only && (
                <button type="button" onClick={() => setOnly("")}
                        className="inline-flex h-8 items-center gap-1.5 rounded-full border bg-card px-3 text-sm hover:bg-accent">
                  {ONLY_LABEL[only]} <span aria-hidden>×</span><span className="sr-only">Clear this filter</span>
                </button>
              )}
              <div className="ml-auto"><ViewToggle value={view} onChange={setView} /></div>
            </div>
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
