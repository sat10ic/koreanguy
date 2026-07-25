"""`manas` CLI — the single orchestration entrypoint (anti-mashup rule #2).

    python -m manas_os.cli init-db
    python -m manas_os.cli run-eod [--date YYYY-MM-DD]

`run-eod` is the ONE command that drives the whole daily pipeline. Stages register here as
they are built (P0 ingest → P1 regime → P2 scan/readiness → ...); each stage writes a
pipeline_runs row so Pipeline Health and staleness detection stay honest.
"""
from __future__ import annotations

import argparse
import sys
from datetime import date as _date

from manas_os import db
from manas_os.ops_logging import configure_ops_logger


# Stages that may be missing from run_manifest without making a date incomplete.
# Derived from the stage registry comments: EXPERIMENTAL / display-only /
# counterfactual-only / shadow-only. Everything else is required (defect #2).
OPTIONAL_STAGES = frozenset({
    "breadth_counts",         # display/enrichment only
    "regime_vol_har",         # EXPERIMENTAL, display-only
    "regime_hmm",             # EXPERIMENTAL
    "ml_sector_downside",     # EXPERIMENTAL
    "discovery_bucket",       # counterfactual only
    "focus_themes",           # discovery aggregation, failure-safe
    "theme_pulse",            # correlated-group surfacing over scan/WATCH/discovery, failure-safe
    "ml_direction",           # EXPERIMENTAL
    "ml_breakout_rf",         # EXPERIMENTAL, shadow-only
})


def fetch_eod_sources() -> list[str]:
    """Refresh bhavcopy and ChartsMaze inputs; return one status line per source."""
    lines, _code = fetch_eod_sources_with_code()
    return lines


def fetch_eod_sources_with_code() -> tuple[list[str], int]:
    """Like fetch_eod_sources, plus a worst-case exit code (0 ok, 1 any failure).

    Source-fetch failures must contribute to the process exit code (audit
    defect #2) so a scheduled task cannot report green when fetch died.
    Non-zero subprocess exit, timeout, and exception each yield code 1
    (partial-level: pipeline may still proceed on cached files).
    """
    import subprocess
    from pathlib import Path

    repo = Path(__file__).resolve().parents[2]
    steps = [
        (
            "fetch_bhavcopy",
            [sys.executable, "download_bhavcopy.py", "--source", "both", "--days", "5"],
            repo / "bhavcopy_extractor",
            300,
        ),
        (
            "fetch_chartsmaze",
            [sys.executable, "extractor.py", "--headless"],
            repo / "chartsmaze_extractor",
            900,
        ),
    ]
    results: list[str] = []
    worst = 0
    for name, argv, cwd, timeout in steps:
        try:
            completed = subprocess.run(
                argv, cwd=str(cwd), capture_output=True, text=True, timeout=timeout
            )
            detail = ""
            if completed.returncode != 0:
                detail = f" — {(completed.stderr or completed.stdout or '')[-200:].strip()}"
                worst = max(worst, 1)
            results.append(f"{name}: exit {completed.returncode}{detail}")
        except subprocess.TimeoutExpired:
            results.append(f"{name}: TIMED OUT ({timeout}s) — source not refreshed")
            worst = max(worst, 1)
        except Exception as exc:  # noqa: BLE001 — one source must not block cached ingest
            results.append(f"{name}: FAILED — {exc}")
            worst = max(worst, 1)
    return results, worst


def _cmd_init_db(args: argparse.Namespace) -> int:
    conn = db.init_db()
    tables = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    )]
    conn.close()
    print(f"init-db ok -> {db.DB_PATH}")
    print(f"tables ({len(tables)}): {', '.join(tables)}")
    return 0


