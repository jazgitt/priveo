import type { ReactNode } from "react";

import { showDate } from "../../../components/format";
import { addDays } from "../DateBar";
import { hhmm } from "../api";

/** Sunday on or before `iso`: the week starts on Sunday (ADM-SCH-09). */
export function weekStartOf(iso: string): string {
  const day = new Date(`${iso}T00:00:00Z`).getUTCDay();
  return addDays(iso, -day);
}

export const weekEndOf = (start: string) => addDays(start, 6);

/** "9 Nov 26 to 15 Nov 26" in the app's date style. */
export const weekLabel = (start: string) => `${showDate(start)} to ${showDate(weekEndOf(start))}`;

export const humanise = (key: string) => {
  const text = key.replace(/_/g, " ").trim();
  return text.charAt(0).toUpperCase() + text.slice(1);
};

const ISO = /^\d{4}-\d{2}-\d{2}$/;

/** A value as the weekly summary shows it: ISO dates as dd-Mon-yy, empty as a dash. */
export function plain(value: unknown): ReactNode {
  if (value === null || value === undefined || value === "") return "-";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (typeof value === "string" && ISO.test(value)) return showDate(value);
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

/** A break window from the daily view, whatever its two keys are called. */
export function breakText(brk: Record<string, unknown> | null | undefined): string {
  if (!brk) return "";
  const a = brk.start_time ?? brk.start, b = brk.end_time ?? brk.end;
  const text = (v: unknown) => (typeof v === "number" ? hhmm(v) : String(v ?? ""));
  return a === undefined || b === undefined ? "" : `${text(a)} to ${text(b)}`;
}

export function Cell({ children, head }: { children?: ReactNode; head?: boolean }) {
  const cls = "px-2 py-1.5 text-left align-top text-sm";
  return head
    ? <th scope="col" className={`${cls} font-medium text-muted-foreground`}>{children}</th>
    : <td className={cls}>{children}</td>;
}
