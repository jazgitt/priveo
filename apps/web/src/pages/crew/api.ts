import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "../../api/client";

export const WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"] as const;
export const ROLES = ["Manager", "Member", "Trainee"] as const;
export const EXCEPTION_KINDS = ["Sick", "Leave", "Late start"] as const;

export interface Slot { start: string; end: string }
/** One weekday. `start` and `end` are the first slot; `extra_slots` are more the same day. */
export interface DayHours {
  day: string; working: boolean; start: string; end: string; extra_slots?: Slot[];
}
export interface CrewException { id: string; date: string; kind: string; start: string }

/** CrewOut. No customer data is part of a crew record. */
export interface Crew {
  id: string;
  name: string;
  mobile: string;
  society_id: string;
  society: string;
  role: string;
  active: boolean;
  locked: boolean;
  working_hours: DayHours[];
  paired_member_id: string | null;
  paired_member: string;
  exceptions: CrewException[];
}

export interface ReleasedJob {
  job_id: string; date: string; service: string; vehicle_id: string; registration: string;
}
export interface CrewChange { crew: Crew; released_jobs: ReleasedJob[] }
export interface CrewExceptionResult {
  crew: Crew; exceptions: CrewException[]; released_jobs: ReleasedJob[];
}
export interface CrewPassword { crew: Crew; login_id: string; password: string }
export interface CrewSession { id: string; channel: string; signed_in_at: string; last_active_at: string;
  device_name?: string; platform?: string; app_version?: string }
export interface Society { id: string; name: string; active: boolean }

/** One stay of a crew member in a society (ADM-CRW-22). */
export interface SocietyStay {
  id: string;
  society_id: string;
  society: string;
  effective_from: string;
  effective_to: string | null;
  pending: boolean;
}

export interface NewCrewBody {
  name: string;
  mobile: string;
  society_id: string;
  role: string;
  working_hours: DayHours[];
  paired_member_id: string | null;
}

/** Every day working 06:00 to 12:00 until the admin edits it. */
export function defaultHours(): DayHours[] {
  return WEEKDAYS.map((day) => ({ day, working: true, start: "06:00", end: "12:00" }));
}

/** The API wants an empty start and end on a day off. */
export function hoursBody(hours: DayHours[]): DayHours[] {
  return hours.map((h) => (h.working
    ? { ...h, extra_slots: h.extra_slots ?? [] }
    : { day: h.day, working: false, start: "", end: "", extra_slots: [] }));
}

const base = "/v1/admin/crew";

export function useSocieties() {
  return useQuery({
    queryKey: ["directory-societies"],
    queryFn: () => api<Society[]>("/v1/admin/directory/societies"),
  });
}

/** The hours a new crew member starts with in a society: its working slots (ADM-CRW-25). */
export function useDefaultHours(societyId: string) {
  return useQuery({
    queryKey: ["crew", "default-hours", societyId],
    queryFn: () => api<DayHours[]>(`${base}/default-hours?society_id=${encodeURIComponent(societyId)}`),
    enabled: societyId !== "",
  });
}

export function useCrewList(societyId: string) {
  return useQuery({
    queryKey: ["crew", "list", societyId],
    queryFn: () => api<Crew[]>(`${base}${societyId ? `?society_id=${encodeURIComponent(societyId)}` : ""}`),
  });
}

export function useCrew(id: string) {
  return useQuery({ queryKey: ["crew", id], queryFn: () => api<Crew>(`${base}/${id}`) });
}

export function useSocietyHistory(id: string) {
  return useQuery({
    queryKey: ["crew", id, "society-history"],
    queryFn: () => api<SocietyStay[]>(`${base}/${id}/society-history`),
  });
}

export function useSessions(id: string) {
  return useQuery({
    queryKey: ["crew", id, "sessions"],
    queryFn: () => api<CrewSession[]>(`${base}/${id}/sessions`),
  });
}

function useCrewMutation<V, R>(fn: (v: V) => Promise<R>) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: fn,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["crew"] }),
  });
}

export function useCrewActions(id: string) {
  const call = <R,>(path: string, method: string, body?: unknown) =>
    api<R>(`${base}/${id}${path}`, { method, body });
  return {
    edit: useCrewMutation((v: { name?: string; mobile?: string }) => call<Crew>("", "PATCH", v)),
    role: useCrewMutation((v: { role: string; paired_member_id: string | null }) =>
      call<CrewChange>("/role", "PUT", v)),
    pair: useCrewMutation((v: { paired_member_id: string }) => call<Crew>("/pair", "PUT", v)),
    moveSociety: useCrewMutation((v: { society_id: string; effective_from: string; paired_member_id: string | null }) =>
      call<CrewChange>("/society", "POST", v)),
    cancelMove: useCrewMutation((assignmentId: string) =>
      call<Crew>(`/society-moves/${assignmentId}`, "DELETE")),
    hours: useCrewMutation((v: DayHours[]) =>
      call<CrewChange>("/working-hours", "PUT", { working_hours: hoursBody(v) })),
    addException: useCrewMutation((v: { kind: string; from_date: string; to_date: string | null; start: string }) =>
      call<CrewExceptionResult>("/exceptions", "POST", v)),
    editException: useCrewMutation((v: { exId: string; kind: string; start: string }) =>
      call<CrewExceptionResult>(`/exceptions/${v.exId}`, "PATCH", { kind: v.kind, start: v.start })),
    removeException: useCrewMutation((exId: string) =>
      call<CrewExceptionResult>(`/exceptions/${exId}`, "DELETE")),
    deactivate: useCrewMutation((v: { release_jobs: boolean }) =>
      call<CrewChange>("/deactivate", "POST", v)),
    reactivate: useCrewMutation(() => call<Crew>("/reactivate", "POST")),
    endSession: useCrewMutation((sid: string) =>
      call<{ ended: number }>(`/sessions/${sid}/logout`, "POST")),
    endAll: useCrewMutation(() => call<{ ended: number }>("/sessions/logout", "POST")),
    resetPassword: useCrewMutation(() => call<CrewPassword>("/password", "POST")),
    unlock: useCrewMutation(() => call<Crew>("/unlock", "POST")),
  };
}

export function useCreateCrew() {
  return useCrewMutation((v: NewCrewBody) => api<CrewPassword>(base, { method: "POST", body: v }));
}
