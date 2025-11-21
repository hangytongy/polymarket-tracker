from utils import *
from orders import get_current_orders, place_order, cancel_order, get_all_orders_id, cancel_all_orders
import pandas as pd
from send_telegram_message import send_telegram_message
import math
import asyncio
import aiohttp
import dotenv

dotenv.load_dotenv()

def round_down(value, decimals):
    factor = 10 ** decimals
    return math.floor(value * factor) / factor


use_async = os.getenv("USE_ASYNC", "0") == "1"
MARKETS_DIR = os.getenv('MARKETS_DIR')
test_market_id = "541622"

try:
    #if use async to run, also need to change in add_markets.py
    if use_async:
        all_rewards = asyncio.run(async_get_rewards())
    else:
        all_rewards = get_all_rewards()

    # === STEP 1: Load CSV ===
    file_path = MARKETS_DIR  # Change to your actual CSV file path

    df = pd.read_csv(file_path, usecols=['question','market_id', 'side'], dtype={'question' : str,'market_id': str, 'side': str})

    # === STEP 2: Validate columns ===
    required_cols = {'question','market_id', 'side'}
    missing_cols = required_cols - set(df.columns)

    if missing_cols:
        raise ValueError(f"❌ Missing required columns: {missing_cols}")
    
    #get wallet balance
    wallet_balance = get_wallet_balance()

    if not wallet_balance:
        message = "error getting USDC balance"
        send_telegram_message(message)
        raise ValueError(f"❌ error getting USDC balance")

    # === STEP 3: Continue with your logic ===

    for _, row in df.iterrows():
        market_id = str(row['market_id'])
        side = str(row['side'])
        print(f"-----{market_id}----")

        try:

            reward_data, token_id = get_wanted_rewards_market(all_rewards,market_id,side)

            if token_id:
                if market_id == test_market_id:
                    print("test cancel order by token_id")
                    resp = cancel_order_by_asset(token_id)
                    send_telegram_message(resp)

        except Exception as e:
            message = f"Error: {e}"
            send_telegram_message(message)


except Exception as e:
    message = f"Error: {e}"
    send_telegram_message(message)
