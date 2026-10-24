import { useQuery } from "@tanstack/react-query";
import { CalendarOff, Car, PauseCircle, Pencil, Power, Settings2 } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";

import { api } from "@/api/client";
import { useConfirm } from "@/blocks/confirm";
import { DetailList, ErrorState, Panel } from "@/blocks/layout";
import { errorMessage, useAppMutation } from "@/blocks/mutation";
import { StatusBadge } from "@/blocks/status";
import { inr, showDate } from "@/components/format";
import { Button } from "@/ui/button";

import type { Changes, Vehicle, VehicleCrew } from "./api";
import { CarDialog, PauseDialog, SettingsDialog, SkipDialog, StatusDialog } from "./dialogs";

type Open = null | "car" | "settings" | "skip" | "pause" | "Active" | "Inactive" | "Activating";

function SubHeading({ children, actions }: { children: string; actions?: React.ReactNode }) {
  return (
    <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
      <h3 className="m-0 text-sm font-semibold">{children}</h3>
      {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
    </div>
  );
}

/** One vehicle: car, subscription, skips and pauses, and payments. Each change opens its own dialog. */
export function VehiclePanel({ v, customerId }: { v: Vehicle; customerId: string }) {
  const [open, setOpen] = useState<Open>(null);
  const confirm = useConfirm();
  const close = () => setOpen(null);
  const sub = v.subscription;
  const changes = useQuery({
    queryKey: ["customer", customerId, "changes", v.id],
    queryFn: () => api<Changes>(`/v1/admin/vehicles/${v.id}/changes`),
  });
  const crew = useQuery({
    queryKey: ["customer", customerId, "crew", v.id],
    queryFn: () => api<VehicleCrew[]>(`/v1/admin/vehicles/${v.id}/crew`),
  });
  const undo = useAppMutation<{ path: string; done: string }>({
    mutationFn: (r) => api(r.path, { method: "DELETE" }),
    success: (_d, r) => r.done,
    invalidate: [["customer", customerId], ["customers"]],
  });

  const setActive = useAppMutation<boolean>({
    mutationFn: (active) => api(`/v1/admin/vehicles/${v.id}`, { method: "PATCH", body: { active } }),
    success: (_d, active) => (active ? `${v.registration} reactivated.` : `${v.registration} deactivated.`),
    invalidate: [["customer", customerId], ["customers"]],
  });
  const deactivate = async () => {
    if (await confirm({
      title: `Deactivate ${v.registration}?`,
      description: "It leaves the customer's app and the schedule, and gets no new visits. Its history is kept and you can reactivate it later.",
      confirmLabel: "Deactivate vehicle", tone: "danger",
    })) setActive.mutate(false);
  };
  const live = v.active !== false;
  const blocked = sub?.status === "Active" || sub?.status === "Activating";

  const unskip = async (s: { id: string; start_date: string }) => {
    if (await confirm({
      title: `Un-skip ${showDate(s.start_date)}?`,
      description: `${v.registration} gets its visit back on that date. If the schedule is frozen, it is assigned automatically or goes to Needs scheduling.`,
      confirmLabel: "Un-skip",
    })) undo.mutate({ path: `/v1/admin/vehicles/${v.id}/skips/${s.id}`, done: "Skip removed." });
  };
  const endPause = async (p: { id: string; start_date: string; end_date: string }) => {
    if (await confirm({
      title: "End this pause now?",
      description: `The pause of ${v.registration} from ${showDate(p.start_date)} to ${showDate(p.end_date)} ends, and visits start again.`,
      confirmLabel: "End pause",
    })) undo.mutate({ path: `/v1/admin/vehicles/${v.id}/pauses/${p.id}`, done: "Pause ended." });
  };

  const statusActions = !sub ? null : sub.status === "Activating" ? (
    <>
      <Button size="sm" onClick={() => setOpen("Active")}>Activate</Button>
      <Button size="sm" variant="ghost" className="text-destructive" onClick={() => setOpen("Inactive")}>Make inactive</Button>
    </>
  ) : sub.status === "Active" ? (
    <Button size="sm" variant="ghost" className="text-destructive" onClick={() => setOpen("Inactive")}>Make inactive</Button>
  ) : sub.status === "Inactive" ? (
    <Button size="sm" variant="outline" onClick={() => setOpen("Activating")}>Reactivate</Button>
  ) : null;

  const skips = changes.data?.skips ?? [];
  const pauses = changes.data?.pauses ?? [];

  return (
    <Panel
      title={(
        <span className="flex flex-wrap items-center gap-x-3 gap-y-1">
          <span className="reg text-base">{v.registration}</span>
          <span className="font-normal text-muted-foreground">{v.make} {v.model} {v.variant}</span>
        </span>
      )}
      actions={(
        <>
          {!live && <StatusBadge status="Deactivated" tone="neutral" />}
          {live && <Button size="sm" variant="outline" onClick={() => setOpen("car")}><Pencil aria-hidden /> Edit car and parking</Button>}
          {live
            ? (
              <span title={blocked ? "Make the subscription inactive first." : undefined}>
                <Button size="sm" variant="ghost" className="text-destructive" disabled={blocked || setActive.isPending}
                        onClick={() => void deactivate()}>
                  <Power aria-hidden /> Deactivate
                </Button>
              </span>
            )
            : <Button size="sm" variant="outline" disabled={setActive.isPending} onClick={() => setActive.mutate(true)}>Reactivate vehicle</Button>}
        </>
      )}
      className={live ? undefined : "opacity-80"}
      bodyClassName="flex flex-col gap-6"
    >
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-[10rem_minmax(0,1fr)]">
        {v.photo_url
          ? <img src={v.photo_url} alt={v.registration} className="aspect-[4/3] w-40 rounded-lg border object-cover" />
          : <div className="flex aspect-[4/3] w-40 items-center justify-center rounded-lg border border-dashed text-muted-foreground"><Car aria-hidden /></div>}
        <DetailList columns={3} items={[
          { label: "Society", value: v.society },
          { label: "Parking", value: `${v.parking_basement}-${v.parking_number}` },
          { label: "Category", value: v.category },
        ]} />
      </div>

      {live && (
      <section className="border-t pt-5">
        <SubHeading actions={sub ? <>{statusActions}<Button size="sm" variant="outline" onClick={() => setOpen("settings")}><Settings2 aria-hidden /> Schedule settings</Button></> : undefined}>
          Subscription
        </SubHeading>
        {!sub ? (
          <p className="text-sm text-muted-foreground">No subscription. This vehicle can book standalone Deep Spa.</p>
        ) : (
          <DetailList columns={3} items={[
            { label: "Status", value: <StatusBadge status={sub.status} /> },
            { label: "Plan", value: <>{sub.plan_name || <span className="text-muted-foreground">No plan set</span>}<span className="text-muted-foreground"> · {inr(sub.price_rupees)}/month</span></> },
            { label: "First service date", value: sub.first_service_date ? showDate(sub.first_service_date) : "Not set" },
            { label: "Service cutoff", value: sub.cutoff_time },
            { label: "Interior care day", value: sub.interior_day ?? "None" },
            { label: "Plan change", value: sub.pending_from ? `Starts ${showDate(sub.pending_from)}` : "None pending" },
          ]} />
        )}
      </section>
      )}

      {live && sub && (
        <section className="border-t pt-5">
          <SubHeading actions={(
            <>
              <Button size="sm" variant="outline" onClick={() => setOpen("skip")}><CalendarOff aria-hidden /> Skip a date</Button>
              <Button size="sm" variant="outline" onClick={() => setOpen("pause")}><PauseCircle aria-hidden /> Pause</Button>
            </>
          )}>Skips and pauses</SubHeading>
          {changes.error && <ErrorState message={errorMessage(changes.error)} />}
          {changes.data && skips.length === 0 && pauses.length === 0 && (
            <p className="text-sm text-muted-foreground">No upcoming skips or pauses.</p>
          )}
          <ul className="m-0 flex list-none flex-col divide-y rounded-lg border p-0 empty:hidden">
            {skips.map((s) => (
              <li key={s.id} className="flex items-center justify-between gap-3 px-3 py-2">
                <span><span className="mr-2 text-xs font-medium text-muted-foreground uppercase">Skip</span>{showDate(s.start_date)}</span>
                <Button size="sm" variant="ghost" disabled={undo.isPending} onClick={() => void unskip(s)}>Un-skip</Button>
              </li>
            ))}
            {pauses.map((p) => (
              <li key={p.id} className="flex items-center justify-between gap-3 px-3 py-2">
                <span><span className="mr-2 text-xs font-medium text-muted-foreground uppercase">Pause</span>{showDate(p.start_date)} to {showDate(p.end_date)}</span>
                <Button size="sm" variant="ghost" disabled={undo.isPending} onClick={() => void endPause(p)}>End pause</Button>
              </li>
            ))}
          </ul>
        </section>
      )}

      {live && (
        <section className="border-t pt-5">
          <SubHeading>Crew serving this vehicle</SubHeading>
          {crew.error && <ErrorState message={errorMessage(crew.error)} />}
          {crew.data && crew.data.length === 0 && (
            <p className="text-sm text-muted-foreground">No crew is scheduled for this vehicle yet.</p>
          )}
          <ul className="m-0 flex list-none flex-col divide-y rounded-lg border p-0 empty:hidden">
            {crew.data?.map((c) => (
              <li key={c.id} className="flex flex-wrap items-center justify-between gap-x-3 px-3 py-2">
                <span><span className="font-medium">{c.name}</span> <span className="text-xs text-muted-foreground">{c.role}</span></span>
                <span className="text-sm text-muted-foreground">{c.services.join(", ")} · next {showDate(c.next_date)}</span>
              </li>
            ))}
          </ul>
        </section>
      )}

      <section className="border-t pt-5">
        <SubHeading actions={<Button size="sm" variant="link" asChild><Link to="/payments">Manage payments</Link></Button>}>Payments</SubHeading>
        {v.payments.length === 0 ? <p className="text-sm text-muted-foreground">No payments yet.</p> : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b text-left text-xs text-muted-foreground uppercase">
                <th className="py-1.5 pr-3 font-semibold">Due</th>
                <th className="py-1.5 pr-3 text-right font-semibold">Amount</th>
                <th className="py-1.5 font-semibold">Status</th>
              </tr>
            </thead>
            <tbody>
              {v.payments.slice(0, 6).map((p) => (
                <tr key={p.id} className="border-b last:border-0">
                  <td className="py-2 pr-3">{showDate(p.due_date)}</td>
                  <td className="py-2 pr-3 text-right tabular-nums">{inr(p.amount_rupees)}</td>
                  <td className="py-2"><StatusBadge status={p.status} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      {open === "car" && <CarDialog v={v} customerId={customerId} onClose={close} />}
      {open === "settings" && sub && <SettingsDialog sub={sub} customerId={customerId} onClose={close} />}
      {open === "skip" && <SkipDialog v={v} customerId={customerId} onClose={close} />}
      {open === "pause" && <PauseDialog v={v} customerId={customerId} onClose={close} />}
      {(open === "Active" || open === "Inactive" || open === "Activating") && sub && (
        <StatusDialog sub={sub} to={open} registration={v.registration} customerId={customerId} onClose={close} />
      )}
    </Panel>
  );
}
