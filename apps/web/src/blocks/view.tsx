import { LayoutGrid, List } from "lucide-react";
import { useState, type ReactNode } from "react";

import { cn } from "@/lib/utils";

export type ViewMode = "list" | "tiles";

/** The list or tile view of a page, remembered in this browser for the next visit. */
export function useViewMode(page: string): [ViewMode, (v: ViewMode) => void] {
  const key = `priveo.view.${page}`;
  const [mode, setMode] = useState<ViewMode>(() => {
    try { return localStorage.getItem(key) === "tiles" ? "tiles" : "list"; } catch { return "list"; }
  });
  return [mode, (v) => {
    setMode(v);
    try { localStorage.setItem(key, v); } catch { /* storage may be blocked */ }
  }];
}

/** The switch between the table and the tile grid. It applies to every tab of the page. */
export function ViewToggle({ value, onChange }: { value: ViewMode; onChange: (v: ViewMode) => void }) {
  const item = (mode: ViewMode, label: string, icon: ReactNode) => (
    <button type="button" aria-pressed={value === mode} title={label} onClick={() => onChange(mode)}
            className={cn("inline-flex h-8 items-center gap-1.5 rounded-md px-2.5 text-sm font-medium transition-colors",
              value === mode ? "bg-background text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground")}>
      {icon}<span className="hidden sm:inline">{label}</span>
    </button>
  );
  return (
    <div role="group" aria-label="View" className="inline-flex rounded-lg bg-muted p-[3px]">
      {item("list", "List", <List className="size-4" aria-hidden />)}
      {item("tiles", "Tiles", <LayoutGrid className="size-4" aria-hidden />)}
    </div>
  );
}

/** Tiles that fill the width: as many columns as fit, each at least 16rem wide. */
export function TileGrid({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div className={cn("grid gap-3 [grid-template-columns:repeat(auto-fill,minmax(16rem,1fr))]", className)}>
      {children}
    </div>
  );
}
