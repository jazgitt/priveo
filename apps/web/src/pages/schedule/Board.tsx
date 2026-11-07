import type { CSSProperties } from "react";

import { StatusBadge } from "@/blocks/status";

import { hhmm, type AdminJob, type CrewDayAvailability, type SchedulingCrew } from "./api";

/** Moves and the timeline snap start times to 5 minutes. */
export const SNAP = 5;

/** The detailed card moves in 15-minute steps (owner, 8-Nov-26). */
export const DETAILED_STEP = 15;

/** How much a card shows: compact, standard, or detailed with the model and the customer. */
export type Density = "compact" | "standard" | "detailed";

/** The minutes a card moves by: 15 on the detailed layout, 5 otherwise. */
export const stepOf = (density: Density): number => (density === "detailed" ? DETAILED_STEP : SNAP);

const CODES: Record<string, string> = {
  "Cleaning-External": "EXT", "Cleaning-Internal": "INT", "Deep Spa": "SPA",
};

/** EXT, INT or SPA for a service. */
export function serviceCode(service: string): string {
  return CODES[service] ?? service.replace(/[^A-Za-z]/g, "").slice(0, 3).toUpperCase();
}

/** The short form of a zone: "Zone 3" is "Z3". Any other name keeps its first letters. */
export function zoneShort(zone: string): string {
  const m = /^\s*zone\s*(.+)$/i.exec(zone);
  return m ? `Z${m[1].trim()}` : zone.trim().slice(0, 4);
}

/** The zones of the jobs shown, in order: Zone 2 before Zone 10. */
export function zonesOf(jobs: AdminJob[]): string[] {
  const names = new Set(jobs.map((j) => j.zone).filter((z): z is string => Boolean(z)));
  return [...names].sort((a, b) => a.localeCompare(b, undefined, { numeric: true }));
}

/**
 * The label colour of a zone: a shade from white (the first zone) to near black
 * (the last), spread over the zones shown. Every job of a zone has the same
 * shade. Undefined when the job has no zone.
 */
export function zoneStyle(zone: string, zones: string[]): CSSProperties | undefined {
  const i = zones.indexOf(zone);
  if (!zone || i < 0) return undefined;
  const light = zones.length === 1 ? 50 : 97 - (i * 79) / (zones.length - 1);
  return {
    background: `hsl(0 0% ${Math.round(light)}%)`,
    color: light < 55 ? "#ffffff" : "#16151a",
    boxShadow: "inset 0 0 0 1px rgba(22, 21, 26, 0.18)",
  };
}

/** A piece of a card's lines. The same kind is shown the same way at every size. */
export type CardPiece = "zone" | "reg" | "model" | "customer" | "cutoff" | "code" | "slot";
export interface CardPart { kind: CardPiece; text: string }

/**
 * The lines a card shows at each size (owner review, 8-Nov-26). Compact: zone, EXT or INT and the
 * cutoff. Standard: zone, car number and cutoff, then EXT or INT and the service slot. Detailed:
 * zone, make and model and cutoff, then EXT or INT and the slot, then car number and customer.
 * The status flags and notes are added by the card itself.
 */
export function cardLines(job: AdminJob, density: Density): CardPart[][] {
  const zone: CardPart | null = job.zone ? { kind: "zone", text: job.zone } : null;
  const reg: CardPart = { kind: "reg", text: job.registration };
  const cutoff: CardPart | null = job.finish_by ? { kind: "cutoff", text: `Cutoff ${job.finish_by}` } : null;
  const code: CardPart = { kind: "code", text: serviceCode(job.service) };
  const slot: CardPart = { kind: "slot", text: job.start_time ? `${job.start_time}-${job.end_time}` : `${job.duration_minutes} min` };
  const model: CardPart | null = job.vehicle ? { kind: "model", text: job.vehicle } : null;
  const customer: CardPart | null = job.customer_name ? { kind: "customer", text: job.customer_name } : null;
  const lines: (CardPart | null)[][] = density === "compact"
    ? [[zone, code, cutoff]]
    : density === "standard"
      ? [[zone, reg, cutoff], [code, slot]]
      : [[zone, model, cutoff], [code, slot], [reg, customer]];
  return lines.map((line) => line.filter((p): p is CardPart => p !== null)).filter((line) => line.length > 0);
}

