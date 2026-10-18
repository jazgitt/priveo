import { useQuery } from "@tanstack/react-query";
import { Plus, Search } from "lucide-react";
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { api } from "@/api/client";
import { DataTable, Pager, type DataColumn } from "@/blocks/DataTable";
import { EmptyState, ErrorState, PageHeader, StatRow, StatTile } from "@/blocks/layout";
import { errorMessage } from "@/blocks/mutation";
import { StatusBadge } from "@/blocks/status";
import { useViewMode, ViewToggle } from "@/blocks/view";
import { useSite } from "@/site/SiteContext";
import { Button } from "@/ui/button";
import { Input } from "@/ui/input";
import { Tabs, TabsList, TabsTrigger } from "@/ui/tabs";

import {
  keepForSite, onboardingState, PAGE_SIZE, STATUS_TABS, useDebounced, type CustomerRow, type CustomerSummary, type StatusTab,
} from "./api";
import { VehicleWizard } from "./VehicleWizard";

export { CustomerDetailPage } from "./CustomerDetailPage";

const COLUMNS: DataColumn<CustomerRow>[] = [
  {
    key: "name", header: "Customer", width: "24%",
    cell: (c) => (
      <div className="min-w-0">
        <Link to={`/customers/${c.id}`} className="block truncate font-medium text-foreground">{c.name}</Link>
        {c.flat && <span className="block truncate text-xs text-muted-foreground">Flat {c.flat}</span>}
      </div>
    ),
  },
  {
    key: "contact", header: "Contact", width: "28%",
    cell: (c) => (
      <div className="min-w-0">
        <span className="block truncate tabular-nums">{c.mobile}</span>
        <span className="block truncate text-xs text-muted-foreground" title={c.email}>{c.email}</span>
      </div>
    ),
  },
  {
    key: "vehicles", header: "Vehicles and subscription", wrap: true,
    cell: (c) => (c.vehicles?.length ?? 0) === 0
      ? <span className="text-muted-foreground">No vehicle</span>
      : (
        <ul className="m-0 flex list-none flex-col gap-1 p-0">
          {c.vehicles!.map((v) => (
            <li key={v.id} className="flex flex-wrap items-center gap-2">
              <span className="reg min-w-24 text-[0.8125rem]">{v.registration || <span className="font-normal text-muted-foreground">No registration</span>}</span>
              <StatusBadge status={v.status ?? "No subscription"} tone={v.status ? undefined : "neutral"} />
            </li>
          ))}
        </ul>
      ),
  },
  {
    key: "onboarding", header: "App onboarding", width: "11rem",
    cell: (c) => {
      if (c.onboarding_confirmed === undefined) return "-";
      const s = onboardingState(c);
      return <StatusBadge status={s.label} tone={s.tone} />;
    },
  },
];

type Tab = "All" | StatusTab;
/** A tile can also narrow the list to customers with a subscription or with add-ons only. */
type Scope = "" | "with_subscription" | "addons_only";

/** One customer as a tile. */
function CustomerTile({ c }: { c: CustomerRow }) {
  const s = c.onboarding_confirmed === undefined ? null : onboardingState(c);
  return (
    <div className="flex h-full flex-col gap-2">
      <div className="min-w-0">
        <p className="m-0 truncate font-medium">{c.name}</p>
        {c.flat && <p className="m-0 truncate text-xs text-muted-foreground">Flat {c.flat}</p>}
      </div>
      <div className="min-w-0 text-sm">
        <span className="block truncate tabular-nums">{c.mobile}</span>
        <span className="block truncate text-xs text-muted-foreground">{c.email}</span>
      </div>
      <ul className="m-0 flex list-none flex-col gap-1 p-0">
        {(c.vehicles?.length ?? 0) === 0 && <li className="text-sm text-muted-foreground">No vehicle</li>}
        {c.vehicles?.map((v) => (
          <li key={v.id} className="flex flex-wrap items-center gap-2">
            <span className="reg text-[0.8125rem]">{v.registration || "No registration"}</span>
            <StatusBadge status={v.status ?? "No subscription"} tone={v.status ? undefined : "neutral"} />
          </li>
        ))}
      </ul>
      {s && <div className="mt-auto pt-1 text-xs text-muted-foreground">App onboarding <StatusBadge status={s.label} tone={s.tone} /></div>}
    </div>
  );
}


