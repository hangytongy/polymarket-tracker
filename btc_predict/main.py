from model import *
from predict_utils import *
from send_telegram_message import send_telegram_message
import time

size = 5

while True:

    timestamp = get_timestamp() #only need to be done every 15min

    token_ids = get_btc_token_ids(timestamp) # need to check if this gets the correct market

    prob, conf, time_left = get_probability()

    if prob > 0.75 and conf > 0.8:
        print("yes, BTC will be higher")
        token_id = token_ids[0]
        
    elif prob < 0.095 and conf >0.8:
        print("no, BTC will be lower")
        token_id = token_ids[1]
        
    else:
        print("nothing, pass")
        token_id = None
        
    if token_id:

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
                if time_left > 1 and mid_price < 0.98 and mid_price > 0.03:
                    place_order(token_id, mid_price,size)
                    message = f"placed order for BTC at {mid_price} with prob {prob}"
                    send_telegram_message(message)
        else:
            if time_left > 1 and mid_price < 0.98 and mid_price > 0.03:
                place_order(token_id, mid_price,size)
                message = f"placed order for BTC at {mid_price} with prob {prob}"
                send_telegram_message(message)
    
    time.sleep(15)


