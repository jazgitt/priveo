import { useEffect, useState } from "react";

import { api } from "../api/client";

/**
 * A blue strip across the top of the test portal, so nobody mistakes it for
 * production. The API says which environment it runs in; nothing shows on
 * prod, on dev, or when the answer cannot be read.
 */
export function EnvBanner() {
  const [environment, setEnvironment] = useState("");

  useEffect(() => {
    const ctrl = new AbortController();
    api<{ environment?: string }>("/v1/public/config", { signal: ctrl.signal, quiet401: true })
      .then((c) => setEnvironment(c.environment ?? ""))
      .catch(() => undefined);
    return () => ctrl.abort();
  }, []);

  if (environment !== "test") return null;
  return (
    <div role="status" className="bg-info px-4 py-1.5 text-center text-sm font-medium text-white">
      TEST portal. Data here is for testing only.
    </div>
  );
}
