import { Search } from "lucide-react";
import { useState } from "react";

import { useConfirm } from "@/blocks/confirm";
import { DataTable } from "@/blocks/DataTable";
import { Field, SelectBox } from "@/blocks/fields";
import { BusyButton } from "@/blocks/FormDialog";
import { EmptyState, ErrorState, PageHeader, StatRow, StatTile } from "@/blocks/layout";
import { EVENTS } from "@/analytics/events";
import { errorMessage, useAppMutation } from "@/blocks/mutation";
import { StatusBadge } from "@/blocks/status";
import { useViewMode, ViewToggle } from "@/blocks/view";
import { showDate } from "@/components/format";
import { useSite } from "@/site/SiteContext";
import { Button } from "@/ui/button";
import { Input } from "@/ui/input";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/ui/sheet";
import { Skeleton } from "@/ui/skeleton";
import { Tabs, TabsList, TabsTrigger } from "@/ui/tabs";
import { Textarea } from "@/ui/textarea";

import {
  allowedMoves, useChangeActions, useChanges, useSetSubscriptionStatus, useSubscriptionEvents,
  useSubscriptions, type SubscriptionRow,
} from "./api";

const STATUS_FILTERS = ["Active", "Activating", "Paused", "Inactive"] as const;
const NO_PLAN = "No plan set";

/** One subscription as a tile. */
function SubscriptionTile({ s }: { s: SubscriptionRow }) {
  return (
    <div className="flex h-full flex-col gap-2">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="m-0 truncate font-medium">{s.customer_name}</p>
          <p className="m-0 truncate text-xs text-muted-foreground">Flat {s.flat}</p>
        </div>
        <StatusBadge status={s.status} />
      </div>
      <p className="m-0 truncate text-sm">{s.vehicle}</p>
      <p className="m-0 truncate text-sm text-muted-foreground">{s.plan_name ?? NO_PLAN}</p>
      <div className="mt-auto flex flex-wrap items-center gap-x-3 gap-y-1 pt-1 text-xs text-muted-foreground">
        <span>First {showDate(s.first_service_date)}</span>
        <span>Renews {showDate(s.renewal_date)}</span>
        {s.payment_due && <StatusBadge status={s.payment_status ?? "Due"} />}
      </div>
    </div>
  );
}

