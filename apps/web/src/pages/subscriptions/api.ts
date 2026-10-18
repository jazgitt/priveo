import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "../../api/client";

export const SUB_STATUSES = ["Inactive", "Activating", "Active"] as const;

/** Expected row of GET /v1/admin/subscriptions. */
export interface SubscriptionRow {
  subscription_id: string;
  vehicle_id: string;
  customer_name: string;
  flat: string;
  society: string;
  vehicle: string;
  plan_name: string | null;
  status: string; // Active | Activating | Paused | Inactive
  first_service_date: string | null;
  renewal_date: string | null;
  /** The latest plan payment's status, and whether it is waiting (Due or Over due). */
  payment_status?: string | null;
  payment_due?: boolean;
}

/** Expected row of GET /v1/admin/subscriptions/{id}/events (ADM-SUB-05). */
export interface SubscriptionEvent {
  from_status: string;
  to_status: string;
  by: string;
  reason: string;
  at: string;
}

export interface Change {
  id: string;
  kind: string;
  status: string;
  start_date: string;
  end_date: string;
  days: number;
  actor: string;
}

export interface Changes {
  vehicle_id: string;
  skips: Change[];
  pauses: Change[];
  renewal_date: string | null;
}

export function useSubscriptions(status: string, societyId = "") {
  return useQuery({
    queryKey: ["admin-subscriptions", status, societyId],
    queryFn: () => api<SubscriptionRow[]>(
      `/v1/admin/subscriptions?${new URLSearchParams({ limit: "500", ...(status && { status }), ...(societyId && { society_id: societyId }) })}`),
    retry: false,
  });
}

export function useSubscriptionEvents(id: string) {
  return useQuery({
    queryKey: ["subscription-events", id],
    queryFn: () => api<SubscriptionEvent[]>(`/v1/admin/subscriptions/${id}/events`),
    retry: false,
  });
}

export function useSetSubscriptionStatus() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (v: { id: string; status: string; reason: string; first_service_date: string | null }) =>
      api<{ subscription_id: string; status: string }>(
        `/v1/admin/subscriptions/${v.id}/status`,
        { method: "PUT", body: { status: v.status, reason: v.reason,
                                 first_service_date: v.first_service_date } }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin-subscriptions"] });
      qc.invalidateQueries({ queryKey: ["subscription-events"] });
    },
  });
}

export function useChanges(vehicleId: string) {
  return useQuery({
    queryKey: ["vehicle-changes", vehicleId],
    queryFn: () => api<Changes>(`/v1/admin/vehicles/${vehicleId}/changes`),
    enabled: vehicleId !== "",
    retry: false,
  });
}

export function useChangeActions(vehicleId: string) {
  const qc = useQueryClient();
  const done = () => qc.invalidateQueries({ queryKey: ["vehicle-changes", vehicleId] });
  const base = `/v1/admin/vehicles/${vehicleId}`;
  return {
    skip: useMutation({
      mutationFn: (date: string) => api(`${base}/skips`, { method: "POST", body: { date } }),
      onSuccess: done,
    }),
    unskip: useMutation({
      mutationFn: (id: string) => api(`${base}/skips/${id}`, { method: "DELETE" }),
      onSuccess: done,
    }),
    pause: useMutation({
      mutationFn: (v: { from_date: string; to_date: string }) =>
        api(`${base}/pauses`, { method: "POST", body: v }),
      onSuccess: done,
    }),
    endPause: useMutation({
      mutationFn: (id: string) => api(`${base}/pauses/${id}`, { method: "DELETE" }),
      onSuccess: done,
    }),
  };
}

/** ADM-SUB-01, -02, -04: the moves the API accepts. */
export function allowedMoves(current: string | null): string[] {
  if (current === null) return [...SUB_STATUSES];
  const out: string[] = [];
  if (current !== "Inactive") out.push("Inactive");
  if (current === "Inactive") out.push("Activating");
  if (current === "Activating") out.push("Active");
  return out;
}
