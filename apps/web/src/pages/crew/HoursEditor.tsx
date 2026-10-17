import { Plus, X } from "lucide-react";

import { cn } from "@/lib/utils";
import { Button } from "@/ui/button";
import { Input } from "@/ui/input";
import { Switch } from "@/ui/switch";

import { WEEKDAYS, type DayHours, type Slot } from "./api";

const toMinutes = (t: string) => {
  const [h, m] = t.split(":").map(Number);
  return (Number.isFinite(h) ? h : 0) * 60 + (Number.isFinite(m) ? m : 0);
};
const toClock = (n: number) => {
  const c = Math.max(0, Math.min(n, 24 * 60 - 1));
  return `${String(Math.floor(c / 60)).padStart(2, "0")}:${String(c % 60).padStart(2, "0")}`;
};

/** The slot to offer when the admin adds one: an hour after the last slot ends, for two hours. */
function nextSlot(h: DayHours): Slot {
  const last = (h.extra_slots ?? []).at(-1)?.end ?? h.end ?? "12:00";
  const start = toMinutes(last) + 60;
  return { start: toClock(start), end: toClock(start + 120) };
}

function TimeRange({ day, n, start, end, onStart, onEnd }: {
  day: string; n: number; start: string; end: string; onStart: (v: string) => void; onEnd: (v: string) => void;
}) {
  const name = n === 1 ? day : `${day} slot ${n}`;
  return (
    <span className="flex items-center gap-2">
      <Input type="time" className="h-8 w-28" aria-label={`${name} start`} value={start} onChange={(e) => onStart(e.target.value)} />
      <span className="text-muted-foreground">to</span>
      <Input type="time" className="h-8 w-28" aria-label={`${name} end`} value={end} onChange={(e) => onEnd(e.target.value)} />
    </span>
  );
}

/**
 * Seven rows, Monday to Sunday: working or off. A working day has one or more
 * slots, for example 05:00 to 13:00 and 17:00 to 19:00 (ADM-CRW-25).
 */
export function HoursEditor({ value, onChange, error }: {
  value: DayHours[];
  onChange: (next: DayHours[]) => void;
  error?: string;
}) {
  const rows: DayHours[] = WEEKDAYS.map((day) => value.find((h) => h.day === day)
    ?? { day, working: false, start: "", end: "", extra_slots: [] });
  const set = (i: number, patch: Partial<DayHours>) =>
    onChange(rows.map((h, j) => (j === i ? { ...h, ...patch } : h)));
  const setExtra = (i: number, k: number, patch: Partial<Slot>) =>
    set(i, { extra_slots: (rows[i].extra_slots ?? []).map((s, n) => (n === k ? { ...s, ...patch } : s)) });
  const removeExtra = (i: number, k: number) =>
    set(i, { extra_slots: (rows[i].extra_slots ?? []).filter((_s, n) => n !== k) });

  return (
    <fieldset className="m-0 min-w-0 border-0 p-0">
      <legend className="mb-2 text-[0.8125rem] font-medium">Working hours</legend>
      <div className="divide-y rounded-lg border bg-card">
        {rows.map((h, i) => (
          <div key={h.day} className={cn("grid grid-cols-[7rem_5.5rem_minmax(0,1fr)] items-start gap-3 px-3 py-2", !h.working && "bg-muted/40")}>
            <span className="pt-1.5 text-sm font-medium">{h.day}</span>
            <label className="flex items-center gap-2 pt-1 text-sm">
              <Switch aria-label={`${h.day} working`} checked={h.working}
                      onCheckedChange={(on) => set(i, on
                        ? { working: true, start: h.start || "06:00", end: h.end || "12:00" }
                        : { working: false, extra_slots: [] })} />
              <span className="text-muted-foreground">{h.working ? "Works" : "Off"}</span>
            </label>
            {h.working ? (
              <div className="flex flex-col gap-2">
                <div className="flex flex-wrap items-center gap-2">
                  <TimeRange day={h.day} n={1} start={h.start} end={h.end} onStart={(v) => set(i, { start: v })} onEnd={(v) => set(i, { end: v })} />
                  <Button type="button" size="sm" variant="ghost" aria-label={`Add a slot on ${h.day}`}
                          onClick={() => set(i, { extra_slots: [...(h.extra_slots ?? []), nextSlot(h)] })}>
                    <Plus aria-hidden /> Add slot
                  </Button>
                </div>
                {(h.extra_slots ?? []).map((s, k) => (
                  <div key={k} className="flex flex-wrap items-center gap-2">
                    <TimeRange day={h.day} n={k + 2} start={s.start} end={s.end}
                               onStart={(v) => setExtra(i, k, { start: v })} onEnd={(v) => setExtra(i, k, { end: v })} />
                    <Button type="button" size="icon-sm" variant="ghost" aria-label={`Remove slot ${k + 2} on ${h.day}`}
                            onClick={() => removeExtra(i, k)}><X /></Button>
                  </div>
                ))}
              </div>
            ) : <span className="pt-1.5 text-sm text-muted-foreground">Day off</span>}
          </div>
        ))}
      </div>
      {error && <p className="mt-2 mb-0 text-xs text-destructive" role="alert">{error}</p>}
    </fieldset>
  );
}
