import pandas as pd
import schedule
import time
from datetime import datetime


from utils import get_polymarket_data, get_new_markets, get_large_tx, get_high_movement, get_all_rewards, get_orderbook_data, get_reward_ob_data
from send_telegram_message import send_telegram_message

def run_4h_tasks():
    print(f"[{datetime.now()}] Running 4-hour tasks...")

    # Get all markets
    df = get_polymarket_data()

    # Filter interesting plays
    cond1 = df['category'].isin(['economy', 'geopolotics', 'world'])
    cond2 = df['liquidity'] >= 3000
    plays_df = df[cond1 & cond2]

    # Save to CSV
    df.to_csv('polymarket.csv', index=False)
    plays_df.to_csv('polymarket_plays.csv', index=False)

    # New markets (every 4h)
    new_markets = get_new_markets(df)
    if new_markets:
        send_telegram_message(new_markets)

    # High movers (every 4h)
    high_movement = get_high_movement(df)
    if high_movement:
        send_telegram_message(high_movement)

def run_daily_tasks():
    print(f"[{datetime.now()}] Running daily tasks...")

    # Get all markets
    df = get_polymarket_data()

    # Large transactions (every day)
    large_tx = get_large_tx(df)
    if large_tx:
        send_telegram_message(large_tx)

# --- Scheduling ---
# Run every 4 hours
schedule.every(4).hours.do(run_4h_tasks)

# Run once a day (e.g., at 00:00)
schedule.every().day.at("00:00").do(run_daily_tasks)

# Initial run when script starts
run_4h_tasks()
run_daily_tasks()

# --- Scheduler loop ---
print("🕒 Scheduler started...")
while True:
    schedule.run_pending()
    time.sleep(60)
