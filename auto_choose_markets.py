import pandas as pd
from send_telegram_message import send_telegram_message
import math
import asyncio
import aiohttp
import dotenv
import os
import requests

dotenv.load_dotenv()

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


buy_in_size = 50 #not used anymore
my_min_size = 100
my_max_size = 800
my_min_amt = int(os.getenv("MIN_AMT", "100"))
size_agression = float(os.getenv("SIZE_AGRESSION", "0.02")) #% of total bid rewards liquidity
agression = float(os.getenv("AGRESSION", "0.5")) # 0.1-0.9
set_buy_if_got_existingPos = os.getenv("BUY_EXISITNG_POS", "0") == "1"
use_async = os.getenv("USE_ASYNC", "0") == "1"
VOLATILITY_THRESHOLD = float(os.getenv("VOLATILITY_THRESHOLD", "0.03"))
MARKETS_DIR = os.getenv('MARKETS_DIR')

try:
    #if use async to run, also need to change in add_markets.py
    if use_async:
        all_rewards = asyncio.run(async_get_rewards())
    else:
        all_rewards = get_all_rewards()

    print(all_rewards)

    #conditions to choose markets
    #1. high liqudiity
    #2. spread not more than x
    #3. yes/no skew
    #4. volume?
    #5. outcome yes/no only
    #6. reward > X amount
    #7. reward bid liquidity > X amount
    #8. volatility? price history do not fluctate more than X over X period of time

except Exception as e:
    print(e)