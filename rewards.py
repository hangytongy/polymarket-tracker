from utils import get_all_rewards, get_wanted_rewards_market, get_orderbook_data, get_reward_ob_data
from orders import get_current_orders, place_order, cancel_order
import pandas as pd
from send_telegram_message import send_telegram_message

buy_in_size = 10

try:
    all_rewards = get_all_rewards()

    # === STEP 1: Load CSV ===
    file_path = "markets.csv"   # Change to your actual CSV file path

    df = pd.read_csv(file_path, usecols=['market_id', 'side'], dtype={'market_id': str, 'side': str})

    # === STEP 2: Validate columns ===
    required_cols = {'market_id', 'side'}
    missing_cols = required_cols - set(df.columns)

    if missing_cols:
        raise ValueError(f"❌ Missing required columns: {missing_cols}")

    # === STEP 3: Continue with your logic ===

    for _, row in df.iterrows():
        market_id = str(row['market_id'])
        side = str(row['side'])
        print(f"-----{market_id}----")

        reward_data, token_id = get_wanted_rewards_market(all_rewards,market_id,side)

        if token_id:
            question = reward_data['question']
            #get market orderbook
            ob_data = get_orderbook_data(token_id)
            #get reward bid and ask spread
            reward_ob_data = get_reward_ob_data(reward_data,ob_data)
            #get minimum order size
            min_size = int(reward_data['reward_min_size'])

            if buy_in_size < min_size:
                size = min_size
            else:
                size = buy_in_size

            #get reward bid range
            reward_bid = reward_ob_data['bids']
            reward_bid = [bid['price'] for bid in reward_bid]
            reward_bid_min = min(reward_bid)
            reward_bid_max = max(reward_bid)
            decimal_places = len(str(reward_bid_max).split(".")[1]) if "." in str(reward_bid_max) else 0
            reward_mid_range = (reward_bid_max + reward_bid_min) / 2
            reward_mid_range = round(reward_mid_range,decimal_places)
            mid_range_lower = round((reward_mid_range + reward_bid_min) / 2,decimal_places)
            mid_range_upper = round((reward_mid_range + reward_bid_max) / 2,decimal_places)

            print(f"Mid range: {reward_mid_range}, Mid range lower: {mid_range_lower}, Mid range upper: {mid_range_upper}")

            #get current orders by token_id
            current_orders = get_current_orders(token_id)

            #check if there is a current order in this market
            if current_orders:
                #check if the current order is in the reward bid range
                for order in current_orders:
                    if float(order['price']) >= mid_range_lower and float(order['price']) <= mid_range_upper:
                        print(f'Current order is in the reward bid range')
                    else:
                        print(f'Current order is not in the reward bid range')
                        order_id = order['id']
                        cancel_order(order_id)
                        bid_price = reward_mid_range
                        place_order(token_id,bid_price,size)
                        print(f"placed order at {bid_price} for {question} and {side}")
                        message = f"Order out of reward range, cancel old price {order['price']} and placed order at {bid_price} for {question} and {side} and size {size}"
                        send_telegram_message(message)


            else:
                print(f'No current order in this market')
                bid_price = reward_mid_range
                place_order(token_id,bid_price,size)
                print(f"placed order at {bid_price} for {question} and {side}")
                message = f"placed order at {bid_price} for {question} and {side} at size {size}"
                send_telegram_message(message)


        else:
            print(f'No reward found for {market_id} and {side}')

except Exception as e:
    message = f"Error: {e}"
    send_telegram_message(message)

