"""V4-T4/T5: named practitioner scanner PRESET_REGISTRY + a uniform run
contract over three underlying data sources (WIREFRAMES_V4.md SCANNERS
section 2A, owner order 2026-07-11 "where is the page to run different
scans as per the traders?").

Three preset "kinds", one row shape out:
  - archetype   -- membership in a discovery_bucket archetype (or the
                   TODAYS_MOVERS/arora_baseline screener.py conditions
                   preset), read via candidates.discovery_bucket_map /
                   screener.py -- LIVE, no new detector.
  - chartsmaze  -- rows already ingested into screener_hits by a trader
                   template (chartsmaze_scanners.SCREENER_REGISTRY) --
                   DATA-READY, thin read only.
  - build       -- corpus-cited, no data flow yet -- BUILD, greyed, no
                   fake rows (owner standing rule: "no dormant fake UI").

PRESET_REGISTRY is the single source of truth for both /api/scanners/
presets (counts + status) and /api/scanners/run (row fetch), so the two
endpoints can never drift on what a given key means.
"""
from __future__ import annotations

from typing import Any

from manas_os.scanner import candidates as scanner_candidates
from manas_os.scanner import discovery_metrics as dm
from manas_os.scanner import screener as scanner_screener

# --- registry ----------------------------------------------------------

