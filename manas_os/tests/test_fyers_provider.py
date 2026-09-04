from manas_os.providers.fyers import FyersProvider


class _QuotesOnlyClient:
    def quotes(self, payload):
        assert payload == {"symbols": "NSE:AAA-EQ"}
        return {
            "s": "ok",
            "d": [
                {
                    "n": "NSE:AAA-EQ",
                    "s": "ok",
                    "v": {
                        "lp": 123.4,
                        "open_price": 120.0,
                        "low_price": 119.5,
                        "high_price": 124.0,
                        "volume": 500_000,
                        "prev_close_price": 118.0,
                    },
                }
            ],
        }


def test_snapshot_lookback_zero_does_not_make_one_history_request_per_symbol(monkeypatch):
    provider = FyersProvider(client_id="id", token="token")
    monkeypatch.setattr(provider, "is_available", lambda: True)
    monkeypatch.setattr(provider, "_get_client", lambda: _QuotesOnlyClient())
    monkeypatch.setattr(
        provider,
        "_compute_avg_vol",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("history must not run")),
    )

    rows = provider.get_snapshot(["AAA"], lookback=0)

    assert len(rows) == 1
    assert rows[0].ok is True
    assert rows[0].last == 123.4
    assert rows[0].avg_vol_n is None
