import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "../../api/client";
import type {
  AdminPayment, MergedAlert, NeedsJob, PaymentAlert, SupportAlertList,
} from "./types";

export const KEYS = {
  alerts: ["admin", "alerts"] as const,
  payAlerts: ["admin", "payment-alerts"] as const,
  complaints: ["admin", "complaints"] as const,
  payments: ["admin", "payments"] as const,
  needs: ["admin", "needs-scheduling"] as const,
};

/** Poll every minute so the bell and the dashboard stay current. */
const POLL_MS = 60_000;

export function useSupportAlerts() {
  return useQuery({
    queryKey: KEYS.alerts,
    queryFn: () => api<SupportAlertList>("/v1/admin/alerts"),
    refetchInterval: POLL_MS,
  });
}

export function usePaymentAlerts() {
  return useQuery({
    queryKey: KEYS.payAlerts,
    queryFn: () => api<PaymentAlert[]>("/v1/admin/payment-alerts"),
    refetchInterval: POLL_MS,
  });
}

/** Both alert sources as one list, newest first, with the unread count. */
export function useMergedAlerts() {
  const support = useSupportAlerts();
  const money = usePaymentAlerts();
  const items: MergedAlert[] = [
    ...(support.data?.items ?? []).map((a): MergedAlert => ({
      key: `support:${a.id}`, source: "support", id: a.id, kind: a.kind, title: a.title,
      body: a.body, created_at: a.created_at, read: a.read,
      link: a.ref_type === "complaint" && a.ref_id ? `/complaints/${a.ref_id}` : null,
    })),
    ...(money.data ?? []).map((a): MergedAlert => ({
      key: `payment:${a.id}`, source: "payment", id: a.id, kind: a.kind, title: a.kind,
      body: a.message, created_at: a.created_at, read: a.read, link: "/payments",
    })),
  ].sort((a, b) => b.created_at.localeCompare(a.created_at));
  return {
    items,
    unread: items.filter((a) => !a.read).length,
    loading: support.isLoading || money.isLoading,
    error: support.isError || money.isError,
  };
}

export function useMarkAlertRead() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (a: Pick<MergedAlert, "source" | "id">) =>
      api<void>(a.source === "support"
        ? `/v1/admin/alerts/${a.id}/read`
        : `/v1/admin/payment-alerts/${a.id}/read`, { method: "POST" }),
    onSettled: () => {
      void qc.invalidateQueries({ queryKey: KEYS.alerts });
      void qc.invalidateQueries({ queryKey: KEYS.payAlerts });
    },
  });
}

/** Payment alerts have no read-all endpoint, so each unread one is marked. */
export function useMarkAllRead() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (unreadPaymentIds: string[]) => {
      await api<void>("/v1/admin/alerts/read-all", { method: "POST" });
      await Promise.all(unreadPaymentIds.map((id) =>
        api<void>(`/v1/admin/payment-alerts/${id}/read`, { method: "POST" })));
    },
    onSettled: () => {
      void qc.invalidateQueries({ queryKey: KEYS.alerts });
      void qc.invalidateQueries({ queryKey: KEYS.payAlerts });
    },
  });
}

export function useNeedsScheduling() {
  return useQuery({
    queryKey: KEYS.needs,
    queryFn: () => api<{ jobs: NeedsJob[] }>("/v1/admin/scheduling/needs-scheduling"),
  });
}

export function usePayments(status: string) {
  return useQuery({
    queryKey: [...KEYS.payments, status],
    queryFn: () => api<AdminPayment[]>(`/v1/admin/payments?status=${encodeURIComponent(status)}`),
  });
}
