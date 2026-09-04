import { useEffect, useState } from "react";
import {
  getFyersStatus,
  setFyersCredentials,
  getFyersAuthUrl,
  submitFyersAuthCode,
  submitFyersToken,
} from "../api.js";

/**
 * FyersSetupPanel — a modal that walks the user through connecting Fyers from
 * the tool (instead of the CLI). Two stages:
 *   1. Credentials — enter app id + secret (saved to config.yaml, gitignored).
 *   2. Login — open the Fyers auth URL, log in, paste the auth_code/redirect
 *      URL back here to exchange it for the daily token.
 * Secrets are never displayed back; status is booleans only.
 *
 * Fyers tokens expire ~6am IST daily, so this is a recurring flow — the panel
 * is reachable any time from the header, not just first-run.
 */
export default function FyersSetupPanel({ onClose, onConnected }) {
  const [status, setStatus] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  const [clientId, setClientId] = useState("");
  const [secretId, setSecretId] = useState("");
  const [redirect, setRedirect] = useState("");
  const [authUrl, setAuthUrl] = useState("");
  const [authCode, setAuthCode] = useState("");
  const [rawToken, setRawToken] = useState("");
  const [showTokenFallback, setShowTokenFallback] = useState(false);

  const refresh = () =>
    getFyersStatus()
      .then((s) => {
        setStatus(s);
        if (s.status === "ready") onConnected?.();
      })
      .catch((e) => setError(e.message));

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const run = async (fn) => {
    setBusy(true);
    setError(null);
    try {
      const s = await fn();
      if (s && typeof s === "object" && "status" in s) {
        setStatus(s);
        if (s.status === "ready") onConnected?.();
      }
      return s;
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  const saveCreds = () => run(() => setFyersCredentials(clientId, secretId, redirect || undefined));
  const getLink = () =>
    run(async () => {
      const { url } = await getFyersAuthUrl();
      setAuthUrl(url);
      window.open(url, "_blank", "noopener");
      return null;
    });
  const exchange = () => run(() => submitFyersAuthCode(authCode));
  const cacheToken = () => run(() => submitFyersToken(rawToken));

  const credsSet = status?.app_id_set && status?.secret_set;
  const connected = status?.status === "ready";

  return (
    <div
      data-testid="fyers-setup-modal"
      className="fixed inset-0 z-50 flex items-center justify-center bg-ink/40 p-4"
      onClick={onClose}
    >
      <div
        className="w-full max-w-md border border-hairline bg-card p-5"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-3 flex items-center justify-between border-b border-hairline pb-2">
          <h2 className="font-mono text-[13px] font-bold uppercase tracking-overline">
            Connect Fyers
          </h2>
          <button
            onClick={onClose}
            className="font-mono text-[11px] text-ink3 hover:text-ink"
            data-testid="fyers-close"
          >
            ✕
          </button>
        </div>

        {/* Status line */}
        <div className="mb-3 flex items-center gap-2 font-mono text-[11px]">
          <span
            className={
              "inline-block h-2 w-2 rounded-full " + (connected ? "bg-bull-dot" : "bg-warn-dot")
            }
          />
          <span className={connected ? "text-bull" : "text-warn"}>
            {connected ? "Connected — token active" : status ? statusWord(status) : "checking…"}
          </span>
        </div>

        {error && (
          <div className="mb-3 border border-bear-border bg-bear-bg px-2 py-1 font-sans text-[11px] text-bear">
            {error}
          </div>
        )}

        {/* Step 1 — credentials */}
        <Section n="1" title="App credentials" done={credsSet}>
          <p className="mb-2 font-sans text-[11px] text-ink3">
            From your Fyers API dashboard (myapi.fyers.in). Saved locally, never shared.
          </p>
          <Field label="App ID (client_id)" value={clientId} onChange={setClientId}
                 placeholder={credsSet ? "•••• already set — re-enter to change" : "e.g. XY12ABC-100"} />
          <Field label="Secret ID" type="password" value={secretId} onChange={setSecretId}
                 placeholder={credsSet ? "•••• already set" : "your secret key"} />
          <Field label="Redirect URI (optional)" value={redirect} onChange={setRedirect}
                 placeholder="leave blank for the Fyers default" />
          <button
            onClick={saveCreds}
            disabled={busy || !clientId || !secretId}
            data-testid="fyers-save-creds"
            className="mt-1 border border-ink bg-ink px-3 py-1 font-mono text-[11px] uppercase tracking-overline text-white disabled:opacity-40"
          >
            Save credentials
          </button>
        </Section>

        {/* Step 2 — login */}
        <Section n="2" title="Log in & paste code" done={connected} disabled={!credsSet}>
          <button
            onClick={getLink}
            disabled={busy || !credsSet}
            data-testid="fyers-get-link"
            className="mb-2 border border-info bg-info-bg px-3 py-1 font-mono text-[11px] uppercase tracking-overline text-info disabled:opacity-40"
          >
            Open Fyers login ↗
          </button>
          {authUrl && (
            <p className="mb-2 break-all font-mono text-[9px] text-ink3">
              If it didn't open: <a className="text-info underline" href={authUrl} target="_blank" rel="noopener noreferrer">{authUrl}</a>
            </p>
          )}
          <p className="mb-1 font-sans text-[11px] text-ink3">
            After logging in you land on a redirect URL containing <code>auth_code=…</code>. Paste
            the whole URL (or just the code) here:
          </p>
          <Field label="auth_code or redirect URL" value={authCode} onChange={setAuthCode}
                 placeholder="https://…?auth_code=…  (or the code)" />
          <button
            onClick={exchange}
            disabled={busy || !authCode || !credsSet}
            data-testid="fyers-exchange"
            className="border border-ink bg-ink px-3 py-1 font-mono text-[11px] uppercase tracking-overline text-white disabled:opacity-40"
          >
            Connect
          </button>

          <button
            onClick={() => setShowTokenFallback((v) => !v)}
            className="mt-2 block font-mono text-[9px] uppercase tracking-overline text-ink3 hover:text-ink2"
          >
            {showTokenFallback ? "▾" : "▸"} paste a token directly instead
          </button>
          {showTokenFallback && (
            <div className="mt-1">
              <Field label="access token" type="password" value={rawToken} onChange={setRawToken}
                     placeholder="a full Fyers access token" />
              <button
                onClick={cacheToken}
                disabled={busy || !rawToken}
                className="border border-hairline px-3 py-1 font-mono text-[11px] uppercase tracking-overline text-ink2 disabled:opacity-40"
              >
                Cache token
              </button>
            </div>
          )}
        </Section>

        {connected && (
          <div className="mt-3 border-t border-hairline pt-2 font-sans text-[11px] text-bull">
            Fyers connected. Sector strength (MARS) will use live index data on the next pipeline run.
          </div>
        )}
      </div>
    </div>
  );
}

function statusWord(s) {
  if (s.status === "missing_app_id") return "Enter your app credentials to start";
  if (s.status === "missing_token") return "Credentials saved — log in to get today's token";
  return "Not connected";
}

function Section({ n, title, done, disabled, children }) {
  return (
    <div className={"mb-3 " + (disabled ? "opacity-50" : "")}>
      <div className="mb-1.5 flex items-center gap-2">
        <span
          className={
            "flex h-4 w-4 items-center justify-center rounded-full font-mono text-[9px] " +
            (done ? "bg-bull text-white" : "bg-muted-bg text-ink2")
          }
        >
          {done ? "✓" : n}
        </span>
        <span className="font-mono text-[11px] font-bold uppercase tracking-overline text-ink">
          {title}
        </span>
      </div>
      <div className={disabled ? "pointer-events-none" : ""}>{children}</div>
    </div>
  );
}

function Field({ label, value, onChange, placeholder, type = "text" }) {
  return (
    <label className="mb-2 block">
      <span className="mb-0.5 block font-mono text-[9px] uppercase tracking-overline text-ink3">
        {label}
      </span>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="w-full border border-hairline bg-raised px-2 py-1 font-mono text-[11px] text-ink outline-none focus:border-info"
      />
    </label>
  );
}
