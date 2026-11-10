import { cn } from "@/lib/utils";

import { WEEKDAYS } from "./types";

/** Green for a working day, grey for a day that is not (shared by every slot list and picker). */
export const WORKING_DAY_CLASS = "bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300";
export const OFF_DAY_CLASS = "bg-muted text-muted-foreground/60";
export const dayTone = (working: boolean) => (working ? WORKING_DAY_CLASS : OFF_DAY_CLASS);

/** All seven weekdays: the working ones green, the others grey. `days` are full weekday names. */
export function DayChips({ days }: { days: readonly string[] }) {
  return (
    <span className="flex flex-wrap gap-1" data-testid="day-chips">
      {WEEKDAYS.map((d) => {
        const working = days.includes(d);
        const short = d.slice(0, 3);
        return (
          <span key={d} data-day={short} data-working={working ? "true" : "false"}
                className={cn("rounded px-1.5 py-0.5 text-xs", dayTone(working), working && "font-medium")}>
            <span aria-hidden>{short}</span>
            <span className="sr-only">{`${short}, ${working ? "working" : "not working"}`}</span>
          </span>
        );
      })}
    </span>
  );
}
