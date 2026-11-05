import { ChevronDown, Users } from "lucide-react";

import { Button } from "@/ui/button";
import {
  DropdownMenu, DropdownMenuCheckboxItem, DropdownMenuContent, DropdownMenuLabel, DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/ui/dropdown-menu";

import type { SchedulingCrew } from "./api";

/** Late and By hand as chips; pressing one keeps only those jobs bright, pressing it again shows all. */
export function FlagKey({ flag, onFlag }: { flag: string; onFlag: (flag: string) => void }) {
  const chip = (id: "late" | "manual", label: string) => (
    <button key={id} type="button" aria-pressed={flag === id} onClick={() => onFlag(flag === id ? "" : id)}
            className={`sch-chip flag-${id}`}>
      {label}
    </button>
  );
  return <div className="flex items-center gap-1.5" role="group" aria-label="Flags">{chip("late", "Late")}{chip("manual", "By hand")}</div>;
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
