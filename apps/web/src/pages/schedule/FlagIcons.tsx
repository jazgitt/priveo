/** The colours of the card flags (owner, 10-Nov-26). The cutoff box takes its colour from --sch-cutoff in schedule.css. */
export const FLAG_COLOR = { late: "#dc143c", manual: "#4169e1", cutoff: "#c026d3" } as const;

interface GlyphProps {
  className?: string;
  /** Inside a control that already has a name (a filter chip), the glyph is hidden from assistive technology. */
  decorative?: boolean;
}

/** The accessibility attributes of a glyph: a named image on a card, hidden inside a named control. */
const a11y = (label: string, decorative?: boolean) =>
  decorative ? { "aria-hidden": true as const } : { role: "img" as const, "aria-label": label };

/** Late: a filled hourglass with an exclamation mark beside it, in crimson. */
export function HourglassAlertGlyph({ className, decorative }: GlyphProps) {
  return (
    <svg viewBox="0 0 24 24" fill={FLAG_COLOR.late} focusable="false" className={className} data-glyph="late" {...a11y("Late", decorative)}>
      <path d="M3 2h12v4l-4 6 4 6v4H3v-4l4-6-4-6z" />
      <rect x="18" y="2" width="3.4" height="12" rx="1.7" />
      <circle cx="19.7" cy="19.6" r="2.1" />
    </svg>
  );
}

/** Placed by hand: a filled hand, in royal blue. */
export function HandGlyph({ className, decorative }: GlyphProps) {
  return (
    <svg viewBox="0 0 24 24" fill={FLAG_COLOR.manual} focusable="false" className={className} data-glyph="manual" {...a11y("Placed by hand", decorative)}>
      <rect x="6" y="3" width="3.4" height="12" rx="1.7" />
      <rect x="9.9" y="1.2" width="3.4" height="13" rx="1.7" />
      <rect x="13.8" y="2.4" width="3.4" height="12" rx="1.7" />
      <rect x="17.6" y="5" width="3.2" height="10" rx="1.6" />
      <path d="M5.4 11h15.4v3.6a7.4 7.4 0 0 1-7.4 7.4h-.9a7.4 7.4 0 0 1-7.4-7.4z" />
      <rect x="1.6" y="10.6" width="3.4" height="8.4" rx="1.7" transform="rotate(-35 3.3 12.3)" />
    </svg>
  );
}
