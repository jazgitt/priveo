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

export interface DayCapacity {
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

/** The board for a society and start date, or null when no run has been made (404). */
export function useBoard(societyId: string, startDate: string) {
  return useQuery({
    queryKey: ["board", societyId, startDate],
    enabled: Boolean(societyId && startDate),
    queryFn: async (): Promise<Board | null> => {
      try {
        const q = new URLSearchParams({ society_id: societyId, start_date: startDate });
        return await api<Board>(`/v1/admin/scheduling/board?${q}`);
      } catch (e) {
        if (e instanceof ApiError && e.status === 404) return null;
        throw e;
      }
    },
  });
}

export function useNeedsScheduling(societyId: string) {
  return useQuery({
    queryKey: ["needs-scheduling", societyId],
    queryFn: async () => {
      const q = societyId ? `?society_id=${encodeURIComponent(societyId)}` : "";
      return (await api<{ jobs: AdminJob[] }>(`/v1/admin/scheduling/needs-scheduling${q}`)).jobs;
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
