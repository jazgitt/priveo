import { useQuery, useQueryClient } from "@tanstack/react-query";
import { createContext, useCallback, useContext, useEffect, useMemo, type ReactNode } from "react";

import { api, ApiError, setUnauthorizedListener } from "../api/client";

export interface Profile {
  user_id: string;
  role: string;
  display_name: string;
}

interface AuthValue {
  /** `loading` until the first answer from GET /v1/web/me. */
  status: "loading" | "signedIn" | "signedOut";
  user: Profile | null;
  signIn: (loginId: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
}

const ME_KEY = ["web", "me"] as const;
const AuthContext = createContext<AuthValue | null>(null);

async function fetchMe(): Promise<Profile | null> {
  try {
    return await api<Profile>("/v1/web/me", { quiet401: true });
  } catch (e) {
    if (e instanceof ApiError && (e.status === 401 || e.status === 403)) return null;
    throw e;
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const qc = useQueryClient();
  const me = useQuery({ queryKey: ME_KEY, queryFn: fetchMe, retry: false, staleTime: 60_000 });

  // A 401 from any call means the session ended: show the sign-in page.
  useEffect(() => {
    setUnauthorizedListener(() => {
      qc.setQueryData(ME_KEY, null);
      qc.removeQueries({ predicate: (q) => q.queryKey[0] !== "web" });
    });
    return () => setUnauthorizedListener(null);
  }, [qc]);

  const signIn = useCallback(async (loginId: string, password: string) => {
    const profile = await api<Profile>("/v1/web/login", {
      method: "POST", body: { login_id: loginId, password }, quiet401: true,
    });
    qc.setQueryData(ME_KEY, profile);
  }, [qc]);

  const signOut = useCallback(async () => {
    try {
      await api<void>("/v1/web/logout", { method: "POST", quiet401: true });
    } finally {
      qc.setQueryData(ME_KEY, null);
      qc.removeQueries({ predicate: (q) => q.queryKey[0] !== "web" });
    }
  }, [qc]);

  const value = useMemo<AuthValue>(() => {
    const user = me.data ?? null;
    const status = me.isPending ? "loading" : user ? "signedIn" : "signedOut";
    return { status, user, signIn, signOut };
  }, [me.data, me.isPending, signIn, signOut]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthValue {
  const v = useContext(AuthContext);
  if (!v) throw new Error("useAuth needs an AuthProvider");
  return v;
}
