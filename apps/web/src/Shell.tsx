import {
  Bell, BookOpen, CalendarClock, CalendarRange, ClipboardList, CreditCard, Gauge, History,
  LayoutDashboard, LogOut, MessageSquareWarning, Settings, Sparkles, Star, Timer, Users,
  UserRound, Wrench, type LucideIcon,
} from "lucide-react";
import { NavLink, Outlet } from "react-router-dom";

import { useAuth } from "./auth/AuthContext";
import { ConfirmProvider } from "./blocks/confirm";
import { SelectBox } from "./blocks/fields";
import { TaskTray, TasksProvider } from "./blocks/tasks";
import { AlertBell } from "./components/AlertBell";
import { useToast } from "./components";
import { cn } from "./lib/utils";
import { NAV, type NavItem } from "./nav";
import { SiteProvider, useSite } from "./site/SiteContext";
import { Button } from "./ui/button";
import { TooltipProvider } from "./ui/tooltip";

const ICONS: Record<string, LucideIcon> = {
  "/": LayoutDashboard, "/alerts": Bell, "/customers": UserRound, "/subscriptions": ClipboardList,
  "/crew": Users, "/schedule": CalendarRange, "/slots": Timer, "/capacity": Gauge,
  "/payments": CreditCard, "/addons": Sparkles, "/complaints": MessageSquareWarning,
  "/feedback": Star, "/operations": Wrench, "/reference": BookOpen, "/settings": Settings,
  "/audit": History,
};

function NavGroup({ title, items }: { title?: string; items: NavItem[] }) {
  return (
    <div className="flex flex-col gap-0.5">
      {title && (
        <div className="px-3 pt-4 pb-1 text-[0.6875rem] font-semibold tracking-wider text-muted-foreground uppercase">
          {title}
        </div>
      )}
      {items.map((n) => {
        const Icon = ICONS[n.path] ?? CalendarClock;
        return (
          <NavLink key={n.path} to={n.path} end={n.path === "/"}
                   className={({ isActive }) => cn(
                     "flex h-9 items-center gap-2.5 rounded-md px-3 text-sm font-medium text-foreground/80 no-underline transition-colors hover:bg-accent hover:text-foreground hover:no-underline",
                     isActive && "bg-accent text-foreground shadow-[inset_3px_0_0_var(--c-gold)]",
                   )}>
            <Icon className="size-4 shrink-0 text-muted-foreground" aria-hidden />
            <span className="truncate">{n.label}</span>
          </NavLink>
        );
      })}
    </div>
  );
}

/** The master Site selector: every site page follows it (ADM-SITE-01). */
function SiteSelect() {
  const site = useSite();
  return (
    <div className="flex flex-col gap-1 px-3 pb-2">
      <span className="text-[0.6875rem] font-semibold tracking-wider text-muted-foreground uppercase">Site</span>
      <SelectBox
        aria-label="Site"
        value={site.id}
        onChange={site.select}
        placeholder={site.sites.length === 0 ? "No sites yet" : "Choose a site"}
        choices={site.sites.map((s) => ({ value: s.id, label: s.name }))}
      />
    </div>
  );
}

/** The signed-in frame: left navigation, the top bar and the page. */
export function Shell() {
  return (
    <SiteProvider>
      <TooltipProvider delayDuration={250}>
        <ConfirmProvider>
          <TasksProvider>
            <Frame />
          </TasksProvider>
        </ConfirmProvider>
      </TooltipProvider>
    </SiteProvider>
  );
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
    <div className="grid min-h-screen grid-cols-1 md:grid-cols-[15rem_minmax(0,1fr)] md:bg-[linear-gradient(to_right,var(--sidebar)_15rem,transparent_15rem)]">
      <aside className="flex flex-col border-b bg-sidebar md:sticky md:top-0 md:h-screen md:border-r md:border-b-0">
        <div className="px-6 pt-5 pb-4 font-display text-[1.75rem] leading-none font-bold text-gold-text">Priveo</div>
        <SiteSelect />
        <nav aria-label="Admin areas" className="flex-1 overflow-y-auto px-2 pb-4">
          <NavGroup items={NAV.filter((n) => !n.group)} />
          <NavGroup title="This site" items={NAV.filter((n) => n.group === "site")} />
          <NavGroup title="All sites" items={NAV.filter((n) => n.group === "master")} />
        </nav>
        <div className="flex items-center justify-between gap-2 border-t px-4 py-3">
          <span className="truncate text-sm text-muted-foreground">{user?.display_name}</span>
          <Button variant="ghost" size="sm" onClick={leave}>
            <LogOut aria-hidden /> Sign out
          </Button>
        </div>
      </aside>
      <div className="flex min-w-0 flex-col">
        <div className="sticky top-0 z-30 flex min-h-14 items-center justify-end gap-3 border-b bg-background/90 px-6 backdrop-blur md:px-8">
          <div className="mr-auto min-w-0"><TaskTray /></div>
          <AlertBell />
        </div>
        <main className="w-full max-w-[90rem] min-w-0 px-6 py-6 md:px-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