/** Every subscription of the site, its status and its skips and pauses (ADM-SUB-01 to -05, ADM-CUS-09). */
export function SubscriptionsPage() {
  const [status, setStatus] = useState("");
  const [plan, setPlan] = useState("");
  const [dueOnly, setDueOnly] = useState(false);
  const [view, setView] = useViewMode("subscriptions");
  const [search, setSearch] = useState("");
  const [open, setOpen] = useState<SubscriptionRow | null>(null);
  const site = useSite();
  // The whole list is loaded once, so every tile and tab can count and filter it.
  const list = useSubscriptions("", site.id);
  const q = search.trim().toLowerCase();
  // The panel follows the list, so a status change shows there at once.
  const shown = open && (list.data?.find((s) => s.subscription_id === open.subscription_id) ?? open);
  const all = list.data;
  const count = (f: (s: SubscriptionRow) => boolean) => all?.filter(f).length;
  const plans = [...new Set((all ?? []).map((s) => s.plan_name ?? NO_PLAN))].sort();
  const rows = all?.filter((s) =>
    (!status || s.status === status)
    && (!plan || (s.plan_name ?? NO_PLAN) === plan)
    && (!dueOnly || s.payment_due)
    && (!q || `${s.customer_name} ${s.flat} ${s.vehicle} ${s.plan_name ?? ""}`.toLowerCase().includes(q)));
  const filtered = Boolean(status || plan || dueOnly);
  const clear = () => { setStatus(""); setPlan(""); setDueOnly(false); };
  const loading = list.isPending;

  return (
    <>
      <PageHeader title="Subscriptions" site={site.name || undefined}
                  description="Start, stop and reactivate subscriptions, and skip or pause on a customer's behalf." />
      {list.isError && <div className="mb-4"><ErrorState message={errorMessage(list.error)} onRetry={() => void list.refetch()} /></div>}
      <StatRow label="Subscription summary">
        <StatTile label="Total subscriptions" value={all?.length} loading={loading} selected={!filtered} onSelect={clear} />
        {STATUS_FILTERS.map((st) => (
          <StatTile key={st} label={st} value={count((s) => s.status === st)} loading={loading}
                    selected={status === st} onSelect={() => setStatus(status === st ? "" : st)} />
        ))}
        <StatTile label="Payment due" value={count((s) => Boolean(s.payment_due))} loading={loading} hint="Due or over due"
                  selected={dueOnly} onSelect={() => setDueOnly(!dueOnly)} />
      </StatRow>
      {plans.length > 0 && (
        <StatRow label="Subscriptions by plan" className="-mt-2">
          {plans.map((p) => (
            <StatTile key={p} label={`Plan: ${p}`} value={count((s) => (s.plan_name ?? NO_PLAN) === p)} loading={loading}
                      selected={plan === p} onSelect={() => setPlan(plan === p ? "" : p)} />
          ))}
        </StatRow>
      )}
      <DataTable
        view={view}
        renderTile={(s) => <SubscriptionTile s={s} />}
        rows={rows}
        loading={list.isPending}
        rowKey={(s) => s.subscription_id}
        onRowClick={setOpen}
        rowLabel={(s) => `Manage ${s.customer_name}, ${s.vehicle}`}
        toolbar={(
          <div className="flex flex-col gap-3">
            <Tabs value={status || "All"} onValueChange={(t) => setStatus(t === "All" ? "" : t)}>
              <TabsList variant="line" aria-label="Subscription status" className="h-auto flex-wrap justify-start">
                {["All", ...STATUS_FILTERS].map((t) => (
                  <TabsTrigger key={t} value={t} className="flex-none px-3">
                    {t}
                    {all && <span className="ml-1.5 text-xs text-muted-foreground tabular-nums">
                      {t === "All" ? all.length : count((s) => s.status === t)}
                    </span>}
                  </TabsTrigger>
                ))}
              </TabsList>
            </Tabs>
            <div className="flex flex-wrap items-center gap-3">
              <div className="relative w-full max-w-sm">
                <Search className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" aria-hidden />
                <Input aria-label="Search subscriptions" placeholder="Search by customer, flat, vehicle or plan" className="bg-card pl-9"
                       value={search} onChange={(e) => setSearch(e.target.value)} />
              </div>
              {plan && <button type="button" onClick={() => setPlan("")} className="inline-flex h-8 items-center gap-1.5 rounded-full border bg-card px-3 text-sm hover:bg-accent">Plan: {plan} <span aria-hidden>×</span><span className="sr-only">Clear this filter</span></button>}
              {dueOnly && <button type="button" onClick={() => setDueOnly(false)} className="inline-flex h-8 items-center gap-1.5 rounded-full border bg-card px-3 text-sm hover:bg-accent">Payment due <span aria-hidden>×</span><span className="sr-only">Clear this filter</span></button>}
              <div className="ml-auto"><ViewToggle value={view} onChange={setView} /></div>
            </div>
          </div>
        )}
        empty={<EmptyState title="No subscriptions match">Change the tab, the tile filter or the search.</EmptyState>}
        columns={[
          { key: "customer", header: "Customer", width: "20%", cell: (s) => (
            <div className="min-w-0"><span className="block truncate font-medium">{s.customer_name}</span>
              <span className="block truncate text-xs text-muted-foreground">Flat {s.flat}</span></div>) },
          { key: "vehicle", header: "Vehicle", width: "20%", cell: (s) => s.vehicle },
          { key: "plan", header: "Plan", cell: (s) => s.plan_name ?? NO_PLAN },
          { key: "pay", header: "Payment", width: "7.5rem", cell: (s) => (s.payment_status ? <StatusBadge status={s.payment_status} /> : "-") },
          { key: "status", header: "Status", width: "8rem", cell: (s) => <StatusBadge status={s.status} /> },
          { key: "first", header: "First service", width: "8rem", cell: (s) => showDate(s.first_service_date) },
          { key: "renewal", header: "Renewal", width: "8rem", cell: (s) => showDate(s.renewal_date) },
          { key: "act", header: "", width: "6.5rem", align: "right", cell: (s) => <Button size="sm" variant="outline" onClick={() => setOpen(s)}>Manage</Button> },
        ]}
      />
      <Sheet open={open !== null} onOpenChange={(o) => { if (!o) setOpen(null); }}>
        <SheetContent className="w-full overflow-y-auto bg-card sm:max-w-xl">
          {shown && <ManagePanel key={shown.subscription_id} row={shown} />}
        </SheetContent>
      </Sheet>
    </>
  );
}