def _load_stages() -> list[tuple[str, object]]:
    """Ordered daily pipeline, imported lazily so `init-db` needs no heavy deps.

    Stages register here as phases land. P0: ingest sources -> compute indicators.
    (P1 adds the regime/XP snapshot stage after ingest.)
    """
    from manas_os.alerts import eod, telegram_engine
    from manas_os.sources import bhavcopy, breadth_counts, chartsmaze, chartsmaze_scanners, classify_universe, earnings_calendar, fii_dii, fundamentals, nse_deals, nse_indices, universe_breadth
    from manas_os.engine import indicators
    from manas_os.regime import mars_ingest, snapshot, vol_har, regime_hmm
    from manas_os.ml import sector_downside
    from manas_os.scanner import expectancy
    from manas_os.agents import coach, debate
    from manas_os.advisor import advisor
    from manas_os.scanner import candidates, discovery, focus, footprint, outcomes, setup_regime, theme_pulse
    from manas_os.ml import direction_lgbm, screener_calibration, breakout_outcome_rf
    from manas_os.alpha import pipeline as alpha_pipeline
    from manas_os.alpha import symbol_identity as alpha_symbol_identity
    return [
        ("ingest_bhavcopy", bhavcopy.run),                  # prices + delivery% (local files)
        ("alpha_symbol_identity", alpha_symbol_identity.run),  # point-in-time identity/universe summary (derived from daily_prices only)
        ("ingest_fii_dii", fii_dii.run),                    # F7: FII/DII cash flows (groww.in; failure-safe skip)
        ("ingest_universe_breadth", universe_breadth.run),  # NIFTYMIDSML400 breadth from bhavcopy (feeds XP/MBI)
        ("breadth_counts", breadth_counts.run),             # Market Breadth V2.0 daily counts from daily_prices (display/enrichment only; BREADTH_ENRICHMENT_WAVE Step 0)
        ("ingest_chartsmaze", chartsmaze.run),              # sector/breadth freshness (local files)
        ("ingest_chartsmaze_scanners", chartsmaze_scanners.run),  # screener hits + quality signals (local files)
        ("classify_universe", classify_universe.run),        # populate universe.sector/industry (feeds alpha_features; runs after chartsmaze_scanners fills basic_industry)
        ("ingest_fundamentals", fundamentals.run),          # W5 quarterly fundamentals history
        ("ingest_disclosures", __import__("manas_os.sources.disclosures", fromlist=["run"]).run),  # disclosure feeds (local files)
        ("ingest_nse_deals", nse_deals.run),                # NSE-direct bulk/block deals; independent of ChartsMaze
        ("ingest_earnings_calendar", earnings_calendar.run),  # EARNINGS_SEASON_HANDHOLD step 1: forward results calendar (BSE primary; NSE stub secondary; failure-safe)
        ("indicators", indicators.run),                     # per-symbol features (depends on prices)
        ("ingest_nse_indices", nse_indices.run),            # every NSE index close incl. NIFTY 50 + India VIX (feeds vol_har)
        ("ingest_mars", mars_ingest.run),                   # sector RS vs benchmark (Fyers; graceful skip)
        ("regime_snapshot", snapshot.run),                  # XP + MBI + posture (depends on breadth)
        ("regime_vol_har", vol_har.run),                    # SHIP-1 #16 (I1): HAR-RV vol_forecast [EXPERIMENTAL]; display-only, gated on QLIKE beating naive
        ("regime_hmm", regime_hmm.run),                     # SHIP-1 #17 (I5): HMM regime confirmation [EXPERIMENTAL]; stored but display-gated (n>=20 live), failure-safe skip w/o hmmlearn
        ("ml_sector_downside", sector_downside.run),        # SHIP-1 #15 (I14): hierarchical sector downside p_drawdown_5d [EXPERIMENTAL]; gated on Brier beating base rate
        ("alpha_features", alpha_pipeline.run_features),     # causal features + the one activity-score writer
        ("footprint_driver", footprint.run),                 # score-consuming price/volume classifier
        ("scan_candidates", candidates.run),                # P2 setup candidates + readiness
        ("discovery_bucket", discovery.run),                # WAVE K K4: Stage-1 sensitive bucket (counterfactual only; registered AFTER scan_candidates, failure-safe)
        ("focus_themes", focus.run),                        # theme-of-the-day aggregation over discovery_bucket (registered AFTER discovery_bucket, failure-safe)
        ("theme_pulse", theme_pulse.run),                   # correlated-group surfacing: scan+WATCH+discovery grouped by industry (registered AFTER discovery_bucket, failure-safe)
        ("agents_debate", debate.run),                      # additive verdict overlay on persisted candidates
        ("alpha_memory", alpha_pipeline.run_memory),         # immutable outcome-aware debate memory
        ("agents_coach", coach.run),                        # journal coach over open positions (exit-safe)
        ("expectancy", expectancy.run),                     # learnings loop (T2.3b)
        ("advisor", advisor.run),                           # ADVISOR second-opinion notes
        ("candidate_outcomes", outcomes.run),               # T+5/T+10/T+20 forward-return plumbing
        ("setup_regime", setup_regime.run),                  # SETUP-REGIME factor: rolling point-in-time hot/cold read per setup family (registered AFTER scan_candidates/candidate_outcomes; failure-safe, additive-only)
        ("screener_calibration", screener_calibration.run), # SHIP-1 #8: screener-hit forward-return calibration
        ("ml_direction", direction_lgbm.run),               # SHIP-1 #7: LightGBM direction P(up 10d) [EXPERIMENTAL]; failure-safe skip w/o lightgbm
        ("ml_breakout_rf", breakout_outcome_rf.run),         # Random Forest breakout success probability [EXPERIMENTAL]; shadow-only
        ("eod_alerts", eod.run),                            # P3 nightly manual-trading alerts
        ("telegram_digest", telegram_engine.run),            # T4.1 deterministic digest + armed list
    ]
    # breadth_sheet.py retained as a fallback provider (different universe), not
    # in the daily pipeline — the regime now runs on NIFTYMIDSML400 computed
    # breadth for scale-correctness vs the reference.


