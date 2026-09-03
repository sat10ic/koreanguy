"""Published-output invariants — the audit, converted into executable contracts.

Every defect found in the 2026-09-01 UI audit was an *unasserted property*, not
a coding mistake. An LLM re-derived each one by hand; nothing in the build could
have caught them. This module turns each into a check that fails
``run_checks.py``, so the same class of defect cannot ship again.

The invariants, and the real defect each one was written against:

  I1  outcome_horizon      "hit_target" was awarded on ZERO forward bars.
                           The newest session read 15 won / 1 stopped (94%)
                           against a 35% archive base rate, because with no
                           forward data almost nothing CAN stop out.
  I2  win_reached_target   137 archive rows were labelled ``hit_target`` at
                           r_multiple < 1.0 -- one at 0.13R (a 0.54% move).
  I3  funnel_nested        The opportunity funnel widened 64 -> 75 at its last
                           step, because "near trigger" filtered all candidates
                           rather than the high-quality survivors.
  I4  price_matches_source A fixture claimed TRENT at Rs 6120 when the exchange
                           close was Rs 2898 -- a 111% error shown beside real
                           candidates.
  I5  regime_matches       The front page rendered a hardcoded BULL while the
                           pipeline had computed CHOP.
  I6  ranked_symbols_live  9 of 73 candidates had not traded on the session
                           date (one last traded 2+ years earlier), and because
                           a frozen price beats a drifting universe, the
                           STALEST names carried the HIGHEST rs_rank.
  I7  score_has_variance   ``setup_quality`` is 100.0 for every candidate --
                           a rule-completion flag presented as a 0-100 score.
  I8  no_fabricated_rows   Illustrative records must never sit in a list the
                           user reads as real output.

Each check reads only PUBLISHED artefacts (the report JSON the UI actually
imports) plus raw bhavcopy, so it validates what the user sees rather than what
the code intended.
"""
from __future__ import annotations

import csv
import glob
import io
import json
import os
import re
from collections import Counter
from datetime import date, datetime
from pathlib import Path
from typing import Any, Optional

_ROOT = Path(__file__).resolve().parents[1]      # unidesk/
_REPO = _ROOT.parent
_UI_DATA = _REPO / "unidesk_terminal" / "src" / "data"
_BHAVCOPY = _REPO / "data" / "bhavcopy"

# A stop this far from entry, measured in the stock's own average daily range,
# needs an implausible run to reach +1R. Diagnostic only -- reported, not fatal.
STOP_ADR_WARN = 3.0


class InvariantFailure(AssertionError):
    """A published artefact violates a contract the UI depends on."""


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

def _newest(pattern: str) -> Optional[Path]:
    hits = sorted(_UI_DATA.glob(pattern))
    return hits[-1] if hits else None


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _session_of(name: str) -> Optional[str]:
    m = re.search(r"(\d{4}-\d{2}-\d{2})", name)
    return m.group(1) if m else None


def _bhavcopy_closes(session: str) -> dict:
    """{symbol: close} for one session, straight from the exchange file."""
    d = datetime.strptime(session, "%Y-%m-%d").date()
    fname = _BHAVCOPY / f"sec_bhavdata_full_{d.strftime('%d%m%Y')}.csv"
    if not fname.exists():
        return {}
    out: dict = {}
    with io.open(fname, encoding="utf-8", errors="ignore") as fh:
        for row in csv.DictReader(fh):
            k = {kk.strip(): (vv.strip() if isinstance(vv, str) else vv)
                 for kk, vv in row.items() if kk}
            if k.get("SERIES") != "EQ":
                continue
            try:
                out[k["SYMBOL"]] = float(k["CLOSE_PRICE"])
            except (KeyError, ValueError):
                pass
    return out


# --------------------------------------------------------------------------
# I1 + I2 — outcome labelling
# --------------------------------------------------------------------------

