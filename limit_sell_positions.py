import os
import dotenv
import requests
from send_telegram_message import send_telegram_message
from utils import *
from orders import *

dotenv.load_dotenv()

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
            total_size = float(position['size'])
            question = position['title']
            print(f"{question} {asset} {total_size}")

            #get order book price
            ob = get_orderbook_data(asset)
            bids = ob['asks']

            sorted_asks = sorted(bids, key=lambda x: float(x['price']), reverse=False)

            price = float(sorted_asks[0]['price'])
            print(f"price = {price}")
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
                message = f"SELL ORDER for {question} at size {total_size}"
                send_telegram_message(message)


    else:
        print("no positions found")

else:
    message = "unable to ping exisiting positions"
    send_telegram_message(message)