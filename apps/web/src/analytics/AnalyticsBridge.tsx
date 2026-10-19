import { useEffect } from "react";

import { useAuth } from "../auth/AuthContext";
import { identifyUser, resetUser } from "./analytics";

/** Follows sign-in and sign-out. Draws nothing. */
export function AnalyticsBridge() {
  const { status, user } = useAuth();
  const userId = user?.user_id;
  const role = user?.role;

  useEffect(() => {
    if (status === "signedIn" && userId && role) identifyUser(userId, role);
    else if (status === "signedOut") resetUser();
  }, [status, userId, role]);

  return null;
}
