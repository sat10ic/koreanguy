"""Rule-engine tests: INSUFFICIENT vs INVALID vs VALID, optional rules, and
the honest skipped-notes in a VALID result."""
from unidesk.momentum.detectors.engine import Rule, evaluate_rules
from unidesk.momentum.detectors.momentum_burst import Detection


def test_missing_mandatory_rule_is_insufficient():
    rules = [
        Rule("gap", available=False, passed=None),
        Rule("rvol", available=True, passed=True),
    ]
    detection, failures = evaluate_rules(rules)
    assert detection is Detection.INSUFFICIENT_DATA
    assert failures == ("missing:gap",)


def test_failed_rule_is_invalid_with_named_detail():
    rules = [
        Rule("gap", available=True, passed=False, detail="gap_pct 0.4 < 2.0"),
        Rule("rvol", available=True, passed=True),
    ]
    detection, failures = evaluate_rules(rules)
    assert detection is Detection.INVALID
    assert failures == ("gap_pct 0.4 < 2.0",)


def test_all_passed_is_valid_clean():
    rules = [
        Rule("gap", available=True, passed=True),
        Rule("rvol", available=True, passed=True),
    ]
    detection, failures = evaluate_rules(rules)
    assert detection is Detection.VALID and failures == ()


def test_optional_unavailable_is_valid_with_skipped_note():
    rules = [
        Rule("gap", available=True, passed=True),
        Rule("avwap_ext", available=False, passed=None, optional=True),
    ]
    detection, failures = evaluate_rules(rules)
    assert detection is Detection.VALID
    assert failures == ("skipped:avwap_ext",)


def test_optional_failed_still_fails():
    rules = [
        Rule("gap", available=True, passed=True),
        Rule("avwap_ext", available=True, passed=False, detail="too extended"),
        Rule("rvol", available=True, passed=True),
    ]
    detection, failures = evaluate_rules(rules)
    assert detection is Detection.INVALID and failures == ("too extended",)
