import { WEEKDAYS, type DayHours } from "./api";

/** Seven rows, Monday to Sunday: working or off, with a start and end. */
export function HoursEditor({ value, onChange, error }: {
  value: DayHours[];
  onChange: (next: DayHours[]) => void;
  error?: string;
}) {
  const rows: DayHours[] = WEEKDAYS.map((day) => value.find((h) => h.day === day)
    ?? { day, working: false, start: "", end: "" });
  const set = (i: number, patch: Partial<DayHours>) =>
    onChange(rows.map((h, j) => (j === i ? { ...h, ...patch } : h)));
  return (
    <fieldset style={{ border: 0, padding: 0, margin: "0 0 1rem" }}>
      <legend style={{ fontWeight: 600 }}>Working hours</legend>
      {rows.map((h, i) => (
        <div key={h.day} style={{ display: "flex", gap: "0.75rem", alignItems: "center",
                                  flexWrap: "wrap", marginBottom: "0.4rem" }}>
          <span style={{ width: "6.5rem" }}>{h.day}</span>
          <label>
            <input type="checkbox" checked={h.working} aria-label={`${h.day} working`}
                   onChange={(e) => set(i, e.target.checked
                     ? { working: true, start: h.start || "06:00", end: h.end || "12:00" }
                     : { working: false })} />{" "}
            Working
          </label>
          {h.working ? (
            <>
              <input type="time" aria-label={`${h.day} start`} value={h.start}
                     onChange={(e) => set(i, { start: e.target.value })} />
              <span>to</span>
              <input type="time" aria-label={`${h.day} end`} value={h.end}
                     onChange={(e) => set(i, { end: e.target.value })} />
            </>
          ) : <span className="muted">Day off</span>}
        </div>
      ))}
      {error && <p className="field-msg" role="alert">{error}</p>}
    </fieldset>
  );
}
