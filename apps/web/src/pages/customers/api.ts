import { useEffect, useState } from "react";

import { api } from "../../api/client";

export interface Society { id: string; name: string; active: boolean; parking_basements: string[] }
export interface Catalogue { id: string; make: string; model: string; variant: string; category: string; active: boolean }
export interface Plan { id: string; name: string; monthly_price_rupees: number; list_price_rupees: number | null; includes_interior: boolean; inclusions: string[]; badge: string; active: boolean }
export interface VehicleInput {
  society_id: string; catalogue_id: string; registration: string; parking_basement: string;
  parking_number: string; plan_id: string; cutoff_time: string; interior_day: string | null;
  photo_upload_id: string; rc_upload_id: string | null; first_payment_status: string;
}
export interface Subscription {
  id: string; status: string; plan_id: string; plan_name: string; price_rupees: number;
  cutoff_time: string; interior_day: string | null; first_service_date: string | null;
  pending_plan_id: string | null; pending_from: string | null;
}
export interface Vehicle {
  id: string; society_id?: string; society: string; registration: string; make: string; model: string;
  variant: string; category: string; parking_basement: string; parking_number: string;
  photo_url: string | null; rc_url: string | null; rc_verified: boolean;
  subscription: Subscription | null;
  payments: { id: string; status: string; amount_rupees: number; due_date: string }[];
}
export interface Customer { id: string; first_name: string; last_name: string; email: string; mobile: string;
  imported_history?: { id: string; date: string | null; service: string; vehicle: string;
    payment_status: string | null; notes: string }[];
  flat: string; email_verified: boolean; password_set: boolean; onboarding_confirmed: boolean;
  vehicles: Vehicle[]; welcome_sent?: boolean; existing?: boolean }
/** One row of the customer list. */
export interface CustomerRow {
  id: string; name: string; email: string; mobile: string; flat?: string;
  email_verified?: boolean; password_set?: boolean; onboarding_confirmed?: boolean;
  vehicles?: { id: string; registration: string; status: string | null }[];
}
export interface Session { id: string; device_name: string; platform: string; app_version: string; last_active: string; channel: string }
export interface Changes { skips: { id: string; start_date: string }[]; pauses: { id: string; start_date: string; end_date: string }[] }

export const newVehicle = (): VehicleInput => ({ society_id: "", catalogue_id: "", registration: "",
  parking_basement: "", parking_number: "", plan_id: "", cutoff_time: "09:00", interior_day: null,
  photo_upload_id: "", rc_upload_id: null, first_payment_status: "Due" });
export const weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];
export const times = Array.from({ length: 48 }, (_, i) => `${String(Math.floor(i / 2)).padStart(2, "0")}:${i % 2 ? "30" : "00"}`);
export const PAGE_SIZE = 50;

/** How far a customer has got with their own sign-in (ADM-CUS-17). */
export function onboardingState(c: { email_verified?: boolean; password_set?: boolean; onboarding_confirmed?: boolean }):
    { label: string; tone: "ok" | "warn" | "neutral" } {
  if (c.onboarding_confirmed) return { label: "Confirmed", tone: "ok" };
  if (c.password_set) return { label: "Review pending", tone: "warn" };
  if (c.email_verified) return { label: "Password not set", tone: "warn" };
  return { label: "Not signed in yet", tone: "neutral" };
}

/** The value after it has stopped changing for `ms`, so a search box does not call the API on every key. */
export function useDebounced<T>(value: T, ms = 300): T {
  const [v, setV] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setV(value), ms);
    return () => clearTimeout(t);
  }, [value, ms]);
  return v;
}

/**
 * Headers the store's signed upload asks for that a browser may not send: Vercel
 * Blob's CORS reply does not list them, so the browser blocks the whole upload.
 * The signed token already carries both settings (no random suffix, overwrite
 * allowed), so the phone can send them and the portal can leave them out.
 */
const NOT_ALLOWED_IN_BROWSER = ["x-add-random-suffix", "x-allow-overwrite"];

export function browserUploadHeaders(headers: Record<string, string>): Record<string, string> {
  return Object.fromEntries(Object.entries(headers).filter(([k]) => !NOT_ALLOWED_IN_BROWSER.includes(k.toLowerCase())));
}

export async function uploadCustomerAsset(file: File, purpose: "vehicle" | "rc") {
  const t = await api<{ id: string; upload_url: string; method: string; headers: Record<string, string> }>(
    "/v1/admin/customer-uploads", { method: "POST", body: { purpose, content_type: file.type, size_bytes: file.size } });
  const sent = await fetch(t.upload_url, { method: t.method, headers: browserUploadHeaders(t.headers), body: file });
  if (!sent.ok) throw new Error("The file could not be uploaded. Please try again.");
  return api<{ id: string; url: string }>(`/v1/admin/customer-uploads/${t.id}/confirm`, { method: "POST" });
}
