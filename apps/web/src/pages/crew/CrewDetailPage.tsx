import { ChevronLeft } from "lucide-react";
import { Link, useParams, useSearchParams } from "react-router-dom";

import { EmptyState, ErrorState, PageHeader } from "@/blocks/layout";
import { errorMessage } from "@/blocks/mutation";
import { StatusBadge } from "@/blocks/status";
import { Tabs } from "@/components";
import { Skeleton } from "@/ui/skeleton";

import { useCrew, type Crew } from "./api";
import { AccountPanel, DetailsPanel, ExceptionsPanel, HoursPanel, RolePanel, SessionsPanel } from "./panels";
import { CREW_RULES_SECTIONS } from "./rules";
import { SocietyPanel } from "./SocietyPanel";

/** The sections of a crew member's page, one tab each. */
export const CREW_TABS = [
  { id: "details", label: "Details" },
  { id: "society", label: "Society" },
  { id: "role", label: "Role and pairing" },
  { id: "hours", label: "Working hours" },
  { id: "exceptions", label: "Exceptions" },
  { id: "account", label: "Account" },
  { id: "sessions", label: "Sessions" },
  { id: "scheduling", label: "Scheduling" },
] as const;

/** The scheduling rules of one crew member, one block per section file found in the rules folder. */
function SchedulingPanel({ crew }: { crew: Crew }) {
  if (!CREW_RULES_SECTIONS.length) {
    return <EmptyState title="No scheduling rules yet">Scheduling rules for this crew member appear here as they are added.</EmptyState>;
  }
  return (
    <div className="flex flex-col gap-8">
      {CREW_RULES_SECTIONS.map(({ id, title, component: Part }) => (
        <section key={id} aria-labelledby={`crew-rules-${id}`} className="flex flex-col gap-3">
          <h2 id={`crew-rules-${id}`} className="text-lg font-semibold">{title}</h2>
          <Part crew={crew} />
        </section>
      ))}
    </div>
  );
}

function Section({ tab, crew }: { tab: string; crew: Crew }) {
  // The key resets a section's form when the saved record changes.
  const v = JSON.stringify([crew.name, crew.mobile, crew.role, crew.paired_member_id, crew.working_hours]);
  switch (tab) {
    case "society": return <SocietyPanel key={`s-${crew.society_id}`} crew={crew} />;
    case "role": return <RolePanel key={`r-${v}`} crew={crew} />;
    case "hours": return <HoursPanel key={`h-${v}`} crew={crew} />;
    case "exceptions": return <ExceptionsPanel crew={crew} />;
    case "account": return <AccountPanel crew={crew} />;
    case "sessions": return <SessionsPanel crew={crew} />;
    case "scheduling": return <SchedulingPanel crew={crew} />;
    default: return <DetailsPanel key={`d-${v}`} crew={crew} />;
  }
}

export function CrewDetailPage() {
  const { id = "" } = useParams();
  const [params, setParams] = useSearchParams();
  const q = useCrew(id);
  const back = <Link to="/crew" className="inline-flex items-center gap-1 text-muted-foreground"><ChevronLeft className="size-4" aria-hidden />Back to crew</Link>;
  if (q.isPending) return <><PageHeader title="Crew member" back={back} /><Skeleton className="h-64 w-full" /></>;
  if (q.isError) {
    return <><PageHeader title="Crew member" back={back} /><ErrorState message={errorMessage(q.error)} onRetry={() => void q.refetch()} /></>;
  }
  const c = q.data;
  const wanted = params.get("tab") ?? "details";
  const tab = CREW_TABS.some((t) => t.id === wanted) ? wanted : "details";
  return (
    <>
      <PageHeader
        back={back}
        title={<span className="flex flex-wrap items-center gap-3">{c.name}
          <StatusBadge status={c.active ? "Active" : "Inactive"} tone={c.active ? "ok" : "neutral"} />
          {c.locked && <StatusBadge status="Locked" tone="warn" />}</span>}
        description={<>{c.role}{c.paired_member ? ` with ${c.paired_member}` : ""} · {c.society} · {c.mobile}</>}
      />
      <Tabs tabs={CREW_TABS} active={tab} label="Crew member sections"
            onChange={(next) => setParams(next === "details" ? {} : { tab: next }, { replace: true })}>
        <Section tab={tab} crew={c} />
      </Tabs>
    </>
  );
}
