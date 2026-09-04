"""P2.3 gold fixtures: frozen real positive and negative examples replay
through the detectors. The JSON is the acceptance artifact; this test
does not re-ingest the bhavcopy store."""
from unidesk.momentum.detectors.gold import load_gold_fixtures, replay_case
from unidesk.momentum.detectors.momentum_burst import Detection
from unidesk.momentum.detectors.registry import DETECTOR_NAMES


def test_gold_coverage_has_positive_and_negative_per_detector():
    doc = load_gold_fixtures()
    assert doc["schema_version"] == 1
    assert len(doc["cases"]) >= 16
    for name in DETECTOR_NAMES:
        cov = doc["coverage"][name]
        assert cov["positives"] >= 1, f"{name} missing a real positive"
        assert cov["negatives"] >= 1, f"{name} missing a real negative"


def test_gold_replay_matches_frozen_expectation():
    doc = load_gold_fixtures()
    for case in doc["cases"]:
        det, failures = replay_case(case)
        assert det.value == case["expected"], (
            f"{case['id']}: got {det.value} expected {case['expected']} "
            f"failures={failures}"
        )
        if case["expected"] == Detection.INVALID.value:
            assert list(failures) == case["expected_failures"], case["id"]
        if case["expected"] == Detection.VALID.value:
            # skipped optional notes are allowed; named rule failures are not
            assert all(f.startswith("skipped:") for f in failures), case["id"]


def test_gold_cases_are_real_symbols_with_inputs():
    doc = load_gold_fixtures()
    seen = set()
    for case in doc["cases"]:
        assert case["symbol"], case["id"]
        assert case["session"], case["id"]
        assert case["inputs"], case["id"]
        assert case["id"] not in seen
        seen.add(case["id"])
        assert case["detector"] in DETECTOR_NAMES
        assert case["polarity"] in ("positive", "negative")
