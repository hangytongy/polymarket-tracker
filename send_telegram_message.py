from dotenv import load_dotenv
import requests
import os

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

    chat_id = TELEGRAM_CHAT_ID

    if "_" in chat_id:
        ids = chat_id.split("_")
        payload = {
            "chat_id": ids[0],
            "message_thread_id" : ids[1],
            "text" : text,
            "parse_mode" : "Markdown"
        }
    
    else:
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown"
        }

    requests.post(url, json=payload)
    print("Message sent")