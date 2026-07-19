"""Fyers API v3 provider: live quotes (batch <=50) + daily history.

Token comes from env FYERS_TOKEN, an explicit constructor arg, or the daily
token cache in manas_os.providers.fyers_auth. Degrades gracefully
(is_available() -> False) if fyers-apiv3 is not installed or no token/app id
is configured.

Adopted from legacy ssrvol/providers/fyers_provider.py (copied + rewired to
manas_os). Added `from_config(cfg)` to construct from the config `fyers:` dict.
"""
from __future__ import annotations

import logging
from typing import Optional

from manas_os.providers import fyers_auth
from manas_os.providers.base import DailyBar, MarketDataProvider, SnapshotRow

logger = logging.getLogger("manas_os.providers.fyers")

BATCH_SIZE = 50


def fyers_symbol(sym: str) -> str:
    """Normalize a bare symbol to Fyers form. Leaves qualified symbols alone.

    - RELIANCE              → NSE:RELIANCE-EQ
    - _NIFTY50 / _INDIAVIX  → NSE:NIFTY50-INDEX / NSE:INDIAVIX-INDEX (legacy aliases)
    - NIFTY AUTO / NIFTY IT / NIFTYMIDSML400 / NIFTY 500 → NSE:<NAME>-INDEX
      (any name starting with NIFTY is an index: sectors + benchmarks)
    """
    if ":" in sym:
        return sym
    if sym == "_NIFTY50":
        return "NSE:NIFTY50-INDEX"
    if sym == "_INDIAVIX":
        return "NSE:INDIAVIX-INDEX"
    bare = sym.strip().upper()
    if bare.startswith("NIFTY") or bare in {"INDIA VIX", "INDIAVIX"}:
        # Indices have spaces preserved (NIFTY AUTO) → Fyers wants them as-is.
        return f"NSE:{bare}-INDEX"
    return f"NSE:{bare}-EQ"


def _bare_symbol(fy_sym: str) -> str:
    s = fy_sym.split(":")[-1]
    if s.endswith("-EQ"):
        s = s[:-3]
    return s


