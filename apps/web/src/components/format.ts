const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

/** An API date (yyyy-mm-dd) as dd-Mon-yy, for example 07-Nov-26. */
export function showDate(iso: string | null | undefined): string {
  if (!iso) return "-";
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso);
  if (!m) return iso;
  return `${m[3]}-${MONTHS[Number(m[2]) - 1] ?? m[2]}-${m[1].slice(2)}`;
}

/** Rupees with the ₹ sign, for example ₹1,499 (GST included). */
export function inr(n: number | null | undefined): string {
  return n === null || n === undefined ? "-" : `₹${n.toLocaleString("en-IN")}`;
}

/** A date-time as dd-Mon-yy HH:MM in India time. */
export function showDateTime(iso: string | null | undefined): string {
  if (!iso) return "-";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  const p = new Intl.DateTimeFormat("en-GB", {
    timeZone: "Asia/Kolkata", day: "2-digit", month: "short", year: "2-digit",
    hour: "2-digit", minute: "2-digit", hour12: false,
  }).formatToParts(d);
  const get = (t: string) => p.find((x) => x.type === t)?.value ?? "";
  return `${get("day")}-${get("month")}-${get("year")} ${get("hour")}:${get("minute")}`;
}

/** Rupees, GST included. */
export function rupees(n: number): string {
  return `Rs ${n.toLocaleString("en-IN")}`;
}
