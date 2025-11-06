from dotenv import load_dotenv
import requests
import os
import html

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

MAX_MESSAGE_LENGTH = 4096  # Telegram's hard limit

def send_telegram_message(text):

    text = html.escape(text)
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    chat_id = TELEGRAM_CHAT_ID

    # Split into chunks
    chunks = [text[i:i + MAX_MESSAGE_LENGTH] for i in range(0, len(text), MAX_MESSAGE_LENGTH)]

    for chunk in chunks:
        if "_" in chat_id:
            ids = chat_id.split("_")
            payload = {
                "chat_id": ids[0],
                "message_thread_id": ids[1],
                "text": chunk,
                "parse_mode": "HTML",
                "disable_web_page_preview": True
            }
        else:
            payload = {
                "chat_id": chat_id,
                "text": chunk,
                "parse_mode": "HTML",
                "disable_web_page_preview": True
            }

        response = requests.post(url, json=payload)

        if response.status_code != 200:
            print(f"⚠️ Failed to send chunk ({response.status_code}): {response.text}")
        else:
            print("✅ Chunk sent successfully")
