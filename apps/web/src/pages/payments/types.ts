export const STATUSES = ["Due", "Over due", "Initiated", "Received"] as const;
export type PaymentStatus = (typeof STATUSES)[number];

/** AdminPaymentOut from GET /v1/admin/payments. */
export interface AdminPayment {
  id: string;
  kind: "Plan" | "Add-on";
  description: string;
  amount_rupees: number;
  status: PaymentStatus;
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

/** ADM-PAY-02 and -07: the API allows any status to any other. Confirm is a
 *  move to Received; reject is a move back from Initiated or Received. */
export function canConfirm(p: AdminPayment): boolean {
  return p.status !== "Received";
}
export function canReject(p: AdminPayment): boolean {
  return p.status === "Initiated" || p.status === "Received";
}
