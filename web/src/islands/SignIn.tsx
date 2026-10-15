import { type SubmitEvent, useEffect, useRef, useState } from "react";

import type { Me } from "../lib/api/client";
import { api } from "../lib/api/client";
import { loadPicked, mergePicked, samePicked, savePicked } from "../lib/topics";

type Turnstile = {
  render: (element: HTMLElement, options: Record<string, unknown>) => string;
  reset: (widget: string) => void;
  remove: (widget: string) => void;
};
declare global {
  interface Window {
    turnstile?: Turnstile;
  }
}

const TURNSTILE = "https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit";

/** After signing in: the browser's topics join the account's, then the reader moves on. */
export async function finishSignIn(me: Me, next: string) {
  const merged = mergePicked(me.topics, loadPicked());
  if (!samePicked(merged, me.topics)) {
    await api().PUT("/api/v1/me/topics", { body: { topics: merged } });
  }
  savePicked(merged);
  location.assign(next);
}

function detail(error: unknown, fallback: string): string {
  const text = (error as { detail?: unknown } | undefined)?.detail;
  return typeof text === "string" ? text : fallback;
}

/** Cloudflare Turnstile tells people from bots before an email is sent; its token works once. */
function useTurnstile(siteKey: string | null) {
  const box = useRef<HTMLDivElement>(null);
  const widget = useRef<string | null>(null);
  const [token, setToken] = useState("");

  useEffect(() => {
    if (!siteKey || !box.current) return;
    const render = () => {
      if (!window.turnstile || !box.current || widget.current) return;
      widget.current = window.turnstile.render(box.current, {
        sitekey: siteKey,
        callback: setToken,
        "expired-callback": () => setToken(""),
      });
    };
    let script = document.querySelector<HTMLScriptElement>(`script[src="${TURNSTILE}"]`);
    if (!script) {
      script = document.createElement("script");
      script.src = TURNSTILE;
      script.async = true;
      document.head.append(script);
    }
    if (window.turnstile) render();
    else script.addEventListener("load", render);
    // The widget goes with the email step, and a new one comes back with it.
    return () => {
      script.removeEventListener("load", render);
      if (widget.current) window.turnstile?.remove(widget.current);
      widget.current = null;
      setToken("");
    };
  }, [siteKey]);

  const reset = () => {
    setToken("");
    if (widget.current) window.turnstile?.reset(widget.current);
  };
  return { box, token, ready: !siteKey || token !== "", reset };
}

/** Sign in with a code sent by email: no password (ADR 0003). */
export default function SignIn({ siteKey, next }: { siteKey: string | null; next: string }) {
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [step, setStep] = useState<"email" | "code">("email");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const bot = useTurnstile(step === "email" ? siteKey : null);

  async function sendCode(event: SubmitEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const { error: failed } = await api().POST("/api/v1/auth/code", {
        body: { email, bot_token: bot.token },
      });
      if (failed) return setError(detail(failed, "The code could not be sent. Try again."));
      setStep("code");
    } catch {
      setError("The code could not be sent. Try again.");
    } finally {
      bot.reset();
      setBusy(false);
    }
  }

  async function signIn(event: SubmitEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const { data, error: failed } = await api().POST("/api/v1/auth/verify", {
        body: { email, code },
      });
      if (!data) return setError(detail(failed, "That did not work. Try again."));
      await finishSignIn(data, next);
    } catch {
      setError("That did not work. Try again.");
    } finally {
      setBusy(false);
    }
  }

  if (step === "code") {
    return (
      <form className="measure stack" onSubmit={signIn}>
        <p>
          We sent a six-digit code to <strong>{email}</strong>. It works once, for ten minutes. The
          email also has a link, if you would rather open it on this device.
        </p>
        <div className="field">
          <label className="label" htmlFor="code">
            Code
          </label>
          <input
            id="code"
            className="input input-code"
            inputMode="numeric"
            autoComplete="one-time-code"
            pattern="[0-9]{6}"
            maxLength={6}
            required
            autoFocus
            value={code}
            onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
          />
        </div>
        {error && (
          <p className="form-error" role="alert">
            {error}
          </p>
        )}
        <div className="chips">
          <button className="button button-primary" type="submit" disabled={busy || code.length !== 6}>
            Sign in
          </button>
          <button
            className="button button-secondary"
            type="button"
            onClick={() => {
              setStep("email");
              setCode("");
              setError("");
            }}
          >
            Use another email
          </button>
        </div>
      </form>
    );
  }

  return (
    <form className="measure stack" onSubmit={sendCode}>
      <div className="field">
        <label className="label" htmlFor="email">
          Email
        </label>
        <input
          id="email"
          className="input"
          type="email"
          autoComplete="email"
          required
          maxLength={254}
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
      </div>
      {siteKey && <div ref={bot.box} className="bot-check" />}
      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}
      <div>
        <button className="button button-primary" type="submit" disabled={busy || !bot.ready}>
          Email me a code
        </button>
      </div>
    </form>
  );
}
