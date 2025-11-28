from model import *
from spam_utils import *
from send_telegram_message import send_telegram_message
import time

size = 10
MAX_PRICE = 0.935

while True:

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
                    if mid_price >= MAX_PRICE and mid_price < 0.99 and time_left < 5:
                        place_order(token_id, mid_price,size)
                        message = f"placed order for BTC at {mid_price} for timestamp {timestamp}"
                        send_telegram_message(message)
                    else:
                        print(f"mid price {mid_price} not at {MAX_PRICE}")
            else:
                if mid_price >= MAX_PRICE and mid_price < 0.99 and time_left < 5:
                    place_order(token_id, mid_price,size)
                    message = f"placed order for BTC at {mid_price} for timestamp {timestamp}"
                    send_telegram_message(message)
                else:
                    print(f"mid price {mid_price} not at {MAX_PRICE}")
        
    time.sleep(5)


