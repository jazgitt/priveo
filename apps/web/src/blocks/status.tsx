import { cn } from "@/lib/utils";

export type Tone = "ok" | "warn" | "error" | "info" | "spa" | "neutral";

/** One colour for each status, the same on every page. */
const TONE_OF: Record<string, Tone> = {
  Active: "ok", Received: "ok", Completed: "ok", Resolved: "ok", Working: "ok",
  Activating: "warn", Due: "warn", Initiated: "info", Partial: "warn", Pending: "warn",
  Unscheduled: "warn", Late: "error",
  Inactive: "error", "Over due": "error", Missed: "error", Off: "neutral",
  Frozen: "info", Draft: "neutral", Scheduled: "info", "In progress": "info", "Could not complete": "error",
};

const CLASSES: Record<Tone, string> = {
  ok: "bg-ok/10 text-ok ring-ok/25",
  warn: "bg-warn/10 text-[#9a6513] ring-warn/30",
  error: "bg-destructive/10 text-destructive ring-destructive/25",
  info: "bg-info/10 text-info ring-info/25",
  spa: "bg-spa/10 text-spa ring-spa/25",
  neutral: "bg-muted text-muted-foreground ring-border",
};

export function toneOf(status: string): Tone {
  return TONE_OF[status] ?? "neutral";
}

/** A status as a coloured badge; the tone comes from the status unless given. */
export function StatusBadge({ status, tone, className }: { status: string; tone?: Tone; className?: string }) {
  return (
    <span className={cn(
      "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium whitespace-nowrap ring-1 ring-inset",
      CLASSES[tone ?? toneOf(status)], className,
    )}>
      {status}
    </span>
  );
}