/** Whether the admin placed the job by hand against a rule and confirmed it: the Board marks it wine (SCHS-22). */
export function breached(job: AdminJob): boolean {
  return (job.hand_breaches?.length ?? 0) > 0;
}

/** The first job that overlaps a job of `duration` starting at `start`, or null when none does. */
export function clashOf(others: AdminJob[], start: number, duration: number): AdminJob | null {
  return others
    .filter((j) => j.start_minute !== null)
    .sort((a, b) => a.start_minute! - b.start_minute!)
    .find((j) => start < j.start_minute! + j.duration_minutes && j.start_minute! < start + duration) ?? null;
}

/** The polite refusal for a drop that would overlap a job: the job in the way, and a time to try (owner, 8-Nov-26). */
export function clashMessage(job: AdminJob, blocker: AdminJob, crewName: string, suggest: number | null): string {
  const when = blocker.start_time && blocker.end_time ? ` (${blocker.start_time}-${blocker.end_time})` : "";
  const next = suggest === null ? "Please try another time." : `Try ${hhmm(suggest)} instead.`;
  return `${job.registration} cannot go there: ${blocker.registration}${when} is in the way for ${crewName}. ${next}`;
}

/** "EXT,HR26AB2324,B1-24": service code, vehicle number and parking place. */
export function jobLabel(job: AdminJob): string {
  return `${serviceCode(job.service)},${job.registration},${job.parking || "-"}`;
}

export function isSpa(job: AdminJob): boolean {
  return job.service.toLowerCase().includes("spa");
}

/** The kind of work, which sets a card's colour: exterior green, interior blue, spa purple (ADM-SCH-34). */
export const JOB_TYPES = ["EXT", "INT", "SPA"] as const;
export function typeClass(job: AdminJob): string {
  if (isSpa(job)) return "t-spa";
  const code = serviceCode(job.service);
  return code === "EXT" ? "t-ext" : code === "INT" ? "t-int" : "t-other";
}

/** Only a Scheduled job can still be placed or moved; a skipped or finished one cannot. */
export function isOpen(job: AdminJob): boolean {
  return job.status === "Scheduled";
}

/** A job still waiting for a crew member. A skipped job has none but needs no place. */
export function isUnplaced(job: AdminJob): boolean {
  return job.crew_id === null && isOpen(job);
}

/** The job statuses in the order the work moves through them. */
export const JOB_STATUSES = ["Scheduled", "In progress", "Completed", "Skipped", "Could not complete"] as const;

/** The CSS class for a job's status: green when completed, red when it could not be done (ADM-SCH-34). */
/** A visit with some jobs done and some not: listed for follow-up, never hidden. */
export const PARTIAL = "Partially Completed";

export function statusClass(job: AdminJob): string {
  if (job.status === "Completed") return "done";
  if (job.status === "Could not complete") return "failed";
  if (job.status === "In progress") return "active";
  return "";
}

/** Whether a job stays bright for the chosen status and vehicle search. */
export function matches(job: AdminJob, focus: string, search: string, type = "", flag = ""): boolean {
  if (type && (isSpa(job) ? "SPA" : serviceCode(job.service)) !== type) return false;
  if (flag === "late" && !job.late) return false;
  if (flag === "manual" && !job.manual) return false;
  if (focus === PARTIAL) return job.visit_outcome === PARTIAL && matchesSearch(job, search);
  if (focus && job.status !== focus) return false;
  return matchesSearch(job, search);
}

/**
 * The search finds a job by vehicle number, parking place, customer, crew member, vehicle model or
 * service. Several words must all be found, in any of those (ADM-SCH-33).
 */
