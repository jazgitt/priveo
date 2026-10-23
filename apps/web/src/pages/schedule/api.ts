// Types and calls for the scheduler (services/api/app/scheduling/schemas.py).
import { useQuery } from "@tanstack/react-query";

import { api, ApiError } from "../../api/client";

export interface ScheduleOut {
  id: string;
  society_id: string;
  society_name: string;
  start_date: string;
  end_date: string;
  status: string;
  frozen_at: string | null;
  freeze_deadline: string;
}

export interface CrewCapacityLine { name: string; role: string; minutes: number; slots: string }
export interface DemandLine { service: string; source: string; jobs: number; minutes: number }

/** Whether a crew member can take work on a day, and why (ADM-SCH-32). */
export interface CrewDayAvailability {
  crew_id: string;
  status: "Working" | "Partial" | "Off";
  windows: { start: number; end: number }[];
  reason: string;
}

export interface DayCapacity {
  availability?: CrewDayAvailability[];
  crew?: CrewCapacityLine[];
  demand?: DemandLine[];
  date: string;
  capacity_minutes: number;
  demand_minutes: number;
  scheduled_minutes: number;
  over_capacity: boolean;
}

export interface SchedulingCrew {
  id: string;
  name: string;
  role: string;
  start_minute: number;
  end_minute: number;
}

export interface AdminJob {
  id: string;
  visit_id: string;
  schedule_id: string;
  schedule_status: string;
  date: string;
  vehicle_id: string;
  registration: string;
  vehicle: string;
  /** For example "B1-24": basement and parking number. */
  parking?: string;
  customer_name: string;
  service: string;
  status: string;
  duration_minutes: number;
  crew_id: string | null;
  crew_name: string | null;
  start_minute: number | null;
  start_time: string | null;
  end_time: string | null;
  finish_by: string | null;
  late: boolean;
  manual: boolean;
  reason: string;
  /** A skipped job only: "Skipped" or "Paused", and by whom (ADM-SCH-36). */
  skip_kind?: string;
  skip_reason?: string;
  /** Derived outcome of the whole visit: Scheduled, Completed, Partially Completed, Not Completed, Rescheduled or Cancelled. */
  visit_outcome?: string;
  planned_services?: string[];
  delivered_services?: string[];
  /** Place in the crew member's day, and whether the admin unlocked it (S-13, C-04). */
  sequence?: number | null;
  queue_unlocked?: boolean;
}

export interface Board {
  schedule: ScheduleOut;
  days: DayCapacity[];
  crew: SchedulingCrew[];
  jobs: AdminJob[];
}

export interface RunResult {
  schedule_id: string;
  society_id: string;
  status: string;
  placed: number;
  unscheduled: number;
  late: number;
}

export interface Society {
  id: string;
  name: string;
}

export interface CrewRow {
  id: string;
  name: string;
  role: string;
  active: boolean;
  society_id: string;
  society: string;
}

export function useCrewList() {
  return useQuery({
    queryKey: ["admin-crew"],
    queryFn: () => api<CrewRow[]>("/v1/admin/crew"),
  });
}

/**
 * The societies the portal knows. There is no societies endpoint yet, so they
 * come from the crew list, which carries each crew member's society. A society
 * with no crew is not listed (needs endpoint: GET /v1/admin/societies).
 */
export function societiesOf(rows: CrewRow[] | undefined): Society[] {
  const seen = new Map<string, string>();
  for (const r of rows ?? []) seen.set(r.society_id, r.society);
  return [...seen].map(([id, name]) => ({ id, name }))
    .sort((a, b) => a.name.localeCompare(b.name));
}

/** The society's schedules ending on or after `from`, oldest first (ADM-SCH-35). */
export function useSchedules(societyId: string, from: string) {
  return useQuery({
    queryKey: ["schedules", societyId, from],
    enabled: Boolean(societyId),
    queryFn: () => {
      const q = new URLSearchParams({ society_id: societyId, date_from: from });
      return api<ScheduleOut[]>(`/v1/admin/scheduling/schedules?${q}`);
    },
  });
}

/** The board of one schedule; idle until there is a schedule (ADM-SCH-35). */
export function useScheduleBoard(scheduleId: string | undefined) {
  return useQuery({
    queryKey: ["board", "id", scheduleId],
    enabled: Boolean(scheduleId),
    queryFn: () => api<Board>(`/v1/admin/scheduling/board?${new URLSearchParams({ schedule_id: scheduleId! })}`),
  });
}

