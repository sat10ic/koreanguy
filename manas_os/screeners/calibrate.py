"""Calibration harness for in-house ChartsMaze screener ports.

The harness compares a pure in-house screener function against archived
ChartsMaze CSV exports for the same trade dates. It deliberately reuses the
existing ChartsMaze dump-folder and dynamic CSV parsing helpers so shifted
headers do not become a second source of bugs.
"""
from __future__ import annotations

import argparse
import math
from collections.abc import Callable, Iterable
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

from manas_os import db
from manas_os.engine.universe_filter import GateConfig, filter_universe
from manas_os.sources import chartsmaze, chartsmaze_scanners

HitComputeFn = Callable[[Any, str], set[str]]
ValueFn = Callable[[Any, str, str], float | int | None]


def _normalize_symbol(raw: Any) -> str:
    return str(raw or "").strip().upper()


def _screener_filename(screener_key: str) -> tuple[str, str]:
    key = screener_key.strip()
    if key.endswith(".csv"):
        fname = key
        stem = Path(key).stem
    else:
        fname = f"{key}.csv"
        stem = key
    for registered, (name, _bearish) in chartsmaze_scanners.SCREENER_REGISTRY.items():
        if key in (name, registered, Path(registered).stem):
            return registered, name
    if fname in chartsmaze_scanners.SCREENER_REGISTRY:
        return fname, chartsmaze_scanners.SCREENER_REGISTRY[fname][0]
    return fname, stem


def _screener_path(screener_key: str, run_date: str) -> Path:
    fname, _ = _screener_filename(screener_key)
    folder = chartsmaze.date_dir(run_date)
    for subdir in ("scanners", "templates"):
        path = folder / subdir / fname
        if path.is_file():
            return path
    return folder / "scanners" / fname


def _available_dates(screener_key: str, start: str, end: str) -> list[str]:
    start_d = datetime.strptime(start, "%Y-%m-%d").date()
    end_d = datetime.strptime(end, "%Y-%m-%d").date()
    if end_d < start_d:
        raise ValueError("end must be on or after start")

    out: list[str] = []
    cur = start_d
    while cur <= end_d:
        run_date = cur.isoformat()
        if _screener_path(screener_key, run_date).is_file():
            out.append(run_date)
        cur += timedelta(days=1)
    return out


def _latest_trade_date(conn, dump_date: str) -> str | None:
    row = conn.execute(
        "SELECT MAX(trade_date) AS trade_date FROM daily_prices WHERE trade_date <= ?",
        (dump_date,),
    ).fetchone()
    return row["trade_date"] if row and row["trade_date"] else None


def load_their_hits(screener_key: str, run_date: str) -> tuple[set[str], pd.DataFrame]:
    """Load one archived ChartsMaze screener CSV.

    Returns ``(symbols, dataframe)``. The dataframe preserves every source
    column and adds a normalized ``symbol`` column.
    """
    path = _screener_path(screener_key, run_date)
    if not path.is_file():
        raise FileNotFoundError(f"ChartsMaze screener CSV not found: {path}")

    text = path.read_text(encoding="utf-8-sig")
    rows = chartsmaze_scanners.parse_screener_csv(text)
    symbols = {r["symbol"] for r in rows if r.get("symbol")}

    df = pd.read_csv(path, encoding="utf-8-sig")
    sym_col = chartsmaze_scanners._symbol_col(list(df.columns))
    if sym_col is None:
        df["symbol"] = ""
    else:
        df["symbol"] = df[sym_col].map(_normalize_symbol)
    df = df[df["symbol"] != ""].copy()
    return symbols, df


def _jaccard(ours: set[str], theirs: set[str]) -> float:
    union = ours | theirs
    if not union:
        return 1.0
    return len(ours & theirs) / len(union)


def _tradeable_universe(conn, trade_date: str) -> set[str]:
    result = filter_universe(
        conn,
        trade_date,
        cfg=GateConfig(min_price=30.0, min_avg_turnover_cr=5.0, exclude_etf=True),
    )
    return {_normalize_symbol(s) for s in result["tradeable"] if _normalize_symbol(s)}


