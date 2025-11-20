import subprocess
import pandas as pd
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import os
import dotenv
dotenv.load_dotenv()
import csv

from bot_commands import *


TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")  # Replace this

# --- /add command ---
async def add_market(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /add <question> <side>")
        return
    
    question = " ".join(context.args[:-1])
    side = context.args[-1]
    try:
        result = subprocess.run(
            ["python3", "add_markets.py", question, side],
            capture_output=True,
            text=True
        )
        await update.message.reply_text(f"✅ Market added:\n{result.stdout or result.stderr}")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

# --- /remove command ---
async def remove_market(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 1:
        await update.message.reply_text("Usage: /remove <question>")
        return
    
    question = " ".join(context.args[:])
    try:
        result = subprocess.run(
            ["python3", "remove_markets.py", question],
            capture_output=True,
            text=True
        )
        await update.message.reply_text(f"🗑️ Market removed:\n{result.stdout or result.stderr}")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

# --- /markets command ---
async def get_markets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        MARKETS_DIR = os.getenv('MARKETS_DIR')
        df = pd.read_csv(MARKETS_DIR)
        if df.empty:
            await update.message.reply_text("No markets found.")
        else:
            msg = df.to_string(index=False)
            await update.message.reply_text(f"📊 Current Markets:\n\n{msg[:4000]}")
    except Exception as e:
        await update.message.reply_text(f"❌ Error reading markets.csv: {e}")

# --- /orders command ---
async def get_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        orders = bot_get_all_orders_info()
        if not orders:
            await update.message.reply_text("unable to get orders.")
        else:
            msg = orders
            #await update.message.reply_text(f"📊 Current Orders:\n\n{msg[:4000]}")
            await send_long_message(update.message.chat, msg)
    except Exception as e:
        await update.message.reply_text(f"❌ Error getting orders: {e}")

async def send_long_message(chat, text, chunk_size=4000):
    for i in range(0, len(text), chunk_size):
        await chat.send_message(text[i:i+chunk_size])

# --- /markets command ---
async def get_positions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        positions = bot_get_positions()
        if not positions:
            await update.message.reply_text("No positons found.")
        else:
            msg = positions
            await send_long_message(update.message.chat, msg)
    except Exception as e:
        await update.message.reply_text(f"❌ Error getting positions: {e}")

# --- /rewards command ---
async def get_rewards(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        rewards = bot_get_reward_details()
        if not rewards:
            await update.message.reply_text("unable to get orders.")
        else:
            msg = str(rewards)
            #await update.message.reply_text(f"📊 Current Orders:\n\n{msg[:4000]}")
            await send_long_message(update.message.chat, msg)
    except Exception as e:
        await update.message.reply_text(f"❌ Error getting orders: {e}")

# --- /manual command ---
async def get_manual(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 1:
        await update.message.reply_text("Usage: /manual <question>")
        return

    question = " ".join(context.args[:])
    try:
        MANUALSELL_DIR = os.getenv("MANUALSELL_DIR")
        with open(MANUALSELL_DIR, "a", newline='', encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([question])
        await update.message.reply_text(f"🗑️ Manual market added:\n{question}")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

# --- /info command ---
async def get_market_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 1:
        await update.message.reply_text("Usage: /info <market_id>")
        return

    market_id = " ".join(context.args[:])
    try:
        msg = bot_get_market_info(market_id)
        await send_long_message(update.message.chat, msg)
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

# --- /placeorder command ---
async def place_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 5:
        await update.message.reply_text("Usage: /placeorder <market_id> <outcome> <side> <price> <size>")
        return
    
    market_id = context.args[0]
    outcome = context.args[1]
    side = context.args[2]
    price = float(context.args[3])
    size = float(context.args[4])
    try:
        result = bot_order(market_id, outcome, side, price, size)
        await update.message.reply_text(f"✅ Order placed:\n{result}")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

async def send_long_message(chat, text, chunk_size=4000):
    for i in range(0, len(text), chunk_size):
        await chat.send_message(text[i:i+chunk_size])
        
# --- main ---
async def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("add", add_market))
    app.add_handler(CommandHandler("remove", remove_market))
    app.add_handler(CommandHandler("markets", get_markets))
    app.add_handler(CommandHandler("orders", get_orders))
    app.add_handler(CommandHandler("rewards", get_rewards))
    app.add_handler(CommandHandler("manual", get_manual))
    app.add_handler(CommandHandler("positions", get_positions))
    app.add_handler(CommandHandler("info", get_market_info))
    app.add_handler(CommandHandler("placeorder",place_order))

    print("🤖 Bot is running...")
    await app.run_polling()

if __name__ == "__main__":
    import asyncio
    import nest_asyncio
    nest_asyncio.apply()
    asyncio.run(main())