def _cmd_backfill_snapshots(args: argparse.Namespace) -> int:
    """Replay breadth_daily history through the live regime-snapshot path.

    One-time-ish operation (I1, plan §P1.5) — not a daily run-eod stage,
    since after the first run there's nothing pending most days. Safe to
    re-run: skips dates that already have a snapshot unless --force.
    """
    from manas_os.regime import backfill as backfill_mod

    conn = db.init_db()
    result = backfill_mod.backfill_snapshots(
        conn, start_date=args.start, end_date=args.end, force=args.force
    )
    conn.close()
    print(f"backfill-snapshots: {result['status']}, {result['dates_processed']} date(s) processed")
    if result["first_failure"]:
        print(f"  stopped at {result['first_failure']}")
    return 0 if result["status"] == "ok" else 1


def _cmd_breadth_backfill(args: argparse.Namespace) -> int:
    from manas_os.sources import breadth_counts

    conn = db.init_db()
    try:
        rows = breadth_counts.backfill_wave2_metrics(conn, sessions=args.sessions)
    finally:
        conn.close()
    print(f"breadth-backfill: {rows} session(s) updated")
    return 0


def _cmd_alpha_backfill(args: argparse.Namespace) -> int:
    from manas_os.alpha import backfill as alpha_backfill

    conn = db.init_db()
    try:
        result = alpha_backfill.backfill_factor_evaluations(
            conn, start_date=args.start, end_date=args.end
        )
    finally:
        conn.close()
    print(
        f"alpha-backfill {args.start}..{args.end}: "
        f"evaluations={result['evaluations_written']} "
        f"dates_processed={result['dates_processed']} "
        f"dates_skipped_insufficient_future="
        f"{result['dates_skipped_insufficient_future']} "
        f"factors_skipped_missing_inputs="
        f"{result['factors_skipped_missing_inputs']}"
    )
    return 0


