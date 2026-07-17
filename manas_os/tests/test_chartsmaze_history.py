import sqlite3

from manas_os.sources.chartsmaze_history import horizon_return, import_industry_graphical


def test_import_and_causal_horizon_return(tmp_path):
    source = tmp_path / "industry-graphical-view.csv"
    source.write_text(
        "Basic Industry,2026-01-01,2026-01-02,2026-01-03,2026-01-04\n"
        "Software,0,10,21,33.1\n",
        encoding="utf-8",
    )
    conn = sqlite3.connect(":memory:")
    conn.executescript(
        "CREATE TABLE chartsmaze_industry_history (trade_date TEXT, name TEXT, "
        "cumulative_return REAL, source_file TEXT, PRIMARY KEY(trade_date,name));"
    )
    result = import_industry_graphical(conn, source)
    assert result["rows"] == 4
    assert round(horizon_return(conn, "Software", "2026-01-04", 3), 6) == 33.1
    assert round(horizon_return(conn, "Software", "2026-01-03", 1), 6) == 10.0
    assert horizon_return(conn, "Software", "2025-12-31", 1) is None
