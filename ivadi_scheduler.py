import schedule
import time
import requests
import os
import json
import random
from datetime import datetime
from dotenv import load_dotenv
from ivadi_post_generator import generate_post, fetch_news
from ivadi_content_prompts import DAILY_SCHEDULE, DIRECTIONS_FACTS
from ivadi_queue import get_next_pending, mark_published, load_queue

load_dotenv('/root/factory/.ivadi.env')

MAX_BOT_TOKEN = os.getenv("IVADI_MAX_BOT_TOKEN")
MAX_CHANNEL_ID = int(os.getenv("IVADI_MAX_CHANNEL_ID", "-75683421497408"))
LOG_FILE = "/root/factory/ivadi_posts_log.json"


def send_to_max_channel(text: str) -> bool:
    if not MAX_BOT_TOKEN:
        print("[MAX] Токен не задан")
        return False
    try:
        r = requests.post(
            "https://platform-api.max.ru/messages",
            headers={
                "Authorization": MAX_BOT_TOKEN,
                "Content-Type": "application/json"
            },
            params={"chat_id": MAX_CHANNEL_ID},
            json={"text": text},
            timeout=15
        )
        return r.status_code == 200
    except Exception as e:
        print(f"[MAX] Ошибка: {e}")
        return False


def log_post(post_type: str, topic: str, success: bool):
    log = []
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            try:
                log = json.load(f)
            except:
                log = []
    log.append({
        "datetime": datetime.now().isoformat(),
        "type": post_type,
        "topic": topic,
        "success": success
    })
    log = log[-200:]
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)


def publish(post_type: str = None):
    """Берёт следующий пост из очереди или генерирует новый"""
    now = datetime.now().strftime("%H:%M %d.%m")
    print(f"\n[{now}] Публикую...")

    # Сначала ищем в очереди по типу
    queue = load_queue()
    pending = [p for p in queue if p["status"] == "pending"]

    if post_type:
        typed = [p for p in pending if p["post_type"] == post_type]
        post = typed[0] if typed else None
    else:
        post = pending[0] if pending else None

    if post:
        text = post["text"]
        ok = send_to_max_channel(text)
        if ok:
            mark_published(post["id"])
            print(f"✅ #{post['id']} [{post['post_type']}] {post['topic'][:40]}")
        else:
            print(f"❌ Ошибка отправки #{post['id']}")
        log_post(post["post_type"], post["topic"], ok)
    else:
        # Очередь пуста — генерируем на лету
        print(f"[Queue] Пусто — генерирую {post_type or 'offer'} на лету...")
        direction = random.choice(list(DIRECTIONS_FACTS.keys()))
        pt = post_type or "offer"
        news_ctx = fetch_news() if pt == "news" else None
        text = generate_post(post_type=pt, direction=direction, news_context=news_ctx)
        ok = send_to_max_channel(text)
        print(f"{'✅' if ok else '❌'} {pt} опубликован на лету")
        log_post(pt, "", ok)


def setup_schedule():
    today = datetime.now().strftime("%A").lower()

    for slot in DAILY_SCHEDULE:
        post_type = slot["type"]
        post_time = slot["time"]
        days = slot["days"]

        for day in days:
            day_method = getattr(schedule.every(), day)
            day_method.at(post_time).do(publish, post_type=post_type)

    today_slots = [s for s in DAILY_SCHEDULE if today in s["days"]]
    print(f"\n📅 Сегодня ({today}) — {len(today_slots)} постов:")
    for s in sorted(today_slots, key=lambda x: x["time"]):
        print(f"  {s['time']} — {s['type']}")


if __name__ == "__main__":
    print("🚀 IvadiTravel контент-агент запущен")
    setup_schedule()

    while True:
        schedule.run_pending()
        time.sleep(60)
