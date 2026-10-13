import { api } from "../../api/client";

export interface Society { id: string; name: string; active: boolean; parking_basements: string[] }
export interface Catalogue { id: string; make: string; model: string; variant: string; category: string; active: boolean }
export interface Plan { id: string; name: string; monthly_price_rupees: number; list_price_rupees: number | null; includes_interior: boolean; inclusions: string[]; badge: string; active: boolean }
export interface VehicleInput {
  society_id: string; catalogue_id: string; registration: string; parking_basement: string;
  parking_number: string; plan_id: string; cutoff_time: string; interior_day: string | null;
  photo_upload_id: string; rc_upload_id: string | null; first_payment_status: string;
}
export interface Vehicle {
  id: string; society: string; registration: string; make: string; model: string; variant: string;
  category: string; parking_basement: string; parking_number: string; photo_url: string | null;
  rc_url: string | null; rc_verified: boolean;
  subscription: { id: string; status: string; plan_id: string; plan_name: string; price_rupees: number;
    cutoff_time: string; interior_day: string | null; first_service_date: string;
    pending_plan_id: string | null; pending_from: string | null } | null;
  payments: { id: string; status: string; amount_rupees: number; due_date: string }[];
}
export interface Customer { id: string; first_name: string; last_name: string; email: string; mobile: string;
  imported_history?: { id: string; date: string | null; service: string; vehicle: string;
    payment_status: string | null; notes: string }[];
  flat: string; email_verified: boolean; password_set: boolean; onboarding_confirmed: boolean;
  vehicles: Vehicle[]; welcome_sent?: boolean; existing?: boolean }
export const newVehicle = (): VehicleInput => ({ society_id: "", catalogue_id: "", registration: "",
  parking_basement: "", parking_number: "", plan_id: "", cutoff_time: "09:00", interior_day: null,
  photo_upload_id: "", rc_upload_id: null, first_payment_status: "Due" });
export const weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];
export const times = Array.from({ length: 48 }, (_, i) => `${String(Math.floor(i / 2)).padStart(2, "0")}:${i % 2 ? "30" : "00"}`);

export async function uploadCustomerAsset(file: File, purpose: "vehicle" | "rc") {
  const t = await api<{ id: string; upload_url: string; method: string; headers: Record<string, string> }>(
    "/v1/admin/customer-uploads", { method: "POST", body: { purpose, content_type: file.type, size_bytes: file.size } });
  const sent = await fetch(t.upload_url, { method: t.method, headers: t.headers, body: file });
  if (!sent.ok) throw new Error("The file could not be uploaded. Please try again.");
  return api<{ id: string; url: string }>(`/v1/admin/customer-uploads/${t.id}/confirm`, { method: "POST" });
}