def _cmd_replay(args: argparse.Namespace) -> int:
    from manas_os.backtest.replay import format_ab_table, format_replay_table, persist_replay, replay

    conn = db.init_db()
    try:
        if args.persist:
            result = persist_replay(conn, args.start, args.end)
            print(f"persist-replay {args.start}..{args.end}: {result}")
            return 0 if result["status"] == "ok" else 1

        if args.train_start or args.train_end or args.test_start or args.test_end:
            required = [args.train_start, args.train_end, args.test_start, args.test_end]
            if any(v is None for v in required):
                raise SystemExit("--train-start/--train-end/--test-start/--test-end must be supplied together")
            train = replay(conn, args.train_start, args.train_end, args.config)
            test = replay(conn, args.test_start, args.test_end, args.config)
            print(format_replay_table(train, title=f"Train window ({args.config})"))
            print()
            print(format_replay_table(test, title=f"Test window ({args.config})"))
            return 0

        if args.a or args.b:
            if not args.a or not args.b:
                raise SystemExit("--a and --b must be supplied together")
            left = replay(conn, args.start, args.end, args.a)
            right = replay(conn, args.start, args.end, args.b)
            print(format_ab_table(left, right))
            return 0

        result = replay(conn, args.start, args.end, args.config)
        print(format_replay_table(result))
        return 0
    finally:
        conn.close()


def eod_stage_names() -> list[str]:
    """Ordered stage names for a full run-eod (including refresh_live_quotes)."""
    return ["refresh_live_quotes", *(name for name, _ in _load_stages())]


def required_stage_names() -> list[str]:
    """Stages that must finish ok/partial/skip in run_manifest for date completion."""
    return [n for n in eod_stage_names() if n not in OPTIONAL_STAGES]


def run_eod(
    run_date: str,
    *,
    fetch_sources_first: bool = True,
    requested_by: str = "cli",
) -> int:
    """Run the canonical EOD stage list, optionally after refreshing source files.

    Exit codes (audit defect #2): 0 succeeded, 1 partial (or source-fetch
    failure), 2 failed. The runner result is no longer discarded.
    """
    from manas_os import jobs
    from manas_os.live import refresh as live_refresh

    logger = configure_ops_logger("pipeline")
    worst = 0
    if fetch_sources_first:
        lines, fetch_code = fetch_eod_sources_with_code()
        for result in lines:
            logger.info(result)
        worst = max(worst, fetch_code)
    conn = db.init_db()
    # API-first: populate the provisional live cache before EOD sources and
    # models run. The stage fails visibly when Fyers auth is absent, while the
    # shared runner continues into NSE/ChartsMaze fallback stages.
    stages = [("refresh_live_quotes", live_refresh.stage), *_load_stages()]
    logger.info("run-eod %s: %s stage(s) registered", run_date, len(stages))

    def _report(result: jobs.StageResult) -> None:
        if result.status == "ok":
            logger.info("[ok] %s", result.name)
        elif result.status in ("skip", "partial"):
            logger.info("[%s] %s: %s", result.status, result.name, result.error or "")
        else:
            logger.error("[FAIL] %s: %s", result.name, result.error)
    try:
        try:
            result = jobs.run_stages(
                conn, run_date, stages, requested_by=requested_by, on_stage=_report
            )
            worst = max(worst, int(result.get("exit_code", jobs.status_exit_code(result["status"]))))
        except Exception:
            # Catastrophic runner failure: honest exit 2 so the scheduler
            # records non-zero instead of a traceback-only crash.
            logger.exception("run-eod %s crashed", run_date)
            worst = max(worst, 2)
    finally:
        conn.close()
    return worst


def _cmd_run_eod(args: argparse.Namespace) -> int:
    return run_eod(args.date or _date.today().isoformat())


def _cmd_live_replay(args: argparse.Namespace) -> int:
    """`manas live-replay` -- the mandated first deliverable (LIVE_LOOP_FABLE
    §3.1). Zero network calls; drives alerts.live_fsm through a fixture
    tick session and reports the safety assertions (dedupe on replay, TTL
    expiry, regime caps, halt-blocks-entries-not-exits, confirm revalidation)."""
    from manas_os.live import replay as live_replay

    conn = db.init_db()
    try:
        fixture = live_replay.load_fixture(args.fixture)
        result = live_replay.run_replay(conn, fixture, replay_twice=not args.no_dedupe_check)
        print(live_replay.format_replay_report(result))
        dedupe = result.get("replay_dedupe_check") or {}
        ok = dedupe.get("zero_duplicate_transitions", True) and dedupe.get("zero_duplicate_pushes", True)
        print(f"\nreplay: {'PASS' if ok else 'FAIL'}")
        return 0 if ok else 1
    finally:
        conn.close()


