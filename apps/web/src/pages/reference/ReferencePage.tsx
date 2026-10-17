import { useState } from "react";

import { AddonsTab } from "./AddonsTab";
import { ChecklistsTab, ReasonsTab } from "./ChecklistsTab";
import { PlansTab } from "./PlansTab";
import { ServicesTab } from "./ServicesTab";
import { SocietiesTab } from "./SocietiesTab";
import { VehiclesTab } from "./VehiclesTab";
import "./reference.css";

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
      <h1 className="page-title">Reference data</h1>
      <div className="ref-tabs" role="tablist" aria-label="Reference data">
        {TABS.map((t) => (
          <button key={t.id} type="button" role="tab" className="ref-tab"
                  aria-selected={tab === t.id} onClick={() => setTab(t.id)}>
            {t.label}
          </button>
        ))}
      </div>
      <View />
    </>
  );
}
