import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { EVENTS } from "@/analytics/events";
import { api } from "@/api/client";
import { useConfirm } from "@/blocks/confirm";
import { ErrorState, PageHeader, Panel } from "@/blocks/layout";
import { useAppMutation } from "@/blocks/mutation";
import { Skeleton } from "@/ui/skeleton";
import { Switch } from "@/ui/switch";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/ui/tabs";

const PATH = "/v1/admin/features";

export interface Feature {
  key: string;
  label: string;
  description: string;
  group: string;
  audience: "customer" | "crew" | "both" | "admin";
  enabled: boolean;
}

const AUDIENCE: Record<Feature["audience"], string> = {
  customer: "Customers", crew: "Crew", both: "Customers and crew", admin: "Admins only",
};

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
        description: feature.audience === "admin"
          ? "Nothing is deleted. You can turn it back on at any time."
          : `${AUDIENCE[feature.audience]} will lose this the next time their app refreshes. Nothing is deleted. You can turn it back on at any time.`,
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

const TABS: { audience: Feature["audience"]; label: string }[] = [
  { audience: "customer", label: "Customers" },
  { audience: "crew", label: "Crew" },
  { audience: "both", label: "Both apps" },
];

/** Feature Plugs (feature flags): switch app features on or off without a release. Apps read them on sign-in and on a hard refresh. */
export function FeaturesPage() {
  const list = useQuery({ queryKey: ["admin-features"], queryFn: () => api<Feature[]>(PATH) });
  const features = list.data ?? [];
  const tabs = TABS.filter((t) => features.some((f) => f.audience === t.audience));
  const [tab, setTab] = useState<Feature["audience"]>("customer");
  const active = tabs.some((t) => t.audience === tab) ? tab : tabs[0]?.audience;
  return (
    <>
      <PageHeader title="Feature Plugs"
                  description="Switch a feature off to hide it from the apps. Apps pick the change up on the next refresh (sign-in, pull to refresh, or return after a few minutes away). Every change is recorded in the Audit log." />
      {list.isLoading && <Skeleton className="h-64" />}
      {list.isError && <ErrorState message="Could not load the feature plugs." onRetry={() => void list.refetch()} />}
      {active && (
        <Tabs value={active} onValueChange={(v) => setTab(v as Feature["audience"])}>
          <TabsList variant="line" aria-label="Feature audience" className="h-auto flex-wrap justify-start">
            {tabs.map((t) => {
              const mine = features.filter((f) => f.audience === t.audience);
              const off = mine.filter((f) => !f.enabled).length;
              return (
                <TabsTrigger key={t.audience} value={t.audience} className="flex-none px-3">
                  {t.label}
                  <span className="ml-1.5 text-xs text-muted-foreground tabular-nums">
                    {mine.length}{off > 0 && `, ${off} off`}
                  </span>
                </TabsTrigger>
              );
            })}
          </TabsList>
          {tabs.map((t) => {
            const mine = features.filter((f) => f.audience === t.audience);
            const groups = [...new Set(mine.map((f) => f.group))];
            return (
              <TabsContent key={t.audience} value={t.audience} className="mt-4 flex flex-col gap-4">
                {groups.map((group) => (
                  <Panel key={group} title={group} bodyClassName="divide-y py-1">
                    {mine.filter((f) => f.group === group).map((f) => <FeatureRow key={f.key} feature={f} />)}
                  </Panel>
                ))}
              </TabsContent>
            );
          })}
        </Tabs>
      )}
    </>
  );
}
