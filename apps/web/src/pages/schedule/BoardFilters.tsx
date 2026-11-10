import { ChevronDown, Users, Wrench } from "lucide-react";
import type { ReactNode } from "react";

import { Button } from "@/ui/button";
import {
  DropdownMenu, DropdownMenuCheckboxItem, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuRadioGroup,
  DropdownMenuRadioItem, DropdownMenuSeparator, DropdownMenuTrigger,
} from "@/ui/dropdown-menu";
import { Switch } from "@/ui/switch";

import { serviceKey } from "./Board";
import { HandGlyph, HourglassAlertGlyph } from "./FlagIcons";
import type { AdminJob, SchedulingCrew } from "./api";

/** Late and By hand as icon chips; pressing one keeps only those jobs bright, pressing it again shows all. */
export function FlagKey({ flag, onFlag }: { flag: string; onFlag: (flag: string) => void }) {
  const chip = (id: "late" | "manual", label: string, glyph: ReactNode) => (
    <button key={id} type="button" aria-pressed={flag === id} aria-label={label} title={label}
            onClick={() => onFlag(flag === id ? "" : id)} className={`sch-chip flag-${id}`}>
      {glyph}
    </button>
  );
  return (
    <div className="flex items-center gap-1.5" role="group" aria-label="Flags">
      {chip("late", "Late", <HourglassAlertGlyph decorative className="sch-flag-icon" />)}
      {chip("manual", "By hand", <HandGlyph decorative className="sch-flag-icon" />)}
    </div>
  );
}

/** The services of the day's jobs, one for each short code (EXT, INT, SPA and any other service), with the full name for the tip. */
export function servicesOf(jobs: AdminJob[]): { key: string; name: string }[] {
  const seen = new Map<string, string>();
  for (const j of jobs) if (!seen.has(serviceKey(j))) seen.set(serviceKey(j), j.service);
  return [...seen].map(([key, name]) => ({ key, name })).sort((a, b) => a.key.localeCompare(b.key));
}

/** One dropdown for the kind of work, in place of the three chips. Single choice; "Clear" shows all services again. */
export function ServicesFilter({ jobs, type, onType }: { jobs: AdminJob[]; type: string; onType: (type: string) => void }) {
  const services = servicesOf(jobs);
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button size="sm" variant="outline" className="h-8" aria-label={type ? `Services: ${type}` : "Services"}>
          <Wrench aria-hidden /> {type || "Services"} <ChevronDown aria-hidden />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" className="w-44">
        <DropdownMenuLabel>Show only this service</DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuRadioGroup value={type} onValueChange={onType}>
          {services.map((s) => (
            <DropdownMenuRadioItem key={s.key} value={s.key} title={s.name}>{s.key}</DropdownMenuRadioItem>
          ))}
        </DropdownMenuRadioGroup>
        {type && (
          <>
            <DropdownMenuSeparator />
            <DropdownMenuItem onSelect={() => onType("")}>Clear</DropdownMenuItem>
          </>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

/**
 * "Show all" (P1-4). Off, the filters hide the cards and rows they do not keep. On, those cards and
 * rows come back in disabled form, so the rest of the day is still in view.
 */
export function ShowAll({ checked, onChange }: { checked: boolean; onChange: (checked: boolean) => void }) {
  return (
    <label className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
      <Switch size="sm" checked={checked} onCheckedChange={onChange} aria-label="Show all" />
      Show all
    </label>
  );
}

/** Chooses which crew members' lanes and rows are shown; none chosen shows everyone. */
export function CrewPicker({ crew, selected, onChange, hideOff, onHideOff }: {
  crew: SchedulingCrew[];
  selected: string[];
  onChange: (ids: string[]) => void;
  /** Leave out the crew members who cannot work this day. */
  hideOff: boolean;
  onHideOff: (hide: boolean) => void;
}) {
  const label = selected.length > 0 ? `${selected.length} of ${crew.length} crew` : hideOff ? "Working crew" : "All crew";
  const toggle = (id: string) => onChange(selected.includes(id) ? selected.filter((s) => s !== id) : [...selected, id]);
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button size="sm" variant="outline" className="h-8" aria-label={`Crew shown: ${label}`}>
          <Users aria-hidden /> {label} <ChevronDown aria-hidden />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" className="w-56">
        <DropdownMenuCheckboxItem checked={hideOff} onCheckedChange={onHideOff} onSelect={(e) => e.preventDefault()}>
          Hide crew who are off today
        </DropdownMenuCheckboxItem>
        <DropdownMenuSeparator />
        <DropdownMenuLabel>Show only these crew</DropdownMenuLabel>
        <DropdownMenuSeparator />
        {crew.map((c) => (
          <DropdownMenuCheckboxItem key={c.id} checked={selected.includes(c.id)}
                                    onCheckedChange={() => toggle(c.id)} onSelect={(e) => e.preventDefault()}>
            {c.name}
          </DropdownMenuCheckboxItem>
        ))}
        {selected.length > 0 && (
          <>
            <DropdownMenuSeparator />
            <DropdownMenuCheckboxItem checked={false} onCheckedChange={() => onChange([])}>Show all crew</DropdownMenuCheckboxItem>
          </>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
