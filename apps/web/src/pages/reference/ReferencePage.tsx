import { useState } from "react";

import { EmptyState, PageHeader } from "@/blocks/layout";
import { Tabs } from "@/components";

import { AddonsTab } from "./AddonsTab";
import { ChecklistsTab, ReasonsTab } from "./ChecklistsTab";
import { PlansTab } from "./PlansTab";
import { ServicesTab } from "./ServicesTab";
import { SocietiesTab } from "./SocietiesTab";
import { VehiclesTab } from "./VehiclesTab";
import { RULES_SECTIONS } from "./rules";
import { ZonesTab } from "./ZonesTab";

/** The scheduling rules, one block per section file found in the rules folder. */
function RulesTab() {
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

const TABS = [
  { id: "societies", label: "Societies", view: SocietiesTab },
  { id: "zones", label: "Zones", view: ZonesTab },
  { id: "plans", label: "Plans", view: PlansTab },
  { id: "vehicles", label: "Vehicle catalogue", view: VehiclesTab },
  { id: "services", label: "Services", view: ServicesTab },
  { id: "checklists", label: "Checklists", view: ChecklistsTab },
  { id: "reasons", label: "Could not complete reasons", view: ReasonsTab },
  { id: "addons", label: "Add-on catalogue", view: AddonsTab },
  { id: "rules", label: "Scheduling rules", view: RulesTab },
] as const;

/** Site Setup (all sites): societies, zones, plans, vehicles, services, checklists, reasons, add-ons. */
export function ReferencePage() {
  const [tab, setTab] = useState<string>(TABS[0].id);
  const View = (TABS.find((t) => t.id === tab) ?? TABS[0]).view;
  return (
    <>
      <PageHeader title="Site Setup" description="Lists every site uses. Changes are recorded in the Audit log." />
      <Tabs tabs={TABS} active={tab} label="Reference data" onChange={setTab}>
        <View />
      </Tabs>
    </>
  );
}
