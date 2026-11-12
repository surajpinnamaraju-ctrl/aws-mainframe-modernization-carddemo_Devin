import { useState } from "react";
import { api } from "../api/client";
import type { Session } from "../types";

export default function Login({ onLogin }: { onLogin: (s: Session) => void }) {
  const [userId, setUserId] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const s = await api<Session>("/api/auth/login", {
        method: "POST",
        body: { user_id: userId, password },
      });
      onLogin(s);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="login-wrap">
      <div className="card login-card">
        <p className="eyebrow">01 / Sign on</p>
        <h2 className="login-title">CardDemo</h2>
        <p className="lead">
          Modernized from the CICS COSGN00C transaction.
        </p>
        {error && <div className="error" role="alert">{error}</div>}
        <form className="stack" onSubmit={submit}>
          <label>User ID
            <input value={userId} onChange={(e) => setUserId(e.target.value)}
                   required maxLength={8} autoFocus />
          </label>
          <label>Password
            <input type="password" value={password}
                   onChange={(e) => setPassword(e.target.value)}
                   required maxLength={8} />
          </label>
          <button className="primary" disabled={busy}>
            {busy ? "Signing in…" : "Sign in"}
          </button>
        </form>
      </div>
    </div>
  );
}