/** Find a customer and open them (ADM-CUS-08), or create one (ADM-CUS-01). */
export function CustomersPage() {
  const navigate = useNavigate();
  const site = useSite();
  const [search, setSearch] = useState("");
  const [tab, setTab] = useState<Tab>("All");
  const [only, setOnly] = useState<Scope>("");
  const [view, setView] = useViewMode("customers");
  const [page, setPage] = useState(0);
  const [creating, setCreating] = useState(false);
  const q = useDebounced(search.trim());
  const scope = `q=${encodeURIComponent(q)}${site.id ? `&society_id=${site.id}` : ""}`;
  const summary = useQuery({
    queryKey: ["customers", "summary", q, site.id],
    placeholderData: keepForSite(site.id),
    queryFn: () => api<CustomerSummary>(`/v1/admin/customers/summary?${scope}`),
  });
  const list = useQuery({
    queryKey: ["customers", q, tab, only, page, site.id],
    placeholderData: keepForSite(site.id),
    queryFn: () => api<CustomerRow[]>(`/v1/admin/customers?${scope}`
      + `${tab === "All" ? "" : `&status=${encodeURIComponent(tab)}`}${only ? `&scope=${only}` : ""}`
      + `&limit=${PAGE_SIZE}&offset=${page * PAGE_SIZE}`),
  });
  const counts = summary.data;
  const inTab = !counts ? undefined : only === "with_subscription" ? counts.with_subscription
    : only === "addons_only" ? counts.addons_only : tab === "All" ? counts.total : counts.by_status[tab];
  /** A tile or a tab sets one filter: the tab, or the scope, never a mix that counts nothing. */
  const show = (nextTab: Tab, nextOnly: Scope = "") => { setTab(nextTab); setOnly(nextOnly); setPage(0); };
  const loadingCounts = summary.isPending;

  return (
    <>
      <PageHeader
        title="Customers"
        site={site.name || undefined}
        description="Find a customer to change their schedule, subscription or account."
        actions={<Button onClick={() => setCreating(true)}><Plus aria-hidden /> Create customer</Button>}
      />
      <StatRow label="Customer summary">
        <StatTile label="Total customers" value={counts?.total} loading={loadingCounts}
                  selected={tab === "All" && !only} onSelect={() => show("All")} />
        <StatTile label="With a subscription" value={counts?.with_subscription} loading={loadingCounts}
                  selected={only === "with_subscription"} onSelect={() => show("All", "with_subscription")} />
        <StatTile label="Add-ons only" value={counts?.addons_only} loading={loadingCounts} hint="No subscription"
                  selected={only === "addons_only"} onSelect={() => show("All", "addons_only")} />
        <StatTile label="Active" value={counts?.by_status.Active} loading={loadingCounts}
                  selected={tab === "Active" && !only} onSelect={() => show("Active")} />
        <StatTile label="Activating" value={counts?.by_status.Activating} loading={loadingCounts}
                  selected={tab === "Activating" && !only} onSelect={() => show("Activating")} />
        <StatTile label="Inactive" value={counts?.by_status.Inactive} loading={loadingCounts}
                  selected={tab === "Inactive" && !only} onSelect={() => show("Inactive")} />
      </StatRow>
      <DataTable
        columns={COLUMNS}
        view={view}
        renderTile={(c) => <CustomerTile c={c} />}
        rows={list.data}
        rowKey={(c) => c.id}
        loading={list.isPending}
        onRowClick={(c) => navigate(`/customers/${c.id}`)}
        rowLabel={(c) => `Open ${c.name}`}
        toolbar={(
          <div className="flex flex-col gap-3">
            <Tabs value={only ? "" : tab} onValueChange={(t) => show(t as Tab)}>
              <TabsList variant="line" aria-label="Customer status" className="h-auto flex-wrap justify-start">
                {(["All", ...STATUS_TABS] as Tab[]).map((t) => (
                  <TabsTrigger key={t} value={t} className="flex-none px-3">
                    {t}
                    {counts && <span className="ml-1.5 text-xs text-muted-foreground tabular-nums">
                      {t === "All" ? counts.total : counts.by_status[t]}
                    </span>}
                  </TabsTrigger>
                ))}
              </TabsList>
            </Tabs>
            <div className="flex flex-wrap items-center gap-3">
              <div className="relative w-full max-w-md">
                <Search className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" aria-hidden />
                <Input
                  aria-label="Search by name, mobile, registration or society"
                  placeholder="Search by name, mobile, registration or society"
                  className="bg-card pl-9"
                  value={search}
                  onChange={(e) => { setSearch(e.target.value); setPage(0); }}
                />
              </div>
              {list.isFetching && !list.isPending && <span className="text-sm text-muted-foreground">Searching…</span>}
              {only && (
                <button type="button" onClick={() => show("All")}
                        className="inline-flex h-8 items-center gap-1.5 rounded-full border bg-card px-3 text-sm hover:bg-accent">
                  {only === "with_subscription" ? "With a subscription" : "Add-ons only"} <span aria-hidden>×</span>
                  <span className="sr-only">Clear this filter</span>
                </button>
              )}
              <div className="ml-auto"><ViewToggle value={view} onChange={setView} /></div>
              {(list.error || summary.error) && (
                <ErrorState message={errorMessage(list.error ?? summary.error)}
                            onRetry={() => { void list.refetch(); void summary.refetch(); }} />
              )}
            </div>
          </div>
        )}
        empty={q
          ? <EmptyState title="No customers found">Nothing matches “{q}”{tab !== "All" && <> in {tab}</>}{only && <> with this filter</>}. Check the spelling, or search by mobile or registration.</EmptyState>
          : tab !== "All"
            ? <EmptyState title={`No ${tab.toLowerCase()} customers`}>Customers with this status appear here.</EmptyState>
            : <EmptyState title="No customers yet" action={<Button onClick={() => setCreating(true)}>Create customer</Button>}>
                Customers you create appear here.
              </EmptyState>}
        footer={<Pager page={page} size={PAGE_SIZE} count={list.data?.length ?? 0} total={inTab}
                       busy={list.isFetching} onPage={setPage} />}
      />
      {creating && (
        <VehicleWizard onClose={() => setCreating(false)}
                       onSaved={(id) => { setCreating(false); navigate(`/customers/${id}`); }} />
      )}
    </>
  );
}
