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

buy_in_size = 5
my_min_size = 5
my_max_amt = int(os.getenv("MAX_AMT", "20"))
my_min_amt = int(os.getenv("MIN_AMT", "10"))
size_agression = float(os.getenv("SIZE_AGRESSION", "0.02")) #% of total bid rewards liquidity
agression = float(os.getenv("AGRESSION", "0.5")) # 0.1-0.9
set_buy_if_got_existingPos = os.getenv("BUY_EXISITNG_POS", "0") == "1"
use_async = os.getenv("USE_ASYNC", "0") == "1"
VOLATILITY_THRESHOLD = float(os.getenv("VOLATILITY_THRESHOLD", "0.03"))
MARKETS_DIR = os.getenv('MARKETS_DIR')

try:

    # === STEP 1: Load CSV ===
    file_path = MARKETS_DIR  # Change to your actual CSV file path

    df = pd.read_csv(file_path, usecols=['question','market_id', 'side','token_id'], dtype={'question' : str,'market_id': str, 'side': str, 'token_id': str})

    # === STEP 2: Validate columns ===
    required_cols = {'question','market_id', 'side', 'token_id'}
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
        question = str(row['question'])
        token_id = str(row['token_id'])
        print(f"-----{market_id}----")

        try:
            
            #currently if old markets.csv is rewritten, those that are not in the new csv, gets stuck, need to remove all orders on them from get_events.py
            if token_id:

                #check for current pos and if have, skip if set_no_buy_if_got_existingPos = True
                assets, values = get_exisiting_positions()
                #if there is a current position
                if token_id in assets:
                    index = assets.index(token_id)
                    value = values[index]
                    #if no "buy the dip" or position value is more than max amount
                    if not set_buy_if_got_existingPos or value >= my_max_amt:
                        continue
                try:
                    #get market orderbook
                    ob_data = get_orderbook_data(token_id)

                    mid_price_ob = ob_data['mid_price']

                except:
                    message = f"no mid price found in {question}, removing market"
                    send_telegram_message(message)
                    df = df[df['market_id'] != market_id]
                    df.to_csv(file_path, index=False)
                    print(f"✅ Removed market_id {market_id} from {file_path}")
                    continue

                #get volume, liquidit and tick
                liquidity, volume, tick = get_market_liquidity_volume_tick(market_id)
                if tick:
                    decimal_places = len(str(tick).split(".")[1]) if "." in str(tick) else 0

                else:
                    message = f"unable to get liquidity volume and tick from {question}"
                    send_telegram_message(message)
                    continue
                
                #get bid_price
                clean_data = {
                "bids": [float(item['price']) for item in ob_data['bids']],
                "asks": [float(item['price']) for item in ob_data['asks']]
                    }
                
                bids = clean_data['bids']
                max_bid_price = max(bids)
                
                #Bid price is current max bid - 1 tick
                bid_price = max_bid_price - tick 

                #min bid price is bid price - 2%, round up
                bid_min = round(max_bid_price * 0.98,decimal_places)

                #get size
                size = buy_in_size

                if size > wallet_balance:
                    while size > wallet_balance:
                        size *=0.8

                #get current orders by token_id
                current_orders = get_current_orders(token_id)

                #check if there is a current order in this market
                if current_orders:

                    buy_orders = [order for order in current_orders if order['side'] == 'BUY']

                    if buy_orders:
                        print(f"there are buy orders {len(buy_orders)}")

                        buy_prices = [float(order['price']) for order in buy_orders]
                        max_buy_price = max(buy_prices)
                        min_buy_price = min(buy_prices)

                        #if market too volatile
                        #if (reward_mid_range - max_buy_price) > VOLATILITY_THRESHOLD:
                        #    message = f"volatility to high for {question}"
                        #    send_telegram_message(message)
                        #    continue

                        if min_buy_price >= bid_min and max_buy_price <= bid_price:
                            #if float(order['price']) >= mid_range_lower and float(order['price']) <= mid_range_upper:
                                print(f'Current order is in the reward bid range')
                        else:
                            print(f'Current order is not in the reward bid range')
                            cancel_resp = cancel_order_by_asset(token_id)

                            if wallet_balance < size * bid_price :
                                message = f"not enough $ for {question}"
                                send_telegram_message(message)
                                continue
                                
                            resp = place_order_scale(token_id, bid_price, bid_min , size, tick, size)
                            if resp:
                                print(f"placed order at {bid_price} for {question} and {side}")
                                message = f"{str(resp)} \n\nOrder out of reward range, cancel old and placed order at {bid_price} to {bid_min} for {question} and {side} and size {size}"
                                send_telegram_message(message)
                            else:
                                message = f"Error placing scale order -> either steps is 0 or size per order less than reward size"
                                send_telegram_message(message)

                    else:
                        print(f'No current order in this market')

                        if wallet_balance < size * bid_price:
                            message = f"not enough $ for {question}"
                            send_telegram_message(message)
                            continue

                        resp = place_order_scale(token_id, bid_price, bid_min , size, tick, size)
                        if resp:
                            print(f"placed order at {bid_price} for {question} and {side}")
                            message = f"{str(resp)} \n\nOrder out of reward range, cancel old and placed order at {bid_price} to {bid_min} for {question} and {side} and size {size}"
                            send_telegram_message(message)
                        else:
                            message = f"Error placing scale order -> either steps is 0 or size per order less than reward size"
                            send_telegram_message(message)
                else:
                    print(f'No current order in this market')

                    if wallet_balance < size * bid_price:
                        message = f"not enough $ for {question}"
                        send_telegram_message(message)
                        continue

                    resp = place_order_scale(token_id, bid_price, bid_min , size, tick, size)
                    if resp:
                        print(f"placed order at {bid_price} for {question} and {side}")
                        message = f"{str(resp)} \n\nPlaced order at {bid_price} to {bid_min} for {question} and {side} and size {size}"
                        send_telegram_message(message)
                    else:
                        message = f"Error placing scale order -> either steps is 0 or size per order less than reward size"
                        send_telegram_message(message)


            else:
                print(f'No Market found for {market_id} and {side}')
                message = f"No Market found for {market_id} {row['question']} and {side}"
                send_telegram_message(message)

                token_ids = get_token_id(market_id)

                if token_ids:
                    for token_id in token_ids:

                        orders = get_current_orders(token_id)
                        if orders:
                            for order in orders:   
                                if order['side'] =="BUY":
                                    order_id = order['id']
                                    cancel_order(order_id)
                            message = f"Order canceled for {market_id} {token_id} and {side}"

                    df = df[df['market_id'] != market_id]
                    df.to_csv(file_path, index=False)
                    print(f"✅ Removed market_id {market_id} from {file_path}")
                    
                    
                else:
                    print("unable to find market to remove")
                    message = "unable to find market to remove"
                    send_telegram_message(message)   

        except Exception as e:
            message = f"{market_id} - {str(row['market_id'])} error : {e}"
            send_telegram_message(message)

except Exception as e:
    message = f"Error: {e}"
    send_telegram_message(message)
