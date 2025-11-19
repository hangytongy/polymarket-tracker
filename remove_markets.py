
import pandas as pd
import json
from orders import *
from utils import *
from send_telegram_message import send_telegram_message
import sys
import dotenv

dotenv.load_dotenv()

MARKETS_DIR = os.getenv('MARKETS_DIR')

try:
    remove_question = " ".join(sys.argv[1:])
    print(remove_question)
    if not remove_question:
        print("no question")
        remove_question = input("Input the polymarket full question u want to remove : ")

except:
    remove_question = input("Input the polymarket full question u want to remove : ")


# === STEP 1: Load CSV ===
file_path = MARKETS_DIR   # Change to your actual CSV file path

df = pd.read_csv(file_path, usecols=['question','market_id', 'side'], dtype={'question' : str,'market_id': str, 'side': str})

for _, row in df.iterrows():
    market_id = str(row['market_id'])
    side = str(row['side'])
    print(f"-----{market_id}----")

    if remove_question.lower() == row['question'].lower():

        token_ids = get_token_id(market_id)

        if token_ids:
            for token_id in token_ids:

                filtered_orders = get_current_orders(token_id)

                if filtered_orders:
                    for order in filtered_orders:
                        if order['side'] =="BUY":
                            order_id = order['id']
                            cancel_order(order_id)

            df = df[df['market_id'] != market_id]
            df.to_csv(file_path, index=False)
            print(f"✅ Removed {row['question'].lower()} from {file_path}")
            message = f"✅ Removed {row['question'].lower()} from {file_path}"
            send_telegram_message(message)

        else:
            print("unable to find market to remove")
            message = "unable to find market to remove"
            send_telegram_message(message)        







