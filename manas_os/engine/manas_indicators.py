"""Pure Python ports of the WAVE G Pine indicators.

All functions accept OHLCV bar dictionaries oldest-first. Expected keys match
``engine.indicators`` daily rows: ``open``, ``high``, ``low``, ``close``, and
``volume``. These ports intentionally do not wire into charts or context packs.
"""
from __future__ import annotations

from math import isfinite
from typing import Any


BENCHMARK_10MA = 21
BENCHMARK_21MA = 42
BENCHMARK_50MA = 63
BENCHMARK_200MA = 252


class SimpleVolumeSeries(list):
    def blue_streak(self, n: int) -> bool:
        return n > 0 and len(self) >= n and all(row["bull_pocket_pivot"] for row in self[-n:])


def _num(bar: dict[str, Any], key: str) -> float | None:
    value = bar.get(key)
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _closes(bars: list[dict[str, Any]]) -> list[float | None]:
    return [_num(bar, "close") for bar in bars]


def _sma(values: list[float | None], length: int) -> list[float | None]:
    out: list[float | None] = []
    for i in range(len(values)):
        window = values[i - length + 1 : i + 1]
        if len(window) == length and all(v is not None for v in window):
            out.append(sum(v for v in window if v is not None) / length)
        else:
            out.append(None)
    return out


def _ema(values: list[float | None], length: int) -> list[float | None]:
    out: list[float | None] = []
    alpha = 2.0 / (length + 1.0)
    prev: float | None = None
    for value in values:
        if value is None:
            out.append(None)
            continue
        prev = value if prev is None else alpha * value + (1.0 - alpha) * prev
        out.append(prev)
    return out


def _true_ranges(bars: list[dict[str, Any]]) -> list[float | None]:
    out: list[float | None] = []
    prev_close: float | None = None
    for bar in bars:
        high = _num(bar, "high")
        low = _num(bar, "low")
        if high is None or low is None:
            out.append(None)
            prev_close = _num(bar, "close")
            continue
        choices = [high - low]
        if prev_close is not None:
            choices.extend([abs(high - prev_close), abs(low - prev_close)])
        out.append(max(choices))
        prev_close = _num(bar, "close")
    return out


def _rma(values: list[float | None], length: int) -> list[float | None]:
    out: list[float | None] = [None] * len(values)
    prev: float | None = None
    for i, value in enumerate(values):
        if value is None:
            continue
        if prev is None:
            window = values[i - length + 1 : i + 1]
            if len(window) == length and all(v is not None for v in window):
                prev = sum(v for v in window if v is not None) / length
                out[i] = prev
        else:
            prev = (prev * (length - 1) + value) / length
            out[i] = prev
    return out


def _atr(bars: list[dict[str, Any]], length: int) -> list[float | None]:
    return _rma(_true_ranges(bars), length)


def _highest_prior(values: list[float | None], index: int, length: int) -> float | None:
    window = values[max(0, index - length) : index]
    clean = [v for v in window if v is not None]
    return max(clean) if clean else None


def _lowest(values: list[float | None], index: int, length: int) -> float | None:
    window = values[max(0, index - length + 1) : index + 1]
    clean = [v for v in window if v is not None]
    return min(clean) if clean else None


def _sum_bool(values: list[bool], index: int, length: int) -> int:
    return sum(1 for v in values[max(0, index - length + 1) : index + 1] if v)


def _round_pine(value: float) -> int:
    return int(value + 0.5) if value >= 0 else int(value - 0.5)


def burst_power(bars: list[dict[str, Any]], lookback_days: int) -> dict[str, Any]:
    """Burst Power aggregate over the last ``lookback_days`` bars."""
    start = max(0, len(bars) - lookback_days) if lookback_days is not None else 0
    count_5 = count_10 = count_19 = 0
    max_move: float | None = None
    for i in range(max(1, start), len(bars)):
        prev_close = _num(bars[i - 1], "close")
        close = _num(bars[i], "close")
        high = _num(bars[i], "high")
        low = _num(bars[i], "low")
        if prev_close in (None, 0) or close is None or high is None or low is None or high == low:
            continue
        close_position = (close - low) / (high - low)
        if close_position < 0:
            continue
        move = (close - prev_close) / prev_close * 100.0
        if not isfinite(move) or abs(move) >= 1e8:
            continue
        max_move = move if max_move is None or move > max_move else max_move
        if 5 <= move < 10:
            count_5 += 1
        elif 10 <= move < 19:
            count_10 += 1
        elif move >= 19:
            count_19 += 1
    power_value = count_5 / 5.0 + count_10 / 2.0 + count_19 / 0.5
    return {
        "count_5": count_5,
        "count_10": count_10,
        "count_19": count_19,
        "max_move": max_move,
        "power_value": power_value,
        "rounded": _round_pine(power_value),
    }