PRESET_REGISTRY: dict[str, dict[str, Any]] = {
    # --- archetype presets: discovery_bucket archetype membership -------
    "arora_baseline": {
        "owner": "Arora", "label": "Arora Baseline",
        "recipe_line": "Screener.in NSE baseline: 3-month return > 30%, NSE-only, average 30d volume > 200,000 shares.",
        "cite": "ARORA_SHARDS_NUANCES.md, extract_ma_small.md:19-25; PRACTITIONER_SCREENERS.md Table 1 row 1",
        "status": "LIVE", "kind": "conditions",
        "source": "screener.py conditions engine (NEW preset, this task) over daily_prices",
    },
    "persistent_momentum": {
        "owner": "TradeTM", "label": "Persistent Momentum",
        "recipe_line": ">10EMA 20d, >20EMA 30d, >50EMA 50d, >200EMA 150d -- trend never broke -- sorted by ADR.",
        "cite": "TRADETM_NUANCES_HINDI.md III1-III4; PRACTITIONER_SCREENERS.md Table 2 row 4",
        "status": "LIVE", "kind": "archetype", "archetype": "persistent_momentum",
        "source": "discovery.build_bucket via candidates.discovery_bucket_map",
    },
    "ep_ipo": {
        "owner": "TradeTM", "label": "Earnings Power (EP)",
        "recipe_line": "~30%+ EPS+sales growth, gapped up post-result, neglected before -- mcap floor ~Rs300cr.",
        "cite": "TRADETM_NUANCES.md B1/B2/B3, F11; PRACTITIONER_SCREENERS.md Table 2 row 1",
        "status": "LIVE", "kind": "archetype", "archetype": "ep_ipo",
        "source": "discovery.build_bucket via candidates.discovery_bucket_map",
    },
    "d2_episodic": {
        "owner": "TradeTM", "label": "D2 / Episodic",
        "recipe_line": "Day-1 burst 10%+ out of a bottom-quartile-tight base, Day-2 inside/tight follow-through.",
        "cite": "TRADETM_NUANCES.md B5/B5b/B5c; PRACTITIONER_SCREENERS.md Table 2 row 3",
        "status": "LIVE", "kind": "archetype", "archetype": "d2_episodic",
        "source": "discovery.build_bucket via candidates.discovery_bucket_map",
    },
    "recent_listing": {
        "owner": "Umang / IPO playbook", "label": "IPO Inside-Bar (recent listing)",
        "recipe_line": "Recent listing + base + inside/NR7 bar coil -- velocity-only gate waived for fresh IPOs.",
        "cite": "STOCKGEEKS_NUANCES.md (IPO entry); PRACTITIONER_SCREENERS.md Table 3 row 3",
        "status": "LIVE", "kind": "archetype", "archetype": "recent_listing",
        "source": "discovery.build_bucket via candidates.discovery_bucket_map",
    },
    "reversal_busted": {
        "owner": "Manas Arora", "label": "Undercut & Recover",
        "recipe_line": "Undercut 10 & 20 MA then reclaim -- weak-hands-shaken-out names get priority for entry.",
        "cite": "extract_ma_small.md:65-68, 77-79; PRACTITIONER_SCREENERS.md Table 1 row 5",
        "status": "LIVE", "kind": "archetype", "archetype": ("reversal", "busted_reversal"),
        "source": "discovery.build_bucket via candidates.discovery_bucket_map",
    },
    "vcp_tightness": {
        "owner": "Minervini / Arora", "label": "VCP / Tightness",
        "recipe_line": "Volatility contraction, strong-start bottom-percentile tightness.",
        "cite": "extract_ma_small.md:142-144; PRACTITIONER_SCREENERS.md Table 1 row 4",
        "status": "LIVE", "kind": "archetype", "archetype": ("vcp_coil", "strong_start_ready"),
        "source": "discovery.build_bucket via candidates.discovery_bucket_map",
    },
    "pullback_to_rising_ma": {
        "owner": "Arora", "label": "Pullback To Rising MA",
        "recipe_line": "Prior-strength leg pulls back into a rising moving average -- buying force read off the prior leg.",
        "cite": "extract_ma_small.md:142-144; discovery.py _reversal_prior_strength; PRACTITIONER_SCREENERS.md Table 1 row 4",
        "status": "LIVE", "kind": "archetype", "archetype": "pullback_to_rising_ma",
        "source": "discovery.build_bucket via candidates.discovery_bucket_map",
    },
    "pullback_to_50ma": {
        "owner": "Arora", "label": "Pullback To 50MA",
        "recipe_line": "Prior-strength leg pulls back to the rising 50-day MA.",
        "cite": "extract_ma_small.md:142-144; discovery.py pullback_to_50ma; PRACTITIONER_SCREENERS.md Table 1 row 4",
        "status": "LIVE", "kind": "archetype", "archetype": "pullback_to_50ma",
        "source": "discovery.build_bucket via candidates.discovery_bucket_map",
    },
    "todays_movers": {
        "owner": "builder preset", "label": "Today's Movers",
        "recipe_line": "Top %change + volume + ADR -- day-1 bursts feed D2 watch per doctrine.",
        "cite": "TTM-B5b D2; screener.py PRESETS['TODAYS_MOVERS']",
        "status": "LIVE", "kind": "conditions", "conditions_preset": "TODAYS_MOVERS",
        "source": "screener.py conditions engine over daily_prices",
    },
    "ipo_inside_bar": {
        "owner": "Umang (StocksGeeks)", "label": "IPO First/Double Inside-Bar",
        "recipe_line": "Fresh-listed IPO makes first inside bar (double inside bar = immediate trade).",
        "cite": "STOCKGEEKS_NUANCES.md:52-57 (first inside bar, IPO_trading_transcript.md:87), "
                ":195-200 (double inside bar = immediate trigger, IPO_trading_transcript.md:112-113)",
        "status": "LIVE", "kind": "archetype", "archetype": "ipo_inside_bar",
        "source": "discovery.build_bucket via candidates.discovery_bucket_map",
    },
    "long_tail": {
        "owner": "Umang (StocksGeeks)", "label": "Long-Tail Candle",
        "recipe_line": "Tail length > 1.5x body; entry 1% above wick low (MBI-green gate not implemented -- no MBI in repo).",
        "cite": "STOCKGEEKS_NUANCES.md:66-71 (Long-Tail Candle, IPO_trading_transcript.md:75)",
        "status": "LIVE", "kind": "archetype", "archetype": "long_tail",
        "source": "discovery.build_bucket via candidates.discovery_bucket_map",
    },
    "weekly_base_breakout": {
        "owner": "TradeTM", "label": "Weekly Base Breakout",
        "recipe_line": "Weekly close > 20-week high pivot, volume >= 1.2x 20-week avg, close in upper portion of range.",
        "cite": "breakoutscanner (weekly timeframe extension)",
        "status": "LIVE", "kind": "archetype", "archetype": "weekly_base_breakout",
        "source": "discovery.build_bucket via candidates.discovery_bucket_map",
    },
    # --- BUILD: corpus-cited, unimplemented, greyed, no fake data --------
    "lf_jump": {
        "owner": "Manas Arora", "label": "Liquidity Force (LF) Jump",
        "recipe_line": "Liquidity force jumps 5x-50x in the last 10-15 days -- institutional-interest signal.",
        "cite": "extract_ma_small.md:67, 86-88; PRACTITIONER_SCREENERS.md Table 1 row 3",
        "status": "BUILD", "kind": "build", "source": None,
    },
    "aoi_down_base": {
        "owner": "Umang (StocksGeeks)", "label": "AOI / Down-Base Scoring",
        "recipe_line": "Consolidation must sit above the previous weekly base; reject if >40-50% fall from high.",
        "cite": "STOCKGEEKS_NUANCES.md (AOI); PRACTITIONER_SCREENERS.md Table 3 row 5",
        "status": "BUILD", "kind": "build", "source": None,
    },
}

