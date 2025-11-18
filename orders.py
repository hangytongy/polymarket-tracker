from py_clob_client.client import ClobClient
from py_clob_client.clob_types import OrderArgs, OrderType
from py_clob_client.order_builder.constants import BUY, SELL
from py_clob_client.clob_types import OpenOrderParams
from py_clob_client.clob_types import OrdersScoringParams
from py_clob_client.clob_types import TradeParams
import os
import dotenv

dotenv.load_dotenv()

HOST      = "https://clob.polymarket.com"
CHAIN_ID  = 137  # Polygon mainnet
PRIVATE_KEY = os.getenv("POLY_PRIVATE_KEY")
FUNDER      = os.getenv("POLY_FUNDER_ADDRESS")

client = ClobClient(
        HOST,
        key=PRIVATE_KEY,
        chain_id=CHAIN_ID,
        signature_type=1,      # adjust: 0=EOA, 1=Magic/Email wallet, 2=Proxy wallet
        funder=FUNDER
    )
client.set_api_creds(client.create_or_derive_api_creds())

def get_current_orders(market_id):
    # Example: get all active orders from your account (no filter)
    open_orders = client.get_orders(OpenOrderParams())
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

    

