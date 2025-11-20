import aiohttp
import asyncio
import pandas as pd
import json
import requests
import pandas as pd
import matplotlib.pyplot as plt
from dateutil import parser
from datetime import datetime, timezone, timedelta
import os
import dotenv
import time
from web3 import Web3

dotenv.load_dotenv()

from utils import get_orderbook_data, get_reward_ob_data, get_all_rewards, async_get_rewards, get_wanted_rewards_market
from orders import place_order, place_sell_order, get_all_orders, get_all_orders_id, get_rewards_scoring

def bot_get_all_orders_info():

    def format_orders(all_data):
        lines = ["📊 Current Orders\n"]
        
        for item in all_data:
            lines.append(
                f"🟦 {item['question']}\n"
                f"• Outcome: {item['outcome']}\n"
                f"• Side: {item['side']}\n"
                f"• Size: {item['size']}\n"
                f"• Price: {item['price']}\n"
                f"• Matched: {item['size matched']}\n"
            )
        
        return "\n".join(lines)

    use_async = os.getenv("USE_ASYNC", "0") == "1"

    try:
        #if use async to run, also need to change in add_markets.py
        if use_async:
            all_rewards = asyncio.run(async_get_rewards())
        else:
            all_rewards = get_all_rewards()

        # === STEP 1: Load CSV ===
        file_path = os.getenv('MARKETS_DIR')   # Change to your actual CSV file path

        df = pd.read_csv(file_path, usecols=['question','market_id', 'side'], dtype={'question' : str,'market_id': str, 'side': str})

        # === STEP 2: Validate columns ===
        required_cols = {'question','market_id', 'side'}
        missing_cols = required_cols - set(df.columns)

        if missing_cols:
            raise ValueError(f"❌ Missing required columns: {missing_cols}")
        
        all_orders = get_all_orders()

        # === STEP 3: Continue with your logic ===
        all_data = []
        for _, row in df.iterrows():
            market_id = str(row['market_id'])
            side = str(row['side'])

            try:

                reward_data, token_id = get_wanted_rewards_market(all_rewards,market_id,side)

                if token_id:

                    #check for current pos and if have, skip if set_no_buy_if_got_existingPos = True
                    for order in all_orders:
                        if token_id == order['asset_id']:
                            d = {
                            'question' : reward_data['question'],
                            'outcome' : order['outcome'],
                            'side' : order['side'],
                            'size' : order['original_size'],
                            'price' : order['price'],
                            'size matched' : order['size_matched']  
                            }
                            all_data.append(d)

            except Exception as e:
                print(f"{e} : error getting assets data")
                return None
        if all_data:
            message = format_orders(all_data)
            return message
        else:
            message = "no data at all"
            return message
    except Exception as e:
        print(f"error {e}")
        return f"error {e}"

def bot_get_positions():

    def format_positions(all_data):
        lines = ["📊 Current Positions\n"]
        
        for item in all_data:
            lines.append(
                f"🟦 {item['question']}\n"
                f"• Outcome: {item['outcome']}\n"
                f"• Size: {item['size']}\n"
                f"• Buyin Price: {item['buyin_price']}\n"
                f"• init val: {item['init_val']}\n"
                f"• curr val: {item['curr_val']}\n"
                f"• PnL: {item['PnL']}\n"

            )
        
        return "\n".join(lines)
    
    all_pos = []
    FUNDER = os.getenv("POLY_FUNDER_ADDRESS")

    positions_url = f"https://data-api.polymarket.com/positions?user={FUNDER}"

    response = requests.get(positions_url)

    if response.status_code == 200:

        positions = response.json()
        if positions:

            for pos in positions:
                d ={
                    'question' : pos['title'],
                    'outcome' : pos['outcome'],
                    'size' : pos['size'],
                    'buyin_price' : pos['avgPrice'],
                    'init_val' : pos['initialValue'],
                    'curr_val' : pos['currentValue'],
                    'PnL' : pos['cashPnl']
                }
                all_pos.append(d)
            message = format_positions(all_pos)
            return message
        else:
            return None
        
def bot_get_reward_details():
        
    orders = get_all_orders()
    orders = get_all_orders_id(orders)
    rewards = get_rewards_scoring(orders)

    if rewards:
        return rewards
    else:
        return None