def _cmd_live_loop(args: argparse.Namespace) -> int:
    """`manas live-loop --paper` -- dry-runs the intraday session driver.

    PAPER MODE ONLY (no flag flips this). Seeds tonight's armed_list into the
    FSM, probes Fyers auth + market-hours state honestly, and either connects
    (during NSE hours with a valid token) or reports why not and shuts down
    clean -- it never pretends coverage it doesn't have (LIVE_LOOP_FABLE §3.4).
    """
    from manas_os.alerts import live_fsm
    from manas_os.live import session as live_session

    if not args.paper:
        print("live-loop: refusing to start without --paper (paper-first is locked for Stage 1)")
        return 1

    run_date = args.date or _date.today().isoformat()
    conn = db.init_db()
    try:
        seeded = live_fsm.arm_from_armed_list(conn, run_date)
        print(f"live-loop --paper {run_date}: seeded {seeded} armed symbol(s) from tonight's armed_list")
        sess = live_session.LiveSession(conn, run_date)
        probe = sess.probe()
        print(f"session state: {probe['state']} -- {probe['detail']}")
        if probe["state"] == live_session.STATE_CONNECTING and not args.probe_only:
            result = sess.connect()
            print(f"connect: {result}")
            sess.close()
        print("live-loop --paper: shutting down clean")
        return 0
    finally:
        conn.close()


def _cmd_scorecard(args: argparse.Namespace) -> int:
    """`manas scorecard --start ... --end ... [--out DIR]` -- funnel +
    forward-performance report over the scan cascade (scanner/scorecard.py).
    Read-only; writes only the two report files below."""
    import json
    from pathlib import Path

    from manas_os.scanner import scorecard

    conn = db.init_db()
    try:
        result = scorecard.build(conn, args.start, args.end)
    finally:
        conn.close()
    md = scorecard.render_md(result)

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = f"SCORECARD_{args.start}_{args.end}"
    md_path = out_dir / f"{stem}.md"
    json_path = out_dir / f"{stem}.json"
    md_path.write_text(md, encoding="utf-8")
    json_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    n_dates = len(result["dates"])
    print(f"scorecard {args.start}..{args.end}: {n_dates} scan_date(s) -> {md_path}")
    print(f"scorecard: json twin -> {json_path}")
    return 0


