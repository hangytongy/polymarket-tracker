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

buy_in_size = 50 #not used anymore
my_min_size = 100
my_max_size = 800
my_min_amt = 100
size_agression = float(os.getenv("SIZE_AGRESSION", "0.02")) #% of total bid rewards liquidity
agression = float(os.getenv("AGRESSION", "0.5")) # 0.1-0.9
set_buy_if_got_existingPos = os.getenv("BUY_EXISITNG_POS", "0") == "1"
use_async = os.getenv("USE_ASYNC", "0") == "1"

try:
    #if use async to run, also need to change in add_markets.py
    if use_async:
        all_rewards = asyncio.run(async_get_rewards())
    else:
        all_rewards = get_all_rewards()

    # === STEP 1: Load CSV ===
    file_path = "markets.csv"   # Change to your actual CSV file path

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

                #check for current pos and if have, skip if set_no_buy_if_got_existingPos = True
                assets = get_exisiting_positions()
                #if there is a current position
                if token_id in assets:
                    #if you want to buy with current existing pos
                    if set_buy_if_got_existingPos:
                        pass
                    else:
                        continue

                question = reward_data['question']
                #get market orderbook
                ob_data = get_orderbook_data(token_id)

                if not ob_data['mid_price']:
                    message = f"no mid price found in {question}"
                    send_telegram_message(message)
                    continue

                #get reward bid and ask spread
                reward_ob_data = get_reward_ob_data(reward_data,ob_data)
                #get minimum order size
                min_size = int(reward_data['reward_min_size'])

                #get volume, liquidit and tick
                liquidity, volume, tick = get_market_liquidity_volume_tick(market_id)
                if tick:
                    pass

                else:
                    message = f"unable to get liquidity volume and tick from {question}"
                    send_telegram_message(message)
                    continue

                #get reward bid range
                reward_bid = reward_ob_data['bids']
                reward_bid = [bid['price'] for bid in reward_bid]
                reward_bid_min = min(reward_bid)
                reward_bid_max = max(reward_bid)
                decimal_places = len(str(tick).split(".")[1]) if "." in str(tick) else 0
                #reward_mid_range = (reward_bid_max + reward_bid_min) / 2
                reward_mid_range = reward_bid_min + agression * (reward_bid_max - reward_bid_min)
                reward_mid_range = round_down(reward_mid_range,decimal_places)
                mid_range_lower = round((reward_mid_range + reward_bid_min) / 2,decimal_places)
                mid_range_upper = round((reward_mid_range + reward_bid_max) / 2,decimal_places)

                print(f"Mid range: {reward_mid_range}, Mid range lower: {mid_range_lower}, Mid range upper: {mid_range_upper}")

                
                #decide size
                reward_bid = reward_ob_data['bids']
                reward_bid_size = [bid['size'] for bid in reward_bid]
                total_reward_bid_size = sum(reward_bid_size)
                size_desired = total_reward_bid_size *size_agression #% of total reward bids

                size = max(size_desired, min_size)

                if size == min_size:
                    size = size
                
                else:

                    if size > wallet_balance:
                        while size > wallet_balance:
                            size *=0.8

                    size = max(size, min_size)

                    size = round(size,1)
                
                size = max(size,my_min_size)

                amt = size * reward_mid_range
                if amt < my_min_amt:
                    size = round(my_min_amt / reward_mid_range,1)
                else:
                    size = size

                #get current orders by token_id
                current_orders = get_current_orders(token_id)

                #check if there is a current order in this market
                if current_orders:
                    #check if the current order is in the reward bid range
                    for order in current_orders:
                        #check for only buy orders
                        if order['side'] == 'BUY':
                            if float(order['price']) >= reward_bid_min and float(order['price']) <= reward_mid_range:
                            #if float(order['price']) >= mid_range_lower and float(order['price']) <= mid_range_upper:
                                print(f'Current order is in the reward bid range')
                            else:
                                print(f'Current order is not in the reward bid range')
                                order_id = order['id']
                                cancel_order(order_id)

                                if wallet_balance < size * reward_mid_range :
                                    message = f"not enough $ for {question}"
                                    send_telegram_message(message)
                                    continue

                                bid_price = reward_mid_range
                                place_order(token_id,bid_price,size)
                                print(f"placed order at {bid_price} for {question} and {side}")
                                message = f"Order out of reward range, cancel old price {order['price']} and placed order at {bid_price} for {question} and {side} and size {size}"
                                send_telegram_message(message)


                else:
                    print(f'No current order in this market')

                    if wallet_balance < size * reward_mid_range:
                        message = f"not enough $ for {question}"
                        send_telegram_message(message)
                        continue

                    bid_price = reward_mid_range
                    place_order(token_id,bid_price,size)
                    print(f"placed order at {bid_price} for {question} and {side}")
                    message = f"placed order at {bid_price} for {question} and {side} at size {size}"
                    send_telegram_message(message)


            else:
                print(f'No reward found for {market_id} and {side}')
                message = f"No reward found for {market_id} {row['question']} and {side}"
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

