
import pandas as pd
remove_question = input("Input the polymarket full question u want to remove : ")
from orders import *


# === STEP 1: Load CSV ===
file_path = "markets.csv"   # Change to your actual CSV file path

df = pd.read_csv(file_path, usecols=['question','market_id', 'side'], dtype={'question' : str,'market_id': str, 'side': str})

for _, row in df.iterrows():
    market_id = str(row['market_id'])
    side = str(row['side'])
    print(f"-----{market_id}----")

    if remove_question.lower() == row['question'].lower():

        filtered_orders = get_current_orders(market_id)

        if filtered_orders:
            all_order_ids = get_all_orders_id(filtered_orders)
            cancel_all_orders(all_order_ids)

            df = df[df['market_id'] != market_id]
            df.to_csv(file_path, index=False)
            print(f"✅ Removed market_id {market_id} from {file_path}")







