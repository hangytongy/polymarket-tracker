import os
import dotenv
import requests
from send_telegram_message import send_telegram_message
from utils import *
from orders import *

dotenv.load_dotenv()

FUNDER = os.getenv("POLY_FUNDER_ADDRESS")

positions_url = url = f"https://data-api.polymarket.com/positions?user={FUNDER}"

response = requests.get(positions_url)

if response.status_code == 200:

    positions = response.json()
    if positions:
        for position in positions:
            asset = position['asset']
            cond_id = position['conditionId']
            total_size = position['size']
            question = position['title']

            #get order book price
            ob = get_orderbook_data(asset)
            bids = ob['asks']

            sorted_asks = sorted(bids, key=lambda x: float(x['price']), reverse=False)

            price = sorted_asks[0]['price']

            #check for current sell orders and cancel and change price if not lowest price
            current_orders = get_current_orders(asset)
            if current_orders:
                for order in current_orders:
                    if order['side'] == 'SELL':
                        current_price = float(order['price'])
                        if current_price != price:
                            order_id = order['id']
                            cancel_order(order_id)
                            place_sell_order(asset,price,total_size)
                            message = f"Cancel old SELL ORDER for {question} at size {total_size} from {current_price} to {price}"
                            send_telegram_message(message)
            #if do not have existing sell orders for this market
            else:
                place_sell_order(asset,price,total_size)
                message = f"SELL ORDER for {question} at size {total_size}"
                send_telegram_message(message)


    else:
        print("no positions found")

else:
    message = "unable to ping exisiting positions"
    send_telegram_message(message)