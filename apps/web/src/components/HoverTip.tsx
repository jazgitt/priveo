import { useState, type ReactNode } from "react";

import "./hovertip.css";

/**
 * A value that shows more detail on hover or keyboard focus. The box is placed
 * with fixed coordinates, below the value or above it when there is no room, so
 * a table's scroll area never clips it.
 */
export function HoverTip({ label, ariaLabel, children }: {
  label: ReactNode; ariaLabel: string; children: ReactNode;
}) {
  const [at, setAt] = useState<{ right: number; top?: number; bottom?: number } | null>(null);
  const show = (el: HTMLElement) => {
    const r = el.getBoundingClientRect();
    const below = window.innerHeight - r.bottom;
    const right = Math.max(8, window.innerWidth - r.right);
    setAt(below >= 240 || below >= r.top
      ? { right, top: r.bottom + 4 }
      : { right, bottom: window.innerHeight - r.top + 4 });
  };
  return (
    <span className="cap-tip" tabIndex={0} aria-label={ariaLabel}
          onMouseEnter={(e) => show(e.currentTarget)} onMouseLeave={() => setAt(null)}
          onFocus={(e) => show(e.currentTarget)} onBlur={() => setAt(null)}>
      <span className="cap-tip-value">{label}</span>
      <span className="cap-tip-box" role="tooltip" style={at ? { ...at, display: "block" } : undefined}>
        {children}
      </span>
    </span>
  );
}

export interface TipRow { key: string; left: string; right: string; note?: string; tone?: "warn" }

/** Rows of "name, note ... value" for a HoverTip. */
export function TipRows({ title, rows, empty }: { title: string; rows: TipRow[]; empty: string }) {
  return (
    <>
      <strong>{title}</strong>
      {rows.length === 0 ? <em>{empty}</em> : rows.map((r) => (
        <span key={r.key} className={`cap-tip-row${r.tone ? ` ${r.tone}` : ""}`}>
          <span>{r.left}{r.note && <small>{r.note}</small>}</span><b>{r.right}</b>
        </span>
      ))}
    </>
  );
}
