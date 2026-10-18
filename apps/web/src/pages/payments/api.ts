import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "../../api/client";
import type { AdminPayment, Invoice, PaymentAlert, PaymentFilters } from "./types";

export interface NewPayment {
  vehicle_id: string;
  kind: string;
  description: string;
  amount_rupees: number;
  due_date: string;
  cycle_start: string | null;
  status: string;
}

export function paymentsPath(f: PaymentFilters, page = 0, society = ""): string {
  const q = new URLSearchParams();
  for (const [k, v] of Object.entries(f)) if (v) q.set(k, v);
  q.set("limit", "50");
  q.set("offset", String(page * 50));
  if (society) q.set("society", society);
  return `/v1/admin/payments?${q.toString()}`;
}

export function usePayments(f: PaymentFilters, page = 0, society = "") {
  return useQuery({
    queryKey: ["admin-payments", f, page, society],
    queryFn: () => api<AdminPayment[]>(paymentsPath(f, page, society)),
  });
}

/** The numbers above the payments list: payments and rupees in each status. */
export interface PaymentsSummary {
  total: number;
  total_rupees: number;
  by_status: Record<string, { count: number; rupees: number }>;
}

export function usePaymentsSummary(society = "") {
  return useQuery({
    queryKey: ["admin-payments", "summary", society],
    queryFn: () => api<PaymentsSummary>(`/v1/admin/payments/summary${society ? `?society=${encodeURIComponent(society)}` : ""}`),
  });
}

export function useAlerts() {
  return useQuery({
    queryKey: ["payment-alerts"],
    queryFn: () => api<PaymentAlert[]>("/v1/admin/payment-alerts?unread_only=true"),
  });
}

function useRefresh() {
  const qc = useQueryClient();
  return () => qc.invalidateQueries({ queryKey: ["admin-payments"] });
}

export function useSetStatus() {
  const refresh = useRefresh();
  return useMutation({
    mutationFn: (v: { id: string; status: string }) =>
      api<AdminPayment>(`/v1/admin/payments/${v.id}/status`, { method: "PUT", body: { status: v.status } }),
    onSuccess: refresh,
  });
}

export function useAction(action: "confirm" | "reject") {
  const refresh = useRefresh();
  return useMutation({
    mutationFn: (id: string) => api<AdminPayment>(`/v1/admin/payments/${id}/${action}`, { method: "POST" }),
    onSuccess: refresh,
  });
}

export function useInvoice() {
  const refresh = useRefresh();
  return useMutation({
    mutationFn: (id: string) => api<Invoice>(`/v1/admin/payments/${id}/invoice`, { method: "POST" }),
    onSuccess: refresh,
  });
}

export function useCreatePayment() {
  const refresh = useRefresh();
  return useMutation({
    mutationFn: (body: NewPayment) =>
      api<AdminPayment>("/v1/admin/payments", { method: "POST", body }),
    onSuccess: refresh,
  });
}

export function useReadAlert() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api<void>(`/v1/admin/payment-alerts/${id}/read`, { method: "POST" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["payment-alerts"] }),
  });
}