function matchesSearch(job: AdminJob, search: string): boolean {
  const words = search.trim().toLowerCase().split(/\s+/).filter(Boolean);
  if (words.length === 0) return true;
  const hay = [job.zone, job.zone ? zoneShort(job.zone) : "", job.registration, job.registration.replace(/\s/g, ""), job.parking, job.customer_name, job.crew_name, job.vehicle, job.service]
    .filter(Boolean).join(" ").toLowerCase();
  return words.every((w) => hay.includes(w));
}

/**
 * How many of the day's jobs are in each status. Pressing a status keeps only
 * its jobs bright on the board; pressing it again shows all (ADM-SCH-34).
 */
export function StatusSummary({ jobs, focus, onFocus }: {
  jobs: AdminJob[];
  focus: string;
  onFocus: (status: string) => void;
}) {
  const counts = new Map<string, number>();
  for (const j of jobs) counts.set(j.status, (counts.get(j.status) ?? 0) + 1);
  const shown = [...JOB_STATUSES.filter((s) => counts.has(s)),
    ...[...counts.keys()].filter((s) => !(JOB_STATUSES as readonly string[]).includes(s))];
  const partial = jobs.filter((j) => j.visit_outcome === PARTIAL).length;
  const chip = (status: string, label: string, n: number) => (
    <button key={status || "all"} type="button" aria-pressed={focus === status}
            onClick={() => onFocus(focus === status ? "" : status)}
            className={`sch-chip${status ? ` st-${status.toLowerCase().replace(/ /g, "-")}` : ""}`}>
      {label} <b>{n}</b>
    </button>
  );
  return (
    <div className="flex flex-wrap items-center gap-2" role="group" aria-label="Job status">
      {chip("", "All jobs", jobs.length)}
      {shown.map((s) => chip(s, s, counts.get(s) ?? 0))}
      {partial > 0 && chip(PARTIAL, PARTIAL, partial)}
    </div>
  );
}

/** The three kinds of work as chips; pressing one keeps only that kind bright, pressing it again shows all. */
export function TypeKey({ type, onType }: { type: string; onType: (type: string) => void }) {
  return (
    <div className="flex items-center gap-1.5" role="group" aria-label="Kind of work">
      {JOB_TYPES.map((t) => (
        <button key={t} type="button" aria-pressed={type === t} onClick={() => onType(type === t ? "" : t)}
                className={`sch-chip type t-${t.toLowerCase()}`}>
          <i aria-hidden /> {t}
        </button>
      ))}
    </div>
  );
}

export function JobLabel({ job }: { job: AdminJob }) {
  return (
    <span className="flex min-w-0 flex-col">
      <strong className="truncate reg text-[0.8125rem]">{job.registration}</strong>
      <span className="truncate text-xs text-muted-foreground">{job.service}{job.parking ? ` · ${job.parking}` : ""}</span>
    </span>
  );
}

export function JobFlags({ job }: { job: AdminJob }) {
  return (
    <>
      {job.visit_outcome === PARTIAL && <StatusBadge status={PARTIAL} tone="warn" />}
      {job.late && <StatusBadge status="Late" tone="error" />}
      {job.manual && <StatusBadge status="Changed by hand" tone="info" />}
    </>
  );
}

export interface Win { start: number; end: number }

/** The windows a member can take work in on the day shown. */
export function windowsOf(member: SchedulingCrew, avail: CrewDayAvailability | undefined): Win[] {
  return avail ? avail.windows : [{ start: member.start_minute, end: member.end_minute }];
}

/** The stretches of [first, last) that lie outside every window. */
export function gaps(wins: Win[], first: number, last: number): Win[] {
  const out: Win[] = [];
  let at = first;
  for (const w of [...wins].sort((a, b) => a.start - b.start)) {
    if (w.start > at) out.push({ start: at, end: Math.min(w.start, last) });
    at = Math.max(at, w.end);
  }
  if (at < last) out.push({ start: at, end: last });
  return out;
}

/** Minutes a member can work on the day. */
export function minutesOf(wins: Win[]): number {
  return wins.reduce((n, w) => n + (w.end - w.start), 0);
}

