import pandas as pd
from send_telegram_message import send_telegram_message
import math
import asyncio
import aiohttp
import dotenv
import os
import requests
from bot_commands import get_market_info
from utils import *
import numpy as np

dotenv.load_dotenv()

def get_price_history(token_id, start_time):
    """
    Fetch historical prices for a market from Polymarket CLOB.
    """
    url_price = f"https://clob.polymarket.com/prices-history?startTs={start_time}&market={token_id}&fidelity=120"
    response = requests.get(url_price)
    
    if response.status_code != 200:
        print(f"Error fetching data: {response.status_code}")
        return None

    data = response.json()
    if not data:
        print("No data returned from API")
        return None

    # convert to DataFrame
    df = pd.DataFrame(data.get('history', []))
    if df.empty or len(df) < 3:
        return None
    else:
        df['price'] = df['p'].astype(float)
        df['timestamp'] = pd.to_datetime(df['t'], unit='s')
        
        return df

def calculate_volatility(df):
    """
    Calculate volatility as standard deviation of log returns.
    """
    df = df.sort_values('timestamp')  # Ensure chronological order
    df['log_return'] = np.log(df['price'] / df['price'].shift(1))
    volatility = df['log_return'].std()
    return volatility

def get_all_rewards():
    all_rewards = []

    url_rewards = "https://polymarket.com/api/rewards/markets?orderBy=rate_per_day&position=DESC&query=&showFavorites=false&tagSlug=all&nextCursor=MA%3D%3D&requestPath=%2Frewards%2Fuser%2Fmarkets&onlyMergeable=false&noCompetition=false&onlyOpenOrders=false&onlyPositions=false"
    polymarket_url = "https://polymarket.com/event/"

    response = requests.get(url_rewards)

    if response.status_code == 200:
        all_data = response.json()['data']
            
        for data in all_data:
            market_id = data['market_id']
            event_slug = data['event_slug']
            market_slug = data['market_slug']
            condition_id = data['condition_id']
            question = data['question']
            volume_24hr = data['volume_24hr']
            tokens_id = [token['token_id'] for token in data['tokens']]
            outcomes = [token['outcome'] for token in data['tokens']]
            reward_start = [config['start_date'] for config in data['rewards_config']]
            reward_end = [config['end_date'] for config in data['rewards_config']]
            reward_amt = [config['rate_per_day'] for config in data['rewards_config']]
            reward_spread = data['rewards_max_spread']
            reward_min_size = data['rewards_min_size']
            competitiveness = data['market_competitiveness']
            
            
            reward = {
                "market_id": market_id,
                "link" : f"{polymarket_url}{event_slug}/{market_slug}",
                "condition_id": condition_id,
                "question": question,
                "volume_24hr": volume_24hr,
                "tokens_id": tokens_id,
                "outcomes": outcomes,
                "reward_start": reward_start,
                "reward_end": reward_end,
                "reward_amt": reward_amt,
                "reward_spread": reward_spread,
                "reward_min_size": reward_min_size,
                "competitiveness": competitiveness
            }
        
            all_rewards.append(reward)
        
        return all_rewards
    else:
        print(f"{response.status_code}")
        return None

async def fetch_rewards(session, slug):
    url_rewards = (
        f"https://polymarket.com/api/rewards/markets"
        f"?orderBy=rate_per_day&position=DESC&query=&showFavorites=false"
        f"&tagSlug={slug}&onlyMergeable=false&noCompetition=false"
        f"&onlyOpenOrders=false&onlyPositions=false"
    )
    polymarket_url = "https://polymarket.com/event/"

    async with session.get(url_rewards) as response:
        if response.status != 200:
            print(f"⚠️ Failed to fetch {slug}: {response.status}")
            return []

        data = (await response.json()).get("data", [])
        results = []

        for item in data:
            reward = {
                "market_id": item.get("market_id"),
                "link": f"{polymarket_url}{item.get('event_slug')}/{item.get('market_slug')}",
                "condition_id": item.get("condition_id"),
                "question": item.get("question"),
                "volume_24hr": item.get("volume_24hr"),
                "tokens_id": [t["token_id"] for t in item.get("tokens", [])],
                "outcomes": [t["outcome"] for t in item.get("tokens", [])],
                "reward_start": [cfg["start_date"] for cfg in item.get("rewards_config", [])],
                "reward_end": [cfg["end_date"] for cfg in item.get("rewards_config", [])],
                "reward_amt": [cfg["rate_per_day"] for cfg in item.get("rewards_config", [])],
                "reward_spread": item.get("rewards_max_spread"),
                "reward_min_size": item.get("rewards_min_size"),
                "competitiveness": item.get("market_competitiveness"),
            }
            results.append(reward)

        return results


async def async_get_rewards():
    slugs = ['politics', 'crypto', 'sports', 'business','pop-culture','science', 'middle-east']
    all_rewards = []

    async with aiohttp.ClientSession() as session:
        tasks = [fetch_rewards(session, slug) for slug in slugs]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for r in results:
            if isinstance(r, list):
                all_rewards.extend(r)

    return all_rewards



