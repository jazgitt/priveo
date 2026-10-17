import type { ReactNode } from "react";

import { SiteContext } from "./SiteContext";

/** Tests: render a page as if the admin had chosen a site in the sidebar. */
export function withSite(ui: ReactNode, id = "s1", name = "Lake View") {
  const site = { id, name, sites: [{ id, name }], select: () => {} };
  return <SiteContext.Provider value={site}>{ui}</SiteContext.Provider>;
}
