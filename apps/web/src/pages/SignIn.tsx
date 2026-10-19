import { useState, type FormEvent } from "react";
import { Navigate, useLocation } from "react-router-dom";

import { analyticsActive } from "../analytics/analytics";
import { ApiError } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { Field } from "../blocks/fields";
import { BusyButton } from "../blocks/FormDialog";
import { Input } from "../ui/input";

export function SignIn() {
  const { status, signIn } = useAuth();
  const location = useLocation();
  const [loginId, setLoginId] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  if (status === "signedIn") {
    const from = (location.state as { from?: string } | null)?.from ?? "/";
    return <Navigate to={from} replace />;
  }

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await signIn(loginId.trim(), password);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Please try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="grid min-h-screen place-items-center bg-background px-4">
      <form onSubmit={submit} className="flex w-full max-w-sm flex-col gap-5 rounded-2xl border bg-card p-8 shadow-sm">
        <div>
          <h1 className="m-0 font-display text-4xl font-bold text-gold-text">Priveo</h1>
          <p className="m-0 mt-1 text-sm text-muted-foreground">Admin sign-in</p>
        </div>
        <Field label="User ID">
          {(p) => <Input {...p} autoComplete="username" autoCapitalize="none" required autoFocus
                         value={loginId} onChange={(e) => setLoginId(e.target.value)} />}
        </Field>
        <Field label="Password">
          {(p) => <Input {...p} type="password" autoComplete="current-password" required
                         value={password} onChange={(e) => setPassword(e.target.value)} />}
        </Field>
        {error && <p role="alert" className="m-0 rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">{error}</p>}
        <BusyButton type="submit" busy={busy} className="w-full">Sign in</BusyButton>
        {analyticsActive() && (
          <p className="m-0 text-center text-xs text-muted-foreground">
            Priveo records how this portal is used, including what is on screen, to improve it.
          </p>
        )}
      </form>
    </main>
  );
}
