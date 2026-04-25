import json
from fyers_apiv3 import fyersModel

with open('SwingEdge/config/settings.json', 'r') as f:
    settings = json.load(f)

fyers = fyersModel.FyersModel(client_id=settings['fyers_app_id'], is_async=False, token=settings['fyers_access_token'], log_path="")

for sym in ["NSE:ZOMATO-EQ", "NSE:ETERNAL-EQ"]:
    data = {"symbol": sym, "resolution": "D", "date_format": "1", "range_from": "2024-01-01", "range_to": "2024-01-10", "cont_flag": "1"}
    print(f"{sym}:", fyers.history(data=data))