def _cmd_integrity(args: argparse.Namespace) -> int:
    """`manas integrity [--date YYYY-MM-DD] [--out DIR]` -- pipeline/data
    integrity watchdog (manas_os/integrity/report.py): freshness (did the
    pipeline actually run for the most recent session), silent skips (did a
    stage report skip while writing zero rows), verdict grading, card/JSON
    self-consistency, threshold-vs-evaluation-date overfit capacity,
    survivorship bias, and a static look-ahead-bias scan. STRICTLY read-only
    over an explicit `file:...?mode=ro` connection -- never db.connect()/
    db.init_db(), so this can never lock or corrupt a live pipeline (see
    integrity/report.py's docstring for why that distinction matters here).

    Exit code is non-zero whenever overall status is FAIL -- the user has
    been burned before by commands that report success while doing nothing;
    this command must never join that list."""
    import json
    from pathlib import Path

    from manas_os.integrity import report as integrity_report

    today = _date.fromisoformat(args.date) if args.date else _date.today()
    result = integrity_report.run_all(db.DB_PATH, today)
    md = integrity_report.to_markdown(result)

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = f"INTEGRITY_{today.isoformat()}"
    md_path = out_dir / f"{stem}.md"
    json_path = out_dir / f"{stem}.json"
    md_path.write_text(md, encoding="utf-8")
    json_path.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")

    print(md)
    print(f"integrity: report written -> {md_path}")
    print(f"integrity: json twin -> {json_path}")
    return 0 if result["overall_status"] != "FAIL" else 1


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="manas", description="sat10ic os")
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("init-db", help="create manas.db schema").set_defaults(func=_cmd_init_db)
    eod = sub.add_parser("run-eod", help="run the end-of-day pipeline")
    eod.add_argument("--date", help="trade date YYYY-MM-DD (default: today)")
    eod.set_defaults(func=_cmd_run_eod)
    bf = sub.add_parser("backfill-snapshots", help="replay breadth_daily history into regime_snapshots")
    bf.add_argument("--start", help="earliest trade_date YYYY-MM-DD (default: all history)")
    bf.add_argument("--end", help="latest trade_date YYYY-MM-DD (default: all history)")
    bf.add_argument("--force", action="store_true", help="recompute dates that already have a snapshot")
    bf.set_defaults(func=_cmd_backfill_snapshots)
    bfb = sub.add_parser("breadth-backfill", help="fill DMA-cross and monthly breadth history")
    bfb.add_argument("--sessions", type=int, default=250, help="most recent sessions to fill")
    bfb.set_defaults(func=_cmd_breadth_backfill)
    abf = sub.add_parser(
        "alpha-backfill", help="replay historical point-in-time factor IC evaluations"
    )
    abf.add_argument("--start", required=True, help="first evaluation date YYYY-MM-DD")
    abf.add_argument("--end", required=True, help="last evaluation date YYYY-MM-DD")
    abf.set_defaults(func=_cmd_alpha_backfill)
    rp = sub.add_parser("replay", help="replay setup candidates over a historical window")
    rp.add_argument("--start", default="2025-06-01", help="start date YYYY-MM-DD")
    rp.add_argument("--end", default=_date.today().isoformat(), help="end date YYYY-MM-DD")
    rp.add_argument("--config", default="legacy", choices=["legacy", "cascade"], help="single config to replay")
    rp.add_argument("--a", choices=["legacy", "cascade"], help="left config for A/B output")
    rp.add_argument("--b", choices=["legacy", "cascade"], help="right config for A/B output")
    rp.add_argument("--train-start", help="walk-forward train start YYYY-MM-DD")
    rp.add_argument("--train-end", help="walk-forward train end YYYY-MM-DD")
    rp.add_argument("--test-start", help="walk-forward test start YYYY-MM-DD")
    rp.add_argument("--test-end", help="walk-forward test end YYYY-MM-DD")
    rp.add_argument("--persist", action="store_true",
                     help="E1-PERSIST: persist passed+refused cohorts into setup_expectancy "
                          "(single scan pass; also backfills candidates/outcomes)")
    rp.set_defaults(func=_cmd_replay)
    lr = sub.add_parser("live-replay", help="run the intraday FSM replay harness (zero network calls)")
    lr.add_argument("--fixture", help="path to a tick-session fixture JSON (default: live/fixtures/sample_session.json)")
    lr.add_argument("--no-dedupe-check", action="store_true", help="skip the replay-twice zero-duplicate assertion")
    lr.set_defaults(func=_cmd_live_replay)
    ll = sub.add_parser("live-loop", help="run the intraday live loop (paper mode only)")
    ll.add_argument("--paper", action="store_true", help="required -- Stage 1 refuses to start without it")
    ll.add_argument("--date", help="trade date YYYY-MM-DD (default: today)")
    ll.add_argument("--probe-only", action="store_true", help="report state without attempting to connect")
    ll.set_defaults(func=_cmd_live_loop)
    sc = sub.add_parser("scorecard", help="funnel + forward-performance scorecard (scan/refuse/debate vs actual T+1/3/5/10)")
    sc.add_argument("--start", required=True, help="start scan_date YYYY-MM-DD")
    sc.add_argument("--end", required=True, help="end scan_date YYYY-MM-DD")
    sc.add_argument("--out", default="manas_os/design/reports/", help="output dir for SCORECARD_<start>_<end>.md/.json")
    sc.set_defaults(func=_cmd_scorecard)
    ig = sub.add_parser(
        "integrity",
        help="pipeline/data integrity watchdog (freshness, silent skips, verdict grading, "
             "card consistency, overfit capacity, survivorship, look-ahead scan)",
    )
    ig.add_argument("--date", help="as-of date YYYY-MM-DD (default: today)")
    ig.add_argument("--out", default="manas_os/design/reports/", help="output dir for INTEGRITY_<date>.md/.json")
    ig.set_defaults(func=_cmd_integrity)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
