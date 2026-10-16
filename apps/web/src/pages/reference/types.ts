// Shapes of /v1/admin/directory/* (services/api/app/directory/schemas.py).

export interface Society {
  id: string;
  name: string;
  sector: string;
  city: string;
  active: boolean;
  parking_basements: string[];
  cars_serviced: number;
  active_subscriptions: number;
  active_crew: number;
}

export interface Slot {
  id: string;
  society_id: string;
  service: string;
  start: string;
  end: string;
  days: string[];
}

export interface Plan {
  id: string;
  /** The plan ID admins quote, like PLN-0001. */
  code: string;
  name: string;
  monthly_price_rupees: number;
  list_price_rupees: number | null;
  includes_interior: boolean;
  inclusions: string[];
  badge: string;
  sort_order: number;
  active: boolean;
  active_subscriptions: number;
}

export interface Vehicle {
  id: string;
  make: string;
  model: string;
  variant: string;
  category: string;
  active: boolean;
}

export interface ServiceRow {
  name: string;
  duration_minutes: number;
  min_photos: number;
  min_videos: number;
}

export interface ChecklistItem {
  id: string;
  service: string;
  key: string;
  label: string;
  sort_order: number;
  active: boolean;
}

export interface Checklist {
  service: string;
  min_photos: number;
  min_videos: number;
  items: ChecklistItem[];
}

export interface Reason {
  id: string;
  key: string;
  label: string;
  sort_order: number;
  active: boolean;
}

export interface Addon {
  id: string;
  /** The add-on ID admins quote, like ADN-0001. */
  code: string;
  name: string;
  description: string;
  service: string;
  price_rupees: number;
  list_price_rupees: number | null;
  duration_minutes: number;
  sort_order: number;
  active: boolean;
}

export const SERVICE_NAMES = ["Cleaning-External", "Cleaning-Internal", "Deep Spa"] as const;
export const WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday",
  "Sunday"] as const;
