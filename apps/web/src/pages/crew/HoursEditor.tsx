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
    <fieldset style={{ border: 0, padding: 0, margin: "0 0 1rem" }}>
      <legend style={{ fontWeight: 600 }}>Working hours</legend>
      {rows.map((h, i) => (
        <div key={h.day} style={{ marginBottom: "0.5rem" }}>
          <div style={{ display: "flex", gap: "0.75rem", alignItems: "center", flexWrap: "wrap" }}>
            <span style={{ width: "6.5rem" }}>{h.day}</span>
            <label>
              <input type="checkbox" checked={h.working} aria-label={`${h.day} working`}
                     onChange={(e) => set(i, e.target.checked
                       ? { working: true, start: h.start || "06:00", end: h.end || "12:00" }
                       : { working: false, extra_slots: [] })} />{" "}
              Working
            </label>
            {h.working ? (
              <>
                <input type="time" aria-label={`${h.day} start`} value={h.start}
                       onChange={(e) => set(i, { start: e.target.value })} />
                <span>to</span>
                <input type="time" aria-label={`${h.day} end`} value={h.end}
                       onChange={(e) => set(i, { end: e.target.value })} />
                <button type="button" className="tab" aria-label={`Add a slot on ${h.day}`}
                        onClick={() => set(i, { extra_slots: [...(h.extra_slots ?? []), nextSlot(h)] })}>
                  + Add slot
                </button>
              </>
            ) : <span className="muted">Day off</span>}
          </div>
          {h.working && (h.extra_slots ?? []).map((s, k) => (
            <div key={k} style={{ display: "flex", gap: "0.75rem", alignItems: "center",
                                  flexWrap: "wrap", margin: "0.3rem 0 0 7.25rem" }}>
              <input type="time" aria-label={`${h.day} slot ${k + 2} start`} value={s.start}
                     onChange={(e) => setExtra(i, k, { start: e.target.value })} />
              <span>to</span>
              <input type="time" aria-label={`${h.day} slot ${k + 2} end`} value={s.end}
                     onChange={(e) => setExtra(i, k, { end: e.target.value })} />
              <button type="button" className="tab" aria-label={`Remove slot ${k + 2} on ${h.day}`}
                      onClick={() => removeExtra(i, k)}>
                Remove
              </button>
            </div>
          ))}
        </div>
      ))}
      {error && <p className="field-msg" role="alert">{error}</p>}
    </fieldset>
  );
}