def get_market_info(market_id : int):
    url = f"https://gamma-api.polymarket.com/markets/{market_id}"

    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
        token_ids = json.loads(data['clobTokenIds'])

        outcomes = json.loads(data['outcomes'])

        prices = json.loads(data['outcomePrices'])

        last_price = data['lastTradePrice'] if data['lastTradePrice'] else None

        question = data['question'] if data['question'] else None 

        tick = data['orderPriceMinTickSize'] if data['orderPriceMinTickSize'] else None

        min_size = data['orderMinSize'] if data['orderMinSize'] else None

        volume = data['volume1wk'] if data['volume1wk'] else None

        liq = data['liquidityNum'] if data['liquidityNum'] else None

        reward_amt = data['clobRewards'][0]['rewardsDailyRate'] if data['clobRewards'][0]['rewardsDailyRate'] else None

        reward_min_size = data['rewardsMinSize'] if data['rewardsMinSize'] else None

        reward_spread = data['rewardsMaxSpread'] if data['rewardsMaxSpread'] else None

        d = {
            'token_ids' : token_ids,
            'outcomes' : outcomes,
            'prices' : prices,
            'last_price' : last_price,
            'question' : question,
            'tick_size' : tick,
            'min_size' : min_size,
            'volume' : volume,
            'liquidity' : liq,
            'reward_amt' : reward_amt,
            'reward_min_size' : reward_min_size,
            'reward_spread' : reward_spread
        }


        return d
    
    else:
        return None
    

def bot_get_market_info(market_id):

    def format_rewards_data(rewards_data):
        msg = "🎁 *Rewards Data*\n\n"

        for r in rewards_data:
            token_id = r['token_id']
            outcome = r['outcome']
            ob = r['reward_order_book']

            msg += f"*Token {token_id}* ({outcome}):\n"

            # Bids
            if ob.get('bids'):
                msg += "  Bids:\n"
                for bid in ob['bids'][:10]:  # show top 5 only for brevity
                    price = bid['price']
                    size = bid['size']
                    msg += f"    {price:>8}  |  {size:>10}\n"

            # Asks
            if ob.get('asks'):
                msg += "  Asks:\n"
                for ask in ob['asks'][:10]:  # show top 5 only
                    price = ask['price']
                    size = ask['size']
                    msg += f"    {price:>8}  |  {size:>10}\n"

            msg += "\n"

        return msg
    
    def format_market_data(market_info):
        msg = "📌 *Market Info*\n"
        for key, val in market_info.items():
            msg += f"• {key}: {val}\n"

        return msg



    market_info = get_market_info(market_id)

    if market_info:

        msg_market_info = format_market_data(market_info)

        token_ids = market_info['token_ids']
        outcomes = market_info['outcomes']

        rewards_data = []

        for i in range(len(token_ids)):
            token_id = token_ids[i]
            outcome = outcomes[i]

            ob = get_orderbook_data(token_id)
            reward_ob = get_reward_ob_data(market_info,ob)

            reward_data = {
                'token_id' : token_id,
                'outcome' : outcome,
                'reward_order_book' : reward_ob
            }

            rewards_data.append(reward_data)
        if rewards_data:
            msg_rewards_data = format_rewards_data(rewards_data)

            msg = msg_market_info + "\n\n" + msg_rewards_data
            return msg

        else:
            return msg_market_info

    else:
        return None
    

def bot_order(market_id, outcome, side, price, size):

    try:

        market_info = get_market_info(market_id)
        token_ids = market_info['token_ids']
        outcomes = market_info['outcomes']

        for i in range(len(token_ids)):
            market_token_id = token_ids[i]
            market_outcome = outcomes[i]

            if market_outcome.lower() == outcome.lower():
                token_id = market_token_id

                if side.lower() == 'buy':
                    place_order(token_id,price,size)
                    return f"order has been placed"

                elif side.lower() == 'sell':
                    place_sell_order(token_id, price, size)
                    return f"order has been placed"
                else:
                    return f"order has NOT been placed"
                    
    except Exception as e:
        return f"Error : {e}"