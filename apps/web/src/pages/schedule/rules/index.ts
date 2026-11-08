import type { ComponentType } from "react";

/**
 * A section of the Scheduler "Rules" tab (per site). A section is a file in this folder named
 * `*Section.tsx` that exports `section`. Later stories add a file here and edit nothing else.
 */
export interface RulesSection {
  id: string;
  title: string;
  /** Lower numbers first. Ties keep the order of the ids. */
  order: number;
  component: ComponentType;
}

export interface SectionModule { section?: RulesSection }

/** Sorts the sections of the loaded modules; a module without a `section` export is ignored. */
export function collectSections(modules: Record<string, SectionModule>): RulesSection[] {
  return Object.values(modules)
    .flatMap((m) => (m.section ? [m.section] : []))
    .sort((a, b) => a.order - b.order || a.id.localeCompare(b.id));
}

export const RULES_SECTIONS: RulesSection[] = collectSections(
  import.meta.glob<SectionModule>("./*Section.tsx", { eager: true }),
);
