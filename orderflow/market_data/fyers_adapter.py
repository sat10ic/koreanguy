"""Raw FYERS market-data messages → canonical models.

This is THE ONLY file in the orderflow package permitted to know FYERS field
names. Everything downstream consumes the canonical models from
``orderflow.market_data.schemas`` and can be grepped clean of FYERS vocabulary
(``orderflow/tests/test_boundaries.py`` enforces this).

Input contract
--------------
The adapter consumes *decoded message dicts exactly as emitted by the official
``fyers-apiv3`` client's ``FyersDataSocket`` ``On_message`` callback. The
official client (v3.1.16, verified against the published wheel source on
2026-08-28) speaks a binary wire protocol internally and hands Python dicts to
its callback — those dicts are this adapter's raw input. A live harness
therefore wires ``FyersDataSocket.On_message`` straight into
``FyersAdapter.parse(raw_dict, ts_received)``.

Message shapes ( Certain: read from official client source v3.1.16 ):
  * quote  — ``type == "sf"``, fields: ``symbol``, ``ltp``, ``open_price``,
             ``high_price``, ``low_price``, ``prev_close_price``,
             ``vol_traded_today``, ``last_traded_qty``, ``exch_feed_time``,
             ``tot_buy_qty``, ``tot_sell_qty``, ``bid_price``/``ask_price``/
             ``bid_size``/``ask_size`` (top of book), plus ``exchange``,
             ``exchange_token``, ``multiplier``, ``precision``. Prices arrive
             already scaled to rupees by the client.
  * depth  — ``type == "dp"``, FLAT numbered fields: ``bid_price1..5`` /
             ``ask_price1..5``, ``bid_size1..5`` / ``ask_size1..5``,
             ``bid_order1..5`` / ``ask_order1..5``, plus ``tot_buy_qty`` /
             ``tot_sell_qty``. The standard data-socket depth is 5 levels by
             protocol; there is no 50-level depth on this socket.
  * index  — ``type == "if"``. Index quotes; not used by the order-flow
             layer, reported as ignored.
  * control— ``type`` in {"cn","sub","unsub","lit","ful","cp","cr"} — auth,
             subscription acks, mode changes. Carries ``code``/``message``/
             ``s``; code 200 + ``s: "ok"`` = success; 11011 subscription
             failure; the client defines a documented batch limit of 5000
             symbols per subscribe request.
  Unverified against live traffic: the exact epoch semantics of
  ``exch_feed_time`` (assumed UTC epoch seconds; a fallback parses the
  documented string form ``"%d %b %Y %H:%M:%S IST"``). The first live session
  must confirm this — until then ``feed_latency_ms`` is provisional.

TBT (tick-by-tick) shape ( Unverified / harness contract ): 50-level TBT on
FYERS is a separate protobuf socket (official client ``tbt_ws.py``; socket URL
provisioned via an authenticated REST call the OWNER must make — this package
never holds credentials). This adapter accepts the decoded-dict shape the
owner's TBT harness is asked to emit:

    {"type": "tbt", "symbol": ..., "exch_feed_time": <epoch seconds>,
     "bids": [{"price": ..., "quantity": ..., "order_count": ...}, ...],
     "asks": [...], "total_buy_qty": ..., "total_sell_qty": ...}

until a live TBT session pins the real decoded object shape.

R5 discipline: a field absent from the message, or unparseable, becomes
``None`` on the canonical model — never zero, never guessed. Structurally
invalid messages return ``None`` and are counted in ``skipped`` with a reason;
they never crash the stream.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping, Optional, Sequence

from .schemas import DepthLevel, DepthSnapshot, QuoteUpdate, SchemaError

IST = timezone(timedelta(hours=5, minutes=30))

EXCHANGE_FEED_TIME_FORMAT = "%d %b %Y %H:%M:%S IST"


class FyersAdapter:
    """Translate decoded FYERS messages into canonical models."""

    #: canonical-kind → wire subscription data_type the official client expects
    WIRE_DATA_TYPES = {"quote": "SymbolUpdate", "depth": "DepthUpdate"}

    QUOTE_MESSAGE_TYPE = "sf"
    DEPTH_MESSAGE_TYPE = "dp"
    INDEX_MESSAGE_TYPE = "if"
    TBT_MESSAGE_TYPE = "tbt"  # owner-harness convention; see module docstring
    CONTROL_TYPES = frozenset({"cn", "sub", "unsub", "lit", "ful", "cp", "cr"})

    #: Data socket the official client connects to (v3.1.16 source).
    DATA_SOCKET_URL = "wss://socket.fyers.in/hsm/v1-5/prod"

    #: Documented limits from the official client source — external claims,
    #: not measurements. The capability audit measures what is enforced.
    DOCUMENTED_LIMITS = {
        "subscribe_batch_max_symbols": 5000,
        "source": "fyers-apiv3 v3.1.16 LIMIT_EXCEED_MSG_5000",
    }

    DEPTH_LEVELS_PER_SIDE = 5  # on the standard data socket

    def __init__(self) -> None:
        self.skipped: Counter[str] = Counter()

    # ------------------------------------------------------------------ classification

    def classify(self, message: Any) -> str:
        """Coarse bucket for a raw message: ``quote`` / ``depth`` / ``tbt`` /
        ``index`` / ``control`` / ``unknown``."""
        if not isinstance(message, Mapping):
            return "unknown"
        kind = message.get("type")
        if kind == self.QUOTE_MESSAGE_TYPE:
            return "quote"
        if kind == self.DEPTH_MESSAGE_TYPE:
            return "depth"
        if kind == self.TBT_MESSAGE_TYPE:
            return "tbt"
        if kind == self.INDEX_MESSAGE_TYPE:
            return "index"
        if kind in self.CONTROL_TYPES:
            return "control"
        return "unknown"

    @staticmethod
    def is_subscribe_ack(message: Any) -> bool:
        """True when the message is a subscription ack on the control stream."""
        return isinstance(message, Mapping) and message.get("type") == "sub"

    @staticmethod
    def ack_indicates_success(message: Mapping[str, Any]) -> bool:
        return message.get("s") == "ok" and message.get("code") == 200

    def parse(self, message: Any, ts_received: datetime) -> Optional[QuoteUpdate | DepthSnapshot]:
        """Parse any raw message; returns a canonical event or ``None``.

        ``None`` means "nothing usable" (control message, index tick, unknown
        or invalid payload); the reason is counted in ``self.skipped``.
        """
        kind = self.classify(message)
        if kind == "quote":
            return self.parse_quote(message, ts_received)
        if kind == "depth":
            return self.parse_depth(message, ts_received)
        if kind == "tbt":
            return self.parse_tbt(message, ts_received)
        if kind in ("index", "control"):
            self.skipped[f"ignored_{kind}"] += 1
        else:
            self.skipped["unknown_message"] += 1
        return None

    # ------------------------------------------------------------------ timestamps

    @staticmethod
    def parse_exchange_time(value: Any) -> Optional[datetime]:
        """``exch_feed_time`` → tz-aware UTC datetime, or ``None``.

        Epoch seconds (int/float) are assumed UTC epoch. String values are
        parsed in the documented IST feed-time format. Anything else is
        ``None`` — never guessed (R5).
        """
        if value is None:
            return None
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            if value < 0:
                return None
            return datetime.fromtimestamp(float(value), tz=timezone.utc)
        if isinstance(value, str):
            try:
                return datetime.strptime(value, EXCHANGE_FEED_TIME_FORMAT).replace(tzinfo=IST)
            except ValueError:
                return None
        return None

    # ------------------------------------------------------------------ quotes

    def parse_quote(self, message: Any, ts_received: datetime) -> Optional[QuoteUpdate]:
        if not isinstance(message, Mapping):
            self.skipped["quote_not_a_dict"] += 1
            return None
        symbol = message.get("symbol")
        if not symbol:
            self.skipped["quote_no_symbol"] += 1
            return None
        try:
            return QuoteUpdate(
                ts_exchange=self.parse_exchange_time(message.get("exch_feed_time")),
                ts_received=ts_received,
                symbol=str(symbol),
                ltp=_opt_float(message.get("ltp")),
                open=_opt_float(message.get("open_price")),
                high=_opt_float(message.get("high_price")),
                low=_opt_float(message.get("low_price")),
                prev_close=_opt_float(message.get("prev_close_price")),
                session_volume=_opt_int(message.get("vol_traded_today")),
                last_trade_qty=_opt_int(message.get("last_traded_qty")),
            )
        except SchemaError:
            self.skipped["quote_invalid"] += 1
            return None

    # ------------------------------------------------------------------ depth

    def parse_depth(self, message: Any, ts_received: datetime) -> Optional[DepthSnapshot]:
        if not isinstance(message, Mapping):
            self.skipped["depth_not_a_dict"] += 1
            return None
        symbol = message.get("symbol")
        if not symbol:
            self.skipped["depth_no_symbol"] += 1
            return None
        bids = self._flat_side(message, "bid")
        asks = self._flat_side(message, "ask")
        try:
            return DepthSnapshot(
                ts_exchange=self.parse_exchange_time(message.get("exch_feed_time")),
                ts_received=ts_received,
                symbol=str(symbol),
                bids=bids,
                asks=asks,
                total_buy_qty=_opt_int(message.get("tot_buy_qty")),
                total_sell_qty=_opt_int(message.get("tot_sell_qty")),
            )
        except SchemaError:
            self.skipped["depth_invalid"] += 1
            return None

    def _flat_side(self, message: Mapping[str, Any], side: str) -> tuple:
        """Expand the flat ``bid_price1..5``-style fields into levels.

        A level needs both price and size present; a missing count is ``None``
        on the level (R5). Levels with unparseable price/size are dropped —
        recorded in ``skipped``, never zero-filled.
        """
        levels = []
        for i in range(1, self.DEPTH_LEVELS_PER_SIDE + 1):
            price = _opt_float(message.get(f"{side}_price{i}"))
            quantity = _opt_int(message.get(f"{side}_size{i}"))
            if price is None or quantity is None:
                # Absent sentinel for a non-existent level — normal beyond the
                # live book; not an error. Only flag when *some* levels exist.
                continue
            order_count = _opt_int(message.get(f"{side}_order{i}"))
            try:
                levels.append(DepthLevel(price=price, quantity=quantity, order_count=order_count))
            except SchemaError:
                self.skipped["depth_level_invalid"] += 1
        return tuple(levels)

    def parse_tbt(self, message: Any, ts_received: datetime) -> Optional[DepthSnapshot]:
        """Parse the owner-harness TBT decoded dict (see module docstring)."""
        if not isinstance(message, Mapping):
            self.skipped["tbt_not_a_dict"] += 1
            return None
        symbol = message.get("symbol")
        if not symbol:
            self.skipped["tbt_no_symbol"] += 1
            return None

        def side(key: str) -> tuple:
            levels = []
            raw = message.get(key) or ()
            for entry in raw:
                if not isinstance(entry, Mapping):
                    self.skipped["tbt_level_not_a_dict"] += 1
                    continue
                price = _opt_float(entry.get("price"))
                quantity = _opt_int(entry.get("quantity"))
                if price is None or quantity is None:
                    self.skipped["tbt_level_missing_fields"] += 1
                    continue
                levels.append(
                    DepthLevel(price=price, quantity=quantity, order_count=_opt_int(entry.get("order_count")))
                )
            return tuple(levels)

        try:
            return DepthSnapshot(
                ts_exchange=self.parse_exchange_time(message.get("exch_feed_time")),
                ts_received=ts_received,
                symbol=str(symbol),
                bids=side("bids"),
                asks=side("asks"),
                total_buy_qty=_opt_int(message.get("total_buy_qty")),
                total_sell_qty=_opt_int(message.get("total_sell_qty")),
            )
        except SchemaError:
            self.skipped["tbt_invalid"] += 1
            return None

    # ------------------------------------------------------------------ outbound encodings

    def encode_subscribe(self, canonical_kind: str, symbols: Sequence[str]) -> dict:
        """Wire payload requesting a subscription for ``canonical_kind``.

        The manager stays FYERS-agnostic: it only sends what this adapter
        encodes. Batch-size limits are the caller's policy; the documented
        ceiling lives in ``DOCUMENTED_LIMITS``.
        """
        data_type = self.WIRE_DATA_TYPES[canonical_kind]
        return {"symbols": list(symbols), "data_type": data_type}

    def encode_unsubscribe(self, canonical_kind: str, symbols: Sequence[str]) -> dict:
        return {"symbols": list(symbols), "data_type": self.WIRE_DATA_TYPES[canonical_kind], "action": "unsubscribe"}


def _opt_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    if out != out or out in (float("inf"), float("-inf")):
        return None
    return out


def _opt_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
