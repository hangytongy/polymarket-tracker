
import pandas as pd
remove_question = input("Input the polymarket full question u want to remove : ")
from orders import *
from utils import *
from send_telegram_message import send_telegram_message

def get_token_id(market_id):
    url = f"https://gamma-api.polymarket.com/markets/{market_id}"

    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
        token_ids = data['clobTokenIds']

        return token_ids
    
    else:
        return None


# === STEP 1: Load CSV ===
file_path = "markets.csv"   # Change to your actual CSV file path

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
                    all_order_ids = get_all_orders_id(filtered_orders)
                    cancel_all_orders(all_order_ids)

            df = df[df['market_id'] != market_id]
            df.to_csv(file_path, index=False)
            print(f"✅ Removed {row['question'].lower()} from {file_path}")
            message = f"✅ Removed {row['question'].lower()} from {file_path}"
            send_telegram_message(message)

        else:
            print("unable to find market to remove")
            message = "unable to find market to remove"
            send_telegram_message(message)        







