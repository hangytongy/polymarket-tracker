import requests
import json
from datetime import datetime, timezone
import csv
import os
import pandas as pd
from utils import get_token_id
from orders import get_current_orders, cancel_order

MARKETS_DIR = os.getenv('MARKETS_DIR')


def get_events(category):

    print(category)

    count = 0
    limit = 500

    url = "https://gamma-api.polymarket.com/events"

    events_category = []

    params = {
        "limit" : limit,
        "offset" : limit * count,
        "order" : "id",
        "ascending" : False,
        "closed" : False,
        "active" : True,
        "tag_slug" : category
    }

    while True:
        
        response = requests.get(url, params = params)

        if response.status_code == 200:
            events = response.json()
            if len(events) > 0:
                print(len(events))
                events_category.extend(events)
                count += 1
                params["offset"] = limit * count
            else:
                break


    print("total events :", len(events_category))
    return events_category


def get_mm_markets(all_events):

    now = datetime.now(timezone.utc)

    events_can_mm = []

    for event in all_events:

        markets = event["markets"]

        for market in markets:

            outcome_Ids = market.get('clobTokenIds')
            question = market.get('question')
            id = market.get('id')
            outcomes = market.get('outcomes')
            outcome_prices = market.get('outcomePrices')
            volume = market.get('volume')
            liquidity = market.get('liquidity')
            end_date = market.get('endDate')

            #print(outcome_Ids) if outcome_Ids else None
            #print(question) if question else None
            #print(id) if id else None
            #print(outcomes) if outcomes else None
            #print(outcome_prices) if outcome_prices else None
            #print(volume) if volume else None
            #print(liquidity) if liquidity else 0
            #print(end_date) if end_date else None

            if end_date and outcome_prices:

                outcome_prices = json.loads(outcome_prices)
                outcomes = json.loads(outcomes)
                outcome_Ids = json.loads(outcome_Ids)

                yes_price = float(outcome_prices[0])
                no_price = float(outcome_prices[1])
                end_date = end_date.replace('Z', '+00:00')
                end_date = datetime.fromisoformat(end_date)
                time_diff = end_date - now
                time_diff_days = time_diff.days
                #print("time diff : ", time_diff_days)
                # time less than 5 days left and price (yes/no) is more than 95%
                if time_diff_days > 0 and time_diff_days <= 5:
                    #print("This market is closing within 5 days, can MM")
                    idx = 0 if yes_price > 0.95 else (1 if no_price >= 0.95 else None)
                    if idx is not None:
                    
                        d = {
                            "id" : id,
                            "question" : question,
                            "end_date" : end_date,
                            "outcomes" : outcomes[idx],
                            "outcome_prices" : outcome_prices[idx],
                            "condition_id" : outcome_Ids[idx],
                            "volume" : volume,
                            "liquidity" : liquidity
                        }
                        events_can_mm.append(d)
            else:
                #print("no end date or outcome prices")
                pass
    return events_can_mm

def remove_old_markets(market_id):
    token_ids = get_token_id(market_id)

    if token_ids:
        for token_id in token_ids:

            orders = get_current_orders(token_id)
            if orders:
                for order in orders:   
                    if order['side'] =="BUY":
                        order_id = order['id']
                        cancel_order(order_id)
                message = f"Order canceled for {market_id} {token_id}"

        print(f"✅ Removed market_id {market_id}")

all_events = []

CATEGORIES = ['economy', 'world', 'politics', 'tech']

for category in CATEGORIES:
    events_category = get_events(category)
    all_events.extend(events_category)

events_can_mm = get_mm_markets(all_events)

if events_can_mm:

    #get all market ids in old markets.csv
    old_df = pd.read_csv("markets.csv")
    old_market_ids = set(old_df['market_id'])

    #remove duplicate markets
    unique_events = list({event['id']: event for event in events_can_mm}.values())
    print(len(unique_events))
    print(unique_events)

    df = pd.DataFrame(unique_events)

    # 2. Rename columns to match your required headers
    column_mapping = {
        "question": "question",
        "id": "market_id",
        "outcomes": "side",
        "condition_id": "token_id"
    }

    # 3. Rename, filter for only those columns, and save
    df = df.rename(columns=column_mapping)[list(column_mapping.values())]
    df.to_csv("markets.csv", index=False)

    print(f"Saved {len(df)} rows to markets.csv")

    if old_market_ids:
        #get new market id, compare with old and remove existing orders of old
        new_market_ids = set(df['market_id'])
        dropped_ids = list(old_market_ids - new_market_ids)

        if dropped_ids:
            for id in dropped_ids:
                remove_old_markets(id)

else:
    print("No markets can be MM")







