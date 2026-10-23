import { useQuery, useQueryClient } from "@tanstack/react-query";

import { EVENTS } from "@/analytics/events";
import { api } from "@/api/client";
import { useConfirm } from "@/blocks/confirm";
import { ErrorState, PageHeader, Panel } from "@/blocks/layout";
import { useAppMutation } from "@/blocks/mutation";
import { Skeleton } from "@/ui/skeleton";
import { Switch } from "@/ui/switch";

const PATH = "/v1/admin/features";

export interface Feature {
  key: string;
  label: string;
  description: string;
  group: string;
  audience: "customer" | "crew" | "both";
  enabled: boolean;
}

const AUDIENCE: Record<Feature["audience"], string> = { customer: "Customers", crew: "Crew", both: "Customers and crew" };

function FeatureRow({ feature }: { feature: Feature }) {
  const qc = useQueryClient();
  const confirm = useConfirm();
  const save = useAppMutation<boolean>({
    event: EVENTS.featureToggled,
    mutationFn: (enabled) => api(`${PATH}/${feature.key}`, { method: "PUT", body: { enabled } }),
    success: (_d, enabled) => `${feature.label} is now ${enabled ? "on" : "off"}.`,
    onSuccess: () => { void qc.invalidateQueries({ queryKey: ["admin-features"] }); },
  });

  const toggle = async (enabled: boolean) => {
    if (!enabled) {
      const ok = await confirm({
        title: `Turn off ${feature.label}?`,
        description: `${AUDIENCE[feature.audience]} will lose this the next time their app refreshes. Nothing is deleted. You can turn it back on at any time.`,
        confirmLabel: "Turn off",
        tone: "danger",
      });
      if (!ok) return;
    }
    save.mutate(enabled);
  };

  const id = `feature-${feature.key}`;
  return (
    <div className="flex items-center justify-between gap-4 py-3">
      <div className="min-w-0">
        <label htmlFor={id} className="text-sm font-medium">{feature.label}</label>
        <p className="m-0 text-xs text-muted-foreground">{feature.description} {AUDIENCE[feature.audience]}.</p>
      </div>
      <Switch id={id} checked={feature.enabled} disabled={save.isPending} aria-label={feature.label}
              onCheckedChange={(v) => void toggle(v)} />
    </div>
  );
}

/** Feature flags: switch app features on or off without a release. Apps read them on sign-in and on a hard refresh. */
export function FeaturesPage() {
  const list = useQuery({ queryKey: ["admin-features"], queryFn: () => api<Feature[]>(PATH) });
  const groups = [...new Set((list.data ?? []).map((f) => f.group))];
  return (
    <>
      <PageHeader title="Features"
                  description="Switch a feature off to hide it from the apps. Apps pick the change up on the next refresh (sign-in, pull to refresh, or return after a few minutes away). Every change is recorded in the Audit log." />
      {list.isLoading && <Skeleton className="h-64" />}
      {list.isError && <ErrorState message="Could not load the features." onRetry={() => void list.refetch()} />}
      {groups.map((group) => (
        <Panel key={group} title={group} bodyClassName="divide-y py-1">
          {(list.data ?? []).filter((f) => f.group === group).map((f) => <FeatureRow key={f.key} feature={f} />)}
        </Panel>
      ))}
    </>
  );
}
