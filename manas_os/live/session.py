"""Fyers WebSocket session manager -- connect/reconnect/dedupe, token-expiry
handling, market-hours gate. This is the "genuinely new" piece per
manas_os/design/FYERS_LIVE_LOOP_PLAN.md §3: ssrvol has REST-polling and OAuth,
but no streaming client anywhere. Built fresh against fyers_apiv3's
FyersWebsocket.data_ws.FyersDataSocket (confirmed present in the installed
fyers-apiv3 package: `from fyers_apiv3.FyersWebsocket import data_ws`).

Design intent: this module and manas_os/live/replay.py drive the *same*
alerts.live_fsm.on_tick() -- the only difference is where ticks come from (a
live socket vs a fixture file). Nothing FSM-shaped lives in this file.

Untested against a live market by this change (no market hours / no
guaranteed live token during this session) -- structurally complete, but the
acceptance test for this module is `manas live-loop --paper` reporting an
honest "market closed" / "auth needed" state and shutting down clean, not a
live tick observed end-to-end. That remains for the Monday market-hours test
noted in the final report.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Optional

from manas_os import config, market_calendar
from manas_os.alerts import live_fsm
from manas_os.live import quotes
from manas_os.providers import fyers_auth
from manas_os.providers.fyers import fyers_symbol

logger = logging.getLogger("manas_os.live.session")

BAR_TS_FMT = "%Y-%m-%dT%H:%M:%S"

# Honest states -- silence is never allowed to look like "no coverage today"
# without one of these being logged (LIVE_LOOP_FABLE §3.4).
STATE_NOT_CONFIGURED = "not_configured"      # no fyers.client_id / app id
STATE_AUTH_NEEDED = "auth_needed"            # app id set, no valid cached token
STATE_MARKET_CLOSED = "market_closed"        # outside NSE hours or non-trading day
STATE_CONNECTING = "connecting"
STATE_CONNECTED = "connected"
STATE_DEGRADED = "degraded"                  # WS dropped / auth-closed mid-session


@dataclass
class TickerState:
    """Per-symbol running intraday state used to derive the confirmation
    predicates (OR-low/VWAP hold, gap-fill, projected RVOL) from raw ticks.
    Kept intentionally simple for Stage 1 -- this is analytics, not risk
    math; trigger/stop/qty never come from here."""
    day_open: Optional[float] = None
    prev_close: Optional[float] = None
    or_low: Optional[float] = None            # opening-range (first 15m) low
    or_start_ts: Optional[datetime] = None
    first_15m_complete: bool = False
    cum_volume: float = 0.0
    cum_pv: float = 0.0                        # price*volume accumulator for VWAP
    avg_vol_baseline: Optional[float] = None   # trailing avg daily volume (from history)
    last_ltp: Optional[float] = None

    def vwap(self) -> Optional[float]:
        return (self.cum_pv / self.cum_volume) if self.cum_volume else None

    def gap_fill_pct(self) -> Optional[float]:
        if self.day_open is None or self.prev_close is None or self.last_ltp is None:
            return None
        gap = self.day_open - self.prev_close
        if gap == 0:
            return 0.0
        filled = (self.day_open - self.last_ltp) / gap
        return max(0.0, min(1.0, filled)) if gap > 0 else max(0.0, min(1.0, -filled))

    def rvol_projected(self, elapsed_fraction_of_day: float) -> Optional[float]:
        if not self.avg_vol_baseline or elapsed_fraction_of_day <= 0:
            return None
        expected_by_now = self.avg_vol_baseline * elapsed_fraction_of_day
        if expected_by_now <= 0:
            return None
        return self.cum_volume / expected_by_now

    def update(self, ltp: float, volume_today: float, bar_ts: datetime) -> None:
        if self.day_open is None:
            self.day_open = ltp
        if self.or_start_ts is None:
            self.or_start_ts = bar_ts
        elapsed_min = (bar_ts - self.or_start_ts).total_seconds() / 60.0 if self.or_start_ts else 0
        if elapsed_min <= 15:
            self.or_low = ltp if self.or_low is None else min(self.or_low, ltp)
        else:
            self.first_15m_complete = True
        # volume_today is Fyers' cumulative-for-the-day counter; derive the
        # incremental slice for the VWAP accumulator.
        incremental = max(0.0, volume_today - self.cum_volume)
        self.cum_pv += ltp * incremental
        self.cum_volume = volume_today
        self.last_ltp = ltp

    def holds_or_low_vwap(self, ltp: float) -> bool:
        vw = self.vwap()
        if self.or_low is None or vw is None:
            return False
        return ltp >= self.or_low and ltp >= vw


def token_status() -> str:
    return fyers_auth.token_status()


def status(*, when: datetime | None = None) -> dict[str, Any]:
    """Non-connecting status probe -- what `manas live-loop --paper` reports
    before deciding whether to open a socket at all."""
    cfg = config.get("fyers", {}) or {}
    if not cfg.get("client_id") and not fyers_auth.app_id():
        return {"state": STATE_NOT_CONFIGURED, "detail": "fyers.client_id not set in config.yaml"}
    ts = token_status()
    if ts != "ready":
        return {"state": STATE_AUTH_NEEDED, "detail": f"fyers_auth.token_status() = {ts}"}
    if not market_calendar.is_market_hours(when):
        return {"state": STATE_MARKET_CLOSED, "detail": "outside NSE hours (09:08-15:30 IST) or non-trading day"}
    return {"state": STATE_CONNECTING, "detail": "ready to connect"}


class LiveSession:
    """Owns the Fyers WS connection and fans ticks into alerts.live_fsm.on_tick().

    reconnect/backoff and dedupe: fyers_apiv3's FyersDataSocket has its own
    reconnect (reconnect=True, reconnect_retry=5); this class adds the
    project-specific dedupe by simply relying on live_fsm.on_tick's own
    idempotency (a duplicate/replayed tick can never re-fire an already-
    logged transition -- see alerts/live_fsm.py docstring), so a socket-level
    reconnect replaying the last few ticks is safe by construction, not by a
    second ad-hoc dedupe layer here.
    """

    def __init__(self, conn, trade_date: str, *, regime_mode: str = "SELECTIVE",
                 on_tick: Callable[[dict], None] | None = None):
        self.conn = conn
        self.trade_date = trade_date
        self.regime_mode = regime_mode
        self.on_tick = on_tick
        self.state = STATE_NOT_CONFIGURED
        self.ticker_state: dict[str, TickerState] = {}
        self._socket = None

    def _symbols(self) -> list[str]:
        rows = self.conn.execute(
            "SELECT DISTINCT symbol FROM live_fsm_state WHERE trade_date=?", (self.trade_date,)
        ).fetchall()
        return [r["symbol"] for r in rows]

    def _on_message(self, msg: dict) -> None:
        """Normalize one Fyers WS payload into alerts.live_fsm's tick schema
        and drive the FSM. Fyers full-mode payloads carry `symbol`, `ltp`,
        `vol_traded_today` among other fields (exact key set depends on
        litemode)."""
        try:
            fy_sym = msg.get("symbol")
            ltp = msg.get("ltp")
            vol = msg.get("vol_traded_today") or msg.get("last_traded_qty") or 0
            if fy_sym is None or ltp is None:
                return
            symbol = fy_sym.split(":")[-1].replace("-EQ", "")
            now = datetime.now()
            st = self.ticker_state.setdefault(symbol, TickerState())
            st.update(float(ltp), float(vol), now)
            elapsed_min = max(1.0, (now - now.replace(hour=9, minute=15, second=0, microsecond=0)).total_seconds() / 60.0)
            elapsed_fraction = min(1.0, elapsed_min / 375.0)  # 09:15-15:30 = 375 min session
            ts = now.strftime(BAR_TS_FMT)
            event = {
                "symbol": symbol,
                "ts": ts,
                "price": st.last_ltp,
                "in_first_15m_complete": st.first_15m_complete,
                "holds_or_low_vwap": st.holds_or_low_vwap(st.last_ltp),
                "gap_fill_pct": st.gap_fill_pct(),
                "rvol_projected": st.rvol_projected(elapsed_fraction),
            }
            quotes.update_quote(self.conn, symbol, st.last_ltp, ts)
            if self.on_tick:
                self.on_tick(event)
            live_fsm.expire_due(self.conn, self.trade_date, ts)
            live_fsm.on_tick(self.conn, self.trade_date, event, regime_mode=self.regime_mode)
        except Exception:  # noqa: BLE001 - one bad tick must never kill the socket
            logger.exception("live session: failed to process tick %r", msg)

    def _on_error(self, msg: Any) -> None:
        logger.warning("live session: WS error %s", msg)
        self.state = STATE_DEGRADED

    def _on_close(self, msg: Any) -> None:
        logger.warning("live session: WS closed %s", msg)
        if self.state == STATE_CONNECTED:
            self.state = STATE_DEGRADED

    def _on_connect(self) -> None:
        symbols = [fyers_symbol(s) for s in self._symbols()]
        if symbols and self._socket is not None:
            self._socket.subscribe(symbols=symbols, data_type="SymbolUpdate")
        self.state = STATE_CONNECTED

    def probe(self) -> dict[str, Any]:
        """Cheap status check without opening a socket -- used for the
        `manas live-loop --paper` dry-run report and the 08:45 pre-flight."""
        return status()

    def connect(self) -> dict[str, Any]:
        probe = self.probe()
        self.state = probe["state"]
        if probe["state"] != STATE_CONNECTING:
            return {"connected": False, **probe}
        try:
            from fyers_apiv3.FyersWebsocket import data_ws
        except Exception as exc:  # noqa: BLE001
            self.state = STATE_DEGRADED
            return {"connected": False, "state": self.state, "detail": f"fyers_apiv3 import failed: {exc}"}

        token = fyers_auth.get_access_token()
        client_id = fyers_auth.app_id()
        access_token_full = f"{client_id}:{token}"
        self._socket = data_ws.FyersDataSocket(
            access_token=access_token_full,
            log_path="",
            litemode=False,
            reconnect=True,
            reconnect_retry=5,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close,
            on_connect=self._on_connect,
        )
        self._socket.connect()
        return {"connected": True, "state": STATE_CONNECTED}

    def close(self) -> None:
        if self._socket is not None:
            try:
                self._socket.close_connection()
            except Exception:  # noqa: BLE001
                pass
        self.state = STATE_MARKET_CLOSED
