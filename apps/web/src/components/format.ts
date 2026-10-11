const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

/** An API date (yyyy-mm-dd) as dd-Mon-yy, for example 07-Nov-26. */
export function showDate(iso: string | null | undefined): string {
  if (!iso) return "-";
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso);
  if (!m) return iso;
  return `${m[3]}-${MONTHS[Number(m[2]) - 1] ?? m[2]}-${m[1].slice(2)}`;
}

/** Rupees, GST included. */
export function rupees(n: number): string {
  return `Rs ${n.toLocaleString("en-IN")}`;
}
