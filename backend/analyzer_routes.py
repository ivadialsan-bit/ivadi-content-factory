from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import os
import json
import sqlite3
import anthropic
from dotenv import load_dotenv
from youtube_extractor import extract_youtube_data

load_dotenv("/root/factory/backend/.env")

router = APIRouter(prefix="/api/analyzer", tags=["analyzer"])

DB_PATH = "/root/factory/backend/factory.db"
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")
CLAUDE_PROXY_URL = "https://anthropic-proxy.ivadialsan.workers.dev"
MODEL = "claude-haiku-4-5-20251001"


class AnalyzeRequest(BaseModel):
    url: str
    niche: Optional[str] = ""


def init_analyzer_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS content_analyses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT NOT NULL,
            niche TEXT,
            niche_label TEXT,
            viral_score INTEGER,
            hook_type TEXT,
            content_format TEXT,
            structure TEXT,
            triggers TEXT,
            why_works TEXT,
            summary TEXT,
            raw_json TEXT,
            created_at TEXT
        )
    """)
    conn.commit()
    conn.close()


def extract_text(msg):
    parts = []
    for block in msg.content:
        if getattr(block, "type", None) == "text":
            parts.append(block.text)
    return "\n".join(parts).strip()


def clean_json(text: str):
    text = text.strip()
    if text.startswith("```"):
        text = text.replace("```json", "").replace("```", "").strip()
    return text


@router.post("/analyze")
def analyze_content(req: AnalyzeRequest):
    if not CLAUDE_API_KEY:
        return {"success": False, "error": "CLAUDE_API_KEY not found in backend/.env"}

    url = req.url.strip()
    niche = (req.niche or "").strip()

    if not url:
        return {"success": False, "error": "URL is required"}

    init_analyzer_db()

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    existing = cur.execute("""
        SELECT id, raw_json, created_at
        FROM content_analyses
        WHERE url = ?
        ORDER BY id DESC
        LIMIT 1
    """, (url,)).fetchone()
    conn.close()

    if existing:
        try:
            cached = json.loads(existing["raw_json"] or "{}")
        except Exception:
            cached = {}

        cached["_cached"] = True
        cached["_cached_id"] = existing["id"]
        cached["_cached_created_at"] = existing["created_at"]

        return {
            "success": True,
            "cached": True,
            "id": existing["id"],
            "analysis": cached
        }

    client = anthropic.Anthropic(
        api_key=CLAUDE_API_KEY,
        base_url=CLAUDE_PROXY_URL
    )

    extracted = {
        "platform": "unknown",
        "video_id": None,
        "metadata": {},
        "transcript": None,
        "has_transcript": False,
        "confidence": "low",
        "errors": []
    }

    if "youtube.com" in url or "youtu.be" in url:
        extracted = extract_youtube_data(url)

    extracted_for_prompt = json.dumps(extracted, ensure_ascii=False, indent=2)[:12000]

    prompt = f"""
Ты — профессиональный SMM-стратег и аналитик короткого контента.

Задача: проанализировать контент по ссылке.
Важно: если ты не можешь открыть ссылку напрямую, не выдумывай детали видео. Анализируй саму ссылку, платформу, вероятный формат и давай практический SMM-разбор как рабочую гипотезу.

Ссылка: {url}
Ниша от пользователя: {niche if niche else "автоопределение"}

ИЗВЛЕЧЁННЫЕ ДАННЫЕ ПО ССЫЛКЕ:
{extracted_for_prompt}

Правила точности:
- Если confidence = high, анализируй по транскрипту и метаданным.
- Если confidence = medium, анализируй по title/description/channel/duration и честно укажи ограничение.
- Если confidence = low, не делай вид, что видел видео. Дай только осторожную гипотезу.
- В summary обязательно напиши, на основе чего сделан анализ: транскрипт / метаданные / только ссылка.

Верни строго JSON без markdown.

