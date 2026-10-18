import { useQuery } from "@tanstack/react-query";
import { Car, ChevronLeft, KeyRound, LogOut, Mail, Pencil, Plus } from "lucide-react";
import { useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";

import { api } from "@/api/client";
import { useConfirm } from "@/blocks/confirm";
import { DetailList, EmptyState, ErrorState, PageHeader, Panel } from "@/blocks/layout";
import { errorMessage, useAppMutation } from "@/blocks/mutation";
import { StatusBadge } from "@/blocks/status";
import { useSite } from "@/site/SiteContext";
import { showDate, showDateTime } from "@/components/format";
import { Button } from "@/ui/button";
import { Skeleton } from "@/ui/skeleton";
import { Switch } from "@/ui/switch";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/ui/tabs";

import { cn } from "@/lib/utils";

import { onboardingState, type Customer, type Session, type Vehicle } from "./api";
import { CustomerDialog, EmailDialog } from "./dialogs";
import { VehiclePanel } from "./VehiclePanel";
import { VehicleWizard } from "./VehicleWizard";

type Call = { path: string; method?: string; body?: unknown };
const call = (r: Call) => api<unknown>(r.path, { method: r.method ?? "POST", body: r.body });

const TABS = ["account", "vehicles", "history"] as const;
type TabName = (typeof TABS)[number];

/**
 * One customer, in tabs: their account details (personal details, onboarding,
 * notifications, sessions and account actions), their vehicles (each with its
 * subscription, schedule and payments), and imported history (ADM-CUS-08 to
 * -21). The tab is kept in the address as `?tab=`.
 */
export function CustomerDetailPage() {
  const { id = "" } = useParams();
  const confirm = useConfirm();
  const site = useSite();
  const [params, setParams] = useSearchParams();
  const asked = params.get("tab");
  const tab: TabName = TABS.includes(asked as TabName) ? (asked as TabName) : "account";
  const openTab = (t: string) => setParams(t === "account" ? {} : { tab: t }, { replace: true });
  const [picked, setPicked] = useState("");
  const [adding, setAdding] = useState(false);
  const [showOff, setShowOff] = useState(false);
  const [editing, setEditing] = useState<"details" | "email" | null>(null);
  const details = useQuery({ queryKey: ["customer", id], queryFn: () => api<Customer>(`/v1/admin/customers/${id}`) });
  const sessions = useQuery({ queryKey: ["customer", id, "sessions"], queryFn: () => api<Session[]>(`/v1/admin/customers/${id}/sessions`) });
  const preferences = useQuery({
    queryKey: ["customer", id, "preferences"],
    queryFn: () => api<{ items: { event: string; label: string; enabled: boolean }[] }>(`/v1/admin/customers/${id}/notification-preferences`),
  });
  const refresh = [["customer", id], ["customers"]];
  const account = useAppMutation<Call & { done: string }>({
    mutationFn: call, success: (_d, v) => v.done, invalidate: refresh,
  });
  const notify = useAppMutation<{ event: string; enabled: boolean; label: string }>({
    mutationFn: (v) => call({ path: `/v1/admin/customers/${id}/notification-preferences`, method: "PUT",
      body: { items: [{ event: v.event, enabled: v.enabled }] } }),
    pending: "Saving notification setting…",
    success: (_d, v) => `${v.label} notifications ${v.enabled ? "on" : "off"}.`,
    invalidate: [["customer", id, "preferences"]],
  });

  const back = <Link to="/customers" className="inline-flex items-center gap-1 text-muted-foreground"><ChevronLeft className="size-4" aria-hidden />Customers</Link>;
  const c = details.data;
  if (!c) {
    return (
      <>
        <PageHeader title="Customer" back={back} />
        {details.error ? <ErrorState message={errorMessage(details.error)} onRetry={() => void details.refetch()} />
          : details.isPending ? <div className="flex flex-col gap-4"><Skeleton className="h-40 w-full" /><Skeleton className="h-64 w-full" /></div>
          : <p>Customer unavailable.</p>}
      </>
    );
  }
  const name = `${c.first_name} ${c.last_name}`;
  const signIn = onboardingState(c);
  const liveVehicles = c.vehicles.filter((v) => v.active !== false);
  const offVehicles = c.vehicles.filter((v) => v.active === false);
  const shownVehicles: Vehicle[] = showOff ? [...liveVehicles, ...offVehicles] : liveVehicles;
  const selected = shownVehicles.find((v) => v.id === picked) ?? shownVehicles[0];
  const hasHistory = (c.imported_history?.length ?? 0) > 0;

  const clearPassword = async () => {
    if (await confirm({
      title: `Clear ${name}'s password?`,
      description: "They are signed out on every device. At the next sign-in they get an emailed code and set a new password.",
      confirmLabel: "Clear password", tone: "danger",
    })) account.mutate({ path: `/v1/admin/customers/${id}/reset-password`, done: "Password cleared. The customer is signed out." });
  };
  const signOutAll = async () => {
    if (await confirm({
      title: `Sign ${name} out everywhere?`,
      description: "Every session of this customer ends now. They sign in again with their password.",
      confirmLabel: "Sign out all sessions", tone: "danger",
    })) account.mutate({ path: `/v1/admin/customers/${id}/sessions/logout`, done: "All sessions signed out." });
  };
  const signOutOne = async (s: Session) => {
    if (await confirm({
      title: "Sign out this session?",
      description: `${s.device_name || s.channel} (${s.platform}) is signed out now.`,
      confirmLabel: "Sign out session", tone: "danger",
    })) account.mutate({ path: `/v1/admin/customers/${id}/sessions/${s.id}/logout`, done: "Session signed out." });
  };

  return (
    <>
      <PageHeader
        back={back}
        title={name}
        description={<>{c.mobile} · {c.email}</>}
      />

      <Tabs value={tab} onValueChange={openTab}>
        <TabsList variant="line" aria-label="Customer sections" className="h-auto flex-wrap justify-start">
          <TabsTrigger value="account" className="flex-none px-3">Account details</TabsTrigger>
          <TabsTrigger value="vehicles" className="flex-none px-3">
            Vehicles <span className="text-xs text-muted-foreground tabular-nums">{liveVehicles.length}</span>
          </TabsTrigger>
          {hasHistory && <TabsTrigger value="history" className="flex-none px-3">Service history</TabsTrigger>}
        </TabsList>

        <TabsContent value="vehicles" className="mt-4 flex flex-col gap-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="m-0 text-sm text-muted-foreground">
              {liveVehicles.length === 0 ? "No active vehicle." : `${liveVehicles.length} active ${liveVehicles.length === 1 ? "vehicle" : "vehicles"}.`}
            </p>
            <div className="flex flex-wrap items-center gap-4">
              {offVehicles.length > 0 && (
                <label className="flex items-center gap-2 text-sm">
                  <Switch aria-label="Show deactivated vehicles" checked={showOff} onCheckedChange={setShowOff} />
                  Show deactivated ({offVehicles.length})
                </label>
              )}
              <Button onClick={() => setAdding(true)}><Plus aria-hidden /> Add vehicle</Button>
            </div>
          </div>
          {c.vehicles.length === 0 && (
            <EmptyState title="No vehicle yet" action={<Button onClick={() => setAdding(true)}>Add vehicle</Button>}>
              Add the customer's vehicle to start a subscription.
            </EmptyState>
          )}
          {shownVehicles.length > 1 && (
            <div role="radiogroup" aria-label="Choose a vehicle" className="flex flex-wrap gap-2">
              {shownVehicles.map((v) => {
                const on = v.id === selected?.id;
                return (
                  <button key={v.id} type="button" role="radio" aria-checked={on}
                          onClick={() => setPicked(v.id)}
                          className={cn(
                            "flex items-center gap-2.5 rounded-lg border bg-card p-1.5 pr-3 text-left transition-colors hover:bg-accent focus-visible:ring-[3px] focus-visible:ring-ring/50 focus-visible:outline-none",
                            on && "border-foreground ring-1 ring-foreground", v.active === false && "opacity-60",
                          )}>
                    {v.photo_url
                      ? <img src={v.photo_url} alt="" className="h-9 w-12 rounded-md border object-cover" />
                      : <span className="flex h-9 w-12 items-center justify-center rounded-md border border-dashed text-muted-foreground"><Car className="size-4" aria-hidden /></span>}
                    <span className="reg text-[0.8125rem]">{v.registration || "No registration"}</span>
                  </button>
                );
              })}
            </div>
          )}
          {selected && <VehiclePanel key={selected.id} v={selected} customerId={id} />}
        </TabsContent>

        <TabsContent value="account" className="mt-4 flex flex-col gap-6">
          <Panel
            title="Personal details"
            description="The customer's fixed details. Vehicles are on their own tab."
            actions={(
              <>
                <Button size="sm" variant="outline" onClick={() => setEditing("email")}><Mail aria-hidden /> Update email</Button>
                <Button size="sm" onClick={() => setEditing("details")}><Pencil aria-hidden /> Edit details</Button>
              </>
            )}
          >
            <DetailList columns={2} items={[
              { label: "First name", value: c.first_name },
              { label: "Last name", value: c.last_name },
              { label: "Email", value: <span className="break-all">{c.email}</span> },
              { label: "Mobile", value: c.mobile },
              { label: "Flat", value: c.flat },
              { label: "Society", value: c.society_id ? site.sites.find((x) => x.id === c.society_id)?.name : undefined },
              { label: "Address line 1", value: c.address_line1 },
              { label: "Address line 2", value: c.address_line2 },
              { label: "App onboarding", value: (
                <div className="flex flex-col gap-1.5">
                  <StatusBadge status={signIn.label} tone={signIn.tone} className="self-start" />
                  <span className="text-xs text-muted-foreground">
                    Email {c.email_verified ? "verified" : "not verified"} · Password {c.password_set ? "set" : "not set"} · Review {c.onboarding_confirmed ? "confirmed" : "pending"}
                  </span>
                </div>
              ) },
            ]} />
          </Panel>

          <Panel title="Account actions" description="These end the customer's sign-in. They are recorded in the audit log.">
            <div className="flex flex-wrap gap-2">
              <Button variant="outline" onClick={() => setEditing("email")}><Mail aria-hidden /> Update email</Button>
              <Button variant="outline" onClick={() => void clearPassword()}><KeyRound aria-hidden /> Clear password</Button>
              <Button variant="outline" className="text-destructive" onClick={() => void signOutAll()}>
                <LogOut aria-hidden /> Sign out all sessions
              </Button>
            </div>
          </Panel>
          <div className="grid grid-cols-1 items-start gap-6 lg:grid-cols-2">
            <Panel title="Notifications" description="The same switches as the customer's own Settings.">
              {preferences.error && <ErrorState message={errorMessage(preferences.error)} />}
              {preferences.isPending && <Skeleton className="h-24 w-full" />}
              <ul className="m-0 flex list-none flex-col gap-3 p-0">
                {preferences.data?.items.map((p) => {
                  const label = p.label || p.event.replaceAll("_", " ");
                  return (
                    <li key={p.event} className="flex items-center justify-between gap-3">
                      <label htmlFor={`pref-${p.event}`} className="text-sm first-letter:uppercase">{label}</label>
                      <Switch id={`pref-${p.event}`} aria-label={label} checked={p.enabled}
                              disabled={notify.isPending}
                              onCheckedChange={(on) => notify.mutate({ event: p.event, enabled: on, label })} />
                    </li>
                  );
                })}
              </ul>
            </Panel>

            <Panel title="Signed-in sessions">
              {sessions.error && <ErrorState message={errorMessage(sessions.error)} />}
              {sessions.data?.length === 0 && <p className="text-sm text-muted-foreground">No active sessions.</p>}
              <ul className="m-0 flex list-none flex-col divide-y p-0">
                {sessions.data?.map((s) => (
                  <li key={s.id} className="flex items-center justify-between gap-3 py-2.5 first:pt-0 last:pb-0">
                    <div className="min-w-0">
                      <p className="m-0 truncate text-sm font-medium">{s.device_name || s.channel}</p>
                      <p className="m-0 text-xs text-muted-foreground">{s.platform} {s.app_version} · Last active {showDateTime(s.last_active)}</p>
                    </div>
                    <Button variant="outline" size="sm" onClick={() => void signOutOne(s)}>Sign out session</Button>
                  </li>
                ))}
              </ul>
              {(sessions.data?.length ?? 0) > 1 && (
                <Button variant="ghost" size="sm" className="mt-3 text-destructive" onClick={() => void signOutAll()}>
                  Sign out all sessions
                </Button>
              )}
            </Panel>
          </div>
        </TabsContent>

        {hasHistory && (
          <TabsContent value="history" className="mt-4">
            <Panel title="Imported service history" description="From the records before Priveo's app. Completion was not recorded.">
              <ul className="m-0 flex list-none flex-col divide-y p-0">
                {c.imported_history!.map((h) => (
                  <li key={h.id} className="grid grid-cols-1 gap-1 py-2.5 first:pt-0 last:pb-0 sm:grid-cols-[8rem_minmax(0,1fr)_10rem]">
                    <span className="text-muted-foreground">{h.date ? showDate(h.date) : "Date unknown"}</span>
                    <span><strong>{h.service}</strong> · {h.vehicle}{h.notes && <span className="block text-xs text-muted-foreground">{h.notes}</span>}</span>
                    <span className="text-sm">Completion not recorded · Payment {h.payment_status || "unknown"}</span>
                  </li>
                ))}
              </ul>
            </Panel>
          </TabsContent>
        )}
      </Tabs>

      <CustomerDialog customer={c} open={editing === "details"} onClose={() => setEditing(null)} />
      <EmailDialog customer={c} open={editing === "email"} onClose={() => setEditing(null)} />
      {adding && (
        <VehicleWizard customerId={id} onClose={() => setAdding(false)}
                       onSaved={() => { setAdding(false); openTab("vehicles"); }} />
      )}
    </>
  );
}
