import { useState } from "react";

import { PageHeader } from "@/blocks/layout";
import { Tabs } from "@/components";

import { AddonsTab } from "./AddonsTab";
import { ChecklistsTab, ReasonsTab } from "./ChecklistsTab";
import { PlansTab } from "./PlansTab";
import { ServicesTab } from "./ServicesTab";
import { SocietiesTab } from "./SocietiesTab";
import { VehiclesTab } from "./VehiclesTab";

const TABS = [
  { id: "societies", label: "Societies", view: SocietiesTab },
  { id: "plans", label: "Plans", view: PlansTab },
  { id: "vehicles", label: "Vehicle catalogue", view: VehiclesTab },
  { id: "services", label: "Services", view: ServicesTab },
  { id: "checklists", label: "Checklists", view: ChecklistsTab },
  { id: "reasons", label: "Could not complete reasons", view: ReasonsTab },
  { id: "addons", label: "Add-on catalogue", view: AddonsTab },
] as const;

/** Master data (all sites): societies, plans, vehicles, services, checklists, reasons, add-ons. */
export function ReferencePage() {
  const [tab, setTab] = useState<string>(TABS[0].id);
  const View = (TABS.find((t) => t.id === tab) ?? TABS[0]).view;
  return (
    <>
      <PageHeader title="Master data" description="Lists every site uses. Changes are recorded in the Audit log." />
      <Tabs tabs={TABS} active={tab} label="Reference data" onChange={setTab}>
        <View />
      </Tabs>
    </>
  );
}
