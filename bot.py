import subprocess
import pandas as pd
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import os
import dotenv
dotenv.load_dotenv()


TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")  # Replace this

# --- /add command ---
async def add_market(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /add <question> <side>")
        return
    
    question = context.args[0]
    side = context.args[1]
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
    
    question = context.args[0]
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
        df = pd.read_csv("markets.csv")
        if df.empty:
            await update.message.reply_text("No markets found.")
        else:
            msg = df.to_string(index=False)
            await update.message.reply_text(f"📊 Current Markets:\n\n{msg[:4000]}")
    except Exception as e:
        await update.message.reply_text(f"❌ Error reading markets.csv: {e}")

# --- main ---
async def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("add", add_market))
    app.add_handler(CommandHandler("remove", remove_market))
    app.add_handler(CommandHandler("markets", get_markets))

    print("🤖 Bot is running...")
    await app.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
