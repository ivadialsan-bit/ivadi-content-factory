import anthropic
import os
import json
import random
import requests
from datetime import datetime
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv('/root/factory/.ivadi.env')

from config import CLAUDE_API_KEY
from ivadi_content_prompts import (
    CHANNEL_VOICE, CONTENT_TYPES, DAILY_SCHEDULE,
    DIRECTIONS_FACTS, NEWS_SOURCES, AFFILIATE_LINKS
)

client = anthropic.Anthropic(
    api_key=CLAUDE_API_KEY,
    base_url="https://anthropic-proxy.ivadialsan.workers.dev"
)

MEMORY_FILE = "/root/factory/ivadi_topics_memory.json"


def load_memory():
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except:
                return []
    return []


def save_memory(topic):
    memory = load_memory()
    memory.append({"topic": topic, "date": datetime.now().isoformat()})
    memory = memory[-50:]
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(memory, f, ensure_ascii=False, indent=2)


def get_fresh_topic(post_type):
    memory = load_memory()
    used = {m["topic"] for m in memory}
    available = CONTENT_TYPES[post_type]["topics"]
    fresh = [t for t in available if t not in used]
    if not fresh:
        fresh = available
    return random.choice(fresh)


def get_affiliate_block(post_type, topic):
    topic_lower = (topic or "").lower()
    blocks = []
    for key, aff in AFFILIATE_LINKS.items():
        if not aff["url"]:
            continue
        if post_type not in aff["use_in"]:
            continue
        if any(w in topic_lower for w in aff["mention_when"]):
            line = "\n-> " + aff["name"] + ": " + aff["description"]
            line += "\n   " + aff["honest_note"]
            line += "\n   " + aff["url"]
            blocks.append(line)
    return "\n".join(blocks) if blocks else ""


def fetch_news():
    headers = {"User-Agent": "Mozilla/5.0"}
    news_items = []
    for url in NEWS_SOURCES[:2]:
        try:
            r = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(r.text, "html.parser")
            for tag in ["h2", "h3", "h1"]:
                for item in soup.find_all(tag)[:5]:
                    text = item.get_text(strip=True)
                    if 20 < len(text) < 200:
                        news_items.append(text)
            if news_items:
                break
        except Exception as e:
            print("[Parser] " + str(e))
    return "\n".join(news_items[:5]) if news_items else ""


def get_post_type_for_today():
    day = datetime.now().strftime("%A").lower()
    today_slots = [s for s in DAILY_SCHEDULE if day in s["days"]]
    config = today_slots[0] if today_slots else DAILY_SCHEDULE[0]
    post_type = config["type"]
    topic = get_fresh_topic(post_type)
    return post_type, CONTENT_TYPES[post_type]["description"], topic


def generate_post(post_type=None, topic=None, direction=None, news_context=None):
    if not post_type:
        post_type, _, topic = get_post_type_for_today()
    if not topic:
        topic = get_fresh_topic(post_type)

    type_config = CONTENT_TYPES.get(post_type, CONTENT_TYPES["honest"])

    direction_context = ""
    if direction and direction in DIRECTIONS_FACTS:
        d = DIRECTIONS_FACTS[direction]
        direction_context = (
            "\nИспользуй факты о направлении (" + d["name"] + "):\n"
            "- Цена: " + d["price_from"] + "\n"
            "- Перелёт: " + d["flight"] + "\n"
            "- Виза: " + d["visa"] + "\n"
            "- Сезон: " + d["best_time"] + "\n"
            "- Курорты: " + d["resorts"] + "\n"
            "- Честно: " + d["honest"] + "\n"
            "- Жемчужины: " + d.get("hidden_gems", "") + "\n"
            "- Избегать: " + d.get("avoid", "") + "\n"
        )

    news_block = ""
    if news_context:
        news_block = "\nАктуальные новости (используй если уместно):\n" + news_context

    prompt = (
        CHANNEL_VOICE + "\n\n"
        "Напиши пост для MAX-канала IvadiTravel.\n\n"
        "Тема: " + topic + "\n"
        "Тип: " + type_config["description"] + "\n"
        "Формат: " + type_config["format"] + "\n"
        + direction_context + news_block + "\n\n"
        "Дата: " + datetime.now().strftime("%d %B %Y") + "\n\n"
        "Верни ТОЛЬКО текст поста без пояснений."
    )

    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}]
    )

    text = response.content[0].text.strip()
    aff = get_affiliate_block(post_type, topic)
    if aff:
        text = text + "\n" + aff
    save_memory(topic)
    return text


if __name__ == "__main__":
    print("Генерирую тестовый пост...\n")
    post_type, desc, topic = get_post_type_for_today()
    direction = random.choice(list(DIRECTIONS_FACTS.keys()))
    print("Тип: " + post_type + " | Тема: " + topic + "\n")
    print("=" * 50)
    text = generate_post(post_type, topic, direction)
    print(text)
    print("=" * 50)
    print("Длина: " + str(len(text)) + " символов")
