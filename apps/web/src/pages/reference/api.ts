import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, ApiError } from "../../api/client";
import { useAppMutation } from "../../blocks/mutation";

export const BASE = "/v1/admin/directory";

/**
 * Every directory read shares the "directory" key, so one save refreshes them all.
 * While a new search or filter loads, the rows already shown stay on screen
 * instead of flashing to a loading state.
 */
export function useDirectory<T>(path: string, enabled = true) {
  return useQuery({
    queryKey: ["directory", path],
    queryFn: () => api<T>(`${BASE}${path}`),
    enabled,
    placeholderData: keepPreviousData,
  });
}

export interface DirCall {
  path: string;
  method?: "POST" | "PATCH" | "PUT" | "DELETE";
  body?: unknown;
}

export function useDirMutation<T = unknown>() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (c: DirCall) =>
      api<T>(`${BASE}${c.path}`, { method: c.method ?? "POST", body: c.body }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["directory"] }),
  });
}

/** A directory change with the Saving / Saved toast; every directory read refreshes after it. */
export function useDirSave() {
  return useAppMutation<DirCall & { done: string }>({
    mutationFn: (c) => api(`${BASE}${c.path}`, { method: c.method ?? "POST", body: c.body }),
    success: (_d, c) => c.done,
    invalidate: [["directory"]],
  });
}

/** The API's message for one field of a failed call, if it named that field. */
export function fieldError(error: unknown, field: string): string | undefined {
  return error instanceof ApiError ? error.fields[field] : undefined;
}

/** Text for an error that is not shown beside a field (for example "in use"). */
export function errorText(error: unknown): string {
  if (!(error instanceof ApiError)) return "Something went wrong. Please try again.";
  const f = error.fields;
  if (error.code === "in_use" && ("active_subscriptions" in f || "active_crew" in f)) {
    return `${error.message} Active subscriptions: ${f.active_subscriptions ?? "0"}. ` +
      `Active crew: ${f.active_crew ?? "0"}.`;
  }
  return error.message;
}

/** The ids with the row at `index` swapped with its neighbour. */
export function moved<T extends { id: string }>(rows: T[], index: number, by: -1 | 1): string[] {
  const ids = rows.map((r) => r.id);
  const j = index + by;
  if (j < 0 || j >= ids.length) return ids;
  [ids[index], ids[j]] = [ids[j], ids[index]];
  return ids;
}