# --- ChartsMaze trader-template presets: DATA-READY, thin reads only ----
# key -> (screener name in screener_hits.screener, owner label)
_CHARTSMAZE_TEMPLATES: dict[str, tuple[str, str]] = {
    "chhirag": ("chhirag", "Chhirag (ChartsMaze)"),
    "himanshu": ("himanshu", "Himanshu (ChartsMaze)"),
    "hiren": ("hiren", "Hiren (ChartsMaze)"),
    "nitin": ("nitin", "Nitin (ChartsMaze)"),
    "shashank": ("shashank", "Shashank (ChartsMaze)"),
}
_CHARTSMAZE_RECIPES: dict[str, str] = {
    "chhirag": "mcap Rs1000cr-2L cr, turnover >Rs5cr/50d, ex-5%-circuit.",
    "himanshu": "RS 70-100, volume gainers, gap-up, listed after 2024-01.",
    "hiren": "turnover >Rs3cr/20d + 1M return 20-100% OR 3M return 30-300%.",
    "nitin": "inside-bar/NR7 within 10/21/50/200 EMA bands.",
    "shashank": "EPS/sales/NP YoY >10%, ROE/ROCE>15, D/E<1, >200DMA.",
}
for _key, (_screener, _owner) in _CHARTSMAZE_TEMPLATES.items():
    PRESET_REGISTRY[_key] = {
        "owner": _owner, "label": f"{_owner.split(' ')[0]} (ChartsMaze template)",
        "recipe_line": _CHARTSMAZE_RECIPES[_key],
        "cite": f"chartsmaze_scanners.py SCREENER_REGISTRY[{_screener}-template.csv]; "
                "PRACTITIONER_SCREENERS.md ChartsMaze inventory",
        "status": "DATA_READY", "kind": "chartsmaze", "screener": _screener,
        "source": "chartsmaze_scanners.py screener_hits ingestion",
    }


# --- shared per-symbol row shaping --------------------------------------

def _watchlist_symbols(conn, date: str) -> set[str]:
    if conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='agent_watchlist'"
    ).fetchone() is None:
        return set()
    rows = conn.execute(
        "SELECT DISTINCT symbol FROM agent_watchlist WHERE scan_date = ? AND status != 'DROP'",
        (date,),
    ).fetchall()
    return {r["symbol"] for r in rows}


def _debate_symbols(conn, date: str) -> set[str]:
    if conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='agent_verdicts'"
    ).fetchone() is None:
        return set()
    rows = conn.execute(
        "SELECT DISTINCT symbol FROM agent_verdicts WHERE scan_date = ?", (date,),
    ).fetchall()
    return {r["symbol"] for r in rows}


def _persisted_bucket_map(conn, date: str) -> dict[str, dict[str, Any]]:
    """Read the nightly-persisted `discovery_bucket` table (written by
    discovery.persist_bucket during the pipeline run) -- a live
    discovery.build_bucket() call over the whole universe costs minutes,
    far too slow for a request-time scanner card/run. Empty dict (not an
    error) when no pipeline has run for `date` yet; callers fall back to
    a live compute only when this table is truly empty for the date, so
    a scanner never goes dark just because it's mid-pipeline."""
    if conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='discovery_bucket'"
    ).fetchone() is None:
        return {}
    rows = conn.execute(
        "SELECT symbol, archetypes_json, metrics_json FROM discovery_bucket WHERE scan_date = ?",
        (date,),
    ).fetchall()
    if not rows:
        return {}
    import json as _json
    out: dict[str, dict[str, Any]] = {}
    for r in rows:
        out[r["symbol"]] = {
            "archetypes": _json.loads(r["archetypes_json"]) if r["archetypes_json"] else [],
            "metrics": _json.loads(r["metrics_json"]) if r["metrics_json"] else {},
        }
    return out