Схема:
{{
  "viral_score": 7,
  "hook_type": "тип хука коротко",
  "content_format": "короткое видео / пост / карусель / аккаунт / неизвестно",
  "niche": "travel/business/education/entertainment/tech/finance/beauty/other",
  "niche_label": "Название ниши на русском",
  "structure": [
    "1. ...",
    "2. ...",
    "3. ...",
    "4. ..."
  ],
  "triggers": [
    "...",
    "...",
    "..."
  ],
  "why_works": [
    "...",
    "...",
    "..."
  ],
  "summary": "Краткое содержание/гипотеза анализа в 4-6 предложениях.",
  "video_scenario": [
    "0-3 сек: что происходит в начале видео / реконструкция по данным",
    "3-10 сек: развитие сцены",
    "10-25 сек: основная часть",
    "25-45 сек: усиление или поворот",
    "45-60 сек: финал / вывод / CTA"
  ],
  "adaptation": [
    "Как использовать эту механику для клиента",
    "Какой похожий контент сделать",
    "Какой CTA поставить"
  ]
}}

Правила:
- Не используй воду.
- Пиши прикладно.
- Не обещай точность, если данных по ссылке недостаточно.
- Оцени виральность от 1 до 10.
- Ответ только валидный JSON.
"""

    try:
        msg = client.messages.create(
            model=MODEL,
            max_tokens=2500,
            temperature=0.3,
            messages=[{"role": "user", "content": prompt}]
        )

        text = clean_json(extract_text(msg))
        data = json.loads(text)

        data["source_confidence"] = extracted.get("confidence", "low")

        if extracted.get("has_transcript"):
            data["source_basis"] = "Транскрипт YouTube + метаданные: title, channel, duration, views, likes."
        elif extracted.get("metadata", {}).get("title"):
            data["source_basis"] = "Метаданные YouTube: title, channel, duration, views, likes. Транскрипт недоступен."
        else:
            data["source_basis"] = "Только ссылка. Метаданные и транскрипт недоступны."

        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO content_analyses
            (url, niche, niche_label, viral_score, hook_type, content_format, structure, triggers, why_works, summary, raw_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            url,
            data.get("niche", niche or "other"),
            data.get("niche_label", "Другое"),
            int(data.get("viral_score", 0)),
            data.get("hook_type", ""),
            data.get("content_format", ""),
            json.dumps(data.get("structure", []), ensure_ascii=False),
            json.dumps(data.get("triggers", []), ensure_ascii=False),
            json.dumps(data.get("why_works", []), ensure_ascii=False),
            data.get("summary", ""),
            json.dumps(data, ensure_ascii=False),
            datetime.now().isoformat(timespec="seconds")
        ))
        analysis_id = cur.lastrowid
        conn.commit()
        conn.close()

        return {
            "success": True,
            "id": analysis_id,
            "analysis": data
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


ASSETS_FILE = "/root/factory/content_assets.json"


def load_content_assets():
    if os.path.exists(ASSETS_FILE):
        with open(ASSETS_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except Exception:
                return []
    return []


def save_content_assets(items):
    with open(ASSETS_FILE, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)


@router.get("/history")
def get_history(limit: int = 30):
    init_analyzer_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    rows = cur.execute("""
        SELECT id, url, niche, niche_label, viral_score, hook_type, content_format, created_at
        FROM content_analyses
        ORDER BY id DESC
        LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return {"success": True, "items": [dict(r) for r in rows]}




@router.get("/item/{analysis_id}")
def get_analysis_item(analysis_id: int):
    init_analyzer_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    row = cur.execute("""
        SELECT *
        FROM content_analyses
        WHERE id = ?
        LIMIT 1
    """, (analysis_id,)).fetchone()

    conn.close()

    if not row:
        return {"success": False, "error": "analysis not found"}

    item = dict(row)

    try:
        item["raw"] = json.loads(item.get("raw_json") or "{}")
    except Exception:
        item["raw"] = {}

    return {"success": True, "item": item}


