from manas_os.sources import nse_deals


def test_parse_nse_bulk_deal_adds_canonical_qty_and_price():
    text = "Date,Symbol,Client Name,Buy/Sell,Quantity Traded,Trade Price / WAvg\n16-07-2026,ABC,Fund,B,1000,125.5\n"
    rows = nse_deals.parse_csv(text, "nse_bulk_deal", "2026-07-16")
    assert rows[0]["trade_date"] == "2026-07-16"
    assert rows[0]["symbol"] == "ABC"
    assert rows[0]["detail"]["quantity"] == "1000"
    assert rows[0]["detail"]["price"] == "125.5"
