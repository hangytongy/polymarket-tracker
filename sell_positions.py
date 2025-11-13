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
            bids = ob['bids']

            sorted_bids = sorted(bids, key=lambda x: float(x['price']), reverse=True)

            remaining = total_size
            orders_to_fill = []

            for bid in sorted_bids:
                price = float(bid['price'])
                size = float(bid['size'])

                if remaining < 0:
                    break

                if size <= remaining:
                    orders_to_fill.append({'price':price, 'size': size})
                    remaining -= size
                
                else:
                    orders_to_fill.append({'price':price, 'size': remaining})
                    remaining = 0
            
            if orders_to_fill:
                for order in orders_to_fill:
                    price_ = order['price'] 
                    size_ = order['size']

                    place_sell_order(asset,price_,size_)
                message = f"SELL ORDER for {question} at size {total_size}"
                send_telegram_message(message)


    else:
        print("no positions found")

else:
    message = "unable to ping exisiting positions"
    send_telegram_message(message)





