/** The six statuses a payment shows (PAY-14). Not Due, Due, Due today and Over due
 *  follow the cycle dates; Initiated and Paid are recorded. */
export const STATUSES = ["Not Due", "Due", "Due today", "Over due", "Initiated", "Paid"] as const;
export type PaymentStatus = (typeof STATUSES)[number];

/** The statuses that follow the cycle dates. Setting one means "no payment counts". */
export const DATE_STATUSES: readonly string[] = ["Not Due", "Due", "Due today", "Over due"];

/** AdminPaymentOut from GET /v1/admin/payments. */
export interface AdminPayment {
  id: string;
  kind: "Plan" | "Add-on";
  description: string;
  amount_rupees: number;
  status: PaymentStatus;
  /** Days left to the due date; negative when over due. */
  days_to_due: number | null;
  status_message: string;
  last_payment_failed: boolean;
  due_date: string;
  cycle_start: string | null;
  cycle_end: string | null;
  vehicle_id: string | null;
  received_on: string | null;
  invoice_number: string | null;
  customer_name: string;
  flat: string;
  society: string;
  vehicle: string;
  initiated_at: string | null;
}

export interface Invoice {
  number: string;
  issued_on: string;
  amount_rupees: number;
  description: string;
  customer_name: string;
  vehicle: string;
  gst_included: boolean;
  seller_name: string;
  seller_address: string;
  seller_gstin: string;
}

export interface PaymentAlert {
  id: string;
  kind: string;
  message: string;
  payment_id: string | null;
  created_at: string;
  read: boolean;
}

export interface PaymentFilters {
  status: string;
  kind: string;
  customer_id: string;
  vehicle_id: string;
  due_after: string;
  due_before: string;
}

export const NO_FILTERS: PaymentFilters = {
  status: "", kind: "", customer_id: "", vehicle_id: "", due_after: "", due_before: "",
};

/** ADM-PAY-02 and -07: Approve and Reject act on an Initiated payment. Any
 *  other move goes through the status menu. */
export function canConfirm(p: AdminPayment): boolean {
  return p.status === "Initiated";
}
export function canReject(p: AdminPayment): boolean {
  return p.status === "Initiated";
}

/** The status menu: Initiated, Paid, and one entry "Open" for the date-based four. */
export const OPEN = "Open";
export function statusChoices(p: AdminPayment): { value: string; label: string }[] {
  const out = [];
  if (p.status !== "Initiated") out.push({ value: "Initiated", label: "Initiated" });
  if (p.status !== "Paid") out.push({ value: "Paid", label: "Paid" });
  if (p.status === "Initiated" || p.status === "Paid") out.push({ value: OPEN, label: "Not paid (follows the cycle dates)" });
  return out;
}

/** What a status looks like in a list: days to go, or days over. */
export function dueNote(p: AdminPayment): string {
  return p.status_message || "";
}
