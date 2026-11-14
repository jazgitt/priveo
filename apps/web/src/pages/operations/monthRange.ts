const iso = (d: Date) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;

/** The first and last day of the current month, as yyyy-mm-dd. The default period of every Operations report. */
export function currentMonth(now: Date = new Date()): { from: string; to: string } {
  return { from: iso(new Date(now.getFullYear(), now.getMonth(), 1)), to: iso(new Date(now.getFullYear(), now.getMonth() + 1, 0)) };
}
