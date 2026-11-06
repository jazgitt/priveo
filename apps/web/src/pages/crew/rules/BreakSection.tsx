import { BreakPanel } from "../../breaks/BreakPanel";
import type { Crew } from "../api";
import type { CrewRulesSection } from ".";

/** SCHS-28: the break of one cleaner, with changes for a date range. */
export function BreakSection({ crew }: { crew: Crew }) {
  return <BreakPanel societyId={crew.society_id} crewMemberId={crew.id} />;
}

export const section: CrewRulesSection = { id: "break", title: "Break", order: 30, component: BreakSection };
