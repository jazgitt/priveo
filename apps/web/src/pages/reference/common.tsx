import type { UseQueryResult } from "@tanstack/react-query";
import type { ReactNode } from "react";

import { StatusChip } from "../../components";
import { errorText } from "./api";

/** Loading and error states around a query, then the data. */
export function QueryState<T>({ query, children }: {
  query: UseQueryResult<T>;
  children: (data: T) => ReactNode;
}) {
  if (query.isLoading) return <p className="muted">Loading...</p>;
  if (query.isError || query.data === undefined) {
    return <p role="alert" className="form-error">{errorText(query.error)}</p>;
  }
  return <>{children(query.data)}</>;
}

export function ActiveChip({ active }: { active: boolean }) {
  return <StatusChip tone={active ? "ok" : "neutral"}>{active ? "Active" : "Inactive"}</StatusChip>;
}

/** A failed action that has no field beside it, such as a blocked deactivation. */
export function Notice({ error }: { error: unknown }) {
  if (!error) return null;
  return <p className="ref-notice" role="alert">{errorText(error)}</p>;
}
