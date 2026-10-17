import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

import { useSocieties } from "../pages/crew/api";

const KEY = "priveo.site";

export interface Site {
  /** The society the admin is working on; empty until the list has loaded. */
  id: string;
  name: string;
  sites: { id: string; name: string }[];
  select: (id: string) => void;
}

export const SiteContext = createContext<Site>({ id: "", name: "", sites: [], select: () => {} });

function remembered(): string {
  try { return localStorage.getItem(KEY) ?? ""; } catch { return ""; }
}

/**
 * The master Site selector: the admin works on one society at a time, and every
 * site page (crew, schedule, payments and so on) follows it (ADM-SITE-01).
 */
export function SiteProvider({ children }: { children: ReactNode }) {
  const q = useSocieties();
  const [chosen, setChosen] = useState(remembered);
  const sites = useMemo(() => (q.data ?? []).map((s) => ({ id: s.id, name: s.name })), [q.data]);
  // A remembered site that no longer exists falls back to the first one.
  const id = sites.some((s) => s.id === chosen) ? chosen : (sites[0]?.id ?? "");
  useEffect(() => {
    try { if (id) localStorage.setItem(KEY, id); } catch { /* storage may be blocked */ }
  }, [id]);
  const value = useMemo<Site>(() => ({
    id, name: sites.find((s) => s.id === id)?.name ?? "", sites, select: setChosen,
  }), [id, sites]);
  return <SiteContext.Provider value={value}>{children}</SiteContext.Provider>;
}

export const useSite = () => useContext(SiteContext);
