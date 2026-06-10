import random
import sys
from ivadi_post_generator import generate_post, get_fresh_topic
from ivadi_content_prompts import CONTENT_TYPES, DAILY_SCHEDULE, DIRECTIONS_FACTS
from ivadi_queue import add_to_queue, show_queue

def generate_day_queue(day: str = None):
    """Генерирует посты на один день и добавляет в очередь"""
    if not day:
        from datetime import datetime
        day = datetime.now().strftime("%A").lower()

    slots = [s for s in DAILY_SCHEDULE if day in s["days"]]
    print(f"\n🗓 Генерирую посты для {day} ({len(slots)} постов)...\n")

    for slot in sorted(slots, key=lambda x: x["time"]):
        post_type = slot["type"]
        time = slot["time"]
        topic = get_fresh_topic(post_type)

        direction = None
        if post_type in ["honest", "offer", "comparison"]:
            direction = random.choice(list(DIRECTIONS_FACTS.keys()))

        print(f"Генерирую {post_type} [{time}]: {topic[:40]}...")
        text = generate_post(post_type, topic, direction)
        add_to_queue(post_type, topic, text, scheduled_time=time)

    print("\nГотово. Проверь очередь:")
    show_queue()


def generate_week_queue():
    """Генерирует посты на всю неделю"""
    days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    for day in days:
        generate_day_queue(day)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        generate_day_queue(sys.argv[1])
    else:
        generate_day_queue()
