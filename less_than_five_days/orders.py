from py_clob_client.client import ClobClient
from py_clob_client.clob_types import OrderArgs, OrderType
from py_clob_client.order_builder.constants import BUY, SELL
from py_clob_client.clob_types import OpenOrderParams, OrderArgs, OrderType, PostOrdersArgs, OrdersScoringParams, TradeParams
import os
import dotenv

dotenv.load_dotenv()

HOST      = "https://clob.polymarket.com"
CHAIN_ID  = 137  # Polygon mainnet
PRIVATE_KEY = os.getenv("POLY_PRIVATE_KEY")
FUNDER      = os.getenv("POLY_FUNDER_ADDRESS")

MIN_SCALE_AMT = int(os.getenv("MIN_SCALE_AMT","1"))

client = ClobClient(
        HOST,
        key=PRIVATE_KEY,
        chain_id=CHAIN_ID,
        signature_type=1,      # adjust: 0=EOA, 1=Magic/Email wallet, 2=Proxy wallet
        funder=FUNDER
    )
client.set_api_creds(client.create_or_derive_api_creds())

def get_current_orders(market_id):
    # Example: get active orders for a specific market
    market_id = market_id#"0x123456..."  # condition/market ID
    filtered_orders = client.get_orders(OpenOrderParams(asset_id=market_id))
    print("Filtered orders:", filtered_orders)
    return filtered_orders

def place_order(token_id, price, size):
    print(f"Placing order for {token_id} at {price} with size {size}")
    

    order_args = OrderArgs(
        token_id  = token_id, # outcome token ID you want to trade
        price    = price, 
        size     = size, 
        side     = BUY
    )

    signed_order = client.create_order(order_args)
    resp = client.post_order(signed_order, OrderType.GTC)  # Good-Till-Cancelled
    print("Order placed:", resp)

def place_order_scale(token_id, start_price, reward_bid_min, size, tick_size, min_reward_size):

    steps = int((start_price - reward_bid_min) / tick_size) + 1

    if steps <= 0:
        print("Error: reward_bid_min must be lower than start_price")
        return None

    # If too many steps, reduce them and spread evenly
    ORIGINAL_STEPS = steps
    if steps > 5:
        steps = max(3, steps // 3)  # prevent steps from becoming 1
        print(f"Reducing steps from {ORIGINAL_STEPS} → {steps}")

        # Spread prices evenly between start and min price
        price_step = (start_price - reward_bid_min) / (steps - 1)
        prices = [start_price - i * price_step for i in range(steps)]

    else:
        # normal tick-size based steps
        prices = [start_price - i * tick_size for i in range(steps)]

    # Round for safety
    prices = [round(p / tick_size) * tick_size for p in prices]

    # Recompute sizing per order
    size_per_order = size / steps

    #get new sizes baded on min amount per order
    values = [price * size_per_order for price in prices]

    new_values = [max(v,MIN_SCALE_AMT) for v in values]

    # Compute NEW sizes to match new_values
    new_sizes = []
    for price, val in zip(prices, new_values):
        if price <= 0:
            new_sizes.append(0)
        else:
            new_sizes.append(val / price)

    new_sizes = [max(s,size_per_order) for s in new_sizes]

    print(f"sizes : {new_sizes} \n prices : {prices}")
    print(f"min size : {min_reward_size}")

    # Check min reward size
    if min(new_sizes) < min_reward_size:
        new_sizes = [max(s,min_reward_size) for s in new_sizes]

    # Build batch order list
    batch_orders = []

    for price, size_out in zip(prices,new_sizes):
        batch_orders.append(
            PostOrdersArgs(
                order=client.create_order(OrderArgs(
                    price=price,
                    size=size_out,
                    side=BUY,
                    token_id=token_id,
                )),
                orderType=OrderType.GTC
            )
        )

    resp = client.post_orders(batch_orders)
    print("Order placed:", resp)
    return f"Order placed: {resp}"

def place_sell_order(token_id, price, size):
    print(f"Placing SELL order for {token_id} at {price} with size {size}")
    

    order_args = OrderArgs(
        token_id  = token_id, # outcome token ID you want to trade
        price    = price, 
        size     = size, 
        side     = SELL
    )

    signed_order = client.create_order(order_args)
    resp = client.post_order(signed_order, OrderType.GTC)  # Good-Till-Cancelled
    print("Order placed:", resp)


def cancel_order(order_id):
    order_id = order_id #"0xabcdef..."  # the order ID you want to cancel
    resp     = client.cancel(order_id)
    print("Cancel response:", resp)

def cancel_order_by_asset(token_id):
    resp = client.cancel_market_orders(asset_id=token_id)
    print("Cancel response:", resp)
    return resp

def get_trades():
    trades = client.get_trades(
        TradeParams(
            maker_address=client.get_address()
        )
    )
    return trades

def get_all_orders():
    # Example: get all active orders from your account (no filter)
    open_orders = client.get_orders(OpenOrderParams())

    return open_orders

def get_all_orders_id(open_orders):

    all_order_ids = [order['id'] for order in open_orders]

    return all_order_ids


def cancel_all_orders(all_order_ids):

    for order_id in all_order_ids:
        resp     = client.cancel(order_id)
        print("Cancel response:", resp)


def get_rewards_scoring(order_ids : list):

    scoring = client.are_orders_scoring(OrdersScoringParams(
        orderIds=order_ids
    )
    )

    return scoring

    

