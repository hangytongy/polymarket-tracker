import pandas as pd
import numpy as np
import time
from binance.client import Client
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, roc_auc_score
from lightgbm import LGBMClassifier
import requests
import json
from datetime import datetime, timedelta

# -------------------------------------------------------
# 1. DOWNLOAD 7 DAYS OF BTC 1-MIN DATA FROM BINANCE
# -------------------------------------------------------

client = Client()  # public endpoint, no API key needed
symbol = "BTCUSDT"
interval = Client.KLINE_INTERVAL_1MINUTE

def get_binance_1m(symbol, days=7):
    frames = []
    current_time = int(time.time() * 1000)

    for i in range(days):
        start_time = current_time - (i + 1) * 1500 * 60 * 1000
        end_time = current_time - i * 1500 * 60 * 1000

        kl = client.get_historical_klines(
            symbol, interval, start_str=start_time, end_str=end_time
        )

        df = pd.DataFrame(kl, columns=[
            "time","open","high","low","close","volume",
            "close_time","quote_volume","n_trades",
            "taker_base","taker_quote","ignore"
        ])
        df["time"] = pd.to_datetime(df["time"], unit="ms")
        df = df[["time","open","high","low","close","volume"]]
        df[["open","high","low","close","volume"]] = df[["open","high","low","close","volume"]].astype(float)
        frames.append(df)
        time.sleep(0.1)

    df_all = pd.concat(frames).sort_values("time").reset_index(drop=True)
    df_all["timestamp"] = df_all["time"]
    df_all = df_all.set_index("timestamp")
    return df_all

df = get_binance_1m(symbol, days=7)

# -------------------------------------------------------
# 2. BUILD FEATURES AND LABELS
# -------------------------------------------------------
df["interval_start"] = df.index.floor("15min")
df["interval_end"] = df["interval_start"] + pd.Timedelta("15min")

interval_open = df.groupby("interval_start")["close"].first()
interval_close = df.groupby("interval_start")["close"].last()
df["last_15m_price"] = df["interval_start"].map(interval_open)
df["future_close"] = df["interval_start"].map(interval_close)
df["label"] = (df["future_close"] > df["last_15m_price"]).astype(int)
df["time_left"] = (df["interval_end"] - df["time"]).dt.total_seconds() / 60.0
df = df[df["time_left"] > 0]

# Features
df["pct_dev"] = (df["close"] - df["last_15m_price"]) / df["last_15m_price"]
df["ret_1m"] = df["close"].pct_change(1)
df["ret_3m"] = df["close"].pct_change(3)
df["ret_5m"] = df["close"].pct_change(5)
df["vol_5m"] = df["ret_1m"].rolling(5).std()
df["vol_15m"] = df["ret_1m"].rolling(15).std()
df = df.dropna()

features = [
    "close", "last_15m_price", "pct_dev", "time_left",
    "ret_1m","ret_3m","ret_5m","vol_5m","vol_15m"
]

X = df[features]
y = df["label"]

# -------------------------------------------------------
# 3. TRAIN / TEST SPLIT AND MODEL
# -------------------------------------------------------
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=False)
model = LGBMClassifier(
    n_estimators=500, learning_rate=0.02, max_depth=6,
    subsample=0.8, colsample_bytree=0.8
)
model.fit(X_train, y_train)

preds = model.predict(X_test)
probs = model.predict_proba(X_test)[:, 1]

print("Accuracy:", accuracy_score(y_test, preds))
print("AUC:", roc_auc_score(y_test, probs))

# -------------------------------------------------------
# 5. EXAMPLE USAGE
# -------------------------------------------------------
def get_current_and_last15(symbol="BTCUSDT"):
    """
    Returns the current price, the last finished 15-min candle close,
    and the time left (in minutes) until the next 15-min interval.
    """
    # --- Get current 1m candle ---
    k1 = client.get_klines(symbol=symbol, interval=Client.KLINE_INTERVAL_1MINUTE, limit=1)
    current_price = float(k1[0][4])
    
    # --- Get last finished 15m candle ---
    k15 = client.get_klines(symbol=symbol, interval=Client.KLINE_INTERVAL_15MINUTE, limit=2)
    last_15m_close = float(k15[-2][4])
    
    # Time left until next 15-min candle
    now = datetime.utcnow()
    mins = now.minute
    next_interval_min = (mins // 15 + 1) * 15
    next_interval = now.replace(minute=0, second=0, microsecond=0) + pd.Timedelta(minutes=next_interval_min)
    time_left = (next_interval - now).total_seconds() / 60.0
    
    return current_price, last_15m_close, time_left

def get_recent_closes(symbol="BTCUSDT", lookback=15):
    """
    Get the latest `lookback` 1-minute closes for feature calculation.
    """
    kl = client.get_klines(symbol=symbol, interval=Client.KLINE_INTERVAL_1MINUTE, limit=lookback)
    closes = [float(candle[4]) for candle in kl]
    return closes

def get_probability(symbol="BTCUSDT"):
    """
    Returns the probability that BTC closes above last 15-min price in this interval.
    """
    current_price, last_15m_price, time_left = get_current_and_last15(symbol)
    recent_closes = get_recent_closes(symbol, lookback=15)
    
    # Compute features
    recent_closes = pd.Series(recent_closes)
    pct_dev = (current_price - last_15m_price) / last_15m_price
    ret_1m = recent_closes.pct_change(1).iloc[-1]
    ret_3m = recent_closes.pct_change(3).iloc[-1]
    ret_5m = recent_closes.pct_change(5).iloc[-1]
    vol_5m = recent_closes.pct_change(1).rolling(5).std().iloc[-1]
    vol_15m = recent_closes.pct_change(1).rolling(15).std().iloc[-1]
    
    row = {
        "close": current_price,
        "last_15m_price": last_15m_price,
        "pct_dev": pct_dev,
        "time_left": time_left,
        "ret_1m": ret_1m,
        "ret_3m": ret_3m,
        "ret_5m": ret_5m,
        "vol_5m": vol_5m,
        "vol_15m": vol_15m,
    }
    
    df_pred = pd.DataFrame([row])
    prob = float(model.predict_proba(df_pred)[0][1])

    # Confidence = distance from 0.5 (scaled 0-1)
    confidence = abs(prob - 0.5) * 2

    print(f"current price:{current_price} \nLast 15min price : {last_15m_price} \nTime left :{time_left}")
    print(f"Probability BTC will close above last 15-min price: {prob:.3f}, confidence: {confidence:.3f}")
    
    return prob, confidence, time_left

def get_btc_token_ids(timestamp):
    
    slug = f"btc-updown-15m-{timestamp}"

    url = f"https://gamma-api.polymarket.com/markets/slug/{slug}"

    response = requests.get(url)

    token_ids = json.loads(response.json()['clobTokenIds'])
    
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
