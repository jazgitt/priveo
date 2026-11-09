// The Demand tab's list (services/api/app/scheduling/routes/demand_list.py).
// Kept out of schedule/api.ts so the capacity build does not share that file.
import { useQuery } from "@tanstack/react-query";

import { api } from "../../api/client";

export interface DemandItem {
  /** "EXT", "INT" or "Other", as the Demand tab groups them. */
  group: string;
  service: string;
  service_label: string;
  vehicle_id: string;
  registration: string;
  vehicle: string;
  /** The customer's cutoff as HH:MM, or null when the job has none. */
  cutoff: string | null;
  source: string;
}

/** The jobs due on one date, in the order the server sends them (EXT, INT, other; each by cutoff). */
export function useDemandList(societyId: string, date: string, service: string) {
  return useQuery({
    queryKey: ["demand", societyId, date, service],
    enabled: Boolean(societyId && date),
    queryFn: () => {
      const q = new URLSearchParams({ society_id: societyId, date });
      if (service !== "All") q.set("service", service);
      return api<DemandItem[]>(`/v1/admin/scheduling/demand?${q}`);
    },
  });
}
