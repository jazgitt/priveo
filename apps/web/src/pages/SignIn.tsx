import { useState, type FormEvent } from "react";
import { Navigate, useLocation } from "react-router-dom";

import { ApiError } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { Button, TextField } from "../components";

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
    <main className="signin">
      <form className="card signin-card" onSubmit={submit}>
        <h1 className="brand-title">Priveo</h1>
        <p className="muted">Admin sign-in</p>
        <TextField label="User ID" autoComplete="username" autoCapitalize="none"
                   value={loginId} onChange={(e) => setLoginId(e.target.value)} required />
        <TextField label="Password" type="password" autoComplete="current-password"
                   value={password} onChange={(e) => setPassword(e.target.value)} required />
        {error && <p className="form-error" role="alert">{error}</p>}
        <Button type="submit" busy={busy}>Sign in</Button>
      </form>
    </main>
  );
}
