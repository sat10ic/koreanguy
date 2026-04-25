import os
import json
import logging
from fyers_apiv3 import fyersModel

with open('SwingEdge/config/settings.json', 'r') as f:
    settings = json.load(f)

app_id = settings.get('fyers_app_id')
token = settings.get('fyers_access_token')
fyers = fyersModel.FyersModel(client_id=app_id, is_async=False, token=token, log_path="")

data = {
    "symbol": "NSE:RELIANCE-EQ",
    "resolution": "D",
    "date_format": "1",
    "range_from": "2022-01-01",
    "range_to": "2024-01-01",
    "cont_flag": "1"
}

resp = fyers.history(data=data)
print("With >1 year:", resp)