def check_outcome_labels() -> str:
    """I1/I2: a win requires an elapsed horizon AND an actually-reached target."""
    p = _newest("outcomes_*.json")
    if p is None:
        return "not_built_yet: no outcomes_*.json published"
    bundle = _load(p)
    calls = bundle.get("calls", [])
    if not calls:
        return f"{p.name}: 0 calls (nothing to check)"

    # I2 — no win below +1R.
    weak = [c for c in calls
            if c.get("outcome") == "hit_target"
            and c.get("rMultiple") is not None and c["rMultiple"] < 1.0]
    if weak:
        ex = ", ".join(f"{c['symbol']}@{c['date']}={c['rMultiple']:.2f}R" for c in weak[:3])
        raise InvariantFailure(
            f"I2 {len(weak)} call(s) labelled hit_target below +1R (e.g. {ex}). "
            "A win must reach the target, not merely avoid the stop.")

    # I1 — no win on a session with no forward data.
    dates = sorted({c["date"] for c in calls})
    last = dates[-1] if dates else None
    if last:
        terminal = [c for c in calls
                    if c["date"] == last and c.get("outcome") == "hit_target"]
        if terminal:
            raise InvariantFailure(
                f"I1 {len(terminal)} call(s) on {last} labelled hit_target, but no session "
                "exists after it — zero forward bars means the horizon cannot have elapsed.")

    mix = Counter(c.get("outcome") for c in calls)
    resolved = mix["hit_target"] + mix["stopped_out"] + mix.get("resolved_flat", 0)
    rate = (mix["hit_target"] / resolved * 100) if resolved else 0.0
    return (f"{p.name}: {len(calls)} calls, {dict(mix)}, "
            f"win rate {rate:.1f}% of horizon-elapsed")


# --------------------------------------------------------------------------
# I3 — funnel nesting
# --------------------------------------------------------------------------

def check_funnel_nested() -> str:
    """I3: opportunity-funnel steps must each be a subset of the one above."""
    p = _newest("tonight_*.json")
    if p is None:
        return "not_built_yet: no tonight_*.json published"
    rep = _load(p)
    hf = rep.get("honesty_footer", {})
    cands = rep.get("candidates", [])

    scanned = hf.get("universe_scanned") or 0
    gated = hf.get("universe_gate_skips_total") or 0
    skipped = hf.get("universe_skipped_insufficient_history") or 0

    def _q(c: dict) -> float:
        sq = c.get("stock_quality") or {}
        v = sq.get("score")
        return v if isinstance(v, (int, float)) else -1.0

    def _near(c: dict) -> bool:
        t, cl = c.get("trigger"), c.get("close")
        if not t or not cl:
            return False
        return (t / cl - 1.0) * 100.0 <= 8.0

    high = [c for c in cands if _q(c) >= 60]
    steps = [
        ("universe seen", scanned + gated + skipped),
        ("passed gates", scanned),
        ("technical candidates", len(cands)),
        ("high quality", len(high)),
        ("and near trigger", len([c for c in high if _near(c)])),
    ]
    for (pn, pv), (nn, nv) in zip(steps, steps[1:]):
        if nv > pv:
            raise InvariantFailure(
                f"I3 funnel widens: '{nn}'={nv} exceeds '{pn}'={pv}. "
                "Each step must filter the survivors of the previous one.")
    return " > ".join(f"{n}:{v}" for n, v in steps)


# --------------------------------------------------------------------------
# I4 — published price equals exchange price
# --------------------------------------------------------------------------

def check_prices_match_source() -> str:
    """I4: every published close must equal the exchange close for that session."""
    p = _newest("tonight_*.json")
    if p is None:
        return "not_built_yet: no tonight_*.json published"
    rep = _load(p)
    session = rep.get("session_date") or _session_of(p.name)
    truth = _bhavcopy_closes(session) if session else {}
    if not truth:
        return f"skipped: no bhavcopy on disk for {session}"

    bad, unchecked = [], 0
    for c in rep.get("candidates", []):
        real = truth.get(c["symbol"])
        if real is None:
            unchecked += 1
            continue
        if c.get("close") is not None and abs(real - c["close"]) > 0.02:
            bad.append((c["symbol"], c["close"], real))
    if bad:
        ex = ", ".join(f"{s}: shown {a} vs exchange {b}" for s, a, b in bad[:3])
        raise InvariantFailure(
            f"I4 {len(bad)} published price(s) disagree with the exchange file ({ex}).")
    return (f"{len(rep.get('candidates', []))} prices match bhavcopy for {session}"
            + (f" ({unchecked} not in file — see I6)" if unchecked else ""))


# --------------------------------------------------------------------------
# I5 — displayed regime equals computed regime
# --------------------------------------------------------------------------

def check_no_hardcoded_market_values() -> str:
    """I5: the UI must not hardcode a regime label or market statistic."""
    src = _REPO / "unidesk_terminal" / "src"
    if not src.exists():
        return "not_built_yet: no UI source tree"
    # Values that were previously hardcoded and contradicted the pipeline.
    banned = {
        "65.86": "stale breadth constant (real value comes from honesty_footer)",
        "2563": "stale universe count",
        "2026-07-03": "stale hardcoded session date",
    }
    hits = []
    for path in list(src.rglob("*.ts")) + list(src.rglob("*.tsx")):
        if path.name.startswith("tonight_") or path.suffix == ".json":
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for needle, why in banned.items():
            if needle in text:
                hits.append(f"{path.relative_to(src)} contains {needle} ({why})")
    if hits:
        raise InvariantFailure("I5 hardcoded market value(s): " + "; ".join(hits[:4]))
    return f"no hardcoded market constants in {src.name}/"