def _bucket_map(conn, date: str) -> dict[str, dict[str, Any]]:
    """Persisted-first bucket read; falls back to a live compute only when
    the nightly stage never ran for this date (e.g. a fresh/replay DB)."""
    bucket = _persisted_bucket_map(conn, date)
    if bucket:
        return bucket
    return scanner_candidates.discovery_bucket_map(conn, date)


def _snap_for(conn, date: str, symbol: str, rs_map: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """pct_chg/volume for ONE symbol via screener.py's per-symbol path --
    matched-set sized (dozens), unlike latest_universe_metrics' full-
    universe scan, so archetype/chartsmaze rows stay request-time-cheap."""
    try:
        snap = scanner_screener.metrics_for_symbol(conn, symbol, date, rs_map=rs_map)
    except Exception:  # noqa: BLE001 — a per-symbol metrics miss must not blank the row
        snap = None
    return snap or {}


def _archetype_rows(conn, date: str, archetype: str | tuple) -> list[dict[str, Any]]:
    """Rows for a discovery_bucket archetype (or tuple of archetypes,
    OR-ed) -- pct_up_65d_low/adr20/purple_dot_count from bucket metrics,
    rs from stock_rs_map. Reads the nightly-persisted bucket (see
    `_bucket_map`); pct_chg/volume are filled per-matched-symbol (cheap --
    NOT a full-universe metrics scan)."""
    bucket = _bucket_map(conn, date)
    if not bucket:
        return []
    wanted = (archetype,) if isinstance(archetype, str) else tuple(archetype)
    rs_map = scanner_candidates.stock_rs_map(date)
    out = []
    for symbol, entry in bucket.items():
        archetypes = entry.get("archetypes") or []
        if not any(a in archetypes for a in wanted):
            continue
        metrics = entry.get("metrics") or {}
        snap = _snap_for(conn, date, symbol, rs_map)
        out.append({
            "symbol": symbol,
            "pct_up_65d_low": metrics.get("pct_up_from_65d_low"),
            "adr20": metrics.get("adr20"),
            "rs": (rs_map.get(symbol) or {}).get("rs"),
            "purple_dot_count": metrics.get("purple_dot_count_60d"),
            "pct_chg": snap.get("pct_change_1d"),
            "volume": snap.get("volume"),
            "archetypes": archetypes,
        })
    return out


def _conditions_rows(conn, date: str, conditions_preset: str) -> list[dict[str, Any]]:
    preset_def = scanner_screener.PRESETS.get(conditions_preset)
    if preset_def is None:
        return []
    rows = scanner_screener.latest_universe_metrics(conn, date)
    filtered = scanner_screener.apply_conditions(rows, preset_def["conditions"])
    out = []
    for r in filtered:
        out.append({
            "symbol": r["symbol"],
            "pct_up_65d_low": r.get("pct_up_from_65d_low"),
            "adr20": r.get("adr20"),
            "rs": r.get("rs"),
            "purple_dot_count": r.get("purple_dot_count_60d"),
            "pct_chg": r.get("pct_change_1d"),
            "volume": r.get("volume"),
        })
    return out


def _conditions_list_rows(conn, date: str, conditions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Same shape as _conditions_rows but for an arbitrary {field,op,value}
    list -- used for arora_baseline (built inline, see ARORA_BASELINE_CONDITIONS)
    and for saved user_screens (key=user:<name>)."""
    rows = scanner_screener.latest_universe_metrics(conn, date)
    filtered = scanner_screener.apply_conditions(rows, conditions)
    out = []
    for r in filtered:
        out.append({
            "symbol": r["symbol"],
            "pct_up_65d_low": r.get("pct_up_from_65d_low"),
            "adr20": r.get("adr20"),
            "rs": r.get("rs"),
            "purple_dot_count": r.get("purple_dot_count_60d"),
            "pct_chg": r.get("pct_change_1d"),
            "volume": r.get("volume"),
        })
    return out


# Arora screener.in baseline (Table 1 row 1): 3m return > 30%, NSE, avg 30d
# volume > 200,000. 3m return isn't a screener.py FIELD (only 1d %change is)
# so it's computed here from daily_prices directly rather than forced
# through the generic conditions engine; avg-volume-30d likewise.
def _arora_baseline_rows(conn, date: str) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT DISTINCT symbol FROM daily_prices WHERE series='EQ' AND trade_date = ?",
        (date,),
    ).fetchall()
    symbols = [r["symbol"] for r in rows]
    if not symbols:
        return []
    rs_map = scanner_candidates.stock_rs_map(date)
    out = []
    for sym in symbols:
        bars = scanner_screener._load_bars(conn, sym, date, limit=80)
        if not bars or bars[-1].get("date") != date:
            continue
        if len(bars) < 64:
            continue
        close_now = bars[-1].get("close")
        close_63d_ago = bars[max(0, len(bars) - 64)].get("close")
        if close_now is None or not close_63d_ago:
            continue
        try:
            ret_3m = (float(close_now) - float(close_63d_ago)) / float(close_63d_ago) * 100.0
        except (TypeError, ValueError, ZeroDivisionError):
            continue
        if ret_3m <= 30.0:
            continue
        vols = [b.get("volume") for b in bars[-30:] if b.get("volume") is not None]
        avg_vol_30d = (sum(vols) / len(vols)) if vols else None
        if avg_vol_30d is None or avg_vol_30d <= 200_000:
            continue
        snap = scanner_screener.metrics_for_symbol(conn, sym, date, bars=bars, rs_map=rs_map)
        out.append({
            "symbol": sym,
            "pct_up_65d_low": dm.pct_up_from_65d_low(bars),
            "adr20": (snap or {}).get("adr20"),
            "rs": (snap or {}).get("rs"),
            "purple_dot_count": (snap or {}).get("purple_dot_count_60d"),
            "pct_chg": (snap or {}).get("pct_change_1d"),
            "volume": bars[-1].get("volume"),
            "ret_3m_pct": round(ret_3m, 2),
            "avg_vol_30d": round(avg_vol_30d),
        })
    return out


def _chartsmaze_rows(conn, date: str, screener: str) -> list[dict[str, Any]]:
    if conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='screener_hits'"
    ).fetchone() is None:
        return []
    hits = conn.execute(
        "SELECT symbol, rs_rating, basic_industry FROM screener_hits "
        "WHERE trade_date = ? AND screener = ? ORDER BY symbol",
        (date, screener),
    ).fetchall()
    if not hits:
        return []
    rs_map = scanner_candidates.stock_rs_map(date)
    out = []
    for h in hits:
        snap = _snap_for(conn, date, h["symbol"], rs_map)
        out.append({
            "symbol": h["symbol"],
            "pct_up_65d_low": snap.get("pct_up_from_65d_low"),
            "adr20": snap.get("adr20"),
            "rs": h["rs_rating"] if h["rs_rating"] is not None else snap.get("rs"),
            "purple_dot_count": snap.get("purple_dot_count_60d"),
            "pct_chg": snap.get("pct_change_1d"),
            "volume": snap.get("volume"),
            "basic_industry": h["basic_industry"],
        })
    return out


def _rs_fallback_map(conn, date: str) -> dict[str, float]:
    """F2: stock_rs_map (used by screener.py's per-symbol `rs`) only covers
    ~165 symbols; screener_hits.rs_rating (ChartsMaze nightly ingestion)
    covers ~2000+ symbols on a given date. Archetype/conditions presets
    (arora_baseline, persistent_momentum, ...) otherwise come back almost
    entirely rs=None even though a broader RS number exists -- this map is
    the fallback applied in run_preset() when a row's own `rs` is None."""
    if conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='screener_hits'"
    ).fetchone() is None:
        return {}
    rows = conn.execute(
        "SELECT symbol, rs_rating FROM screener_hits "
        "WHERE trade_date = ? AND rs_rating IS NOT NULL",
        (date,),
    ).fetchall()
    out: dict[str, float] = {}
    for r in rows:
        if r["symbol"] not in out:
            out[r["symbol"]] = r["rs_rating"]
    return out


def build_scout_note(
    label: str | None,
    pct_up_65d_low: float | None,
    purple_dot_count: int | None,
    fallback_reasoning: str | None = None,
) -> str | None:
    """V4-T3/F2: one deterministic Scout annotation line, shared by DEBATE
    cards (manas_os/api/app.py) and SCANNERS result rows (run_preset below)
    so the two never drift on how a scout_note is built. Prefers the
    label + a key metric; falls back to the first sentence of an LLM
    reasoning string (DEBATE only has this fallback available)."""
    if pct_up_65d_low is not None:
        note = f"{label or 'setup'}: up {pct_up_65d_low:.1f}% off 65d-low"
        if purple_dot_count:
            note += f", {purple_dot_count} purple dot{'s' if purple_dot_count != 1 else ''}"
        return note
    if fallback_reasoning:
        import re as _re
        first_sentence = _re.split(r"(?<=[.!?])\s+", fallback_reasoning.strip())
        return first_sentence[0] if first_sentence else None
    return None


def _fast_arora_baseline_count(conn, date: str) -> int:
    sessions = [
        row["trade_date"]
        for row in conn.execute(
            "SELECT DISTINCT trade_date FROM daily_prices WHERE series='EQ' AND trade_date<=? "
            "ORDER BY trade_date DESC LIMIT 64",
            (date,),
        ).fetchall()
    ]
    if len(sessions) < 64:
        return 0
    row = conn.execute(
        "SELECT COUNT(*) n FROM daily_prices now JOIN daily_prices old"
        " ON old.symbol=now.symbol AND old.series='EQ' AND old.trade_date=?"
        " WHERE now.series='EQ' AND now.trade_date=? AND old.close>0"
        " AND (now.close-old.close)/old.close*100.0>30.0"
        " AND (SELECT AVG(v.volume) FROM daily_prices v WHERE v.symbol=now.symbol"
        " AND v.series='EQ' AND v.trade_date BETWEEN ? AND ?) > 200000",
        (sessions[-1], sessions[0], sessions[29], sessions[0]),
    ).fetchone()
    return int(row["n"]) if row else 0


def _fast_todays_movers_count(conn, date: str) -> int:
    sessions = [
        row["trade_date"]
        for row in conn.execute(
            "SELECT DISTINCT trade_date FROM daily_prices WHERE series='EQ' AND trade_date<=? "
            "ORDER BY trade_date DESC LIMIT 20",
            (date,),
        ).fetchall()
    ]
    if len(sessions) < 20:
        return 0
    row = conn.execute(
        "SELECT COUNT(*) n FROM daily_prices now"
        " WHERE now.series='EQ' AND now.trade_date=? AND now.prev_close>0"
        " AND (now.close-now.prev_close)/now.prev_close*100.0>=5.0"
        " AND now.volume>=1000000 AND (SELECT AVG((v.high-v.low)*100.0/v.close)"
        " FROM daily_prices v WHERE v.symbol=now.symbol AND v.series='EQ'"
        " AND v.trade_date BETWEEN ? AND ? AND v.close>0)>=4.0",
        (sessions[0], sessions[-1], sessions[0]),
    ).fetchone()
    return int(row["n"]) if row else 0


def preset_hit_counts(conn, date: str) -> dict[str, int | None]:
    """Return every preset-card count in one bounded pass.

    Counts are intentionally read from persisted nightly artefacts.  A card
    request must never fall back to ``discovery.build_bucket`` or materialise
    full-universe per-symbol metrics: those are pipeline jobs, not HTTP work.
    ``None`` therefore means "not computed for this session", not zero hits.
    """
    counts: dict[str, int | None] = {
        key: None if definition["kind"] == "build" else 0
        for key, definition in PRESET_REGISTRY.items()
    }

    # Archetype membership is already persisted by the nightly discovery
    # stage. Use the most recent completed bucket at or before the requested
    # market date, so a weekend/current-session page remains useful.
    bucket_date = None
    if conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='discovery_bucket'"
    ).fetchone() is not None:
        row = conn.execute(
            "SELECT MAX(scan_date) AS d FROM discovery_bucket WHERE scan_date <= ?",
            (date,),
        ).fetchone()
        bucket_date = row["d"] if row else None
    archetype_counts: dict[str, int] = {}
    if bucket_date:
        import json as _json
        for row in conn.execute(
            "SELECT archetypes_json FROM discovery_bucket WHERE scan_date = ?",
            (bucket_date,),
        ).fetchall():
            for archetype in (_json.loads(row["archetypes_json"] or "[]")):
                archetype_counts[archetype] = archetype_counts.get(archetype, 0) + 1

    for key, definition in PRESET_REGISTRY.items():
        if definition["kind"] != "archetype":
            continue
        if not bucket_date:
            counts[key] = None
            continue
        wanted = definition["archetype"]
        wanted = (wanted,) if isinstance(wanted, str) else tuple(wanted)
        counts[key] = sum(archetype_counts.get(name, 0) for name in wanted)

    # ChartsMaze templates share one persisted table and one grouped query.
    if conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='screener_hits'"
    ).fetchone() is not None:
        grouped = {
            row["screener"]: int(row["n"])
            for row in conn.execute(
                "SELECT screener, COUNT(*) AS n FROM screener_hits "
                "WHERE trade_date = ? GROUP BY screener",
                (date,),
            ).fetchall()
        }
        for key, definition in PRESET_REGISTRY.items():
            if definition["kind"] == "chartsmaze":
                counts[key] = grouped.get(definition["screener"], 0)

    if "arora_baseline" in counts:
        counts["arora_baseline"] = _fast_arora_baseline_count(conn, date)
    if "todays_movers" in counts:
        counts["todays_movers"] = _fast_todays_movers_count(conn, date)
    return counts


