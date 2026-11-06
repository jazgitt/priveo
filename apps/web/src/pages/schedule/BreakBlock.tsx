import { cn } from "@/lib/utils";

import type { Win } from "./Board";
import { hhmm } from "./api";

/** The break of one cleaner as a block that holds no job (SCHR-BRK-09). It is not a drop target. */
export function BreakBlock({ start, end, className }: { start: number; end: number; className?: string }) {
  return (
    <div className={cn("sch-break sch-break-rest", className)} data-break data-start={start} data-end={end}
         aria-label={`Break ${hhmm(start)}-${hhmm(end)}`}>
      Break {hhmm(start)}-{hhmm(end)}
    </div>
  );
}

/** The windows of a day with the break taken out, so no free slot is drawn over the break. */
export function aroundBreak(wins: Win[], brk: Win | null): Win[] {
  if (!brk) return wins;
  return wins.flatMap((w) => {
    if (w.end <= brk.start || w.start >= brk.end) return [w];
    const out: Win[] = [];
    if (w.start < brk.start) out.push({ start: w.start, end: brk.start });
    if (w.end > brk.end) out.push({ start: brk.end, end: w.end });
    return out;
  });
}

/** The break of a cleaner on the day, or null (no break, or the site is not on the new rules). */
export function breakOf(avail: { break_start?: number | null; break_end?: number | null } | undefined): Win | null {
  return avail && typeof avail.break_start === "number" && typeof avail.break_end === "number"
    ? { start: avail.break_start, end: avail.break_end } : null;
}
