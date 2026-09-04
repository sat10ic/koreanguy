from manas_os.engine import pine_ports


def _bars(start: float, step: float, n: int = 60):
    return [{"date": f"2026-01-{i:02d}", "close": start + (i * step)} for i in range(n)]


def test_moving_average_relative_strength_returns_plain_english_evidence():
    subject = _bars(100, 2.0)
    benchmark = _bars(100, 0.5)

    result = pine_ports.moving_average_relative_strength(subject, benchmark, ma_length=50)

    assert result["available"] is True
    assert result["value"] > 0
    assert result["state"] in {"ABSOLUTE_OUT", "GROSS_OUT", "RELATIVE_OUT"}
    assert "MARS" in result["detail"]
    assert "benchmark" in result["detail"]


def test_moving_average_relative_strength_handles_short_history():
    result = pine_ports.moving_average_relative_strength(_bars(100, 1, 10), _bars(100, 1, 60))

    assert result["available"] is False
    assert result["state"] is None
    assert "Insufficient history" in result["detail"]
