import { BreakPanel } from "../../breaks/BreakPanel";
import { useSite } from "../../../site/SiteContext";
import type { RulesSection } from ".";

/** SCHS-28: the break for the whole site, with changes for a date range. */
export function BreakSection() {
  const { id } = useSite();
  if (!id) return <p className="text-sm text-muted-foreground">Choose a site to see its break.</p>;
  return <BreakPanel societyId={id} />;
}

export const section: RulesSection = { id: "break", title: "Break", order: 20, component: BreakSection };
