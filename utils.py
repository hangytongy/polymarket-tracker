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
from orders import *

dotenv.load_dotenv()


def get_polymarket_data():

    BASE_URL = "https://gamma-api.polymarket.com/events/pagination"
    POLYMARKET_URL = "https://polymarket.com/event/"
    CATEGORIES = ['economy', 'geopolotics', 'world', 'politics', 'tech', 'fed-rates']

    CONCURRENCY_LIMIT = 5  # max concurrent category fetches

    semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)


    async def fetch_category(session, category):
        """Fetch all markets for one category (with pagination)."""
        all_markets = []
        offset = 0
        limit = 80

        async with semaphore:
            while True:
                params = {
                    "limit": limit,
                    "active": "true",
                    "archived": "false",
                    "tag_slug": category,
                    "closed": "false",
                    "order": "volume24hr",
                    "ascending": "false",
                    "offset": offset
                }

                try:
                    async with session.get(BASE_URL, params=params, timeout=15) as resp:
                        if resp.status == 429:
                            print(f"⚠️ Rate limited fetching {category}, waiting 3s...")
                            await asyncio.sleep(3)
                            continue
                        elif resp.status != 200:
                            print(f"❌ Failed to fetch {category} ({resp.status})")
                            break

                        data = await resp.json()
                        results = data.get("data", [])
                        if not results:
                            break

                        for event in results:
                            id_ = event.get("id")
                            slug = event.get("slug")
                            markets = event.get("markets", [])

                            for market in markets:
                                m = {
                                    "id": id_,
                                    "market_id": market.get("id"),
                                    "link": f"{POLYMARKET_URL}{slug}",
                                    "category": category,
                                    "question": market.get("question"),
                                    "description": market.get("description"),
                                    "startDate": market.get("startDate"),
                                    "endDate": market.get("endDate"),
                                    "outcomes": market.get("outcomes"),
                                    "outcomePrices": market.get("outcomePrices"),
                                    "token_ids" : market.get("clobTokenIds"),
                                    "price_change_1wk": market.get("oneWeekPriceChange"),
                                    "price_change_1mo": market.get("oneMonthPriceChange"),
                                    "closed": market.get("closed"),
                                    "liquidity": market.get("liquidity"),
                                    "volume1yr": market.get("volume1yr"),
                                    "volume1mo": market.get("volume1mo"),
                                    "volume1wk": market.get("volume1wk")
                                }
                                all_markets.append(m)

                        if len(results) < limit:
                            break  # no more pages
                        offset += limit  # next page

                except Exception as e:
                    print(f"⚠️ Error fetching {category}: {e}")
                    break

        return all_markets


    async def main():
        async with aiohttp.ClientSession() as session:
            tasks = [fetch_category(session, cat) for cat in CATEGORIES]
            results = await asyncio.gather(*tasks)

        all_markets = [m for sublist in results for m in sublist]
        df = pd.DataFrame(all_markets)

        # Safely parse JSON-like string fields if needed
        def safe_json_parse(x):
            try:
                return json.loads(x) if isinstance(x, str) else x
            except Exception:
                return x

        if not df.empty:
            df['outcomes'] = df['outcomes'].apply(safe_json_parse)
            df['outcomePrices'] = df['outcomePrices'].apply(safe_json_parse)

        return df


    df = asyncio.run(main())
    print(f"✅ Total markets fetched: {len(df)}")
    df['liquidity'] = df['liquidity'].astype(float)
    df['startDate'] = df['startDate'].apply(lambda x: parser.isoparse(x) if pd.notna(x) else pd.NaT)
    return df