function ManagePanel({ row }: { row: SubscriptionRow }) {
  return (
    <>
      <SheetHeader className="border-b px-6 py-5">
        <SheetTitle>{row.customer_name}, flat {row.flat}</SheetTitle>
        <SheetDescription>{row.vehicle} · {row.plan_name ?? "No plan set"} · {row.society}</SheetDescription>
      </SheetHeader>
      <div className="flex flex-col gap-8 px-6 py-5">
        <StatusSection key={row.status} row={row} />
        <ChangesSection vehicleId={row.vehicle_id} />
      </div>
    </>
  );
}

function SectionTitle({ children }: { children: string }) {
  return <h3 className="m-0 mb-3 text-sm font-semibold">{children}</h3>;
}

/** The status change the API accepts now, with what it needs, and the history (ADM-SUB-05). */
function StatusSection({ row }: { row: SubscriptionRow }) {
  const current = row.status === "Paused" ? "Active" : row.status;
  const moves = allowedMoves(current);
  const [next, setNext] = useState(moves[0] ?? "");
  const [reason, setReason] = useState("");
  const [first, setFirst] = useState("");
  const set = useSetSubscriptionStatus();
  const events = useSubscriptionEvents(row.subscription_id);
  const save = useAppMutation<void>({
    event: EVENTS.subscriptionStatusChanged,
    mutationFn: () => set.mutateAsync({ id: row.subscription_id, status: next, reason: reason.trim(), first_service_date: next === "Active" ? first || null : null }),
    success: `Subscription is now ${next}.`,
    onSuccess: () => { setReason(""); setFirst(""); },
  });
  const valid = next !== "" && (next !== "Inactive" || reason.trim() !== "") && (next !== "Active" || first !== "");

  return (
    <section>
      <SectionTitle>Status</SectionTitle>
      <div className="flex items-center gap-2 text-sm">Now <StatusBadge status={row.status} /></div>
      {moves.length === 0 ? <p className="mt-3 text-sm text-muted-foreground">This status cannot be changed.</p> : (
        <form className="mt-4 flex flex-col gap-4 rounded-lg border bg-muted/30 p-4" onSubmit={(e) => { e.preventDefault(); if (valid) save.mutate(); }}>
          <Field label="New status">
            {(p) => <SelectBox {...p} value={next} onChange={setNext} choices={moves.map((m) => ({ value: m, label: m }))} />}
          </Field>
          {next === "Active" && (
            <Field label="First service date" hint="Visits are scheduled from this date and the billing cycle starts on it.">
              {(p) => <Input {...p} type="date" value={first} onChange={(e) => setFirst(e.target.value)} />}
            </Field>
          )}
          <Field label="Reason" optional={next !== "Inactive"} hint={next === "Inactive" ? "Required. Future visits are removed from schedules." : "Recorded in the history."}>
            {(p) => <Textarea {...p} rows={2} value={reason} onChange={(e) => setReason(e.target.value)} />}
          </Field>
          <BusyButton type="submit" className="self-start" variant={next === "Inactive" ? "destructive" : "default"}
                      busy={save.isPending} disabled={!valid}>
            {next === "Inactive" ? "Make inactive" : next === "Active" ? "Activate" : "Reactivate"}
          </BusyButton>
        </form>
      )}
      <h4 className="mt-5 mb-2 text-xs font-semibold tracking-wide text-muted-foreground uppercase">History</h4>
      {events.isPending && <Skeleton className="h-10" />}
      {events.isError && <p className="text-sm text-muted-foreground">The history is not available.</p>}
      {events.data && (events.data.length === 0 ? <p className="text-sm text-muted-foreground">No changes yet.</p> : (
        <ol className="m-0 flex list-none flex-col gap-2 border-l pl-4">
          {events.data.map((e, i) => (
            <li key={i} className="text-sm">
              <span className="font-medium">{e.from_status} → {e.to_status}</span>
              <span className="text-muted-foreground"> · {showDate(e.at)} · {e.by}</span>
              {e.reason && <span className="block text-xs text-muted-foreground">{e.reason}</span>}
            </li>
          ))}
        </ol>
      ))}
    </section>
  );
}