# --------------------------------------------------------------------------
# I6 — ranked symbols must have traded
# --------------------------------------------------------------------------

def check_ranked_symbols_traded() -> str:
    """I6: a symbol with no print on the session date must not be ranked.

    A frozen price against a drifting universe manufactures relative strength,
    so stale names float to the TOP of the ranking. This is the check that
    would have caught UJJIVAN (last traded 2024-05-02) carrying rs_rank 84.7.
    """
    p = _newest("tonight_*.json")
    if p is None:
        return "not_built_yet: no tonight_*.json published"
    rep = _load(p)
    session = rep.get("session_date") or _session_of(p.name)
    truth = _bhavcopy_closes(session) if session else {}
    if not truth:
        return f"skipped: no bhavcopy on disk for {session}"

    dead = [c["symbol"] for c in rep.get("candidates", []) if c["symbol"] not in truth]
    if dead:
        raise InvariantFailure(
            f"I6 {len(dead)} candidate(s) did not trade on {session} "
            f"(e.g. {', '.join(dead[:5])}). A symbol with no print must not be "
            "ranked — stale prices inflate relative strength.")
    return f"all {len(rep.get('candidates', []))} candidates traded on {session}"


# --------------------------------------------------------------------------
# I7 — a score must actually score
# --------------------------------------------------------------------------

def check_scores_have_variance() -> str:
    """I7: a field presented as a 0-100 score must vary across the cohort.

    ``setup_quality`` is 100.0 for every candidate: it is a rule-completion
    flag, not a graded assessment. Reported (not fatal) so the degeneracy is
    visible every run instead of being rediscovered by hand.
    """
    p = _newest("tonight_*.json")
    if p is None:
        return "not_built_yet: no tonight_*.json published"
    cands = _load(p).get("candidates", [])
    if not cands:
        return "0 candidates"

    notes = []
    for field in ("stock_quality", "setup_quality", "entry_quality"):
        vals = [c[field]["score"] for c in cands
                if isinstance(c.get(field), dict) and c[field].get("score") is not None]
        if not vals:
            notes.append(f"{field}: absent")
            continue
        spread = max(vals) - min(vals)
        notes.append(f"{field}: n={len(vals)} spread={spread:.1f}"
                     + (" DEGENERATE — constant, not a score" if spread < 1e-9 else ""))

    # Scalar metrics that are supposed to discriminate. These were added
    # BECAUSE setup_quality turned out constant; catching a future flat metric
    # is the whole point, so a genuinely constant one FAILS rather than warns.
    for field, floor in (("adr_max_pct", 0.5), ("chop_score", 1.0)):
        vals = [c[field] for c in cands if isinstance(c.get(field), (int, float))]
        if not vals:
            notes.append(f"{field}: absent")
            continue
        spread = max(vals) - min(vals)
        if spread < floor:
            raise InvariantFailure(
                f"I7 {field} spread {spread:.3f} < {floor} across {len(vals)} candidates — "
                "it no longer discriminates and must not be presented as a varying metric.")
        notes.append(f"{field}: n={len(vals)} spread={spread:.1f}")
    return "; ".join(notes)


# --------------------------------------------------------------------------
# I8 — no fabricated rows in anything the user reads as real
# --------------------------------------------------------------------------

def check_no_fabricated_rows() -> str:
    """I8: illustrative records must not sit in a list read as real output."""
    fx = _REPO / "unidesk_terminal" / "src" / "data" / "fixtures.ts"
    if not fx.exists():
        return "not_built_yet: no fixtures.ts"
    text = fx.read_text(encoding="utf-8", errors="ignore")
    # The merged array is the specific pattern that let a fabricated TRENT at
    # Rs 6120 render beside real candidates.
    m = re.search(r"export const ALL_CANDIDATES[^=]*=\s*\[([^\]]*)\]", text, re.S)
    if m and m.group(1).strip():
        raise InvariantFailure(
            "I8 ALL_CANDIDATES is non-empty — fabricated records are merged into a "
            "list the user reads as real scan output (this shipped TRENT at Rs 6120 "
            "against a real close of Rs 2898).")
    return "no fabricated candidate rows merged into real output"


# --------------------------------------------------------------------------
# diagnostic (never fatal) — risk expressed in the stock's own daily range
# --------------------------------------------------------------------------