/** A cutoff change a customer made after the freeze (ADM-SCH-22). */
export interface CutoffRequest {
  id: string; registration: string; customer_name: string; date: string; cutoff_time: string;
  old_cutoff: string | null; crew_name: string | null; start_time: string | null;
}

export function useCutoffRequests() {
  return useQuery({
    queryKey: ["cutoff-requests"],
    queryFn: () => api<CutoffRequest[]>("/v1/admin/scheduling/cutoff-requests"),
  });
}

/** The dates from `start` to `end`, both included. */
export function datesOf(start: string, end: string): string[] {
  const out: string[] = [];
  const d = new Date(`${start.slice(0, 10)}T00:00:00Z`);
  const last = end.slice(0, 10);
  while (d.toISOString().slice(0, 10) <= last && out.length < 400) {
    out.push(d.toISOString().slice(0, 10));
    d.setUTCDate(d.getUTCDate() + 1);
  }
  return out;
}

/** An add-on waiting for a scheduling period to be run. */
export interface PendingAddon { id: string; registration: string; date: string; finish_by: string }

export function useNeedsScheduling(societyId: string) {
  return useQuery({
    queryKey: ["needs-scheduling", societyId],
    queryFn: async () => {
      const q = societyId ? `?society_id=${encodeURIComponent(societyId)}` : "";
      const r = await api<{ jobs?: AdminJob[]; pending_addons?: PendingAddon[] }>(`/v1/admin/scheduling/needs-scheduling${q}`);
      return { jobs: r.jobs ?? [], pending_addons: r.pending_addons ?? [] };
    },
  });
}

export function useCapacity(societyId: string, startDate: string, days: number) {
  return useQuery({
    queryKey: ["capacity", societyId, startDate, days],
    enabled: Boolean(societyId && startDate),
    queryFn: () => {
      const q = new URLSearchParams({
        society_id: societyId, start_date: startDate, days: String(days),
      });
      return api<DayCapacity[]>(`/v1/admin/scheduling/capacity?${q}`);
    },
  });
}

// ---- helpers ---------------------------------------------------------------

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const WEEKDAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

function parts(iso: string): [number, number, number] {
  const [y, m, d] = iso.slice(0, 10).split("-").map(Number);
  return [y, m, d];
}

/** "2026-11-07" -> "07-Nov-26" (dates in the portal are dd-Mon-yy). */
export function fmtDate(iso: string): string {
  const [y, m, d] = parts(iso);
  return `${String(d).padStart(2, "0")}-${MONTHS[m - 1]}-${String(y % 100).padStart(2, "0")}`;
}

export function weekday(iso: string): string {
  const [y, m, d] = parts(iso);
  return WEEKDAYS[new Date(Date.UTC(y, m - 1, d)).getUTCDay()];
}

export function toIso(d: Date): string {
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  return `${d.getFullYear()}-${mm}-${String(d.getDate()).padStart(2, "0")}`;
}

/** The next Sunday on or after today: the week starts on Sunday (ADM-SCH-09). */
export function nextSunday(from: Date = new Date()): string {
  const d = new Date(from.getFullYear(), from.getMonth(), from.getDate());
  d.setDate(d.getDate() + ((7 - d.getDay()) % 7));
  return toIso(d);
}

/** Days from this date to the end of its month (a Monthly run). */
export function daysInMonthFrom(iso: string): number {
  const [y, m, d] = parts(iso);
  return new Date(y, m, 0).getDate() - d + 1;
}

/** Minutes after midnight -> "HH:MM". */
export function hhmm(minute: number): string {
  return `${String(Math.floor(minute / 60)).padStart(2, "0")}:${String(minute % 60).padStart(2, "0")}`;
}

/** "HH:MM" -> minutes after midnight, or null when it is not a time. */
export function minuteOf(text: string): number | null {
  const m = /^(\d{1,2}):(\d{2})$/.exec(text.trim());
  if (!m) return null;
  return Number(m[1]) < 24 && Number(m[2]) < 60 ? Number(m[1]) * 60 + Number(m[2]) : null;
}

export function fmtHours(minutes: number): string {
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return m === 0 ? `${h} h` : `${h} h ${m} min`;
}

export function errorText(e: unknown): string {
  return e instanceof ApiError ? e.message : "Something went wrong. Please try again.";
}