/** Skips and pauses on the customer's behalf (ADM-CUS-09). */
function ChangesSection({ vehicleId }: { vehicleId: string }) {
  const confirm = useConfirm();
  const changes = useChanges(vehicleId);
  const act = useChangeActions(vehicleId);
  const [skipDate, setSkipDate] = useState("");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const run = useAppMutation<{ go: () => Promise<unknown>; done: string }>({
    mutationFn: (v) => v.go(), success: (_d, v) => v.done,
  });
  const live = (x: { status: string }) => x.status !== "Cancelled" && x.status !== "Ended";
  const skips = changes.data?.skips.filter(live) ?? [];
  const pauses = changes.data?.pauses.filter(live) ?? [];
  const order = from && to && to < from ? "The pause must end on or after its first day." : undefined;

  return (
    <section>
      <SectionTitle>Skips and pauses</SectionTitle>
      {changes.isPending && <Skeleton className="h-16" />}
      {changes.isError && <ErrorState message={errorMessage(changes.error)} />}
      {changes.data && skips.length === 0 && pauses.length === 0 && <p className="text-sm text-muted-foreground">No skips or pauses.</p>}
      <ul className="m-0 flex list-none flex-col divide-y rounded-lg border p-0 empty:hidden">
        {skips.map((s) => (
          <li key={s.id} className="flex items-center justify-between gap-3 px-3 py-2 text-sm">
            <span><span className="mr-2 text-xs font-medium text-muted-foreground uppercase">Skip</span>{showDate(s.start_date)}<span className="text-muted-foreground"> · by {s.actor}</span></span>
            <Button size="sm" variant="ghost" onClick={async () => {
              if (await confirm({ title: `Remove the skip on ${showDate(s.start_date)}?`, description: "The visit comes back on that date.", confirmLabel: "Remove skip" })) {
                run.mutate({ go: () => act.unskip.mutateAsync(s.id), done: "Skip removed." });
              }
            }}>Remove skip</Button>
          </li>
        ))}
        {pauses.map((p) => (
          <li key={p.id} className="flex items-center justify-between gap-3 px-3 py-2 text-sm">
            <span><span className="mr-2 text-xs font-medium text-muted-foreground uppercase">Pause</span>{showDate(p.start_date)} to {showDate(p.end_date)}<span className="text-muted-foreground"> · by {p.actor}</span></span>
            <Button size="sm" variant="ghost" onClick={async () => {
              if (await confirm({ title: "End this pause now?", description: `The pause from ${showDate(p.start_date)} to ${showDate(p.end_date)} ends, and visits start again.`, confirmLabel: "End pause" })) {
                run.mutate({ go: () => act.endPause.mutateAsync(p.id), done: "Pause ended." });
              }
            }}>End pause</Button>
          </li>
        ))}
      </ul>
      <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
        <form className="flex flex-col gap-3 rounded-lg border bg-muted/30 p-4"
              onSubmit={(e) => { e.preventDefault(); if (skipDate) run.mutate({ go: () => act.skip.mutateAsync(skipDate), done: "Skip added." }); }}>
          <Field label="Skip date">{(p) => <Input {...p} type="date" value={skipDate} onChange={(e) => setSkipDate(e.target.value)} />}</Field>
          <BusyButton type="submit" variant="outline" className="self-start" disabled={!skipDate} busy={act.skip.isPending}>Skip this day</BusyButton>
        </form>
        <form className="flex flex-col gap-3 rounded-lg border bg-muted/30 p-4"
              onSubmit={(e) => { e.preventDefault(); if (from && to && !order) run.mutate({ go: () => act.pause.mutateAsync({ from_date: from, to_date: to }), done: "Pause added." }); }}>
          <div className="grid grid-cols-2 gap-2">
            <Field label="Pause from">{(p) => <Input {...p} type="date" value={from} onChange={(e) => setFrom(e.target.value)} />}</Field>
            <Field label="Pause to" error={order}>{(p) => <Input {...p} type="date" value={to} onChange={(e) => setTo(e.target.value)} />}</Field>
          </div>
          <BusyButton type="submit" variant="outline" className="self-start" disabled={!from || !to || Boolean(order)} busy={act.pause.isPending}>Pause</BusyButton>
        </form>
      </div>
    </section>
  );
}
