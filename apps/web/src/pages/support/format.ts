const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

/** dd-Mon-yy, for example 07-Nov-26. Accepts a date or a date-time string. */
export function formatDate(value: string | null | undefined): string {
  if (!value) return "-";
  const d = new Date(value.length === 10 ? `${value}T00:00:00` : value);
  if (Number.isNaN(d.getTime())) return "-";
  const dd = String(d.getDate()).padStart(2, "0");
  return `${dd}-${MONTHS[d.getMonth()]}-${String(d.getFullYear()).slice(-2)}`;
}

/** The yyyy-mm-dd part of a date or date-time string, for date filters. */
export function dayOf(value: string): string {
  return value.slice(0, 10);
}

export function stars(n: number | null): string {
  return n === null ? "-" : `${n} / 5`;
}
