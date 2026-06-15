import asyncio
import sqlite3
import json
import os
import anthropic
from datetime import datetime, timedelta
from telethon import TelegramClient
from telethon.tl.types import Message
from dotenv import load_dotenv

load_dotenv('/root/factory/backend/.env')

API_ID = int(os.getenv('TG_API_ID', '2040'))
API_HASH = os.getenv('TG_API_HASH', '')
PHONE = os.getenv('TG_PHONE', '')
CLAUDE_API_KEY = os.getenv('CLAUDE_API_KEY', '')
CLAUDE_PROXY_URL = os.getenv('CLAUDE_PROXY_URL', '')
DB_PATH = '/root/factory/backend/factory.db'
SESSION_PATH = '/root/factory/tg_session'

client = TelegramClient(SESSION_PATH, API_ID, API_HASH)

def get_db():
    return sqlite3.connect(DB_PATH)

def get_user_profile():
    db = get_db()
    cur = db.execute("SELECT skills, niches, rates, cases, about FROM user_profile LIMIT 1")
    row = cur.fetchone()
    db.close()
    if not row:
        return {}
    return {
        "skills": row[0] or "",
        "niches": row[1] or "",
        "rates": row[2] or "",
        "cases": row[3] or "",
        "about": row[4] or ""
    }

def get_active_channels():
    db = get_db()
    cur = db.execute("SELECT username FROM tg_channels WHERE is_active=1")
    rows = cur.fetchall()
    db.close()
    return [r[0] for r in rows]

def is_duplicate(tg_message_id, channel):
    db = get_db()
    cur = db.execute(
        "SELECT id FROM opportunities WHERE tg_message_id=? AND channel=?",
        (tg_message_id, channel)
    )
    exists = cur.fetchone() is not None
    db.close()
    return exists

def save_opportunity(tg_message_id, channel, text, score, reason, category, posted_at):
    db = get_db()
    db.execute(
        """INSERT INTO opportunities (tg_message_id, channel, text, score, score_reason, category, status, posted_at, created_at)
           VALUES (?, ?, ?, ?, ?, ?, 'new', ?, ?)""",
        (tg_message_id, channel, text, score, reason, category, posted_at, datetime.utcnow())
    )
    db.commit()
    db.close()

def update_channel_checked(username):
    db = get_db()
    db.execute(
        "UPDATE tg_channels SET last_checked_at=? WHERE username=?",
        (datetime.utcnow(), username)
    )
    db.commit()
    db.close()

def score_with_claude(text, profile):
    try:
        claude = anthropic.Anthropic(
            api_key=CLAUDE_API_KEY,
            base_url=CLAUDE_PROXY_URL
        )
        prompt = f"""Ты — AI-ассистент, который оценивает вакансии и проекты для SMM-специалиста.

ПРОФИЛЬ СПЕЦИАЛИСТА:
О себе: {profile.get('about', '')}
Навыки: {profile.get('skills', '')}
Ниши: {profile.get('niches', '')}
Ставки: {profile.get('rates', '')}
Кейсы: {profile.get('cases', '')}

ПОСТ ИЗ TELEGRAM:
{text}

Оцени этот пост по шкале 0-100:
- 0-20: не вакансия / не релевантно
- 21-50: слабое совпадение
- 51-75: хорошее совпадение
- 76-100: отличное совпадение

Определи категорию: вакансия / проект / подряд / партнёрство / нерелевантно

Ответь строго в JSON:
{{"score": 75, "reason": "краткое объяснение", "category": "вакансия"}}"""

        response = claude.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}]
        )
        raw = response.content[0].text.strip()
        raw = raw.replace('```json', '').replace('```', '').strip()
        data = json.loads(raw)
        return data.get('score', 0), data.get('reason', ''), data.get('category', '')
    except Exception as e:
        print(f"Claude error: {e}")
        return 0, '', ''

async def parse_channel(username):
    try:
        entity = await client.get_entity(username)
        since = datetime.utcnow() - timedelta(hours=2)
        messages = await client.get_messages(entity, limit=50)
        new_count = 0
        for msg in messages:
            if not isinstance(msg, Message):
                continue
            if not msg.text or len(msg.text) < 50:
                continue
            if msg.date.replace(tzinfo=None) < since:
                continue
            if is_duplicate(msg.id, username):
                continue
            score, reason, category = score_with_claude(msg.text, get_user_profile())
            if score >= 30:
                save_opportunity(msg.id, username, msg.text, score, reason, category, msg.date.replace(tzinfo=None))
                new_count += 1
                print(f"[{username}] score={score} category={category}")
        update_channel_checked(username)
        print(f"[{username}] done, saved {new_count} new")
    except Exception as e:
        print(f"[{username}] error: {e}")

async def run():
    await client.start(phone=PHONE)
    channels = get_active_channels()
    if not channels:
        print("No active channels in DB")
        return
    for ch in channels:
        await parse_channel(ch)

if __name__ == '__main__':
    asyncio.run(run())
