import { Link, useParams, useSearchParams } from "react-router-dom";

import { ApiErrorNote } from "../../components/ApiErrorNote";
import { StatusChip, Tabs } from "../../components";
import { useCrew, type Crew } from "./api";
import {
  AccountPanel, DetailsPanel, ExceptionsPanel, HoursPanel, RolePanel, SessionsPanel,
} from "./panels";
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
] as const;

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
    default: return <DetailsPanel key={`d-${v}`} crew={crew} />;
  }
}

export function CrewDetailPage() {
  const { id = "" } = useParams();
  const [params, setParams] = useSearchParams();
  const q = useCrew(id);
  if (q.isPending) return <p className="loading">Loading...</p>;
  if (q.isError) {
    return (
      <>
        <p><Link className="sp-link" to="/crew">Back to crew</Link></p>
        <ApiErrorNote error={q.error} />
      </>
    );
  }
  const c = q.data;
  const wanted = params.get("tab") ?? "details";
  const tab = CREW_TABS.some((t) => t.id === wanted) ? wanted : "details";
  return (
    <>
      <p><Link className="sp-link" to="/crew">Back to crew</Link></p>
      <h1 className="page-title">{c.name}</h1>
      <p>
        <StatusChip tone={c.active ? "ok" : "neutral"}>{c.active ? "Active" : "Inactive"}</StatusChip>{" "}
        {c.locked && <StatusChip tone="warn">Locked</StatusChip>}{" "}
        {c.role}, {c.society}, {c.mobile}
      </p>
      <Tabs tabs={CREW_TABS} active={tab} label="Crew member sections"
            onChange={(next) => setParams(next === "details" ? {} : { tab: next }, { replace: true })}>
        <Section tab={tab} crew={c} />
      </Tabs>
    </>
  );
}
