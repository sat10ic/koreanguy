"""I10 fix: vision/observer chart-analysis LLMs had no notion of "today" and
could narrate an old region of the daily/weekly PNG (e.g. a Sep 2024 episode)
as if it were current market structure. Covers:
  1. manas_os.agents._shared.recency_rule / stale_evidence_warning (the two
     shared building blocks used by both agents' prompts and post-checks).
  2. vision._system_prompt / observer._system_prompt actually embed the
     scan_date + recency instruction.
"""
from manas_os.agents import _shared, observer, vision


AS_OF = "2026-06-30"


# ---------------------------------------------------------------------------
# _shared.stale_evidence_warning (the post-check function)
# ---------------------------------------------------------------------------

def test_stale_evidence_warning_flags_old_month_year():
    text = "This looks similar to the base it carved out in Sep 2024 before the move."
    warning = _shared.stale_evidence_warning(text, AS_OF)
    assert warning is not None
    assert "Sep 2024" in warning
    assert "treat dated claims with suspicion" in warning


def test_stale_evidence_warning_flags_full_month_name_and_multiple_mentions():
    text = "Compare to the January 2024 breakout and the failed retest in September 2024."
    warning = _shared.stale_evidence_warning(text, AS_OF)
    assert warning is not None
    assert "January 2024" in warning
    assert "September 2024" in warning


def test_stale_evidence_warning_passes_recent_date():
    # AS_OF is 2026-06-30; a May 2026 mention is well within the 6-month window.
    text = "Base built out through May 2026 with tightening ranges into the breakout."
    assert _shared.stale_evidence_warning(text, AS_OF) is None


def test_stale_evidence_warning_passes_no_date_text():
    text = "Clean stage-2 uptrend, volume expanding on up days, base is 8 weeks tight."
    assert _shared.stale_evidence_warning(text, AS_OF) is None


def test_stale_evidence_warning_handles_empty_and_missing_scan_date():
    assert _shared.stale_evidence_warning("", AS_OF) is None
    assert _shared.stale_evidence_warning("Sep 2024 base", "") is None
    assert _shared.stale_evidence_warning("Sep 2024 base", "not-a-date") is None


def test_stale_evidence_warning_boundary_just_inside_six_months_passes():
    # AS_OF - 6 months (month-start) is 2025-12-01 -> Dec 2025 mention should
    # NOT be flagged (not strictly older than the cutoff month).
    text = "Structure has held since Dec 2025."
    assert _shared.stale_evidence_warning(text, AS_OF) is None


def test_stale_evidence_warning_boundary_just_outside_six_months_flags():
    text = "Structure has held since Nov 2025."
    warning = _shared.stale_evidence_warning(text, AS_OF)
    assert warning is not None
    assert "Nov 2025" in warning


# ---------------------------------------------------------------------------
# _shared.recency_rule
# ---------------------------------------------------------------------------

def test_recency_rule_contains_scan_date_and_last_60_and_ambiguity_instruction():
    rule = _shared.recency_rule(AS_OF)
    assert AS_OF in rule
    assert "RECENCY RULE" in rule
    assert "LAST 60" in rule
    assert "ambiguous about dates" in rule


# ---------------------------------------------------------------------------
# Prompt builders actually wire scan_date + the recency rule in
# ---------------------------------------------------------------------------

def test_vision_system_prompt_includes_scan_date_and_recency():
    prompt = vision._system_prompt(AS_OF)
    assert AS_OF in prompt
    assert "RECENCY RULE" in prompt
    assert "LAST 60" in prompt


def test_vision_text_prompt_includes_scan_date_field():
    item = {"symbol": "ADANIENT", "setup": "Pullback", "setup_family": "strong_start"}
    text = vision._text_prompt(item, AS_OF)
    assert f'"scan_date": "{AS_OF}"' in text


def test_observer_system_prompt_includes_scan_date_and_recency():
    prompt = observer._system_prompt(AS_OF)
    assert AS_OF in prompt
    assert "RECENCY RULE" in prompt
    assert "LAST 60" in prompt


def test_observer_text_prompt_includes_scan_date_field():
    item = {"symbol": "ADANIENT", "setup": "Pullback", "setup_family": "strong_start"}
    text = observer._text_prompt(item, AS_OF)
    assert f'"scan_date": "{AS_OF}"' in text
