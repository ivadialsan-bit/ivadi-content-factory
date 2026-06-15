import requests
import sqlite3
import json
import os
import re
import anthropic
import xml.etree.ElementTree as ET
from datetime import datetime
from dotenv import load_dotenv

load_dotenv('/root/factory/backend/.env')

CLAUDE_API_KEY = os.getenv('CLAUDE_API_KEY', '')
CLAUDE_PROXY_URL = os.getenv('CLAUDE_PROXY_URL', '')
DB_PATH = '/root/factory/backend/factory.db'

RSS_CHANNELS = [
    "vacancysmm",
    "smm_pro",
    "freelance_ru",
    "content_job",
    "smm_russia",
]

def get_db():
    return sqlite3.connect(DB_PATH)

def is_duplicate(guid, channel):
    db = get_db()
    cur = db.execute(
        "SELECT id FROM opportunities WHERE tg_message_id=? AND channel=?",
        (str(guid), channel)
    )
    exists = cur.fetchone() is not None
    db.close()
    return exists

def save_opportunity(guid, channel, text, score, reason, category):
    db = get_db()
    db.execute(
        """INSERT INTO opportunities (tg_message_id, channel, text, score, score_reason, category, status, posted_at, created_at)
           VALUES (?, ?, ?, ?, ?, ?, 'new', ?, ?)""",
        (str(guid), channel, text, score, reason, category, datetime.utcnow(), datetime.utcnow())
    )
    db.commit()
    db.close()

def clean_html(text):
    return re.sub(r'<[^>]+>', ' ', text).strip()

def score_with_claude(text):
    try:
        claude = anthropic.Anthropic(
            api_key=CLAUDE_API_KEY,
            base_url=CLAUDE_PROXY_URL
        )
        prompt = f"""Ты оцениваешь посты из Telegram для AI контент-системы IVADI Factory.

Система умеет:
- Анализ вирусного контента YouTube/Instagram/VK/Telegram
- Генерация контент-стратегии для клиента
- Генерация сценариев, постов, image prompts
- Генерация изображений через Leonardo AI
- Публикация в MAX, VK, Telegram
- Client CRM: брифы, профили, AI-карта клиента
- Контент-план на месяц
- Аналитика роста аккаунтов
- Ведение соцсетей под ключ

ПОСТ:
{text[:1000]}

Оцени релевантность 0-100.
Категория: вакансия / проект / подряд / партнёрство / нерелевантно

JSON:
{{"score": 75, "reason": "объяснение", "category": "проект", "closes": ["контент-стратегия", "посты"], "manual": ["коммуникация с клиентом"]}}"""

        response = claude.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=400,
            messages=[{"role": "user", "content": prompt}]
        )
        raw = response.content[0].text.strip().replace('```json','').replace('```','').strip()
        data = json.loads(raw)
        return data.get('score',0), data.get('reason',''), data.get('category',''), data.get('closes',[]), data.get('manual',[])
    except Exception as e:
        print(f"Claude error: {e}")
        return 0, '', '', [], []

def notify_telegram(text, score, reason, category, closes, manual, channel, link):
    try:
        import sys; sys.path.insert(0, '/root/factory/backend'); from telegram_notify import send_message
        msg = f"🎯 <b>Новый заказ [{score}%]</b>\n\n"
        msg += f"📌 {clean_html(text)[:250]}\n\n"
        msg += f"📊 <b>Категория:</b> {category}\n"
        msg += f"💡 <b>Оценка:</b> {reason}\n\n"
        if closes:
            msg += "✅ <b>Система закрывает:</b>\n" + "\n".join(f"— {c}" for c in closes) + "\n\n"
        if manual:
            msg += "👤 <b>Нужны руки:</b>\n" + "\n".join(f"— {m}" for m in manual)
        buttons = []
        if link:
            buttons.append({"text": "🔗 Открыть пост", "url": link})
        buttons.append({"text": "🏭 Dashboard", "url": "http://147.45.97.143:8000/dashboard.html"})
        send_message(msg, buttons)
    except Exception as e:
        print(f"Telegram notify error: {e}")

def parse_channel(username):
    url = f"https://tg.i-c-a.su/rss/{username}?limit=20"
    try:
        r = requests.get(url, timeout=20)
        root = ET.fromstring(r.content)
        items = root.findall('.//item')
        print(f"[{username}] found {len(items)} items")
        for item in items:
            desc = item.findtext('description') or ''
            title = item.findtext('title') or ''
            link = item.findtext('link') or ''
            guid = item.findtext('guid') or link
            text = clean_html(f"{title}\n{desc}")
            if len(text) < 50:
                continue
            if is_duplicate(guid, username):
                print(f"[{username}] duplicate skip")
                continue
            score, reason, category, closes, manual = score_with_claude(text)
            print(f"[{username}] score={score} category={category}")
            if score >= 40:
                save_opportunity(guid, username, text, score, reason, category)
                notify_telegram(text, score, reason, category, closes, manual, username, link)
    except Exception as e:
        print(f"[{username}] error: {e}")

if __name__ == '__main__':
    print(f"RSS Hunter started at {datetime.utcnow()}")
    for ch in RSS_CHANNELS:
        parse_channel(ch)
        import time; time.sleep(5)
    print("Done")