@router.get("/niches/{niche}")
def get_niche_items(niche: str, limit: int = 30):
    init_analyzer_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    rows = cur.execute("""
        SELECT id, url, niche, niche_label, viral_score, hook_type, content_format, created_at
        FROM content_analyses
        WHERE niche = ?
        ORDER BY id DESC
        LIMIT ?
    """, (niche, limit)).fetchall()

    conn.close()
    return {"success": True, "niche": niche, "items": [dict(r) for r in rows]}


@router.get("/niches")
def get_niches():
    init_analyzer_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    rows = cur.execute("""
        SELECT
            niche,
            COUNT(*) as count,
            ROUND(AVG(viral_score), 1) as avg_viral,
            MAX(created_at) as last_added
        FROM content_analyses
        GROUP BY niche
        ORDER BY count DESC
    """).fetchall()

    labels = {
        "travel": "Туризм",
        "business": "Бизнес",
        "education": "Образование",
        "entertainment": "Развлечения",
        "tech": "Технологии",
        "finance": "Финансы",
        "beauty": "Красота",
        "other": "Другое"
    }

    items = []
    for r in rows:
        d = dict(r)
        d["niche_label"] = labels.get(d.get("niche"), d.get("niche") or "Другое")
        items.append(d)

    conn.close()
    return {"success": True, "items": items}


@router.post("/item/{analysis_id}/scenario")
def generate_scenario_from_analysis(analysis_id: int):
    if not CLAUDE_API_KEY:
        return {"success": False, "error": "CLAUDE_API_KEY not found in backend/.env"}

    init_analyzer_db()

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    row = cur.execute("""
        SELECT *
        FROM content_analyses
        WHERE id = ?
        LIMIT 1
    """, (analysis_id,)).fetchone()

    conn.close()

    if not row:
        return {"success": False, "error": "analysis not found"}

    item = dict(row)

    try:
        raw = json.loads(item.get("raw_json") or "{}")
    except Exception:
        raw = {}

    client = anthropic.Anthropic(
        api_key=CLAUDE_API_KEY,
        base_url=CLAUDE_PROXY_URL
    )

    prompt = f"""
Ты — сценарист коротких вертикальных видео.

На основе анализа контента создай НОВЫЙ сценарий.
Не копируй исходный ролик. Используй только механику, структуру, триггеры и формат.

АНАЛИЗ:
{json.dumps(raw, ensure_ascii=False, indent=2)[:12000]}

Верни строго JSON без markdown.

Схема:
{{
  "title": "короткое название",
  "hook": "сильный хук для первых 2 секунд",
  "script": [
    "0-3 сек: ...",
    "3-7 сек: ...",
    "7-12 сек: ...",
    "12-20 сек: ...",
    "20-30 сек: ..."
  ],
  "voiceover": "готовый текст озвучки",
  "visual_style": "стиль визуала",
  "cta": "призыв к действию"
}}
"""

    try:
        msg = client.messages.create(
            model=MODEL,
            max_tokens=2000,
            temperature=0.5,
            messages=[{"role": "user", "content": prompt}]
        )

        text = clean_json(extract_text(msg))
        data = json.loads(text)

        return {
            "success": True,
            "analysis_id": analysis_id,
            "scenario": data
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/assets")
def save_content_asset(asset: dict):
    items = load_content_assets()

    next_id = max([x.get("id", 0) for x in items], default=0) + 1

    item = {
        "id": next_id,
        "source_analysis_id": asset.get("source_analysis_id"),
        "title": asset.get("title", ""),
        "hook": asset.get("hook", ""),
        "script": asset.get("script", []),
        "voiceover": asset.get("voiceover", ""),
        "visual_style": asset.get("visual_style", ""),
        "cta": asset.get("cta", ""),
        "status": "new",
        "created_at": datetime.now().isoformat(timespec="seconds")
    }

    items.append(item)
    save_content_assets(items)

    return {"success": True, "asset": item}


@router.get("/assets")
def get_content_assets():
    return {"success": True, "items": load_content_assets()[-100:]}
