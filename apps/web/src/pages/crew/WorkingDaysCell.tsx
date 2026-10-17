import { HoverTip, TipRows, type TipRow } from "../../components";
import { showDate } from "../../components/format";
import { WEEKDAYS, type Crew, type DayHours } from "./api";

const LETTERS = ["M", "T", "W", "T", "F", "S", "S"];
const FULL_DAY = new Set(["Sick", "Leave"]);

const iso = (d: Date) =>
  `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
const minutes = (t: string) => Number(t.slice(0, 2)) * 60 + Number(t.slice(3, 5));
const clock = (m: number) => `${String(Math.floor(m / 60)).padStart(2, "0")}:${String(m % 60).padStart(2, "0")}`;

/** The seven dates of the week that holds `today`, Monday first. */
export function weekDates(today: Date): string[] {
  const monday = new Date(today.getFullYear(), today.getMonth(), today.getDate());
  monday.setDate(monday.getDate() - ((monday.getDay() + 6) % 7));
  return WEEKDAYS.map((_, i) => {
    const d = new Date(monday);
    d.setDate(monday.getDate() + i);
    return iso(d);
  });
}

export interface DaySummary {
  letter: string;
  day: string;
  date: string;
  status: "working" | "partial" | "off";
  /** "05:00-14:00, 19:00-20:30", cut by a late start. */
  hours: string;
  note: string;
}

/** One weekday's windows, with a late start cutting each window (ADM-CRW-26). */
function windows(h: DayHours, lateFrom: number | null): string {
  const all = [{ start: h.start, end: h.end }, ...(h.extra_slots ?? [])]
    .map((s) => ({ s: minutes(s.start), e: minutes(s.end) }))
    .map((w) => (lateFrom === null ? w : { s: Math.max(w.s, lateFrom), e: w.e }))
    .filter((w) => w.e > w.s);
  return all.map((w) => `${clock(w.s)}-${clock(w.e)}`).join(", ");
}

/**
 * The week's days for a crew member. A day off, or off the whole day (Sick or
 * Leave), is "off". A late start keeps the day but marks it "partial".
 */
export function summariseWeek(c: Crew, today: Date = new Date()): DaySummary[] {
  const dates = weekDates(today);
  return WEEKDAYS.map((day, i) => {
    const h = c.working_hours.find((x) => x.day === day);
    const date = dates[i];
    const ex = c.exceptions.find((e) => e.date === date);
    const base = { letter: LETTERS[i], day, date };
    if (!h || !h.working) return { ...base, status: "off", hours: "", note: "Day off" };
    if (ex && FULL_DAY.has(ex.kind)) {
      return { ...base, status: "off", hours: "", note: `${ex.kind} on ${showDate(date)}` };
    }
    if (ex) {
      const from = ex.start ? minutes(ex.start) : null;
      return { ...base, status: "partial", hours: windows(h, from),
               note: `${ex.kind}${ex.start ? ` from ${ex.start}` : ""} on ${showDate(date)}` };
    }
    return { ...base, status: "working", hours: windows(h, null), note: "" };
  });
}

/**
 * "M, T, W, T, F" for the days worked this week, with a partial day (late start)
 * in another colour. Hover gives each day with its hours and the exceptions.
 */
export function WorkingDaysCell({ crew, today }: { crew: Crew; today?: Date }) {
  const week = summariseWeek(crew, today);
  const worked = week.filter((d) => d.status !== "off");
  const away = week.filter((d) => d.status === "off" && d.note !== "Day off");
  const rows: TipRow[] = [
    ...worked.map((d) => ({
      key: d.date, left: d.day, right: d.hours || "-",
      note: d.status === "partial" ? d.note : undefined,
      tone: d.status === "partial" ? "warn" as const : undefined,
    })),
    ...away.map((d) => ({ key: d.date, left: d.day, right: "Off", note: d.note, tone: "warn" as const })),
  ];
  const label = worked.length === 0 ? "None" : worked.map((d, i) => (
    <span key={d.date}>
      {i > 0 && ", "}
      <span className={d.status === "partial" ? "dow-warn" : undefined}>{d.letter}</span>
    </span>
  ));
  const text = worked.map((d) => d.day).join(", ") || "no working days";
  return (
    <HoverTip label={label} ariaLabel={`Working days this week: ${text}. Hover for the hours.`}>
      <TipRows title={`This week, ${showDate(week[0].date)} to ${showDate(week[6].date)}`}
               rows={rows} empty="No working days" />
    </HoverTip>
  );
}
