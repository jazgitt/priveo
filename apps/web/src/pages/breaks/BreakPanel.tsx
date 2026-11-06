import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { api } from "@/api/client";
import { useConfirm } from "@/blocks/confirm";
import { ErrorState } from "@/blocks/layout";
import { useAppMutation } from "@/blocks/mutation";
import { Badge } from "@/ui/badge";
import { Button } from "@/ui/button";
import { Skeleton } from "@/ui/skeleton";

import { showDate } from "../../components/format";
import { hhmm, toIso } from "../schedule/api";
import { BreakDialog, type BreakRule, type SiteBreak } from "./BreakDialog";

interface SiteSetting { key: string; value: string }
interface CrewBreaks { scheduling_crew_id: string; society_id: string; rules: BreakRule[] }

const isOpen = (r: BreakRule) => r.start_date === null;

/** The rank of a rule: date and cleaner first, then date, then cleaner (SCHR-BRK-06). */
const rank = (r: BreakRule) => (isOpen(r) ? 2 : r.crew_id ? 0 : 1);

/** The rule that decides the break on `day`: the most specific one that covers it. The last listed wins a tie. */
export function ruleInForce(rules: BreakRule[], day: string): BreakRule | null {
  const covering = rules.filter((r) => isOpen(r) || (r.start_date! <= day && day <= r.end_date!));
  let best: BreakRule | null = null;
  for (const r of covering) if (best === null || rank(r) <= rank(best)) best = r;
  return best;
}

const describe = (r: BreakRule, site: SiteBreak) => {
  if (!r.enabled) return "No break";
  return `${hhmm(r.start_minute ?? site.start)} to ${hhmm(r.end_minute ?? site.end)}`;
};

/**
 * SCHS-28: the break rules of a site, or of one cleaner (`crewMemberId`), with Add and Delete.
 * For a cleaner the list also shows the site-wide date rules, with a mark on the rule in force today.
 */
export function BreakPanel({ societyId, crewMemberId, today = toIso(new Date()) }: {
  societyId: string;
  crewMemberId?: string;
  today?: string;
}) {
  const confirm = useConfirm();
  const [adding, setAdding] = useState(false);
  const settings = useQuery({
    queryKey: ["site-settings", societyId],
    queryFn: () => api<SiteSetting[]>(`/v1/admin/scheduling/site-settings?society_id=${societyId}`),
    enabled: !!societyId,
  });
  const key = crewMemberId ? ["crew", crewMemberId, "break-rules"] : ["break-rules", societyId];
  const rulesQ = useQuery({
    queryKey: key,
    queryFn: async () => {
      if (crewMemberId) return api<CrewBreaks>(`/v1/admin/crew/${crewMemberId}/break-rules`);
      const rules = await api<BreakRule[]>(`/v1/admin/scheduling/break-rules?society_id=${societyId}`);
      return { scheduling_crew_id: "", society_id: societyId, rules: rules.filter((r) => r.crew_id === null) };
    },
  });
  const remove = useAppMutation<string, unknown>({
    mutationFn: (id) => api(`/v1/admin/scheduling/break-rules/${id}`, { method: "DELETE" }),
    success: "Break rule deleted.",
    invalidate: [key],
  });

  if (rulesQ.isError || settings.isError) {
    return <ErrorState message="The break rules could not be loaded." onRetry={() => { void rulesQ.refetch(); void settings.refetch(); }} />;
  }
  if (!rulesQ.data || !settings.data) return <Skeleton className="h-20 w-full" />;

  const value = (k: string) => settings.data.find((s) => s.key === k)?.value;
  const site: SiteBreak = {
    start: Number(value("site.break_start_minute") ?? 0), end: Number(value("site.break_end_minute") ?? 0),
  };
  const siteOn = value("site.break_enabled") !== "false";
  const { rules } = rulesQ.data;
  const inForce = crewMemberId ? ruleInForce(rules, today) : null;

  const ask = async (r: BreakRule) => {
    const when = isOpen(r) ? "always" : `${showDate(r.start_date)} to ${showDate(r.end_date)}`;
    const ok = await confirm({
      title: "Delete this break rule?", tone: "danger", confirmLabel: "Delete rule",
      description: `The rule for ${when} (${describe(r, site)}) is removed. The next rule in line applies.`,
    });
    if (ok) remove.mutate(r.id);
  };

  return (
    <div className="flex flex-col gap-3">
      <p className="text-sm text-muted-foreground">
        Site break: {siteOn ? `${hhmm(site.start)} to ${hhmm(site.end)}` : "off"}.
      </p>
      {rules.length === 0 ? (
        <p className="text-sm text-muted-foreground">No break changes. The site break applies.</p>
      ) : (
        <ul className="flex flex-col gap-2">
          {rules.map((r) => (
            <li key={r.id} className="flex flex-wrap items-center gap-3 text-sm">
              <span className="font-medium">
                {isOpen(r) ? "Every day" : r.start_date === r.end_date ? showDate(r.start_date) : `${showDate(r.start_date)} to ${showDate(r.end_date)}`}
              </span>
              <span>{describe(r, site)}</span>
              <span className="text-muted-foreground">{r.crew_id ? "This cleaner" : "All cleaners"}</span>
              {inForce?.id === r.id && <Badge>In force today</Badge>}
              <Button type="button" variant="ghost" size="sm" aria-label={`Delete break rule ${showDate(r.start_date)}`}
                onClick={() => void ask(r)}>Delete</Button>
            </li>
          ))}
        </ul>
      )}
      <div>
        <Button type="button" variant="outline" size="sm" onClick={() => setAdding(true)}>Change break</Button>
      </div>
      {adding && (
        <BreakDialog open onOpenChange={(o) => setAdding(o)} societyId={societyId} today={today}
          crewId={crewMemberId ? rulesQ.data.scheduling_crew_id : undefined} siteBreak={site} invalidate={[key]} />
      )}
    </div>
  );
}
