import type { ComponentType } from "react";

import type { Crew } from "../api";

/**
 * A section of the crew "Scheduling" panel. A section is a file in this folder named
 * `*Section.tsx` that exports `section`. Later stories add a file here and edit nothing else.
 */
export interface CrewRulesSection {
  id: string;
  title: string;
  /** Lower numbers first. Ties keep the order of the ids. */
  order: number;
  component: ComponentType<{ crew: Crew }>;
}

export interface SectionModule { section?: CrewRulesSection }

/** Sorts the sections of the loaded modules; a module without a `section` export is ignored. */
export function collectSections(modules: Record<string, SectionModule>): CrewRulesSection[] {
  return Object.values(modules)
    .flatMap((m) => (m.section ? [m.section] : []))
    .sort((a, b) => a.order - b.order || a.id.localeCompare(b.id));
}

export const CREW_RULES_SECTIONS: CrewRulesSection[] = collectSections(
  import.meta.glob<SectionModule>("./*Section.tsx", { eager: true }),
);