def get_wanted_rewards_market(all_rewards,market_id : str, side : str):
    print(f"Processing market {market_id} with side {side}")

    for reward in all_rewards:
        if reward['market_id'] == market_id:
            print(f"Found market {market_id} in rewards")
            for num,outcome in enumerate(reward['outcomes']):
                if side.lower() == outcome.lower():
                    return reward, reward['tokens_id'][num]
    return None, None


#--params--
liquidity_threshold = 50000
bid_liquidity_threshold = 10000
vol_threshold = 100000
tick_spread = 3
yes_skew_threshold = 80/20
no_skew_threshold = 80/20
reward_threshold = 20
volitility_threshold = 0.004
use_async = os.getenv("USE_ASYNC", "0") == "1"
MARKETS_DIR = os.getenv('MARKETS_DIR')

def auto_select_markets():

    try:
        potential_markets = []
        print("get all rewards")
        #if use async to run, also need to change in add_markets.py
        if use_async:
            all_rewards = asyncio.run(async_get_rewards())
        else:
            all_rewards = get_all_rewards()

        start_time = int(time.time() - 48*3600)
        for reward in all_rewards:
            try:
                market_id = reward['market_id']
                question = reward['question']
                token_ids = reward['tokens_id']
                outcomes = reward['outcomes']
                reward_end = reward['reward_end'][0]
                reward_amt = reward['reward_amt'][0]
                reward_spread = reward['reward_spread']
                reward_min_size = reward['reward_min_size']
                competitiveness = reward['competitiveness']

                print(f"-----{market_id}-----")

                market_info = get_market_info(market_id)


                #2. spread not more than x
                spread = market_info['spread']
                tick = market_info['tick_size']

                spread_trigger = False
                if tick == 0.01:
                    if spread <= 0.01:
                        spread_trigger = True
                else:
                    if spread <= tick* tick_spread:
                        spread_trigger = True

                skew_trigger = False
                #5. outcome yes/no only
                outcomes = market_info['outcomes']
                if [o.lower() for o in outcomes] == ['yes', 'no'] or [o.lower() for o in outcomes] == ['no', 'yes']:
                #3. yes/no skew
                    yes_no_price = market_info['prices']
                    yes_price = float(yes_no_price[0])
                    no_price  = float(yes_no_price[1])

                    skew_yes = yes_price / no_price

                    if skew_yes > yes_skew_threshold or skew_yes < no_skew_threshold:
                        skew_trigger = True
                    
                liquidity_trigger = False
                #1. high liqudiity
                total_liquidity = market_info['liquidity']
                if total_liquidity > liquidity_threshold:
                    liquidity_trigger = True

                #4. volume?
                volume_trigger = False
                volume = market_info['volume']
                if volume > vol_threshold:
                    volume_trigger = True

                #6. reward > X amount
                reward_trigger = False
                reward_amt = market_info['reward_amt']
                if reward_amt > reward_threshold:
                    reward_trigger = True

                if all([spread_trigger, skew_trigger, liquidity_trigger, volume_trigger, reward_trigger]):

                    print("check for each token id")

                    # ---- 7. BID LIQUIDITY CHECK ----
                    bid_liquidity_trigger = False
                    
                    for token_id in token_ids:

                        ob_data = get_orderbook_data(token_id)
                        reward_ob_data = get_reward_ob_data(market_info, ob_data)

                        bids = reward_ob_data.get("bids", [])

                        # compute liquidity safely
                        total_bid_liquidity = sum(
                            float(b.get("price", 0) or 0) * float(b.get("size", 0) or 0)
                            for b in bids
                            if b.get("price") not in [None, "null", "None"] and 
                            b.get("size") not in [None, "null", "None"]
                        )

                        print(f"total bid liq for {token_id}: {total_bid_liquidity}")

                        if total_bid_liquidity > bid_liquidity_threshold:
                            bid_liquidity_trigger = True
                            break


                    # ---- 8. VOLATILITY CHECK ----
                    volatility_trigger = False

                    for token_id in token_ids:

                        df_prices = get_price_history(token_id, start_time)

                        if df_prices is None or df_prices.empty:
                            print(f"No price data for {token_id}")
                            continue

                        volatility = calculate_volatility(df_prices)
                        print(f"Volatility for {token_id}: {volatility:.6f}")

                        if volatility <= volitility_threshold:
                            volatility_trigger = True
                            break


                    # ---- FINAL CONDITION ----
                    if bid_liquidity_trigger and volatility_trigger:
                        message = (
                            f"{question} -- {market_info['outcomes']} "
                            f"{market_info['prices']} is good to MM "
                            f"with rewards {market_info['reward_amt']}"
                        )
                        print(message)
                        potential_markets.append(message)

            except Exception as e:
                print(e)
        return potential_markets       
    except Exception as e:
        print(e)