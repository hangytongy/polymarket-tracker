from model import *
from spam_utils import get_current_orders, get_exisiting_positions, place_order, cancel_order
from send_telegram_message import send_telegram_message
import time
import os
import dotenv

dotenv.load_dotenv()

#size = int(os.getenv("SIZE"))
#MAX_PRICE = float(os.getenv("MAX_PRICE"))
#MAX_TIME_LEFT = float(os.getenv("MAX_TIME_LEFT"))

while True:

    size = int(os.getenv("SIZE"))
    MAX_PRICE = float(os.getenv("MAX_PRICE"))
    MAX_TIME_LEFT = float(os.getenv("MAX_TIME_LEFT"))
    MIN_TIME_LEFT = float(os.getenv("MIN_TIME_LEFT"))
    BUY_SLEEP_TIME= int(os.getenv("BUY_SLEEP_TIME"))

    timestamp = get_timestamp() #only need to be done every 15min

    token_ids = get_btc_token_ids(timestamp) # need to check if this gets the correct market

    time_left = get_time_left()
        
    if token_ids:

        for token_id in token_ids:

            #check for current pos and if have, skip if set_no_buy_if_got_existingPos = True
            assets = get_exisiting_positions()
            #if there is a current position
            if token_id in assets:
                print("already have exisitng positions no place order")
                continue

            mid_price = get_mid_price(token_id)
            current_orders = get_current_orders(token_id)
            if current_orders:
                print(current_orders)
                buy_orders = [order for order in current_orders if order['side'] == 'BUY']
                if not buy_orders:
                    if mid_price >= MAX_PRICE and mid_price < 0.99 and time_left < MAX_TIME_LEFT and time_left > MIN_TIME_LEFT:
                        place_order(token_id, mid_price,size)
                        message = f"placed order for BTC at {mid_price} for timestamp {timestamp}"
                        send_telegram_message(message)
                    else:
                        print(f"mid price {mid_price} not at {MAX_PRICE}")
                else:
                    for order in buy_orders:
                        if time_left < MIN_TIME_LEFT:
                            order_id = order['id']
                            cancel_order(order_id)
                            message = f"BTC order out of time range {time_left}, cancel"
                            send_telegram_message(message)
            else:
                if mid_price >= MAX_PRICE and mid_price < 0.99 and time_left < MAX_TIME_LEFT and time_left > MIN_TIME_LEFT:
                    place_order(token_id, mid_price,size)
                    message = f"placed order for BTC at {mid_price} for timestamp {timestamp}"
                    send_telegram_message(message)
                else:
                    print(f"mid price {mid_price} not at {MAX_PRICE}")
        
    time.sleep(BUY_SLEEP_TIME)


