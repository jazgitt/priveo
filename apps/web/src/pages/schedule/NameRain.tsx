import { useMemo } from "react";

/** The names fall for as long as the scheduler runs. Each one is shown at least once. */
const MIN_FALLING = 12;

/** Fisher-Yates shuffle, so the names fall in no fixed order. */
function shuffled<T>(items: readonly T[]): T[] {
  const out = [...items];
  for (let i = out.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [out[i], out[j]] = [out[j], out[i]];
  }
  return out;
}

function prefersReducedMotion(): boolean {
  return typeof window !== "undefined" && typeof window.matchMedia === "function"
    && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

/**
 * A light rain of names (crew members and car registrations) falling down the screen while the
 * scheduler runs. Purely decorative: it ignores the pointer, is hidden from assistive tech, and
 * shows nothing when the admin asks for reduced motion.
 */
export function NameRain({ names, active }: { names: string[]; active: boolean }) {
  // The names are keyed by their joined text, so a new array of the same names does not restart the rain.
  const key = names.join("\u0000");
  // Rebuilt each time a run starts, so every run falls in a new order.
  const items = useMemo(() => {
    const list = key ? key.split("\u0000") : [];
    if (!active || list.length === 0) return [];
    const count = Math.max(list.length, MIN_FALLING);
    const order = shuffled(list);
    return Array.from({ length: count }, (_, i) => ({
      id: i,
      name: i < order.length ? order[i] : order[Math.floor(Math.random() * order.length)],
      left: Math.random() * 100,
      delay: Math.random() * 3,
      duration: 4 + Math.random() * 2.5,
      size: 0.7 + Math.random() * 0.35,
    }));
  }, [active, key]);

  if (!active || items.length === 0 || prefersReducedMotion()) return null;

  return (
    <div className="sch-rain" aria-hidden="true" data-testid="name-rain">
      {items.map((it) => (
        <span key={it.id} className="sch-rain-item"
              style={{
                left: `${it.left}%`,
                animationDelay: `${it.delay}s`,
                animationDuration: `${it.duration}s`,
                fontSize: `${it.size}rem`,
              }}>
          {it.name}
        </span>
      ))}
    </div>
  );
}