def simple_volume(bars: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Simple Volume/Pocket Pivot per-bar states."""
    volumes = [_num(bar, "volume") for bar in bars]
    avg_volume = _sma(volumes, 50)
    out: SimpleVolumeSeries = SimpleVolumeSeries()

    def is_up_at(i: int) -> bool:
        close = _num(bars[i], "close")
        if close is None:
            return False
        if i == 0:
            open_ = _num(bars[i], "open")
            return open_ is not None and close >= open_
        prev_close = _num(bars[i - 1], "close")
        return prev_close is not None and close > prev_close

    def is_down_at(i: int) -> bool:
        close = _num(bars[i], "close")
        if close is None:
            return False
        if i == 0:
            open_ = _num(bars[i], "open")
            return open_ is not None and close < open_
        prev_close = _num(bars[i - 1], "close")
        return prev_close is not None and close < prev_close

    for i, bar in enumerate(bars):
        volume = _num(bar, "volume")
        prior = range(max(0, i - 10), i)
        down_vols = [_num(bars[j], "volume") for j in prior if is_down_at(j)]
        up_vols = [_num(bars[j], "volume") for j in prior if is_up_at(j)]
        down_vols = [v for v in down_vols if v is not None]
        up_vols = [v for v in up_vols if v is not None]
        max_down = max(down_vols) if down_vols else None
        max_up = max(up_vols) if up_vols else None
        is_up = is_up_at(i)
        is_down = is_down_at(i)
        is_bull_pp = bool(is_up and max_down is not None and volume is not None and volume > max_down)
        is_bear_pp = bool(is_down and max_up is not None and volume is not None and volume > max_up)
        avg = avg_volume[i]
        is_dry = bool(avg is not None and avg > 0 and volume is not None and volume <= avg * 0.20)
        is_high_up = bool(is_up and avg is not None and volume is not None and volume > avg)
        is_high_down = bool(is_down and avg is not None and volume is not None and volume > avg)
        state = (
            "dry"
            if is_dry
            else "bull_pp"
            if is_bull_pp
            else "bear_pp"
            if is_bear_pp
            else "high_down"
            if is_high_down
            else "high_up"
            if is_high_up
            else "noise"
        )
        out.append(
            {
                "is_up": is_up,
                "is_down": is_down,
                "max_down_volume": max_down,
                "max_up_volume": max_up,
                "bull_pocket_pivot": is_bull_pp,
                "bear_pocket_pivot": is_bear_pp,
                "dry": is_dry,
                "high_up": is_high_up,
                "high_down": is_high_down,
                "state": state,
                "avg_volume": avg,
            }
        )

    return out


def _cross_over(prev_price: float | None, price: float, prev_ma: float | None, ma: float) -> bool:
    return prev_price is not None and prev_ma is not None and prev_price <= prev_ma and price > ma


def _cross_under(prev_price: float | None, price: float, prev_ma: float | None, ma: float) -> bool:
    return prev_price is not None and prev_ma is not None and prev_price >= prev_ma and price < ma


def persistency(bars: list[dict[str, Any]], ma_type: str, length: int) -> list[dict[str, Any]]:
    """Persistency count with decisive-exit state machine."""
    closes = _closes(bars)
    ma_values = _ema(closes, length) if ma_type.upper() == "EMA" else _sma(closes, length)
    count = 0
    exit_level: float | None = None
    pending_exit = False
    populated = False
    out: list[dict[str, Any]] = []

    for i, bar in enumerate(bars):
        price = _num(bar, "close")
        low = _num(bar, "low")
        high = _num(bar, "high")
        ma = ma_values[i]
        entry_signal = False
        exit_signal = False
        if price is not None and low is not None and high is not None and ma is not None:
            if not populated:
                populated = True
                if price > ma:
                    count = 1
                    entry_signal = True
            prev_price = _num(bars[i - 1], "close") if i > 0 else None
            prev_ma = ma_values[i - 1] if i > 0 else None
            pos_exit_trigger = price < ma
            neg_exit_trigger = price > ma
            entry_signal = False
            exit_signal = False

            if count > 0:
                if pending_exit:
                    if exit_level is not None and low < exit_level:
                        count = -1
                        pending_exit = False
                        exit_level = None
                        exit_signal = True
                        if neg_exit_trigger:
                            pending_exit = True
                            exit_level = high
                    elif neg_exit_trigger:
                        pending_exit = False
                        exit_level = None
                        count += 1
                    else:
                        count += 1
                else:
                    if pos_exit_trigger:
                        pending_exit = True
                        exit_level = low
                        count += 1
                    else:
                        count += 1
            elif count < 0:
                if pending_exit:
                    if exit_level is not None and high > exit_level:
                        count = 1
                        pending_exit = False
                        exit_level = None
                        entry_signal = True
                        if pos_exit_trigger:
                            pending_exit = True
                            exit_level = low
                    elif pos_exit_trigger:
                        pending_exit = False
                        exit_level = None
                        count -= 1
                    else:
                        count -= 1
                else:
                    if neg_exit_trigger:
                        pending_exit = True
                        exit_level = high
                        count -= 1
                    else:
                        count -= 1
            else:
                if _cross_over(prev_price, price, prev_ma, ma):
                    count = 1
                    exit_level = None
                    pending_exit = False
                    entry_signal = True
                elif _cross_under(prev_price, price, prev_ma, ma):
                    count = -1
                    exit_level = None
                    pending_exit = False
                    exit_signal = True

        out.append(
            {
                "ma": ma,
                "count": count,
                "pending_exit": pending_exit,
                "exit_level": exit_level,
                "entry_signal": entry_signal,
                "exit_signal": exit_signal,
            }
        )
    return out


def persistency_ema_bundle(bars: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    return {
        "ema10": persistency(bars, "EMA", 10),
        "ema21": persistency(bars, "EMA", 21),
        "ema50": persistency(bars, "EMA", 50),
        "ema200": persistency(bars, "EMA", 200),
    }


def _pine_momentum(values: list[float | None], index: int, length: int) -> float | None:
    current = values[index]
    if current is None:
        return None
    available_len = 0
    for bars_ago in range(0, length + 1):
        j = index - bars_ago
        if j >= 0 and values[j] is not None:
            available_len = bars_ago
    actual_len = available_len if available_len > 0 else length
    j = index - actual_len
    base = values[j] if j >= 0 else None
    if base in (None, 0):
        return None
    return (current - base) * 100.0 / base / actual_len


def mswing(bars: list[dict[str, Any]], index_bars: list[dict[str, Any]]) -> list[dict[str, Any]]:
    stock_close = _closes(bars)
    index_close = _closes(index_bars)
    n = min(len(stock_close), len(index_close))
    out: list[dict[str, Any]] = []
    for i in range(n):
        momo20 = _pine_momentum(stock_close, i, 20)
        momo50 = _pine_momentum(stock_close, i, 50)
        index_momo20 = _pine_momentum(index_close, i, 20)
        index_momo50 = _pine_momentum(index_close, i, 50)
        stock_mswing = None if momo20 is None or momo50 is None else momo20 + momo50
        index_mswing = None if index_momo20 is None or index_momo50 is None else index_momo20 + index_momo50
        if stock_mswing is None or index_mswing is None:
            color = None
        elif stock_mswing > 0 and stock_mswing >= index_mswing:
            color = "up"
        elif stock_mswing > 0 and stock_mswing < index_mswing:
            color = "neutral_positive"
        elif stock_mswing < 0 and stock_mswing >= index_mswing:
            color = "neutral_negative"
        else:
            color = "down"
        out.append(
            {
                "momo20": momo20,
                "momo50": momo50,
                "mswing": stock_mswing,
                "index_momo20": index_momo20,
                "index_momo50": index_momo50,
                "index_mswing": index_mswing,
                "color": color,
            }
        )
    return out


def rmv(
    bars: list[dict[str, Any]],
    atr_len: int = 3,
    abs_tight_len: int = 5,
    abs_mult: float = 0.75,
    thresh: int = 50,
) -> list[dict[str, Any]]:
    ranges = [(_num(bar, "high") or 0.0) - (_num(bar, "low") or 0.0) for bar in bars]
    ranges_opt: list[float | None] = [r for r in ranges]
    atr_prior = _atr(bars, atr_len)
    abs_atr_prior = _atr(bars, abs_tight_len)
    ema7 = _ema(_closes(bars), 7)
    ema10 = _ema(_closes(bars), 10)
    ema21 = _ema(_closes(bars), 21)
    ema50 = _ema(_closes(bars), 50)
    ema200 = _ema(_closes(bars), 200)
    vol_ema21 = _ema([_num(bar, "volume") for bar in bars], 21)
    closes = _closes(bars)
    volumes = [_num(bar, "volume") for bar in bars]
    rmv_values: list[float | None] = []
    out: list[dict[str, Any]] = []

    open_eq_low: list[bool] = []
    close_eq_high: list[bool] = []
    close_gt_prev: list[bool] = []
    pct_le_minus5: list[bool] = []

    for i, bar in enumerate(bars):
        open_ = _num(bar, "open")
        high = _num(bar, "high")
        low = _num(bar, "low")
        close = _num(bar, "close")
        volume = _num(bar, "volume")
        if open_ is None or high is None or low is None or close is None:
            rmv_val = None
            out.append({"rmv": None, "tightness_setup": False, "vdu_setup": False, "rank": 0})
            rmv_values.append(rmv_val)
            open_eq_low.append(False)
            close_eq_high.append(False)
            close_gt_prev.append(False)
            pct_le_minus5.append(False)
            continue
        range_today = high - low
        body_today = abs(open_ - close)
        range_safe = max(range_today, 0.001)
        open_pos_pct = (open_ - low) / range_safe * 100.0
        close_pos_pct = (close - low) / range_safe * 100.0
        abs_prior = abs_atr_prior[i - 1] if i > 0 else None
        is_abs_tight = bool(abs_prior is not None and range_today <= abs_prior * abs_mult)
        strong_oc = open_pos_pct > thresh and close_pos_pct > thresh
        numerator = body_today if is_abs_tight or strong_oc else range_today
        atr_base = atr_prior[i - 1] if i > 0 else None
        max_hl_prior = _highest_prior(ranges_opt, i, atr_len)
        denom_candidates = [v for v in [atr_base, max_hl_prior] if v is not None]
        denominator = max(denom_candidates) if denom_candidates else None
        epsilon = max(0.001, close * 0.0001)
        rmv_val = min(numerator / max(denominator or 0.0, epsilon) * 50.0, 100.0)
        rmv_values.append(rmv_val)

        prev_close = closes[i - 1] if i > 0 else None
        prev2_close = closes[i - 2] if i > 1 else None
        pct_chg = (close - prev_close) / prev_close * 100.0 if prev_close not in (None, 0) else None
        pct_chg_prev = (
            (prev_close - prev2_close) / prev2_close * 100.0 if prev_close is not None and prev2_close not in (None, 0) else None
        )
        open_eq_low.append(open_ == low)
        close_eq_high.append(close == high)
        close_gt_prev.append(bool(prev_close is not None and close > prev_close))
        pct_le_minus5.append(bool(pct_chg is not None and pct_chg <= -5))
        not_runaway = not (_sum_bool(open_eq_low, i, 10) >= 3 and _sum_bool(close_eq_high, i, 10) >= 3)
        highest_high_7_prior = _highest_prior([_num(b, "high") for b in bars], i, 7)
        tightness_setup = bool(
            atr_prior[i] is not None
            and range_today <= atr_prior[i]
            and ema10[i] is not None
            and ema21[i] is not None
            and ema50[i] is not None
            and ema200[i] is not None
            and low <= ema10[i] * 1.04
            and close >= ema10[i] * 0.99
            and close >= ema21[i]
            and close >= ema50[i]
            and close >= ema200[i]
            and not_runaway
            and close >= open_ * 0.985
            and pct_chg is not None
            and pct_chg <= 4
            and pct_chg >= -1
            and pct_chg_prev is not None
            and pct_chg_prev <= 7.5
            and pct_chg + pct_chg_prev <= 7
            and highest_high_7_prior is not None
            and close >= highest_high_7_prior * 0.9
            and _sum_bool(close_gt_prev, i, 9) != 9
        )
        lowest_vol_90 = _lowest(volumes, i, 90)
        lowest_vol_365 = _lowest(volumes, i, 365)
        is_vdu = bool(
            volume is not None
            and vol_ema21[i] is not None
            and (
                volume <= vol_ema21[i] * 0.5
                or (i >= 1 and volumes[i - 1] is not None and volumes[i - 1] <= vol_ema21[i] * 0.5)
                or (i >= 2 and volumes[i - 2] is not None and volumes[i - 2] <= vol_ema21[i] * 0.6)
                or volume == lowest_vol_90
                or volume == lowest_vol_365
            )
        )
        vdu_setup = bool(
            is_vdu
            and ema7[i] is not None
            and ema10[i] is not None
            and ema21[i] is not None
            and ema50[i] is not None
            and ema200[i] is not None
            and ema21[i] >= ema50[i] * 1.03
            and ema50[i] >= ema200[i]
            and close <= ema10[i] * 1.06
            and not_runaway
            and pct_chg is not None
            and pct_chg <= 4
            and pct_chg >= -2
            and pct_chg_prev is not None
            and pct_chg_prev <= 4
            and pct_chg_prev > -3
            and i >= 3
            and ema10[i - 3] is not None
            and ema10[i] > ema10[i - 3]
            and ema7[i] > ema10[i]
            and ema10[i] > ema21[i]
            and ema21[i] > ema50[i]
            and ema50[i] > ema200[i]
            and _sum_bool(pct_le_minus5, i, 7) == 0
        )
        aplus = (tightness_setup or vdu_setup) and rmv_val <= 15
        is_trough = bool(rmv_val == _lowest(rmv_values, i, 5))
        rank = 1 if aplus and is_trough else 2 if aplus else 3 if is_trough else 4 if rmv_val <= 20 else 0
        out.append(
            {
                "rmv": rmv_val,
                "is_abs_tight": is_abs_tight,
                "strong_oc": strong_oc,
                "numerator": numerator,
                "denominator": max(denominator or 0.0, epsilon),
                "tightness_setup": tightness_setup,
                "vdu_setup": vdu_setup,
                "rank": rank,
            }
        )
    return out


def ss_rvol(bars: list[dict[str, Any]], lookback: int = 20) -> list[dict[str, Any]]:
    volumes = [_num(bar, "volume") for bar in bars]
    out: list[dict[str, Any]] = []
    for i, bar in enumerate(bars):
        prior = volumes[max(0, i - lookback) : i]
        avg = sum(v for v in prior if v is not None) / lookback if len(prior) == lookback and all(v is not None for v in prior) else None
        volume = _num(bar, "volume")
        rvol = volume / avg if volume is not None and avg and avg > 0 else None
        open_ = _num(bar, "open")
        low = _num(bar, "low")
        prev_close = _num(bars[i - 1], "close") if i > 0 else None
        strong_start = bool(open_ is not None and low is not None and prev_close is not None and open_ > prev_close and low >= prev_close * 0.995)
        out.append({"rvol": rvol, "avg_volume": avg, "strong_start": strong_start})
    return out


def purple_dot(bars: list[dict[str, Any]], vol_floor: int = 1_000_000, pct: float = 5) -> list[bool]:
    out: list[bool] = []
    for i, bar in enumerate(bars):
        close = _num(bar, "close")
        prev_close = _num(bars[i - 1], "close") if i > 0 else None
        volume = _num(bar, "volume")
        roc = abs((close - prev_close) / prev_close * 100.0) if close is not None and prev_close not in (None, 0) else None
        out.append(bool(roc is not None and roc >= pct and volume is not None and volume >= vol_floor))
    return out