def get_new_markets(df):
    #new markets

    # Example function to create Telegram message
    def df_to_telegram_message(df):
        messages = []
        for _, row in df.iterrows():
            msg = (
                f"link: {row['link']}\n"
                f"question: {row['question']}\n"
                f"start Date: {row['startDate']}\n"
                f"end Date: {row['endDate']}\n"
                f"outcomes: {row['outcomes']}\n"
                f"outcomePrices: {row['outcomePrices']}\n"
            )
            messages.append(msg)
        
        # Join all messages with an extra newline between each market
        return "\n".join(messages)

    one_day_ago = datetime.now(timezone.utc) - timedelta(hours=4)
    cond1 = df['startDate'] > one_day_ago
    cond2 = df['category'] != "crypto"

    new_markets = df[cond1 & cond2]

    if not new_markets.empty:
        telegram_message = df_to_telegram_message(new_markets)
        return telegram_message
    else:
        return None
    

def get_large_tx(df):
    BASE_URL = "https://data-api.polymarket.com/trades"
    THRESHOLD = 10000
    MAX_CONCURRENT_REQUESTS = 5  # 👈 adjust to stay below rate limit


    async def get_large_tx(session, event_id, sem):
        """Fetch and process large transactions for a given event ID asynchronously with rate limit."""
        url = f"{BASE_URL}?eventId={event_id}&limit=50&offset=0&filterType=CASH&filterAmount=1"

        async with sem:  # 👈 limits concurrency
            await asyncio.sleep(0.5)  # small delay between requests (optional)
            async with session.get(url) as response:
                if response.status == 429:
                    print(f"⏳ Rate limited for event {event_id}, retrying...")
                    await asyncio.sleep(2)
                    return await get_large_tx(session, event_id, sem)

                if response.status != 200:
                    print(f"⚠️ Failed to fetch event {event_id} ({response.status})")
                    return pd.DataFrame(columns=['nickname', 'date', 'question', 'outcome', 'total_value'])

                data = await response.json()

        if not data:
            return pd.DataFrame(columns=['nickname', 'date', 'question', 'outcome', 'total_value','event_id'])

        txs = []
        for tx in data:
            t = {
                "event_id" : event_id,
                "question": tx.get('title'),
                "outcome": tx.get('outcome'),
                "side": tx.get('side'),
                "size": float(tx.get('size', 0)),
                "price": float(tx.get('price', 0)),
                "time": pd.to_datetime(tx.get('timestamp'), unit='s'),
                "wallet": tx.get('proxyWallet'),
                "nickname": tx.get('pseudonym'),
            }
            txs.append(t)

        if not txs:
            return pd.DataFrame(columns=['nickname', 'date', 'question', 'outcome', 'total_value','event_id'])

        df_tx = pd.DataFrame(txs)
        df_tx['date'] = df_tx['time'].dt.date
        df_tx['trade_value'] = df_tx['size'] * df_tx['price'] * df_tx['side'].map({'BUY': 1, 'SELL': -1})

        summary = (
            df_tx.groupby(['nickname', 'date', 'question', 'outcome','event_id'], as_index=False)
            .agg(total_value=('trade_value', 'sum'))
        )

        summary['date'] = pd.to_datetime(summary['date'], utc=True)
        cond1 = summary['total_value'] >= THRESHOLD
        cond2 = summary['total_value'] <= -THRESHOLD
        cond3 = summary['date'] > (datetime.now(timezone.utc) - timedelta(days=1))
        large_tx = summary[cond1 | cond2 & cond3]

        return large_tx


    async def main(event_ids):
        sem = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)
        async with aiohttp.ClientSession() as session:
            tasks = [get_large_tx(session, eid, sem) for eid in event_ids]
            results = await asyncio.gather(*tasks)
        return pd.concat(results, ignore_index=True)
    
    # Example function to create Telegram message
    def df_to_telegram_message(df):
        messages = []
        for _, row in df.iterrows():
            msg = (
                f"nickname: {row['nickname']}\n"
                f"question: {row['question']}\n"
                f"date: {row['date']}\n"
                f"outcome: {row['outcome']}\n"
                f"value: {row['total_value']}\n"
                f"event id: {row['event_id']}\n"
            )
            messages.append(msg)
        
        # Join all messages with an extra newline between each market
        return "\n".join(messages)

    import nest_asyncio
    nest_asyncio.apply()

    # Replace with your df['id'].unique()
    df = df[df['category'] != "crypto"]
    event_ids = df['id'].unique()

    combined_df = asyncio.run(main(event_ids))

    if not combined_df.empty:
        telegram_message = df_to_telegram_message(combined_df)
        return telegram_message
    else:
        return None