def _summary_jaccard(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {
            "median_jaccard": None,
            "median_raw_jaccard": None,
            "median_universe_jaccard": None,
            "dates_n": 0,
        }
    raw_values = sorted(float(r["raw_jaccard"]) for r in rows)
    universe_values = sorted(float(r["universe_jaccard"]) for r in rows)
    raw_median = _median(raw_values)
    return {
        "median_jaccard": raw_median,
        "median_raw_jaccard": raw_median,
        "median_universe_jaccard": _median(universe_values),
        "dates_n": len(rows),
    }


def calibrate(
    screener_key: str,
    compute_fn: HitComputeFn,
    start: str,
    end: str,
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    """Compare an in-house screener against archived ChartsMaze hits."""
    _fname, normalized_name = _screener_filename(screener_key)
    rows: list[dict[str, Any]] = []
    skipped: list[dict[str, str]] = []
    conn = db.connect(db_path)
    try:
        dump_dates = _available_dates(screener_key, start, end)
        mapped: list[tuple[str, str, set[str]]] = []
        seen_trade_dates: set[str] = set()
        for dump_date in dump_dates:
            trade_date = _latest_trade_date(conn, dump_date)
            if trade_date is None:
                skipped.append({
                    "dump_date": dump_date,
                    "reason": "no daily_prices trade_date <= dump_date",
                })
                continue
            if trade_date in seen_trade_dates:
                skipped.append({
                    "dump_date": dump_date,
                    "trade_date": trade_date,
                    "reason": "duplicate mapped trade_date",
                })
                continue
            theirs, _their_df = load_their_hits(screener_key, dump_date)
            mapped.append((dump_date, trade_date, theirs))
            seen_trade_dates.add(trade_date)

        their_window_symbols = (
            set().union(*(theirs for _dump, _trade, theirs in mapped))
            if mapped else set()
        )
        for dump_date, trade_date, theirs in mapped:
            ours = {_normalize_symbol(s) for s in compute_fn(conn, trade_date)}
            ours.discard("")
            our_universe = _tradeable_universe(conn, trade_date)
            shared_flaggable = our_universe & their_window_symbols
            raw_jaccard = _jaccard(ours, theirs)
            universe_ours = ours & shared_flaggable
            universe_theirs = theirs & shared_flaggable
            universe_jaccard = _jaccard(universe_ours, universe_theirs)
            only_ours = sorted(ours - theirs)
            only_theirs = sorted(theirs - ours)
            rows.append({
                "date": trade_date,
                "dump_date": dump_date,
                "trade_date": trade_date,
                "screener": normalized_name,
                "ours_n": len(ours),
                "theirs_n": len(theirs),
                "raw_jaccard": raw_jaccard,
                "universe_jaccard": universe_jaccard,
                "jaccard": raw_jaccard,
                "universe_ours_n": len(universe_ours),
                "universe_theirs_n": len(universe_theirs),
                "shared_flaggable_n": len(shared_flaggable),
                "only_ours": only_ours,
                "only_theirs": only_theirs,
            })
    finally:
        conn.close()
    return {"rows": rows, "summary": _summary_jaccard(rows), "skipped": skipped}


def _to_float(raw: Any) -> float | None:
    if raw is None:
        return None
    try:
        if pd.isna(raw):
            return None
    except (TypeError, ValueError):
        pass
    text = str(raw).strip().replace(",", "").replace("%", "")
    if text in ("", "-", "--", "NA", "N/A", "N.A.", "n.a."):
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _median(values: list[float]) -> float | None:
    if not values:
        return None
    n = len(values)
    mid = n // 2
    if n % 2:
        return values[mid]
    return (values[mid - 1] + values[mid]) / 2.0


def _percentile(values: list[float], pct: float) -> float | None:
    if not values:
        return None
    if len(values) == 1:
        return values[0]
    rank = (len(values) - 1) * pct
    low = math.floor(rank)
    high = math.ceil(rank)
    if low == high:
        return values[low]
    frac = rank - low
    return values[low] * (1 - frac) + values[high] * frac


def value_calibrate(
    screener_key: str,
    column: str,
    value_fn: ValueFn,
    start: str,
    end: str,
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    """Compare numeric per-stock values against one ChartsMaze CSV column."""
    rows: list[dict[str, Any]] = []
    conn = db.connect(db_path)
    try:
        seen_trade_dates: set[str] = set()
        for dump_date in _available_dates(screener_key, start, end):
            trade_date = _latest_trade_date(conn, dump_date)
            if trade_date is None or trade_date in seen_trade_dates:
                continue
            seen_trade_dates.add(trade_date)
            _hits, their_df = load_their_hits(screener_key, dump_date)
            if column not in their_df.columns:
                raise KeyError(f"Column {column!r} not present for {screener_key} on {dump_date}")
            for _idx, row in their_df.iterrows():
                symbol = _normalize_symbol(row.get("symbol"))
                theirs = _to_float(row.get(column))
                ours = value_fn(conn, trade_date, symbol)
                ours_f = _to_float(ours)
                if symbol and theirs is not None and ours_f is not None:
                    rows.append({
                        "date": trade_date,
                        "dump_date": dump_date,
                        "trade_date": trade_date,
                        "symbol": symbol,
                        "column": column,
                        "ours": ours_f,
                        "theirs": theirs,
                        "abs_error": abs(ours_f - theirs),
                    })
    finally:
        conn.close()

    errors = sorted(r["abs_error"] for r in rows)
    return {
        "rows": rows,
        "summary": {
            "median_abs_error": _median(errors),
            "p90_abs_error": _percentile(errors, 0.90),
            "n": len(errors),
        },
    }


def volume_spike_compute_fn(multiplier: float = 3.0) -> HitComputeFn:
    """Reference volume-spike implementation: volume >= multiplier * prior SMA20."""
    def compute(conn, run_date: str) -> set[str]:
        universe = _tradeable_universe(conn, run_date)
        if not universe:
            return set()
        rows = conn.execute(
            """
            WITH hist AS (
                SELECT
                    symbol,
                    trade_date,
                    volume,
                    AVG(volume) OVER (
                        PARTITION BY symbol
                        ORDER BY trade_date
                        ROWS BETWEEN 20 PRECEDING AND 1 PRECEDING
                    ) AS adv20_prior,
                    COUNT(volume) OVER (
                        PARTITION BY symbol
                        ORDER BY trade_date
                        ROWS BETWEEN 20 PRECEDING AND 1 PRECEDING
                    ) AS adv20_n
                FROM daily_prices
                WHERE trade_date <= ?
                  AND series = 'EQ'
                  AND volume IS NOT NULL
            )
            SELECT symbol
            FROM hist
            WHERE trade_date = ?
              AND adv20_n = 20
              AND volume >= ? * adv20_prior
            ORDER BY symbol
            """,
            (run_date, run_date, float(multiplier)),
        ).fetchall()
        return {_normalize_symbol(r["symbol"]) for r in rows} & universe

    return compute


def volume_ratio_value(conn, run_date: str, symbol: str) -> float | None:
    row = conn.execute(
        """
        WITH hist AS (
            SELECT
                symbol,
                trade_date,
                volume,
                AVG(volume) OVER (
                    PARTITION BY symbol
                    ORDER BY trade_date
                    ROWS BETWEEN 20 PRECEDING AND 1 PRECEDING
                ) AS adv20_prior,
                COUNT(volume) OVER (
                    PARTITION BY symbol
                    ORDER BY trade_date
                    ROWS BETWEEN 20 PRECEDING AND 1 PRECEDING
                ) AS adv20_n
            FROM daily_prices
            WHERE symbol = ?
              AND trade_date <= ?
              AND series = 'EQ'
              AND volume IS NOT NULL
        )
        SELECT volume, adv20_prior
        FROM hist
        WHERE trade_date = ?
          AND adv20_n = 20
        """,
        (_normalize_symbol(symbol), run_date, run_date),
    ).fetchone()
    if row is None or row["adv20_prior"] in (None, 0):
        return None
    return float(row["volume"]) / float(row["adv20_prior"])


def _format_list(values: Iterable[str], limit: int = 5) -> str:
    vals = list(values)
    if not vals:
        return "-"
    shown = ",".join(vals[:limit])
    if len(vals) > limit:
        return f"{shown},+{len(vals) - limit}"
    return shown


def _print_hit_table(result: dict[str, Any], label: str) -> None:
    summary = result["summary"]
    raw_med = summary["median_raw_jaccard"]
    uni_med = summary["median_universe_jaccard"]
    raw_text = "NA" if raw_med is None else f"{raw_med:.3f}"
    uni_text = "NA" if uni_med is None else f"{uni_med:.3f}"
    skipped = result.get("skipped") or []
    print(
        f"{label}: dates={summary['dates_n']} "
        f"median_raw_jaccard={raw_text} median_universe_jaccard={uni_text} "
        f"skipped={len(skipped)}"
    )
    for item in skipped:
        trade = item.get("trade_date", "-")
        print(f"skip dump_date={item['dump_date']} trade_date={trade} reason={item['reason']}")
    print("dump_date  trade_date ours theirs raw_jaccard universe_jaccard only_ours only_theirs")
    for row in result["rows"]:
        print(
            f"{row['dump_date']} {row['trade_date']} {row['ours_n']:>4} {row['theirs_n']:>6} "
            f"{row['raw_jaccard']:.3f} {row['universe_jaccard']:.3f} "
            f"{_format_list(row['only_ours']):<24} "
            f"{_format_list(row['only_theirs'])}"
        )


def _print_value_summary(result: dict[str, Any], label: str) -> None:
    summary = result["summary"]
    med = summary["median_abs_error"]
    p90 = summary["p90_abs_error"]
    med_text = "NA" if med is None else f"{med:.4f}"
    p90_text = "NA" if p90 is None else f"{p90:.4f}"
    print(f"{label}: n={summary['n']} median_abs_error={med_text} p90_abs_error={p90_text}")


def _volume_value_fn_for_column(column: str) -> ValueFn:
    normalized = " ".join(column.strip().lower().replace("_", " ").split())
    supported = {
        "volume ratio",
        "volume ratio 20",
        "vol ratio",
        "vol ratio 20",
        "vol ratio 20dma",
        "volume/20dma",
        "volume / 20dma",
        "volume vs 20dma",
        "volume ratio 20d",
        "volume ratio 20 dma",
    }
    if normalized in supported:
        return volume_ratio_value
    raise ValueError(
        "CLI value mode currently has a built-in value function only for "
        "volume ratio columns on volume-spike."
    )


def _default_start_end(screener_key: str, sessions: int = 15) -> tuple[str, str]:
    root = chartsmaze.chartsmaze_dir()
    if not root.is_dir():
        today = date.today().isoformat()
        return today, today
    dates = sorted(
        p.name for p in root.iterdir()
        if p.is_dir() and _screener_path(screener_key, p.name).is_file()
    )
    if not dates:
        today = date.today().isoformat()
        return today, today
    return dates[max(0, len(dates) - sessions)], dates[-1]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Calibrate in-house screeners against ChartsMaze dumps.")
    parser.add_argument("--screener", required=True)
    parser.add_argument("--start")
    parser.add_argument("--end")
    parser.add_argument("--column")
    parser.add_argument("--db-path")
    args = parser.parse_args(argv)

    start, end = (args.start, args.end) if args.start and args.end else _default_start_end(args.screener)

    if args.column:
        if args.screener != "volume-spike":
            raise SystemExit("CLI value mode currently supports only the volume-spike reference screener.")
        result = value_calibrate(
            args.screener,
            args.column,
            _volume_value_fn_for_column(args.column),
            start,
            end,
            args.db_path,
        )
        _print_value_summary(result, f"{args.screener} column={args.column} {start}..{end}")
        return 0

    if args.screener == "volume-spike":
        best: tuple[float, float, float] | None = None
        for multiplier in (2.0, 2.5, 3.0):
            result = calibrate(
                args.screener,
                volume_spike_compute_fn(multiplier),
                start,
                end,
                args.db_path,
            )
            _print_hit_table(result, f"{args.screener} multiplier={multiplier:g} {start}..{end}")
            print("")
            avg = (
                sum(float(row["universe_jaccard"]) for row in result["rows"]) / len(result["rows"])
                if result["rows"] else None
            )
            med = result["summary"]["median_universe_jaccard"]
            if med is not None and avg is not None and (
                best is None or (med, avg) > (best[1], best[2])
            ):
                best = (multiplier, med, avg)
        if best is not None:
            print(f"best_multiplier={best[0]:g} median_universe_jaccard={best[1]:.3f}")
        return 0

    raise SystemExit(f"No CLI reference implementation is registered for {args.screener!r}.")


if __name__ == "__main__":
    raise SystemExit(main())