def preset_hit_count(conn, key: str, date: str) -> int | None:
    """Compatibility wrapper for a single card count."""
    definition = PRESET_REGISTRY.get(key)
    if definition is None:
        return None
    return preset_hit_counts(conn, date).get(key)


def run_preset(conn, key: str, date: str) -> dict[str, Any]:
    """/api/scanners/run contract: hits[] for a preset key, each row +
    in_watchlist/in_debate. Also accepts key='user:<name>' -> a saved
    user_screens conditions-set run through the same contract."""
    watchlist = _watchlist_symbols(conn, date)
    debate = _debate_symbols(conn, date)

    if key.startswith("user:"):
        name = key[len("user:"):]
        scanner_screener.ensure_screens_schema(conn)
        row = conn.execute(
            "SELECT conditions_json FROM user_screens WHERE name = ?", (name,)
        ).fetchone()
        if row is None:
            return {"available": False, "key": key, "error": f"no saved screen {name!r}", "hits": []}
        import json
        conditions = json.loads(row["conditions_json"]) if row["conditions_json"] else []
        hits = _conditions_list_rows(conn, date, conditions)
        rs_fallback = _rs_fallback_map(conn, date)
        for h in hits:
            h["in_watchlist"] = h["symbol"] in watchlist
            h["in_debate"] = h["symbol"] in debate
            if h.get("rs") is None:
                h["rs"] = rs_fallback.get(h["symbol"])
            h["scout_note"] = build_scout_note(name, h.get("pct_up_65d_low"), h.get("purple_dot_count"))
        return {"available": True, "key": key, "date": date, "kind": "user", "hits": hits}

    definition = PRESET_REGISTRY.get(key)
    if definition is None:
        return {"available": False, "key": key, "error": f"unknown preset {key!r}", "hits": []}
    kind = definition["kind"]
    if kind == "build":
        return {"available": False, "key": key, "status": "BUILD", "hits": []}
    if kind == "archetype":
        hits = _archetype_rows(conn, date, definition["archetype"])
    elif kind == "chartsmaze":
        hits = _chartsmaze_rows(conn, date, definition["screener"])
    elif kind == "conditions":
        hits = _arora_baseline_rows(conn, date) if key == "arora_baseline" else _conditions_rows(conn, date, definition["conditions_preset"])
    else:
        hits = []
    label = definition.get("label")
    rs_fallback = _rs_fallback_map(conn, date)
    for h in hits:
        h["in_watchlist"] = h["symbol"] in watchlist
        h["in_debate"] = h["symbol"] in debate
        if h.get("rs") is None:
            h["rs"] = rs_fallback.get(h["symbol"])
        h["scout_note"] = build_scout_note(label, h.get("pct_up_65d_low"), h.get("purple_dot_count"))
    return {"available": True, "key": key, "date": date, "kind": kind, "hits": hits}