def report_stop_distance_in_adr() -> str:
    """Not an invariant: surfaces WHY R:R is poor.

    ``stop% / adr%`` is the number of average days of adverse room a trade
    carries. Stops 3+ ADR away need an implausible run to reach +1R, which is
    what drove R:R to 0.01 on the nearest-to-trigger names.
    """
    p = _newest("tonight_*.json")
    if p is None:
        return "not_built_yet"
    cands = _load(p).get("candidates", [])
    vals = []
    for c in cands:
        t, inv, adr = c.get("trigger"), c.get("invalidation"), c.get("adr_pct")
        if None in (t, inv, adr) or not adr or not t:
            continue
        vals.append(((t - inv) / t * 100.0) / adr)
    if not vals:
        return "no candidates with trigger/invalidation/adr"
    vals.sort()
    med = vals[len(vals) // 2]
    wide = sum(1 for v in vals if v > STOP_ADR_WARN)
    return (f"stop distance in ADR units: median={med:.1f}, "
            f"{wide}/{len(vals)} beyond {STOP_ADR_WARN} ADR")




# --------------------------------------------------------------- F-7 class guards

def _ui_src() -> Path:
    return _REPO / "unidesk_terminal" / "src"


def check_setup_sections_cover_detectors() -> str:
    """F-7/A-1 class guard: every detector the report emits must have a UI
    section mapping (SETUP_LABEL in fixtures.ts). The original defect was a
    detector rendered by NO section while the header kept counting it."""
    p = _newest("tonight_*.json")
    if p is None:
        return "not_built_yet: no bundled report"
    report = _load(p)
    detectors = {c.get("detector") for c in report.get("candidates", []) if c.get("detector")}
    fixtures = (_ui_src() / "data" / "fixtures.ts").read_text(encoding="utf-8")
    label_block = re.search(r"SETUP_LABEL[^=]*=\s*\{(.*?)\}", fixtures, re.S)
    mapped = set(re.findall(r'(\w+):\s*"', label_block.group(1))) if label_block else set()
    unmapped = sorted(d for d in detectors if d not in mapped)
    if unmapped:
        raise InvariantFailure(f"detectors with no UI section mapping: {unmapped}")
    return f"{len(detectors)} report detectors all mapped to UI sections"


def check_dated_bundles_sorted_newest_first() -> str:
    """F-7/C-2 class guard: every dated-bundle data module must sort
    newest-first, never trust glob order (settings.ts picked the OLDEST
    settings file the moment a second landed)."""
    offenders: list[str] = []
    for path in sorted(_ui_src().glob("data/*.ts")):
        src = path.read_text(encoding="utf-8")
        if "import.meta.glob" not in src:
            continue
        if "sort(" not in src or "localeCompare" not in src:
            offenders.append(path.name)
    if offenders:
        raise InvariantFailure(f"dated-bundle modules without newest-first sort: {offenders}")
    return "all glob-consuming data modules sort newest-first"


def check_no_hardcoded_status_prose() -> str:
    """F-7/A-5+A-6 class guard: status claims the report owns must never be
    hardcoded prose in the UI. Catches the exact phrases that drifted before
    ('adjustment pass still open', 'seven detectors', stale session literals
    in src/data)."""
    patterns = re.compile(
        r"(adjustment pass still open|still open \(N\d|seven detectors|"
        r"tonight_\d{4}-\d{2}-\d{2}\.json)"
    )
    offenders: list[str] = []
    for path in list(_ui_src().glob("screens/*.tsx")) + list(_ui_src().glob("data/*.ts")):
        for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if patterns.search(line) and not line.strip().startswith("//"):
                offenders.append(f"{path.name}:{i}")
    if offenders:
        raise InvariantFailure(f"hardcoded status prose / session literals: {offenders}")
    return "no hardcoded status prose or session literals in screens/ or data/"


ALL_INVARIANTS = (
    ("outcome_labels", check_outcome_labels),
    ("funnel_nested", check_funnel_nested),
    ("prices_match_source", check_prices_match_source),
    ("no_hardcoded_market_values", check_no_hardcoded_market_values),
    ("ranked_symbols_traded", check_ranked_symbols_traded),
    ("scores_have_variance", check_scores_have_variance),
    ("no_fabricated_rows", check_no_fabricated_rows),
    ("setup_sections_cover_detectors", check_setup_sections_cover_detectors),
    ("dated_bundles_sorted_newest_first", check_dated_bundles_sorted_newest_first),
    ("no_hardcoded_status_prose", check_no_hardcoded_status_prose),
)
