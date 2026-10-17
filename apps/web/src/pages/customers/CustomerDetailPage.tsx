import { useQuery } from "@tanstack/react-query";
import { ChevronLeft, KeyRound, LogOut, Mail, MoreHorizontal, Pencil, Plus } from "lucide-react";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";

import { api } from "@/api/client";
import { useConfirm } from "@/blocks/confirm";
import { DetailList, EmptyState, ErrorState, PageHeader, Panel } from "@/blocks/layout";
import { errorMessage, useAppMutation } from "@/blocks/mutation";
import { StatusBadge } from "@/blocks/status";
import { showDate, showDateTime } from "@/components/format";
import { Button } from "@/ui/button";
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuTrigger,
} from "@/ui/dropdown-menu";
import { Skeleton } from "@/ui/skeleton";
import { Switch } from "@/ui/switch";

import { onboardingState, type Customer, type Session } from "./api";
import { CustomerDialog, EmailDialog } from "./dialogs";
import { VehiclePanel } from "./VehiclePanel";
import { VehicleWizard } from "./VehicleWizard";

type Call = { path: string; method?: string; body?: unknown };
const call = (r: Call) => api<unknown>(r.path, { method: r.method ?? "POST", body: r.body });

/** One customer: vehicles, subscriptions, schedule settings, payments and account (ADM-CUS-08 to -21). */
export function CustomerDetailPage() {
  const { id = "" } = useParams();
  const confirm = useConfirm();
  const [adding, setAdding] = useState(false);
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
        actions={(
          <>
            <Button variant="outline" onClick={() => setEditing("details")}><Pencil aria-hidden /> Edit details</Button>
            <Button onClick={() => setAdding(true)}><Plus aria-hidden /> Add vehicle</Button>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline" size="icon" aria-label="Account actions"><MoreHorizontal /></Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-56">
                <DropdownMenuItem onSelect={() => setEditing("email")}><Mail aria-hidden /> Correct email</DropdownMenuItem>
                <DropdownMenuItem onSelect={() => void clearPassword()}><KeyRound aria-hidden /> Clear password</DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem variant="destructive" onSelect={() => void signOutAll()}>
                  <LogOut aria-hidden /> Sign out all sessions
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </>
        )}
      />

      <div className="grid grid-cols-1 items-start gap-6 xl:grid-cols-[minmax(0,1fr)_22rem]">
        <div className="flex min-w-0 flex-col gap-6">
          {c.vehicles.length === 0 && (
            <EmptyState title="No vehicle yet" action={<Button onClick={() => setAdding(true)}>Add vehicle</Button>}>
              Add the customer's vehicle to start a subscription.
            </EmptyState>
          )}
          {c.vehicles.map((v) => <VehiclePanel key={v.id} v={v} customerId={id} />)}
          {(c.imported_history?.length ?? 0) > 0 && (
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
          )}
        </div>

        <div className="flex min-w-0 flex-col gap-6">
          <Panel title="Customer">
            <DetailList columns={1} items={[
              { label: "Email", value: <span className="break-all">{c.email}</span> },
              { label: "Mobile", value: c.mobile },
              { label: "Flat", value: c.flat },
              { label: "App sign-in", value: (
                <div className="flex flex-col gap-1.5">
                  <StatusBadge status={signIn.label} tone={signIn.tone} className="self-start" />
                  <span className="text-xs text-muted-foreground">
                    Email {c.email_verified ? "verified" : "not verified"} · Password {c.password_set ? "set" : "not set"} · Review {c.onboarding_confirmed ? "confirmed" : "pending"}
                  </span>
                </div>
              ) },
            ]} />
          </Panel>

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
      </div>

      <CustomerDialog customer={c} open={editing === "details"} onClose={() => setEditing(null)} />
      <EmailDialog customer={c} open={editing === "email"} onClose={() => setEditing(null)} />
      {adding && (
        <VehicleWizard customerId={id} onClose={() => setAdding(false)} onSaved={() => setAdding(false)} />
      )}
    </>
  );
}
