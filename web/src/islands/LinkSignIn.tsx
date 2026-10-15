import { useEffect, useState } from "react";

import { api } from "../lib/api/client";
import { finishSignIn } from "./SignIn";

/** The link from the sign-in email. Its token is in the address's fragment, which never reaches
 * the server's logs, and it is spent only when the reader presses the button: mail scanners
 * that open links do not press buttons. */
export default function LinkSignIn() {
  const [token, setToken] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    setToken(location.hash.slice(1));
    // Out of the history, so the token is not left behind on this device.
    history.replaceState(null, "", location.pathname);
  }, []);

  async function signIn() {
    if (!token) return;
    setBusy(true);
    setError("");
    try {
      const { data, error: failed } = await api().POST("/api/v1/auth/link", { body: { token } });
      if (!data) {
        const text = (failed as { detail?: unknown } | undefined)?.detail;
        return setError(typeof text === "string" ? text : "That link did not work.");
      }
      await finishSignIn(data, "/");
    } catch {
      setError("That link did not work. Try again.");
    } finally {
      setBusy(false);
    }
  }

  if (token === "") {
    return (
      <p className="measure">
        This link is missing its code. <a href="/sign-in">Ask for a new one</a>.
      </p>
    );
  }
  return (
    <div className="measure stack">
      <p>Sign in to Daily AI Notes on this device.</p>
      {error && (
        <p className="form-error" role="alert">
          {error} <a href="/sign-in">Ask for a new code</a>.
        </p>
      )}
      <div>
        <button className="button button-primary" type="button" disabled={busy || !token} onClick={signIn}>
          Sign in
        </button>
      </div>
    </div>
  );
}
