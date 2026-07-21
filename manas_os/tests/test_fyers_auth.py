"""Tests for truthful Fyers token readiness (reliability defect #5).

All network probes are mocked — never hit the real Fyers API.
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from manas_os.providers import fyers_auth
from manas_os.providers.fyers import FyersProvider

IST = ZoneInfo("Asia/Kolkata")


@pytest.fixture(autouse=True)
def _isolate_token_state(monkeypatch, tmp_path):
    """Each test gets a private token cache and a clean env/probe cache."""
    token_path = tmp_path / ".fyers_token.json"
    monkeypatch.setattr(fyers_auth, "_token_path", lambda: token_path)
    monkeypatch.delenv("FYERS_TOKEN", raising=False)
    monkeypatch.delenv("FYERS_APP_ID", raising=False)
    monkeypatch.delenv("FYERS_CLIENT_ID", raising=False)
    monkeypatch.delenv("FYERS_SECRET_KEY", raising=False)
    monkeypatch.delenv("FYERS_SECRET_ID", raising=False)
    # Avoid reading real config.yaml credentials.
    monkeypatch.setattr(fyers_auth, "_config_fyers_value", lambda key: None)
    monkeypatch.setattr(fyers_auth, "_load_env_file", lambda: None)
    fyers_auth.clear_probe_cache()
    yield
    fyers_auth.clear_probe_cache()


def _set_creds(monkeypatch, *, app_id="APP.ID", secret="SECRET"):
    monkeypatch.setenv("FYERS_APP_ID", app_id)
    monkeypatch.setenv("FYERS_SECRET_KEY", secret)


def _write_cache(token: str, obtained_at: datetime, token_path: Path | None = None):
    path = token_path or fyers_auth._token_path()
    expires_at = fyers_auth.next_0600_ist_after(obtained_at).timestamp()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({
            "access_token": token,
            "obtained_at": obtained_at.isoformat(),
            "expires_at": expires_at,
        }),
        encoding="utf-8",
    )


def test_next_0600_ist_after_same_day_before_boundary():
    # 05:00 IST on 19 Jul → next boundary is 06:00 IST same day.
    obtained = datetime(2026, 7, 19, 5, 0, tzinfo=IST)
    exp = fyers_auth.next_0600_ist_after(obtained)
    assert exp == datetime(2026, 7, 19, 6, 0, tzinfo=IST)


def test_next_0600_ist_after_rolls_to_tomorrow():
    obtained = datetime(2026, 7, 19, 10, 30, tzinfo=IST)
    exp = fyers_auth.next_0600_ist_after(obtained)
    assert exp == datetime(2026, 7, 20, 6, 0, tzinfo=IST)


def test_fresh_valid_token(monkeypatch):
    _set_creds(monkeypatch)
    # Obtained this morning after 06:00 IST → expires tomorrow 06:00.
    obtained = datetime(2026, 7, 19, 8, 0, tzinfo=IST)
    _write_cache("fresh-token-abcdef", obtained)

    def _probe(token, client_id):
        assert token == "fresh-token-abcdef"
        assert client_id == "APP.ID"
        return True, None

    monkeypatch.setattr(fyers_auth, "_probe_token_uncached", _probe)

    # Freeze the module clock at same-session afternoon (before next 06:00),
    # so every expiry check downstream -- token_status() AND the later bare
    # get_access_token() call -- sees the same frozen "now", regardless of
    # the real wall-clock time the suite happens to run at.
    frozen_now = datetime(2026, 7, 19, 15, 0, tzinfo=IST).timestamp()
    monkeypatch.setattr(fyers_auth, "_now_ts", lambda: frozen_now)
    st = fyers_auth.token_status()

    assert st["app_id_set"] is True
    assert st["secret_set"] is True
    assert st["token_present"] is True
    assert st["token_valid"] is True
    assert st["expired"] is False
    assert st["token_ready"] is True
    assert st["status"] == "ready"
    assert st["action"] == "ready"
    assert st == "ready"  # str-compat
    assert "probe_error" not in st
    assert fyers_auth.get_access_token() == "fresh-token-abcdef"


def test_present_but_expired_past_0600_ist(monkeypatch):
    _set_creds(monkeypatch)
    # Obtained yesterday morning; next 06:00 IST has already passed.
    obtained = datetime(2026, 7, 18, 9, 0, tzinfo=IST)
    _write_cache("stale-token-zzzzzzzz", obtained)

    monkeypatch.setattr(
        fyers_auth, "_probe_token_uncached", lambda *a, **k: (False, "token expired")
    )

    # Now: day after obtain, past 06:00 IST.
    now = datetime(2026, 7, 19, 10, 0, tzinfo=IST).timestamp()
    st = fyers_auth.token_status(now=now)

    assert st["token_present"] is True
    assert st["expired"] is True
    assert st["token_valid"] is False
    assert st["token_ready"] is False
    assert st["status"] == "expired"
    assert "paste today's token" in st["action"].lower()
    assert st.get("probe_error") == "token expired"
    # Known-expired material is withheld from get_access_token.
    assert fyers_auth.get_access_token() is None


def test_probe_fails(monkeypatch):
    _set_creds(monkeypatch)
    obtained = datetime(2026, 7, 19, 8, 0, tzinfo=IST)
    _write_cache("bad-token-xxxxxxxx", obtained)
    monkeypatch.setattr(
        fyers_auth,
        "_probe_token_uncached",
        lambda *a, **k: (False, "invalid auth code"),
    )

    # Freeze the module clock (same session, before next 06:00 IST expiry)
    # so "expired" reflects the token's actual age, not real wall-clock time.
    frozen_now = datetime(2026, 7, 19, 12, 0, tzinfo=IST).timestamp()
    monkeypatch.setattr(fyers_auth, "_now_ts", lambda: frozen_now)
    st = fyers_auth.token_status()

    assert st["token_present"] is True
    assert st["expired"] is False
    assert st["token_valid"] is False
    assert st["token_ready"] is False
    assert st["probe_error"] == "invalid auth code"
    assert st["status"] == "invalid"


def test_env_token_unknown_age_not_fresh(monkeypatch):
    """Env token without obtained_at is age-unverified — not token_ready."""
    _set_creds(monkeypatch)
    monkeypatch.setenv("FYERS_TOKEN", "env-only-token-xyz")

    monkeypatch.setattr(
        fyers_auth, "_probe_token_uncached", lambda *a, **k: (True, None)
    )

    st = fyers_auth.token_status()
    assert st["token_present"] is True
    assert st["expired"] is True  # unverified age
    assert st["token_valid"] is True  # probe ok
    assert st["token_ready"] is False  # readiness requires not expired
    assert st["status"] == "expired"
    assert st["expires_at"] is None
    # Material still available for provider/probe use.
    assert fyers_auth.get_access_token() == "env-only-token-xyz"


def test_probe_cache_window_respected(monkeypatch):
    _set_creds(monkeypatch)
    obtained = datetime(2026, 7, 19, 8, 0, tzinfo=IST)
    _write_cache("cached-probe-token-1", obtained)

    calls = {"n": 0}

    def _probe(token, client_id):
        calls["n"] += 1
        return True, None

    monkeypatch.setattr(fyers_auth, "_probe_token_uncached", _probe)
    t0 = datetime(2026, 7, 19, 12, 0, tzinfo=IST).timestamp()

    st1 = fyers_auth.token_status(now=t0)
    st2 = fyers_auth.token_status(now=t0 + 60)  # within 5 min
    assert st1["token_valid"] is True
    assert st2["token_valid"] is True
    assert calls["n"] == 1

    # After TTL, probe runs again.
    st3 = fyers_auth.token_status(now=t0 + fyers_auth.PROBE_CACHE_TTL_S + 1)
    assert st3["token_valid"] is True
    assert calls["n"] == 2


def test_cache_access_token_persists_obtained_at_and_ist_expiry(monkeypatch, tmp_path):
    _set_creds(monkeypatch)
    before = datetime.now(timezone.utc)
    fyers_auth.cache_access_token("manual-token-12345678")
    after = datetime.now(timezone.utc)

    raw = json.loads(fyers_auth._token_path().read_text(encoding="utf-8"))
    assert raw["access_token"] == "manual-token-12345678"
    assert "obtained_at" in raw
    obtained = datetime.fromisoformat(raw["obtained_at"])
    assert before - timedelta(seconds=2) <= obtained <= after + timedelta(seconds=2)
    expected_exp = fyers_auth.next_0600_ist_after(obtained).timestamp()
    assert abs(float(raw["expires_at"]) - expected_exp) < 1.0


def test_is_available_requires_token_valid(monkeypatch):
    _set_creds(monkeypatch)
    obtained = datetime(2026, 7, 19, 8, 0, tzinfo=IST)
    _write_cache("tok-for-provider-xx", obtained)
    monkeypatch.setattr(
        fyers_auth, "_probe_token_uncached", lambda *a, **k: (False, "nope")
    )
    # Avoid importing real fyers SDK for module check path after refresh.
    provider = FyersProvider(client_id="APP.ID", token="tok-for-provider-xx")
    monkeypatch.setattr(provider, "_get_module", lambda: object())
    assert provider.is_available() is False

    fyers_auth.clear_probe_cache()
    monkeypatch.setattr(
        fyers_auth, "_probe_token_uncached", lambda *a, **k: (True, None)
    )
    provider2 = FyersProvider(client_id="APP.ID", token="tok-for-provider-xx")
    monkeypatch.setattr(provider2, "_get_module", lambda: object())
    assert provider2.is_available() is True


def test_token_status_missing_app_id(monkeypatch):
    monkeypatch.setenv("FYERS_TOKEN", "orphan-token")
    monkeypatch.setattr(
        fyers_auth, "_probe_token_uncached", lambda *a, **k: (True, None)
    )
    st = fyers_auth.token_status()
    assert st["app_id_set"] is False
    assert st["token_ready"] is False
    assert st["status"] == "missing_app_id"
    assert st == "missing_app_id"