def get_high_movement(df):
    #4hr high movement

    async def get_high_mover(session, start_time, token_info, sem):
        """
        token_info: dict containing
            token_id, link, question, outcomes, outcomePrices
        """
        token_id = token_info['token_id']
        url_price = f"https://clob.polymarket.com/prices-history?startTs={start_time}&market={token_id}&fidelity=120"

        async with sem:  # limit concurrency
            try:
                async with session.get(url_price) as resp:
                    if resp.status != 200:
                        return None
                    data = await resp.json()

                    df_price = pd.DataFrame(data.get('history', []))
                    if df_price.empty or len(df_price) < 3:
                        return None

                    df_price['time'] = pd.to_datetime(df_price['t'], unit='s')

                    p_1 = df_price['p'].iloc[-1]
                    p_2 = df_price['p'].iloc[-3]
                    p_diff = p_1 - p_2

                    if abs(p_diff) > 0.15:
                        return {
                            "token_id": token_id,
                            "price_diff": p_diff,
                            "link": token_info['link'],
                            "question": token_info['question'],
                            "outcomes": token_info['outcomes'],
                            "outcomePrices": token_info['outcomePrices']
                        }
                    return None
            except Exception as e:
                print(f"Error for token {token_id}: {e}")
                return None

    async def main(df, start_time, max_concurrency=5):
        sem = asyncio.Semaphore(max_concurrency)
        tasks = []

        async with aiohttp.ClientSession() as session:
            for row in range(len(df)):
                token_ids = df['token_ids'].iloc[row]

                # Ensure token_ids is a list
                if isinstance(token_ids, str):
                    token_ids = json.loads(token_ids)
                elif not token_ids:
                    continue

                token_info = {
                    "token_id": token_ids[0],
                    "link": df['link'].iloc[row],
                    "question": df['question'].iloc[row],
                    "outcomes": df['outcomes'].iloc[row],
                    "outcomePrices": df['outcomePrices'].iloc[row]
                }
                tasks.append(get_high_mover(session, start_time, token_info, sem))

            results = await asyncio.gather(*tasks)
            # Filter out None results
            results = [r for r in results if r]
            return results
        
    def df_to_telegram_message(df):
        messages = []
        for _, row in df.iterrows():
            msg = (
                f"link: {row['link']}\n"
                f"question: {row['question']}\n"
                f"price movement: {row['price_diff']}\n"
                f"outcomes: {row['outcomes']}\n"
                f"outcomePrices: {row['outcomePrices']}\n"
            )
            messages.append(msg)
        
        # Join all messages with an extra newline between each market
        return "\n".join(messages)


    dt_minus_5 = datetime.now() - timedelta(days=1)
    start_time = int(dt_minus_5.timestamp())

    df = df[df['category'] != "crypto"]
    high_movers = asyncio.run(main(df, start_time, max_concurrency=7))
        
    if high_movers:
        high_movers = pd.DataFrame(high_movers)
        high_movers = high_movers[~high_movers['outcomePrices'].isin([['0','1'], ['1', '0']])]

        message = df_to_telegram_message(high_movers)
        print(message)
        return message
    else:
        return None
    

##rewards

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
    
## order book
def get_orderbook_data(token_id):

    url_order_book = "https://clob.polymarket.com/books?token_ids"

    payload = [
        {
            "token_id": token_id
        }
    ]

    headers = {
        "Content-Type": "application/json"
    }

    response = requests.post(url_order_book, json=payload, headers=headers)

    try:
    
        if response.status_code == 200:
            market_contract = response.json()[0]['market']
            time = response.json()[0]['timestamp']
            bids = response.json()[0]['bids']
            asks = response.json()[0]['asks']
            tick_size = response.json()[0]['tick_size']
            try:
                mid_price = mid_price = (float(response.json()[0]['bids'][-1]['price']) + float(response.json()[0]['asks'][-1]['price']))/2
            except:
                print("no mid price found")
                mid_price = None
            data = {
                "market_contract" : market_contract,
                "time" : time,
                "bids" : bids,
                "asks" : asks,
                "tick_size" : tick_size,
                "mid_price" : mid_price
            }

            return data
    except Exception as e:
        print(f"error {e}")
        return None
    
