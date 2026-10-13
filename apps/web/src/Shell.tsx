import { NavLink, Outlet } from "react-router-dom";

import { useAuth } from "./auth/AuthContext";
import { AlertBell } from "./components/AlertBell";
import { Button, useToast } from "./components";
import { NAV } from "./nav";

/** The signed-in frame: left navigation and the page. */
export function Shell() {
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
        <nav aria-label="Admin areas">
          {NAV.map((n) => (
            <NavLink key={n.path} to={n.path} end={n.path === "/"}
                     className={({ isActive }) => `nav-link${isActive ? " active" : ""}`}>
              {n.label}
            </NavLink>
          ))}
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
