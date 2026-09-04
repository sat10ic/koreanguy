"""Fyers auth/token helper.

Non-interactive by design: reads FYERS_TOKEN from the environment or a cached
token file. Run this module directly when a new daily token is needed.

Adopted from legacy ssrvol/fyers_auth.py (copied + rewired to manas_os). Config
is resolved from manas_os/config.yaml (fyers: section) instead of the legacy
project root.

Token readiness is truthful: Fyers sessions expire at the next 06:00 IST after
obtain time (not a generic 18h TTL). An env token without obtained_at is treated
as age-unverified (not fresh). token_status() probes the API (cached ~5 min).
"""
from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional
from urllib.parse import parse_qs, urlparse
from zoneinfo import ZoneInfo

REDIRECT_URI = "https://trade.fyers.in/api-login/redirect-uri/index.html"
# manas_os package root (…/manas_os) — config.yaml + data/ live here.
ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TOKEN_PATH = ROOT / "data" / ".fyers_token.json"

IST = ZoneInfo("Asia/Kolkata")
# Grace seconds before computed expiry when treating a token as stale.
_EXPIRY_GRACE_S = 60
# Probe result cache window — avoid hammering Fyers on every status poll.
PROBE_CACHE_TTL_S = 300
_PROBE_TIMEOUT_S = 5.0

logger = logging.getLogger("manas_os.providers.fyers_auth")

# In-process probe cache: {token_fingerprint: {valid, error, checked_at}}
_probe_cache: dict[str, dict[str, Any]] = {}


def _now_ts() -> float:
    """Single injectable clock for this module (epoch seconds).

    Every function below that needs 'now' must go through this (directly, or
    via an explicit `now` parameter that defaults to it) -- never a bare
    time.time()/datetime.now() call -- so tests can make expiry/freshness
    checks deterministic by monkeypatching this one function instead of
    depending on the real wall clock.
    """
    return time.time()


class TokenStatus(dict):
    """Dict status with str-compat for legacy callers that compare to 'ready'."""

    def __eq__(self, other: object) -> bool:
        if isinstance(other, str):
            return self.get("status") == other
        return super().__eq__(other)

    def __ne__(self, other: object) -> bool:
        return not self.__eq__(other)

    def __str__(self) -> str:
        return str(self.get("status") or self.get("action") or "unknown")

    def __repr__(self) -> str:
        return f"TokenStatus({dict.__repr__(self)})"


def _load_env_file() -> None:
    """Best-effort .env loader without adding a runtime dependency."""
    env_path = ROOT / ".env"
    if not env_path.exists():
        return
    try:
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
    except Exception:
        return


def _config_fyers_value(key: str) -> Optional[str]:
    try:
        import yaml  # type: ignore

        cfg_path = ROOT / "config.yaml"
        if not cfg_path.exists():
            return None
        data = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
        value = (data.get("fyers", {}) or {}).get(key)
        return str(value) if value else None
    except Exception:
        return None


def _token_path() -> Path:
    """Token cache location — config fyers.token_path (relative to ROOT) or default."""
    configured = _config_fyers_value("token_path")
    if configured:
        p = Path(configured)
        return p if p.is_absolute() else ROOT / p
    return DEFAULT_TOKEN_PATH


def app_id() -> Optional[str]:
    _load_env_file()
    return (
        os.environ.get("FYERS_APP_ID")
        or os.environ.get("FYERS_CLIENT_ID")
        or _config_fyers_value("client_id")
    )


def secret_key() -> Optional[str]:
    _load_env_file()
    return (
        os.environ.get("FYERS_SECRET_KEY")
        or os.environ.get("FYERS_SECRET_ID")
        or _config_fyers_value("secret_id")
    )


def redirect_uri() -> str:
    _load_env_file()
    return (
        os.environ.get("FYERS_REDIRECT_URI")
        or _config_fyers_value("redirect_uri")
        or REDIRECT_URI
    )


def _load_cached() -> dict | None:
    path = _token_path()
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _save_cached(payload: dict) -> None:
    path = _token_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def next_0600_ist_after(obtained_at: datetime) -> datetime:
    """Return the next 06:00 Asia/Kolkata strictly after *obtained_at*.

    Fyers daily access tokens expire at the following 06:00 IST session boundary.
    """
    if obtained_at.tzinfo is None:
        obtained_at = obtained_at.replace(tzinfo=timezone.utc)
    local = obtained_at.astimezone(IST)
    candidate = local.replace(hour=6, minute=0, second=0, microsecond=0)
    if local >= candidate:
        candidate = candidate + timedelta(days=1)
    return candidate