def get_reward_ob_data(rewards_data,ob):

    reward_upper_lim = ob['mid_price'] + rewards_data['reward_spread']/100
    reward_lower_lim = ob['mid_price'] - rewards_data['reward_spread']/100
    
    get_reward_ob_bid = [
        {'price': float(price), 'size': float(size)}
        for bid in ob['bids']
        for price, size in [(bid['price'], bid['size'])]
        if float(price) > reward_lower_lim
    ]

    get_reward_ob_ask = [
        {'price': float(price), 'size': float(size)}
        for bid in ob['asks']
        for price, size in [(bid['price'], bid['size'])]
        if float(price) < reward_upper_lim
    ]
    
    data = {
        "bids" : get_reward_ob_bid,
        "asks" : get_reward_ob_ask 
    }
    
    return data

def get_wallet_balance():
    USDC_CONTRACT = "0x2791bca1f2de4661ed88a30c99a7a9449aa84174"
    address = os.getenv('POLY_FUNDER_ADDRESS')
    RPC = "https://polygon-rpc.com"
    w3 = Web3(Web3.HTTPProvider(RPC))
    erc20_abi = [{"constant":True,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"type":"function"},
             {"constant":True,"inputs":[],"name":"decimals","outputs":[{"name":"","type":"uint8"}],"type":"function"}]
    contract = w3.eth.contract(address=Web3.to_checksum_address(USDC_CONTRACT), abi=erc20_abi)

    try:
        raw = contract.functions.balanceOf(Web3.to_checksum_address(address)).call()
        usdc = raw / 1e6
        return usdc
    except Exception as e:
        print(f"Error query balance: {e}")
        return None





def get_wallet_balance_moralis():
    api_key = os.getenv('MORALIS_API_KEY')
    wallet = os.getenv('POLY_FUNDER_ADDRESS')
    usdc = "0x2791bca1f2de4661ed88a30c99a7a9449aa84174"

    url = f"https://deep-index.moralis.io/api/v2.2/{wallet}/erc20?chain=polygon&token_addresses%5B0%5D={usdc}"

    headers = {
        "Accept": "application/json",
        "X-API-Key": api_key
    }

    response = requests.get(url, headers = headers)

    if response.status_code == 200:
        responses = response.json()
        if responses:
            for data in responses:
                if data['symbol'] == 'USDC':
                    bal = int(data['balance'])
                    decimal = int(data['decimals'])
                    value = bal / decimal
                    return value
                
            return None

        else:
            print("unable to find USDC")
            return None

    else:
        print("error getting USDC balance")
        return None

def get_market_liquidity_volume_tick(market_id):
    url = f"https://gamma-api.polymarket.com/markets/{market_id}"

    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
        liquidity = data['liquidityNum']
        volume = data['volumeNum']
        tick = data['orderPriceMinTickSize']

        print(f"liqudity: {liquidity}, volume: {volume}, tick size : {tick}")
        return liquidity, volume, tick

    else:
        print("error getting market data")
        return None, None , None

def get_token_id(market_id):
    url = f"https://gamma-api.polymarket.com/markets/{market_id}"

    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
        token_ids = data['clobTokenIds']
        token_ids = json.loads(token_ids)

        return token_ids
    
    else:
        return None
    
def get_exisiting_positions():
    assets = []
    FUNDER = os.getenv("POLY_FUNDER_ADDRESS")

    positions_url = f"https://data-api.polymarket.com/positions?user={FUNDER}"

    response = requests.get(positions_url)

    if response.status_code == 200:

        positions = response.json()
        if positions:
            for position in positions:
                asset = position['asset']
                assets.append(asset)
    return assets


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
        file_path = "markets.csv"   # Change to your actual CSV file path

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