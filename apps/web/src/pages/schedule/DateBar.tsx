import { ChevronLeft, ChevronRight } from "lucide-react";
import { useEffect, useRef, type ReactNode } from "react";

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
export function DateBar({ date, today, from, to, scheduleOf, attention, onChange, children }: {
  date: string;
  today: string;
  /** The first and last day of the strip. */
  from: string;
  to: string;
  scheduleOf: Map<string, ScheduleOut>;
  /** Days with jobs that need scheduling or cutoff requests. */
  attention: Set<string>;
  onChange: (date: string) => void;
  /** The schedule of the day, under the strip. */
  children?: ReactNode;
}) {
  const strip = useRef<HTMLDivElement>(null);
  useEffect(() => {
    strip.current?.querySelector<HTMLElement>("[aria-pressed=true]")
      ?.scrollIntoView?.({ inline: "center", block: "nearest" });
  }, [date]);
  const days = datesOf(from < date ? from : date, to > date ? to : date);

  return (
    <div className="mb-5 rounded-xl border bg-card shadow-xs">
      <div className="flex flex-wrap items-center gap-2 border-b px-4 py-3">
        <Button size="icon" variant="outline" aria-label="Previous day" onClick={() => onChange(addDays(date, -1))}>
          <ChevronLeft aria-hidden />
        </Button>
        <Input type="date" aria-label="Day" className="w-40" value={date}
               onChange={(e) => { if (e.target.value) onChange(e.target.value); }} />
        <Button size="icon" variant="outline" aria-label="Next day" onClick={() => onChange(addDays(date, 1))}>
          <ChevronRight aria-hidden />
        </Button>
        <span className="ml-3 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted-foreground" aria-hidden>
          <span className="sch-day-key"><i className="dot draft" /> Draft</span>
          <span className="sch-day-key"><i className="dot frozen" /> Frozen</span>
          <span className="sch-day-key"><i className="dot" /> No schedule</span>
          <span className="sch-day-key"><i className="flag" /> Needs you</span>
        </span>
      </div>
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
      {children && <div className="border-t">{children}</div>}
    </div>
  );
}
