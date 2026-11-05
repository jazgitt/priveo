import { CalendarDays, ChevronLeft, ChevronRight } from "lucide-react";
import { useEffect, useRef, useState, type ReactNode } from "react";

import { cn } from "@/lib/utils";
import { Button } from "@/ui/button";
import { Input } from "@/ui/input";

import { Scroller } from "./Scroller";
import { datesOf, fmtDate, weekday, type ScheduleOut } from "./api";

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

export function addDays(iso: string, n: number): string {
  const d = new Date(`${iso}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() + n);
  return d.toISOString().slice(0, 10);
}

/**
 * The day the whole Schedule page works on, chosen first. The arrows step a
 * day, the field jumps to any date, and the strip shows the days around it
 * with the status of their schedule (Draft or Frozen) and a mark where
 * something needs the admin (ADM-SCH-35).
 */
export function DateBar({ date, today, from, to, scheduleOf, attention, onChange, title, site, children }: {
  /** The page title and the site, shown at the left of the one slim bar. */
  title: string;
  site?: string;
  date: string;
  today: string;
  /** The first and last day of the strip. */
  from: string;
  to: string;
  scheduleOf: Map<string, ScheduleOut>;
  /** Days with jobs that need scheduling or cutoff requests. */
  attention: Set<string>;
  onChange: (date: string) => void;
  /** The schedule of the day and its actions, in the same bar. */
  children?: ReactNode;
}) {
  const strip = useRef<HTMLDivElement>(null);
  useEffect(() => {
    strip.current?.querySelector<HTMLElement>("[aria-pressed=true]")
      ?.scrollIntoView?.({ inline: "center", block: "nearest" });
  }, [date]);
  const days = datesOf(from < date ? from : date, to > date ? to : date);

  // The strip can be folded away to give the board the room; the choice is remembered.
  const [folded, setFolded] = useState(readFolded);
  const toggle = () => setFolded((f) => { saveFolded(!f); return !f; });

  return (
    <div className="mb-2 rounded-xl border bg-card shadow-xs">
      <div className="flex flex-wrap items-center gap-x-2 gap-y-1.5 px-3 py-2">
        <h1 className="m-0 text-base font-semibold tracking-tight">{title}</h1>
        {site && <span className="text-sm font-medium">{site}</span>}
        <span className="mx-1 hidden h-5 border-l sm:inline-block" aria-hidden />
        <Button size="icon" variant="outline" className="size-8" aria-label="Previous day" onClick={() => onChange(addDays(date, -1))}>
          <ChevronLeft aria-hidden />
        </Button>
        <Input type="date" aria-label="Day" className="h-8 w-36" value={date}
               onChange={(e) => { if (e.target.value) onChange(e.target.value); }} />
        <Button size="icon" variant="outline" className="size-8" aria-label="Next day" onClick={() => onChange(addDays(date, 1))}>
          <ChevronRight aria-hidden />
        </Button>
        {children}
        <Button size="sm" variant="ghost" className="ml-auto h-8" aria-expanded={!folded} aria-controls="sch-days"
                onClick={toggle}>
          <CalendarDays aria-hidden /> {folded ? "Show days" : "Hide days"}
        </Button>
      </div>
      {!folded && (
        <div id="sch-days" className="border-t">
          <Scroller innerRef={strip} className="sch-days" role="group" aria-label="Days">
            {days.map((d) => {
              const s = scheduleOf.get(d);
              const [, m, dd] = d.split("-");
              return (
                <button key={d} type="button" aria-pressed={d === date} onClick={() => onChange(d)}
                        aria-label={`${weekday(d)} ${fmtDate(d)}, ${s ? s.status : "no schedule"}${d === today ? ", today" : ""}${attention.has(d) ? ", needs you" : ""}`}
                        className={cn("sch-day", d < today && "past", d === today && "today", weekday(d) === "Sun" && "week")}>
                  <span className="dow">{d === today ? "Today" : weekday(d)}</span>
                  <span className="dom">{dd}</span>
                  <span className="mon">{MONTHS[Number(m) - 1]}</span>
                  <i className={cn("dot", s?.status.toLowerCase())} />
                  {attention.has(d) && <i className="flag" />}
                </button>
              );
            })}
          </Scroller>
          <p className="m-0 flex flex-wrap items-center gap-x-4 gap-y-1 border-t px-3 py-1 text-xs text-muted-foreground" aria-hidden>
            <span className="sch-day-key"><i className="dot draft" /> Draft</span>
            <span className="sch-day-key"><i className="dot frozen" /> Frozen</span>
            <span className="sch-day-key"><i className="dot" /> No schedule</span>
            <span className="sch-day-key"><i className="flag" /> Needs you</span>
          </p>
        </div>
      )}
    </div>
  );
}

const FOLD_KEY = "priveo.schedule.days-folded";
function readFolded(): boolean {
  try { return localStorage.getItem(FOLD_KEY) === "1"; } catch { return false; }
}
function saveFolded(folded: boolean) {
  try { localStorage.setItem(FOLD_KEY, folded ? "1" : "0"); } catch { /* A private window keeps nothing; the bar still works. */ }
}
