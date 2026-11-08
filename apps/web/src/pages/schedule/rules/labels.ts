/**
 * The names the Scheduler Rules tab uses (SCHR-CUT-06). The three cutoffs are named the same
 * way in screens and reports: Customer cutoff, Freeze and 9 PM rule.
 */
export const CUTOFF_NAMES = [
  { name: "Customer cutoff", meaning: "The scheduler's deadline: the time by which a customer's service should end." },
  { name: "Freeze", meaning: "The hour the day before when the schedule is frozen." },
  { name: "9 PM rule", meaning: "The hour the day before after which customers cannot change their service." },
] as const;

/** Labels that replace the registry label, so the cutoff names read the same everywhere. */
export const LABELS: Record<string, string> = {
  "site.weekday_cutoff_hard": "Customer cutoff is strict on weekdays",
  "site.weekend_cutoff_flexible": "Customer cutoff is flexible on weekend days",
  "schedule.freeze_hour": "Freeze hour",
  "schedule.customer_change_hour": "9 PM rule hour",
};

export const labelOf = (key: string, fallback: string) => LABELS[key] ?? fallback;

/** Monday 0 to Sunday 6, as the API counts weekdays. */
export const WEEKDAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"] as const;

const pad = (n: number) => String(n).padStart(2, "0");

/** A value in minutes after midnight as HH:MM. */
export const clock = (m: number) => `${pad(Math.floor(m / 60))}:${pad(m % 60)}`;

/** HH:MM as minutes after midnight, or null when it is not a time. */
export function minutesOf(t: string): number | null {
  const [h, m] = t.split(":").map(Number);
  return Number.isFinite(h) && Number.isFinite(m) ? h * 60 + m : null;
}

/** Minutes keys end in `_minute` and show as a time. */
export const isMinuteKey = (key: string) => key.endsWith("_minute");
