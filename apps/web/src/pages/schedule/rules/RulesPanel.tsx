import { EmptyState } from "@/blocks/layout";

import { RULES_SECTIONS } from ".";

/** The Scheduler Rules tab: the per-site rules, one block per section file found in this folder. */
export function RulesPanel() {
  if (!RULES_SECTIONS.length) {
    return <EmptyState title="No scheduling rules yet">Scheduling rules appear here as they are added.</EmptyState>;
  }
  return (
    <div className="flex flex-col gap-8">
      {RULES_SECTIONS.map(({ id, title, component: Section }) => (
        <section key={id} aria-labelledby={`rules-${id}`} className="flex flex-col gap-3">
          <h2 id={`rules-${id}`} className="text-lg font-semibold">{title}</h2>
          <Section />
        </section>
      ))}
    </div>
  );
}
