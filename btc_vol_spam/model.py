from binance.client import Client
import requests
import json
from datetime import datetime, timedelta
import pandas as pd

# -------------------------------------------------------
# 1. DOWNLOAD 7 DAYS OF BTC 1-MIN DATA FROM BINANCE
# -------------------------------------------------------

client = Client()  # public endpoint, no API key needed
symbol = "BTCUSDT"
interval = Client.KLINE_INTERVAL_1MINUTE

def get_btc_token_ids(timestamp):
    
    slug = f"btc-updown-15m-{timestamp}"

    url = f"https://gamma-api.polymarket.com/markets/slug/{slug}"

    response = requests.get(url)

    data = response.json()

    token_ids = json.loads(data['clobTokenIds'])
    
    return token_ids


def get_mid_price(token_id):
    url = f"https://clob.polymarket.com/midpoint?token_id={token_id}"
    response = requests.get(url)
    return float(response.json()['mid'])


def get_timestamp():
    current_time = datetime.now()
    minutes_to_subtract = current_time.minute % 15
    rounded_dt = current_time - timedelta(minutes=minutes_to_subtract)
    rounded_dt = rounded_dt.replace(second=0, microsecond=0)
    timestamp = int(rounded_dt.timestamp())

    return timestamp

def get_time_left():

    now = datetime.utcnow()
    mins = now.minute
    next_interval_min = (mins // 15 + 1) * 15
    next_interval = now.replace(minute=0, second=0, microsecond=0) + pd.Timedelta(minutes=next_interval_min)
    time_left = (next_interval - now).total_seconds() / 60.0

    return time_left