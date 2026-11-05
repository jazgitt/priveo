import type { ComponentType } from "react";

/** What the Schedule page gives a report: the chosen site and day. */
export interface ReportProps {
  societyId: string;
  date: string;
}

/**
 * A section of the Schedule "Reports" tab. A section is a file in this folder named
 * `*Section.tsx` that exports `section`. Later stories add a file here and edit nothing else.
 */
export interface ReportSection {
  id: string;
  title: string;
  /** Lower numbers first. Ties keep the order of the ids. */
  order: number;
  component: ComponentType<ReportProps>;
}

export interface SectionModule { section?: ReportSection }

/** Sorts the sections of the loaded modules; a module without a `section` export is ignored. */
export function collectSections(modules: Record<string, SectionModule>): ReportSection[] {
  return Object.values(modules)
    .flatMap((m) => (m.section ? [m.section] : []))
    .sort((a, b) => a.order - b.order || a.id.localeCompare(b.id));
}

export const REPORT_SECTIONS: ReportSection[] = collectSections(
  import.meta.glob<SectionModule>("./*Section.tsx", { eager: true }),
);
