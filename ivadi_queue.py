import json
import os
from datetime import datetime

QUEUE_FILE = "/root/factory/ivadi_queue.json"


def load_queue() -> list:
    if os.path.exists(QUEUE_FILE):
        with open(QUEUE_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except:
                return []
    return []


def save_queue(queue: list):
    with open(QUEUE_FILE, "w", encoding="utf-8") as f:
        json.dump(queue, f, ensure_ascii=False, indent=2)


def add_to_queue(post_type: str, topic: str, text: str, scheduled_time: str = None):
    queue = load_queue()
    queue.append({
        "id": len(queue) + 1,
        "post_type": post_type,
        "topic": topic,
        "text": text,
        "scheduled_time": scheduled_time,
        "status": "pending",
        "created_at": datetime.now().isoformat()
    })
    save_queue(queue)
    print(f"✅ Добавлен в очередь #{queue[-1]['id']}: {topic[:50]}")


def get_pending() -> list:
    return [p for p in load_queue() if p["status"] == "pending"]


def get_next_pending():
    pending = get_pending()
    return pending[0] if pending else None


def mark_published(post_id: int):
    queue = load_queue()
    for post in queue:
        if post["id"] == post_id:
            post["status"] = "published"
            post["published_at"] = datetime.now().isoformat()
            break
    save_queue(queue)


def mark_rejected(post_id: int):
    queue = load_queue()
    for post in queue:
        if post["id"] == post_id:
            post["status"] = "rejected"
            break
    save_queue(queue)


def show_queue():
    queue = load_queue()
    pending = [p for p in queue if p["status"] == "pending"]
    published = [p for p in queue if p["status"] == "published"]

    print(f"\n📋 Очередь постов IvadiTravel")
    print(f"Ожидают: {len(pending)} | Опубликованы: {len(published)}\n")

    if not pending:
        print("Очередь пуста — запусти генерацию")
        return

    for p in pending:
        print(f"#{p['id']} [{p['post_type']}] {p['topic'][:50]}")
        print(f"   {p['text'][:100]}...")
        print()


if __name__ == "__main__":
    show_queue()
