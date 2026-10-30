import type { ReactNode } from "react";

import { useManiAccess } from "@/api/mani";
import { ErrorState, PageHeader } from "@/blocks/layout";
import { Skeleton } from "@/ui/skeleton";

/**
 * Shows its page only to the Founder. Any other admin sees a plain "Not available".
 * This is for looks: the server refuses every Mani call from anyone else.
 */
export function ManiGate({ children }: { children: ReactNode }) {
  const { access, retry } = useManiAccess();
  if (access === "loading") return <Skeleton className="h-64" />;
  if (access === "error") return <ErrorState message="Could not check access." onRetry={retry} />;
  if (access === "denied") {
    return <PageHeader title="Not available" description="This page is not available to your account." />;
  }
  return <>{children}</>;
}
