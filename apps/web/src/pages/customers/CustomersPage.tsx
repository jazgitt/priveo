import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { Plus, Search } from "lucide-react";
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { api } from "@/api/client";
import { DataTable, Pager, type DataColumn } from "@/blocks/DataTable";
import { EmptyState, ErrorState, PageHeader } from "@/blocks/layout";
import { errorMessage } from "@/blocks/mutation";
import { StatusBadge } from "@/blocks/status";
import { useSite } from "@/site/SiteContext";
import { Button } from "@/ui/button";
import { Input } from "@/ui/input";

import { onboardingState, PAGE_SIZE, useDebounced, type CustomerRow } from "./api";
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
    key: "onboarding", header: "App sign-in", width: "11rem",
    cell: (c) => {
      if (c.onboarding_confirmed === undefined) return "-";
      const s = onboardingState(c);
      return <StatusBadge status={s.label} tone={s.tone} />;
    },
  },
];

/** Find a customer and open them (ADM-CUS-08), or create one (ADM-CUS-01). */
export function CustomersPage() {
  const navigate = useNavigate();
  const site = useSite();
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(0);
  const [creating, setCreating] = useState(false);
  const q = useDebounced(search.trim());
  const list = useQuery({
    queryKey: ["customers", q, page, site.id],
    placeholderData: keepPreviousData,
    queryFn: () => api<CustomerRow[]>(`/v1/admin/customers?q=${encodeURIComponent(q)}`
      + `${site.id ? `&society_id=${site.id}` : ""}&limit=${PAGE_SIZE}&offset=${page * PAGE_SIZE}`),
  });

  return (
    <>
      <PageHeader
        title="Customers"
        site={site.name || undefined}
        description="Find a customer to change their schedule, subscription or account."
        actions={<Button onClick={() => setCreating(true)}><Plus aria-hidden /> Create customer</Button>}
      />
      <DataTable
        columns={COLUMNS}
        rows={list.data}
        rowKey={(c) => c.id}
        loading={list.isPending}
        onRowClick={(c) => navigate(`/customers/${c.id}`)}
        toolbar={(
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
            {list.error && <ErrorState message={errorMessage(list.error)} onRetry={() => void list.refetch()} />}
          </div>
        )}
        empty={q
          ? <EmptyState title="No customers found">Nothing matches “{q}”. Check the spelling, or search by mobile or registration.</EmptyState>
          : <EmptyState title="No customers yet" action={<Button onClick={() => setCreating(true)}>Create customer</Button>}>
              Customers you create appear here.
            </EmptyState>}
        footer={<Pager page={page} size={PAGE_SIZE} count={list.data?.length ?? 0} busy={list.isFetching} onPage={setPage} />}
      />
      {creating && (
        <VehicleWizard onClose={() => setCreating(false)}
                       onSaved={(id) => { setCreating(false); navigate(`/customers/${id}`); }} />
      )}
    </>
  );
}
