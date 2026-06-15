import os
import requests

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
PROXY_URL = os.getenv("TELEGRAM_PROXY_URL", "https://telegram-proxy-render.onrender.com")

def send_message(text: str, buttons: list = None):
    url = f"{PROXY_URL}/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    }
    if buttons:
        payload["reply_markup"] = {
            "inline_keyboard": [[{"text": b["text"], "url": b["url"]}] for b in buttons]
        }
    try:
        r = requests.post(url, json=payload, timeout=15)
        return r.json()
    except Exception as e:
        print(f"Telegram notify error: {e}")
        return None

def notify_system(event: str, details: str = ""):
    text = f"🏭 <b>IVADI Factory</b>\n\n{event}"
    if details:
        text += f"\n\n{details}"
    return send_message(text)
