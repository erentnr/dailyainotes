import { useState } from "react";

import { api } from "../lib/api/client";

/** Sign out, or delete the account after one more press. */
export default function AccountActions() {
  const [confirming, setConfirming] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function run(action: () => Promise<{ error?: unknown; response: Response }>) {
    setBusy(true);
    setError("");
    try {
      const { response } = await action();
      if (!response.ok) return setError("That did not work. Try again.");
      location.assign("/");
    } catch {
      setError("That did not work. Try again.");
    } finally {
      setBusy(false);
    }
  }

  const signOut = () => run(() => api().POST("/api/v1/auth/sign-out"));
  const remove = () => run(() => api().DELETE("/api/v1/me"));

  return (
    <>
      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}
      <section className="section stack">
        <div className="label">This device</div>
        <div>
          <button className="button button-secondary" type="button" disabled={busy} onClick={signOut}>
            Sign out
          </button>
        </div>
      </section>
      <section className="section">
        <div className="label">Delete your account</div>
        {confirming ? (
          <div className="stack">
            <p>
              This removes your email, your topics, your topic suggestions and your questions to Ask, at
              once and for good.
              The topics you picked stay in this browser.
            </p>
            <div className="chips">
              <button className="button button-danger" type="button" disabled={busy} onClick={remove}>
                Delete my account
              </button>
              <button className="button button-secondary" type="button" onClick={() => setConfirming(false)}>
                Keep it
              </button>
            </div>
          </div>
        ) : (
          <div className="stack">
            <p className="muted">Everything we keep about you goes with it.</p>
            <div>
              <button className="button button-secondary" type="button" onClick={() => setConfirming(true)}>
                Delete account
              </button>
            </div>
          </div>
        )}
      </section>
    </>
  );
}
