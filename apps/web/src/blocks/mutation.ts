import { useMutation, useQueryClient, type QueryKey } from "@tanstack/react-query";
import { toast } from "sonner";

import { track } from "@/analytics/analytics";
import { ApiError } from "@/api/client";

/** The message of an API error envelope, or a general one. */
export function errorMessage(e: unknown): string {
  if (e instanceof ApiError) {
    const fields = Object.values(e.fields);
    return fields.length > 0 ? `${e.message} ${fields.join(" ")}` : e.message;
  }
  if (e instanceof Error && e.message) return e.message;
  return "Something went wrong. Please try again.";
}

export interface AppMutationOptions<TVars, TData> {
  mutationFn: (vars: TVars) => Promise<TData>;
  /** Shown while it runs. */
  pending?: string | ((vars: TVars) => string);
  /** Shown when it worked. */
  success: string | ((data: TData, vars: TVars) => string);
  /** Queries to refresh after it worked. */
  invalidate?: QueryKey[];
  onSuccess?: (data: TData, vars: TVars) => void;
  onError?: (error: unknown, vars: TVars) => void;
  /** Analytics name (see analytics/events.ts). Sent when it worked; "<name> failed" when not. */
  event?: string;
}

/**
 * Every change made in the portal goes through this hook, so each one says
 * "Saving…", then that it worked or why it did not, in one toast.
 */
export function useAppMutation<TVars = void, TData = unknown>(o: AppMutationOptions<TVars, TData>) {
  const qc = useQueryClient();
  return useMutation<TData, unknown, TVars, { toastId: string | number }>({
    mutationFn: o.mutationFn,
    onMutate: (vars) => ({
      toastId: toast.loading(typeof o.pending === "function" ? o.pending(vars) : o.pending ?? "Saving…"),
    }),
    onSuccess: async (data, vars, ctx) => {
      toast.success(typeof o.success === "function" ? o.success(data, vars) : o.success,
        { id: ctx?.toastId });
      if (o.event) track(o.event);
      o.onSuccess?.(data, vars);
      await Promise.all((o.invalidate ?? []).map((queryKey) => qc.invalidateQueries({ queryKey })));
    },
    onError: (e, vars, ctx) => {
      toast.error(errorMessage(e), { id: ctx?.toastId, duration: 8000 });
      // Status and code only: the message and fields can name a customer.
      if (o.event) {
        track(`${o.event} failed`, e instanceof ApiError ? { status: e.status, code: e.code } : {});
      }
      o.onError?.(e, vars);
    },
  });
}
