/** The fill of the empty part of the lock: red when locked, green when unlocked (P3-1). */
export const LOCK_FILL = { locked: "#dc2626", unlocked: "#16a34a" } as const;

/** The shackle of a locked lock: both legs go into the body. */
export const LOCKED_SHACKLE = "M8 11V7a4 4 0 0 1 8 0v4";
/**
 * The shackle of an unlocked lock: the left leg is lifted clear of the body and the arch is swung
 * to the left, so open and closed differ in shape as well as colour (P3-1).
 */
export const UNLOCKED_SHACKLE = "M8 7a4 4 0 0 1 8 0v4";

/**
 * The lock icon of a card and the crew queue (P3-1). The outline is drawn by hand because the
 * library lock is outline-only and has no empty part to fill. The body's empty part is filled red
 * when locked and green when unlocked.
 */
export function LockGlyph({ locked, className }: { locked: boolean; className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round"
         strokeLinejoin="round" aria-hidden="true" focusable="false" className={className}
         data-state={locked ? "locked" : "unlocked"}>
      <rect data-part="body" x="4" y="11" width="16" height="10" rx="2"
            fill={locked ? LOCK_FILL.locked : LOCK_FILL.unlocked} />
      <path data-part="shackle" d={locked ? LOCKED_SHACKLE : UNLOCKED_SHACKLE} />
    </svg>
  );
}
