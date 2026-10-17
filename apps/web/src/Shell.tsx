import { NavLink, Outlet } from "react-router-dom";

import { useAuth } from "./auth/AuthContext";
import { AlertBell } from "./components/AlertBell";
import { Button, useToast } from "./components";
import { NAV, type NavItem } from "./nav";
import { SiteProvider, useSite } from "./site/SiteContext";

function NavGroup({ title, items }: { title?: string; items: NavItem[] }) {
  return (
    <>
      {title && <div className="nav-group">{title}</div>}
      {items.map((n) => (
        <NavLink key={n.path} to={n.path} end={n.path === "/"}
                 className={({ isActive }) => `nav-link${isActive ? " active" : ""}`}>
          {n.label}
        </NavLink>
      ))}
    </>
  );
}

/** The master Site selector: every site page follows it (ADM-SITE-01). */
function SiteSelect() {
  const site = useSite();
  return (
    <label className="site-select">
      <span>Site</span>
      <select value={site.id} onChange={(e) => site.select(e.target.value)} aria-label="Site">
        {site.sites.length === 0 && <option value="">No sites yet</option>}
        {site.sites.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
      </select>
    </label>
  );
}

/** The signed-in frame: left navigation and the page. */
export function Shell() {
  return <SiteProvider><Frame /></SiteProvider>;
}

function Frame() {
  const { user, signOut } = useAuth();
  const toast = useToast();

  async function leave() {
    try {
      await signOut();
    } catch {
      toast.show("Could not sign out. Please try again.", "error");
    }
  }

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="sidebar-brand">Priveo</div>
        <SiteSelect />
        <nav aria-label="Admin areas">
          <NavGroup items={NAV.filter((n) => !n.group)} />
          <NavGroup title="This site" items={NAV.filter((n) => n.group === "site")} />
          <NavGroup title="All sites" items={NAV.filter((n) => n.group === "master")} />
        </nav>
        <div className="sidebar-foot">
          <span className="muted">{user?.display_name}</span>
          <Button variant="ghost" onClick={leave}>Sign out</Button>
        </div>
      </aside>
      <main className="content">
        <div className="content-top"><AlertBell /></div>
        <Outlet />
      </main>
    </div>
  );
}