def _parse_obtained_at(payload: dict | None) -> Optional[datetime]:
    if not payload:
        return None
    raw = payload.get("obtained_at")
    if not raw:
        return None
    try:
        if isinstance(raw, (int, float)):
            return datetime.fromtimestamp(float(raw), tz=timezone.utc)
        text = str(raw).strip()
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        dt = datetime.fromisoformat(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def _expires_at_unix(obtained_at: Optional[datetime]) -> Optional[float]:
    if obtained_at is None:
        return None
    return next_0600_ist_after(obtained_at).timestamp()


def _is_expired(
    obtained_at: Optional[datetime],
    *,
    now: Optional[float] = None,
    expires_at: Optional[float] = None,
) -> bool:
    """True when age is unknown (unverified) or past next 06:00 IST expiry."""
    if obtained_at is None and expires_at is None:
        # Unverified age — not treated as fresh.
        return True
    exp = expires_at if expires_at is not None else _expires_at_unix(obtained_at)
    if exp is None:
        return True
    t = _now_ts() if now is None else float(now)
    return t >= float(exp) - _EXPIRY_GRACE_S


def _is_fresh(payload: dict, *, now: Optional[float] = None) -> bool:
    """Cache freshness: requires obtained_at (or legacy expires_at) and not past boundary."""
    obtained = _parse_obtained_at(payload)
    legacy_exp = payload.get("expires_at")
    if obtained is not None:
        return not _is_expired(obtained, now=now)
    if legacy_exp is not None:
        # Legacy cache without obtained_at: honour stored expires_at only if still future,
        # but do not invent freshness — treat missing obtained_at as unverified once past.
        try:
            t = _now_ts() if now is None else float(now)
            return t < float(legacy_exp) - _EXPIRY_GRACE_S
        except (TypeError, ValueError):
            return False
    return False


def _resolve_token_material(*, now: Optional[float] = None) -> dict[str, Any]:
    """Resolve raw token + age metadata without claiming readiness.

    Env FYERS_TOKEN is accepted as material but does not bypass freshness:
    without obtained_at (from matching cache) age is unverified / expired.

    *now* (epoch seconds) overrides the module clock (_now_ts()) for the
    expiry check — callers pass it through from token_status()/get_access_token()
    so a frozen test clock reaches every expiry decision, not just the probe.
    """
    _load_env_file()
    env_token = (os.environ.get("FYERS_TOKEN") or "").strip() or None
    cached = _load_cached() or {}
    cached_token = (cached.get("access_token") or "").strip() or None

    token: Optional[str] = None
    obtained_at: Optional[datetime] = None
    source: Optional[str] = None

    if env_token:
        token = env_token
        source = "env"
        # Attach cache metadata only when it describes the same token.
        if cached_token and cached_token == env_token:
            obtained_at = _parse_obtained_at(cached)
        # else: env-only / mismatched cache → age unknown
    elif cached_token:
        token = cached_token
        source = "cache"
        obtained_at = _parse_obtained_at(cached)

    expires_at = _expires_at_unix(obtained_at)
    # Prefer recomputed IST expiry; fall back to legacy expires_at only when no obtained_at.
    if expires_at is None and cached.get("expires_at") is not None and token == cached_token:
        try:
            expires_at = float(cached["expires_at"])
        except (TypeError, ValueError):
            expires_at = None

    expired = _is_expired(obtained_at, now=now, expires_at=expires_at)
    return {
        "access_token": token,
        "obtained_at": obtained_at,
        "expires_at": expires_at,
        "expired": expired,
        "source": source,
    }


def get_access_token(*, now: Optional[float] = None) -> Optional[str]:
    """Return a non-expired access token. Never prompts and never raises.

    Known-expired tokens are withheld. Age-unverified env tokens are returned
    as material (caller must use token_status() for readiness, not presence).

    *now* overrides the module clock (_now_ts()) for the expiry check --
    normal callers omit it and get the real clock.
    """
    info = _resolve_token_material(now=now)
    token = info.get("access_token")
    if not token:
        return None
    obtained = info.get("obtained_at")
    # Known age and past 06:00 IST → do not hand out a dead token.
    if obtained is not None and info.get("expired"):
        return None
    # Unverified age (expired=True, obtained_at=None): still return material so
    # probes and providers can attempt use; readiness stays false until verified.
    return token


def has_cached_token() -> bool:
    cached = _load_cached()
    return bool(cached and cached.get("access_token"))


def cache_access_token(token: str, ttl_hours: float = 18.0) -> None:
    """Cache a manually supplied token with Fyers daily (06:00 IST) expiry.

    *ttl_hours* is retained for call-site compatibility but is not used for
    expiry — Fyers sessions end at the next 06:00 IST after obtain time.
    """
    del ttl_hours  # explicit: daily IST boundary replaces generic TTL
    token = (token or "").strip()
    if not token:
        raise ValueError("Fyers token is required.")

    obtained_at = datetime.fromtimestamp(_now_ts(), tz=timezone.utc)
    expires_at = next_0600_ist_after(obtained_at).timestamp()
    _save_cached({
        "access_token": token,
        "expires_at": expires_at,
        "obtained_at": obtained_at.isoformat(),
        "redirect_uri": redirect_uri(),
    })
    os.environ["FYERS_TOKEN"] = token
    # New token invalidates prior probe results.
    _probe_cache.clear()


def clear_probe_cache() -> None:
    """Test helper: drop cached probe results."""
    _probe_cache.clear()


def _token_fingerprint(token: str) -> str:
    # Avoid storing full token as cache key in logs; short fingerprint is enough.
    return f"{len(token)}:{token[:8]}:{token[-4:]}" if len(token) >= 12 else token


def _probe_token_uncached(token: str, client_id: str) -> tuple[bool, Optional[str]]:
    """Live Fyers probe — single harmless quotes request with a short timeout.

    Separated so tests can monkeypatch this without standing up the SDK.
    """
    try:
        from fyers_apiv3 import fyersModel  # type: ignore
    except Exception as exc:  # pragma: no cover - import env
        return False, f"fyers-apiv3 not installed: {exc}"

    try:
        client = fyersModel.FyersModel(
            client_id=client_id,
            token=token,
            is_async=False,
            log_path="",
        )
        # One liquid index quote — read-only, no order side effects.
        # Prefer get_profile when available (lighter); fall back to quotes.
        resp = None
        if hasattr(client, "get_profile"):
            try:
                resp = client.get_profile()
            except Exception:
                resp = None
        if resp is None:
            resp = client.quotes({"symbols": "NSE:NIFTY50-INDEX"})
        if not isinstance(resp, dict):
            return False, "bad probe response"
        # Fyers success markers vary slightly across endpoints.
        code = resp.get("s") or resp.get("code")
        if code in ("ok", "OK", 200, "200") or resp.get("data") is not None:
            # Reject explicit error bodies even when a data key is present.
            if str(resp.get("s", "")).lower() == "error":
                return False, str(resp.get("message") or resp.get("errmsg") or "probe error")
            return True, None
        if str(resp.get("s", "")).lower() == "error" or resp.get("code") not in (None, 200, "200"):
            return False, str(resp.get("message") or resp.get("errmsg") or resp)
        return False, str(resp.get("message") or "probe failed")
    except Exception as exc:
        return False, str(exc)


def probe_token(
    token: Optional[str] = None,
    client_id: Optional[str] = None,
    *,
    now: Optional[float] = None,
    force: bool = False,
) -> tuple[bool, Optional[str]]:
    """Probe token validity; results cached for PROBE_CACHE_TTL_S (~5 min)."""
    token = (token or "").strip() or None
    client_id = (client_id or app_id() or "").strip() or None
    if not token or not client_id:
        return False, "missing token or app id"

    t = _now_ts() if now is None else float(now)
    key = _token_fingerprint(token)
    if not force:
        hit = _probe_cache.get(key)
        if hit and (t - float(hit.get("checked_at", 0))) < PROBE_CACHE_TTL_S:
            return bool(hit.get("valid")), hit.get("error")

    valid, error = _probe_token_uncached(token, client_id)
    _probe_cache[key] = {"valid": valid, "error": error, "checked_at": t}
    return valid, error


def token_status(*, now: Optional[float] = None, force_probe: bool = False) -> TokenStatus:
    """Truthful Fyers readiness — presence alone is never enough.

    Returns a dict-shaped TokenStatus with:
      app_id_set, secret_set, token_present, token_valid, expired,
      expires_at, action, token_ready, probe_error (optional), status (legacy str)
    """
    aid = app_id()
    secret = secret_key()
    app_id_set = bool(aid)
    secret_set = bool(secret)

    info = _resolve_token_material(now=now)
    token = info.get("access_token")
    token_present = bool(token)
    expired = bool(info.get("expired")) if token_present else False
    expires_at = info.get("expires_at")

    probe_error: Optional[str] = None
    token_valid = False

    if token_present and app_id_set:
        token_valid, probe_error = probe_token(
            token, aid, now=now, force=force_probe
        )
    elif not token_present:
        probe_error = None
    elif not app_id_set:
        probe_error = "missing app id"

    token_ready = bool(token_present and token_valid and not expired)

    if not app_id_set:
        action = "Set FYERS_APP_ID (and secret) then paste today's token"
        legacy = "missing_app_id"
    elif not token_present:
        action = "Fyers token missing — paste today's token"
        legacy = "missing_token"
    elif expired and not token_valid:
        action = "Fyers token expired — paste today's token"
        legacy = "expired"
    elif expired and token_valid:
        # Probe ok but age unverified/expired — still not "ready" for daily boundary.
        action = "Fyers token age unverified or past 06:00 IST — paste today's token"
        legacy = "expired"
    elif not token_valid:
        action = "Fyers token invalid — paste today's token"
        legacy = "invalid"
    else:
        action = "ready"
        legacy = "ready"

    out = TokenStatus(
        app_id_set=app_id_set,
        secret_set=secret_set,
        token_present=token_present,
        token_valid=token_valid,
        expired=expired,
        expires_at=expires_at,
        action=action,
        token_ready=token_ready,
        status=legacy,
    )
    if probe_error:
        out["probe_error"] = probe_error
    if info.get("obtained_at") is not None:
        out["obtained_at"] = info["obtained_at"].isoformat()
    return out


def extract_auth_code(value: str) -> str:
    raw = (value or "").strip()
    if not raw:
        return ""
    if "auth_code=" not in raw:
        return raw
    try:
        parsed = urlparse(raw)
        return (parse_qs(parsed.query).get("auth_code") or [""])[0].strip()
    except Exception:
        return raw


def _new_session_model():
    aid = app_id()
    secret = secret_key()
    redir = redirect_uri()
    if not aid or not secret:
        raise RuntimeError("Set FYERS_APP_ID and FYERS_SECRET_KEY before running Fyers login.")

    from fyers_apiv3 import fyersModel  # type: ignore

    session = fyersModel.SessionModel(
        client_id=aid,
        secret_key=secret,
        redirect_uri=redir,
        response_type="code",
        grant_type="authorization_code",
    )
    return session


def generate_auth_url() -> str:
    return _new_session_model().generate_authcode()


def exchange_auth_code(value: str) -> str:
    auth_code = extract_auth_code(value)
    if not auth_code:
        raise RuntimeError("No auth_code entered.")

    session = _new_session_model()
    session.set_token(auth_code)
    resp = session.generate_token()
    if not resp or "access_token" not in resp:
        raise RuntimeError(f"Fyers token exchange failed: {resp}")

    token = resp["access_token"]
    cache_access_token(token)
    return token


def interactive_login() -> str:
    """Prompt for an auth code and cache the resulting token."""
    auth_url = generate_auth_url()
    print("\nFYERS LOGIN")
    print("=" * 70)
    print("Open this URL, log in, then paste the auth_code or full redirect URL:\n")
    print(auth_url)
    print()
    token = exchange_auth_code(input("auth_code or redirect URL> ").strip())
    cached = _load_cached() or {}
    exp = cached.get("expires_at")
    print(f"\nToken cached at {_token_path()}")
    if exp:
        print(f"Expires at {datetime.fromtimestamp(float(exp), tz=IST).isoformat()} (06:00 IST boundary)")
    print(f"FYERS_TOKEN={token}")
    return token


def main() -> int:
    interactive_login()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
