import { Loader2, PartyPopper, Volume2, VolumeX } from "lucide-react";
import { useEffect, useRef } from "react";

/** A spark of a firework: it moves, slows under a little gravity and fades. */
interface Spark { x: number; y: number; vx: number; vy: number; life: number; max: number; hue: number }

const SPARKS_PER_BURST = 60;
/** While the scheduler runs, a new firework goes up about every this many milliseconds. */
const RUNNING_EVERY_MS = 650;
/** The celebration: this many bursts, this far apart, then the caption leaves. */
const CELEBRATE_BURSTS = 12;
const CELEBRATE_EVERY_MS = 250;
const CELEBRATE_FOR_MS = 3800;
/** With reduced motion there is no animation, only the caption, for this long. */
const REDUCED_FOR_MS = 2500;

const reducedMotion = () =>
  typeof window !== "undefined" && typeof window.matchMedia === "function"
  && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

/**
 * An overlay that shows fireworks while the scheduler runs ("running") and a
 * celebration when it has finished ("celebrate", with the result as its caption).
 * It never takes clicks, except its Mute control, so the page stays usable under it.
 * With reduced motion it shows the caption only. The music is started by the page.
 */
export function Fireworks({ mode, message, onEnd, muted, onToggleMute }: {
  mode: "running" | "celebrate";
  /** The result of the run, shown under the celebration. */
  message?: string;
  /** Called once the celebration has finished. */
  onEnd?: () => void;
  /** Whether the run music is muted, and the control that toggles it (ux9). Without a toggle there is no control. */
  muted?: boolean;
  onToggleMute?: () => void;
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const endRef = useRef(onEnd);
  endRef.current = onEnd;

  useEffect(() => {
    const timers: number[] = [];
    const endLater = (ms: number) => { timers.push(window.setTimeout(() => endRef.current?.(), ms)); };

    if (reducedMotion()) {
      if (mode === "celebrate") endLater(REDUCED_FOR_MS);
      return () => timers.forEach((t) => window.clearTimeout(t));
    }

    const canvas = canvasRef.current;
    const ctx = canvas?.getContext("2d") ?? null;
    let sparks: Spark[] = [];
    let raf = 0;

    const size = () => {
      if (!canvas) return;
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    };
    size();
    window.addEventListener("resize", size);

    const burst = () => {
      if (!canvas) return;
      const x = canvas.width * (0.15 + Math.random() * 0.7);
      const y = canvas.height * (0.1 + Math.random() * 0.4);
      const hue = Math.random() * 360;
      for (let i = 0; i < SPARKS_PER_BURST; i++) {
        const angle = Math.random() * Math.PI * 2;
        const speed = 1 + Math.random() * 4.5;
        sparks.push({
          x, y, vx: Math.cos(angle) * speed, vy: Math.sin(angle) * speed,
          life: 0, max: 45 + Math.random() * 30, hue: hue + (Math.random() * 60 - 30),
        });
      }
    };

    const frame = () => {
      if (ctx && canvas) {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        sparks = sparks.filter((p) => p.life < p.max);
        for (const p of sparks) {
          p.life += 1;
          p.vx *= 0.98;
          p.vy = p.vy * 0.98 + 0.06;
          p.x += p.vx;
          p.y += p.vy;
          ctx.fillStyle = `hsla(${p.hue}, 90%, 60%, ${1 - p.life / p.max})`;
          ctx.beginPath();
          ctx.arc(p.x, p.y, 2.2, 0, Math.PI * 2);
          ctx.fill();
        }
      }
      raf = window.requestAnimationFrame(frame);
    };
    raf = window.requestAnimationFrame(frame);

    if (mode === "running") {
      burst();
      timers.push(window.setInterval(burst, RUNNING_EVERY_MS));
    } else {
      for (let i = 0; i < CELEBRATE_BURSTS; i++) timers.push(window.setTimeout(burst, i * CELEBRATE_EVERY_MS));
      endLater(CELEBRATE_FOR_MS);
    }

    return () => {
      window.cancelAnimationFrame(raf);
      window.removeEventListener("resize", size);
      timers.forEach((t) => { window.clearTimeout(t); window.clearInterval(t); });
    };
  }, [mode]);

  const reduced = reducedMotion();
  return (
    <div className="sch-fireworks" data-mode={mode}>
      {!reduced && <canvas ref={canvasRef} className="sch-fireworks-canvas" aria-hidden />}
      {onToggleMute && (
        <button type="button" className="sch-fireworks-mute" onClick={onToggleMute}>
          {muted ? <VolumeX className="size-4" aria-hidden /> : <Volume2 className="size-4" aria-hidden />}
          <span>{muted ? "Unmute music" : "Mute music"}</span>
        </button>
      )}
      <div role="status" className="sch-fireworks-caption">
        {mode === "running" ? (
          <><Loader2 className="size-4 animate-spin" aria-hidden /> <span>Scheduling the jobs…</span></>
        ) : (
          <><PartyPopper className="size-4" aria-hidden /> <strong>Schedule done</strong>{message && <span>{message}</span>}</>
        )}
      </div>
    </div>
  );
}
