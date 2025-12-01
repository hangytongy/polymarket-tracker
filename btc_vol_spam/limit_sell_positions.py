import os
import dotenv
import requests
from send_telegram_message import send_telegram_message
import pandas as pd
dotenv.load_dotenv()
from spam_utils import *

SET_NEVER_BELOW_COST=os.getenv("SET_NEVER_BELOW_COST","0") == "1"
SELL_PRICE=float(os.getenv("SELL_PRICE"))

FUNDER = os.getenv("POLY_FUNDER_ADDRESS")

positions_url = f"https://data-api.polymarket.com/positions?user={FUNDER}"

response = requests.get(positions_url)

if response.status_code == 200:

    positions = response.json()
    if positions:
        print(f"no of pos : {len(positions)}")
        for position in positions:
            try:
                slug = position['slug']
                event_slug = position['eventSlug']
                asset = position['asset']
                cond_id = position['conditionId']
                event_id = position['eventId']
                total_size = float(position['size'])
                question = position['title']
                avg_price = position['avgPrice']
                print(f"{question} {asset} {total_size} - {avg_price}")

                if 'bitcoin up or down' not in question.lower():
                    print("skip this question")
                    continue

                #get tick size
                decimal_places = 2

                #get mid price
                url = f"https://clob.polymarket.com/midpoint?token_id={asset}"
                response = requests.get(url)
                print(response.json())
                curr_price = float(response.json()['mid'])
                print(f"now price = {curr_price}")

                sell_price = SELL_PRICE
                sell_price = min(SELL_PRICE,avg_price * 1.1)

                #if prices now is lower than buy in price
                if curr_price < avg_price:
                    #if dont want to lose a single cent
                    #if SET_NEVER_BELOW_COST:
                    #    print("skip, price is lower than avg price")
                    #    price = round(avg_price,decimal_places)
                    #if hit stop loss
                    if curr_price < avg_price * 0.8:
                        price = round(curr_price,decimal_places)
                    else:
                        price = sell_price
                elif curr_price > sell_price:
                    price = curr_price
                else:
                    price = sell_price

                price = round(price,decimal_places)

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
                                print(message)
                                send_telegram_message(message)
                #if do not have existing sell orders for this market
                if sell_count == 0:
                    print("add sell order")
                    place_sell_order(asset,price,total_size)
                    message = f"SELL ORDER for {question} at size {total_size} at price {price}"
                    print(message)
                    send_telegram_message(message)
            except Exception as e:
                print(f"error : {e}")


    else:
        print("no positions found")

else:
    message = "unable to ping exisiting positions"
    send_telegram_message(message)
