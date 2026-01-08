import os
import dotenv
import requests
from send_telegram_message import send_telegram_message
from utils import *
from orders import *
import pandas as pd
dotenv.load_dotenv()

SET_NEVER_BELOW_COST=os.getenv("SET_NEVER_BELOW_COST","1") == "1"
MARKETS_DIR = os.getenv('MARKETS_DIR')

file_path = MARKETS_DIR  # Change to your actual CSV file path

df = pd.read_csv(file_path, usecols=['question','market_id', 'side','token_id'], dtype={'question' : str,'market_id': str, 'side': str, 'token_id': str})

required_cols = {'question','market_id', 'side', 'token_id'}
missing_cols = required_cols - set(df.columns)

if missing_cols:
    raise ValueError(f"❌ Missing required columns: {missing_cols}")

csv_questions_set = set(df['question'].str.lower())

FUNDER = os.getenv("POLY_FUNDER_ADDRESS")

positions_url = f"https://data-api.polymarket.com/positions?user={FUNDER}"

response = requests.get(positions_url)

if response.status_code == 200:

    positions = response.json()
    if positions:
        print(f"no of pos : {len(positions)}")
        for position in positions:
            slug = position['slug']
            event_slug = position['eventSlug']
            asset = position['asset']
            cond_id = position['conditionId']
            event_id = position['eventId']
            total_size = float(position['size'])
            question = position['title']
            avg_price = position['avgPrice']
            print(f"{question} {asset} {total_size} - {avg_price}")

            if question.lower() not in csv_questions_set:
                print("skip this question, not found in csv file")
                continue

            #get tick size
            url = f"https://gamma-api.polymarket.com/events/{event_id}"

            response = requests.get(url)
            data = response.json()
            markets = data['markets']
            for market in markets:
                if market['slug'].lower() == slug.lower():
                    tick = market['orderPriceMinTickSize']
                    decimal_places = len(str(tick).split(".")[1]) if "." in str(tick) else 0

            #get order book price
            ob = get_orderbook_data(asset)
            bids = ob['asks']

            sorted_asks = sorted(bids, key=lambda x: float(x['price']), reverse=False)

            price = float(sorted_asks[0]['price'])
            print(f"price = {price}")

            #New avg price
            if decimal_places == 0:
                avg_price = avg_price + float(tick)
            else:
                avg_price = avg_price + float(tick) * 5

            if price < avg_price and SET_NEVER_BELOW_COST:
                print("skip, price is lower than avg price")
                price = round(avg_price,decimal_places)
                #price = avg_price
            

            sell_count = 0

            #check for current sell orders and cancel and change price if not lowest price
            current_orders = get_current_orders(asset)
            if current_orders:
                print("check for sell orders")
                for order in current_orders:
                    print(order)
                    if order['side'] == 'SELL':
                        print("add sell count")
                        sell_count += 1
                        current_price = float(order['price'])
                        if current_price != price:
                            order_id = order['id']
                            cancel_order(order_id)
                            place_sell_order(asset,price,total_size)
                            message = f"Cancel old SELL ORDER for {question} at size {total_size} from {current_price} to {price}"
                            send_telegram_message(message)
            #if do not have existing sell orders for this market
            if sell_count == 0:
                print("add sell order")
                place_sell_order(asset,price,total_size)
                message = f"SELL ORDER for {question} at size {total_size} at price {price}"
                send_telegram_message(message)


    else:
        print("no positions found")

else:
    message = "unable to ping exisiting positions"
    send_telegram_message(message)
