// Shapes of the support and billing admin endpoints used by the support pages.
// They follow services/api/app/support/schemas.py and app/billing/schemas.py.

export interface Update {
  id: string;
  author_role: string;
  note: string;
  status: string | null;
  created_at: string;
}

export interface ComplaintSummary {
  id: string;
  number: number;
  display_id: string;
  category: string;
  description: string;
  status: string;
  visit_id: string | null;
  created_at: string;
  updated_at: string;
  latest_note: string | null;
  customer_name: string;
  society: string;
  flat: string;
  overdue: boolean;
}

export interface ComplaintDetail extends ComplaintSummary {
  photo_keys: string[];
  updates: Update[];
}

export interface FeedbackItem {
  id: string;
  category: string | null;
  rating: number | null;
  comment: string;
  testimonial_permission: boolean;
  customer_name: string;
  society: string;
  created_at: string;
}

export interface RatingItem {
  visit_id: string;
  rating: number;
  tags: string[];
  comment: string;
  testimonial_permission: boolean;
  created_at: string;
  society: string;
}

export interface RatingsReport {
  count: number;
  average: number | null;
  tag_counts: Record<string, number>;
  items: RatingItem[];
}

export interface CheckInItem {
  id: string;
  customer_name: string;
  society: string;
  vehicle_label: string;
  cycle_start: string;
  answers: { category: string; rating: number }[];
  comment: string;
  created_at: string;
}

export interface CheckInsReport {
  category_averages: Record<string, number>;
  items: CheckInItem[];
}

export interface OptionAdmin {
  id: string;
  kind: string;
  name: string;
  description: string;
  sort_order: number;
  active: boolean;
}

export interface SupportAlert {
  id: string;
  kind: string;
  title: string;
  body: string;
  ref_type: string | null;
  ref_id: string | null;
  created_at: string;
  read: boolean;
}

export interface SupportAlertList {
  unread_count: number;
  items: SupportAlert[];
}

export interface PaymentAlert {
  id: string;
  kind: string;
  message: string;
  payment_id: string | null;
  created_at: string;
  read: boolean;
}

export interface AdminPayment {
  id: string;
  kind: string;
  description: string;
  amount_rupees: number;
  status: string;
  due_date: string;
  customer_name: string;
  flat: string;
  society: string;
  vehicle: string;
}

export interface NeedsJob {
  id: string;
  date: string;
  registration: string;
  vehicle: string;
  customer_name: string;
  service: string;
  reason: string;
}

/** One row of the merged alert list, tagged by where it came from. */
export interface MergedAlert {
  key: string;
  source: "support" | "payment";
  id: string;
  kind: string;
  title: string;
  body: string;
  created_at: string;
  read: boolean;
  /** The portal path the alert points to, when it points anywhere. */
  link: string | null;
}