/** "3 h 20 min", "45 min" or "6 h". */
export function hm(minutes: number): string {
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  if (!h) return `${m} min`;
  return m ? `${h} h ${m} min` : `${h} h`;
}

const spans = (jobs: AdminJob[]) => jobs.filter((j) => j.start_minute !== null)
  .map((j) => ({ start: j.start_minute!, end: j.start_minute! + j.duration_minutes }))
  .sort((a, b) => a.start - b.start);

/** Whether a job of `duration` can start at `start`: inside a slot and over no other job. */
export function fitsAt(wins: Win[], others: AdminJob[], start: number, duration: number): boolean {
  return wins.some((w) => start >= w.start && start + duration <= w.end)
    && spans(others).every((b) => start + duration <= b.start || start >= b.end);
}

/** The free stretches of a member's slots: the time no job takes (ADM-SCH-33). */
export function freeSlots(wins: Win[], jobs: AdminJob[]): Win[] {
  const busy = spans(jobs);
  const out: Win[] = [];
  for (const w of [...wins].sort((a, b) => a.start - b.start)) {
    let at = w.start;
    for (const b of busy) {
      if (b.end <= at || b.start >= w.end) continue;
      if (b.start > at) out.push({ start: at, end: b.start });
      at = Math.max(at, b.end);
    }
    if (at < w.end) out.push({ start: at, end: w.end });
  }
  return out.filter((g) => g.end - g.start >= SNAP);
}

/**
 * The start time for a job dropped into a crew member's column at `index`
 * (0 is the top). It is the earliest free time after the job above it, inside
 * a slot the member works, that overlaps no other job. When nothing is free
 * after that job, the earliest free time of the day is used. Null when the job
 * fits nowhere (ADM-SCH-33).
 */
export function freeStart(wins: Win[], others: AdminJob[], index: number, duration: number, step = SNAP): number | null {
  const busy = spans(others);
  const fits = (s: number) => fitsAt(wins, others, s, duration);
  const tries = [...wins.map((w) => w.start), ...busy.map((b) => b.end)]
    .map((m) => Math.ceil(m / step) * step).sort((a, b) => a - b);
  const after = index > 0 && busy[index - 1] ? busy[index - 1].end : -Infinity;
  return tries.find((s) => s >= after && fits(s)) ?? tries.find(fits) ?? null;
}

/** Why the jobs of a crew member are where they are: hours, load and the scheduler notes. */
export function Reasoning({ member, avail, jobs }: {
  member: SchedulingCrew; avail: CrewDayAvailability | undefined; jobs: AdminJob[];
}) {
  const wins = windowsOf(member, avail);
  const available = minutesOf(wins);
  const booked = jobs.reduce((n, j) => n + j.duration_minutes, 0);
  const byService = new Map<string, number>();
  for (const j of jobs) byService.set(j.service, (byService.get(j.service) ?? 0) + 1);
  const notes = jobs.filter((j) => j.reason).slice(0, 5);
  return (
    <>
      <strong>{member.name}, {member.role}</strong>
      <span className="cap-tip-row"><span>{avail?.reason ?? "Works the hours shown."}</span></span>
      {wins.length > 0 && (
        <span className="cap-tip-row"><span>Slots</span>
          <b>{wins.map((w) => `${hhmm(w.start)}-${hhmm(w.end)}`).join(", ")}</b></span>
      )}
      <span className="cap-tip-row"><span>Booked</span>
        <b>{booked} of {available} min, {jobs.length} {jobs.length === 1 ? "job" : "jobs"}</b></span>
      {[...byService].map(([service, n]) => (
        <span key={service} className="cap-tip-row"><span>{service}</span><b>{n}</b></span>
      ))}
      <small className="cap-tip-why">
        {jobs.length === 0
          ? (avail?.status === "Off" ? "Cannot take work this day." : "No job was given to this member.")
          : "Jobs were placed inside these slots, in time order, within each finish-by time."}
      </small>
      {notes.map((j) => (
        <small key={j.id} className="cap-tip-why">{j.start_time} {j.registration}: {j.reason}</small>
      ))}
    </>
  );
}