class FyersProvider(MarketDataProvider):
    name = "fyers"

    def __init__(self, client_id: Optional[str] = None, token: Optional[str] = None):
        self.client_id = client_id or fyers_auth.app_id()
        self.token = token or fyers_auth.get_access_token()
        self._fyers_model = None
        self._client = None

    @classmethod
    def from_config(cls, cfg: Optional[dict] = None) -> "FyersProvider":
        """Construct from the config `fyers:` dict (see config.example.yaml).

        Only client_id is read here; the access token is resolved at call time
        from env/cache via fyers_auth so a stale config never pins a dead token.
        """
        fy = (cfg or {}).get("fyers", {}) if cfg else {}
        return cls(client_id=fy.get("client_id") or None)

    def refresh_credentials(self) -> None:
        self.client_id = fyers_auth.app_id()
        self.token = fyers_auth.get_access_token()
        self._client = None

    def _get_module(self):
        if self._fyers_model is None:
            from fyers_apiv3 import fyersModel  # type: ignore
            self._fyers_model = fyersModel
        return self._fyers_model

    def is_available(self) -> bool:
        """True only when credentials exist and the token probes as valid.

        Presence of a cached/env token alone is not enough (Fyers daily tokens
        expire at 06:00 IST and may already be dead).
        """
        try:
            status = fyers_auth.token_status()
        except Exception:
            return False
        if not status.get("app_id_set") or not status.get("token_valid"):
            # Keep local fields in sync for subsequent data calls.
            self.refresh_credentials()
            return False
        try:
            self._get_module()
        except Exception:
            return False
        if not self.client_id or not self.token:
            self.refresh_credentials()
        return bool(self.client_id and self.token)

    def _get_client(self):
        if self._client is None:
            fyersModel = self._get_module()
            self._client = fyersModel.FyersModel(
                client_id=self.client_id, token=self.token, is_async=False, log_path=""
            )
        return self._client

    def get_snapshot(self, symbols: list[str], lookback: int = 20) -> list[SnapshotRow]:
        if not symbols:
            return []
        if not self.is_available():
            return [SnapshotRow(symbol=s, ok=False, error="fyers token required") for s in symbols]

        client = self._get_client()
        fy_symbols = [fyers_symbol(s) for s in symbols]
        rows: list[SnapshotRow] = []

        for i in range(0, len(fy_symbols), BATCH_SIZE):
            batch = fy_symbols[i:i + BATCH_SIZE]
            try:
                resp = client.quotes({"symbols": ",".join(batch)})
            except Exception as e:
                logger.warning("Fyers quotes batch failed: %s", e)
                rows.extend(SnapshotRow(symbol=_bare_symbol(s), ok=False, error=str(e)) for s in batch)
                continue

            if not isinstance(resp, dict) or resp.get("s") != "ok":
                err = resp.get("message", "unknown error") if isinstance(resp, dict) else "bad response"
                rows.extend(SnapshotRow(symbol=_bare_symbol(s), ok=False, error=err) for s in batch)
                continue

            by_symbol = {}
            for item in resp.get("d", []):
                sym = item.get("n") or item.get("symbol")
                by_symbol[sym] = item

            for fy_sym in batch:
                bare = _bare_symbol(fy_sym)
                item = by_symbol.get(fy_sym)
                if not item or item.get("s") != "ok":
                    rows.append(SnapshotRow(symbol=bare, ok=False, error="not found"))
                    continue
                v = item.get("v", {})
                try:
                    # Universe-wide live refreshes are quote-only. Avoid one
                    # history request per symbol when no baseline is requested.
                    avg_vol_n = self._compute_avg_vol(client, fy_sym, lookback) if lookback > 0 else None
                    rows.append(SnapshotRow(
                        symbol=bare,
                        last=v.get("lp"),
                        today_open=v.get("open_price"),
                        today_low=v.get("low_price"),
                        today_high=v.get("high_price"),
                        today_volume=v.get("volume"),
                        prev_close=v.get("prev_close_price"),
                        avg_vol_n=avg_vol_n,
                        ok=True,
                    ))
                except Exception as e:
                    logger.warning("Fyers normalize failed for %s: %s", fy_sym, e)
                    rows.append(SnapshotRow(symbol=bare, ok=False, error=str(e)))
        return rows

    def _compute_avg_vol(self, client, fy_sym: str, lookback: int) -> Optional[float]:
        bars = self._history(client, fy_sym, lookback_days=lookback + 10)
        if len(bars) < 2:
            return None
        prior = bars[-(lookback + 1):-1] if len(bars) > lookback else bars[:-1]
        vols = [b.volume for b in prior]
        return sum(vols) / len(vols) if vols else None

    def _history(self, client, fy_sym: str, lookback_days: int) -> list[DailyBar]:
        import time
        end = int(time.time())
        start = end - lookback_days * 86400 * 2  # generous window incl. weekends/holidays
        try:
            resp = client.history({
                "symbol": fy_sym, "resolution": "D", "date_format": "0",
                "range_from": str(start), "range_to": str(end), "cont_flag": "1",
            })
        except Exception as e:
            logger.warning("Fyers history failed for %s: %s", fy_sym, e)
            return []
        if not isinstance(resp, dict) or resp.get("s") != "ok":
            return []
        bars = []
        for c in resp.get("candles", []):
            try:
                ts, o, h, low_, cl, v = c
                import datetime as _dt
                d = _dt.datetime.fromtimestamp(ts, _dt.UTC).strftime("%Y-%m-%d")
                bars.append(DailyBar(date=d, open=o, high=h, low=low_, close=cl, volume=v))
            except Exception:
                continue
        return bars

    def get_daily_history(self, symbol: str, lookback_days: int = 60) -> list[DailyBar]:
        if not self.is_available():
            return []
        client = self._get_client()
        return self._history(client, fyers_symbol(symbol), lookback_days)

    def get_index_history(self, symbol: str, lookback_days: int = 80) -> list[DailyBar]:
        """Daily history for an index (sector index or benchmark).

        Same path as get_daily_history but with a longer default lookback (80
        sessions gives a stable SMA50 with margin) — indices have no delivery,
        so callers only consume closes. Returns [] if unavailable.
        """
        return self.get_daily_history(symbol, lookback_days=lookback_days)
