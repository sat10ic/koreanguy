"""Fyers auth/token helper.

Non-interactive by design: reads FYERS_TOKEN from the environment or a cached
token file. Run this module directly when a new daily token is needed.

Adopted from legacy ssrvol/fyers_auth.py (copied + rewired to manas_os). Config
is resolved from manas_os/config.yaml (fyers: section) instead of the legacy
project root.
"""
from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from urllib.parse import parse_qs, urlparse

REDIRECT_URI = "https://trade.fyers.in/api-login/redirect-uri/index.html"
# manas_os package root (…/manas_os) — config.yaml + data/ live here.
ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TOKEN_PATH = ROOT / "data" / ".fyers_token.json"


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


def _is_fresh(payload: dict) -> bool:
    exp = payload.get("expires_at")
    return bool(exp and time.time() < float(exp) - 60)


def get_access_token() -> Optional[str]:
    """Return an env or cached token. Never prompts and never raises."""
    _load_env_file()
    token = os.environ.get("FYERS_TOKEN")
    if token:
        return token
    cached = _load_cached()
    if cached and _is_fresh(cached):
        return cached.get("access_token")
    return None


def has_cached_token() -> bool:
    cached = _load_cached()
    return bool(cached and cached.get("access_token"))


def cache_access_token(token: str, ttl_hours: float = 18.0) -> None:
    """Cache a manually supplied token and make it active for this process."""
    token = (token or "").strip()
    if not token:
        raise ValueError("Fyers token is required.")

    expires_at = time.time() + float(ttl_hours) * 3600
    _save_cached({
        "access_token": token,
        "expires_at": expires_at,
        "obtained_at": datetime.now(timezone.utc).isoformat(),
        "redirect_uri": redirect_uri(),
    })
    os.environ["FYERS_TOKEN"] = token


def token_status() -> str:
    aid = app_id()
    token = get_access_token()
    if aid and token:
        return "ready"
    if not aid:
        return "missing_app_id"
    return "missing_token"


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
    expires_at = time.time() + 18 * 3600
    print(f"\nToken cached at {_token_path()}")
    print(f"Expires around {datetime.fromtimestamp(expires_at)}")
    print(f"FYERS_TOKEN={token}")
    return token


def main() -> int:
    interactive_login()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
