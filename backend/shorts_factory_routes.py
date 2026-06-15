from fastapi import APIRouter, UploadFile, File
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import os, json, time, base64, hashlib, hmac, sqlite3, subprocess, requests
import anthropic
from dotenv import load_dotenv

load_dotenv("/root/factory/backend/.env")

router = APIRouter(prefix="/api/shorts-factory", tags=["shorts_factory"])

DB_PATH = "/root/factory/backend/factory.db"
UPLOADS_DIR = "/root/factory/backend/static/uploads"
AUDIO_DIR = "/root/factory/backend/static/audio"
VIDEO_DIR = "/root/factory/backend/static/video"

CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")
CLAUDE_PROXY_URL = os.getenv("CLAUDE_PROXY_URL", "https://anthropic-proxy-render.onrender.com")
LEONARDO_API_KEY = os.getenv("LEONARDO_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
KLING_API_KEY = os.getenv("KLING_API_KEY", "")
KLING_API_SECRET = os.getenv("KLING_API_SECRET", "")
MODEL = "claude-haiku-4-5-20251001"

for d in [UPLOADS_DIR, AUDIO_DIR, VIDEO_DIR]:
    os.makedirs(d, exist_ok=True)


def init_shorts_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS shorts_channels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            niche TEXT,
            language TEXT DEFAULT 'ru',
            voice_id TEXT,
            voice_name TEXT,
            visual_style_json TEXT,
            style_image_url TEXT,
            status TEXT DEFAULT 'active',
            created_at TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS shorts_references (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_id INTEGER,
            url TEXT,
            platform TEXT DEFAULT 'youtube',
            formula_json TEXT,
            hook_type TEXT,
            pacing TEXT,
            emotion TEXT,
            structure_json TEXT,
            raw_analysis_json TEXT,
            created_at TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS shorts_scenarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_id INTEGER,
            reference_id INTEGER,
            title TEXT,
            hook TEXT,
            script_json TEXT,
            voiceover TEXT,
            visual_style TEXT,
            cta TEXT,
            status TEXT DEFAULT 'draft',
            created_at TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS shorts_productions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scenario_id INTEGER,
            channel_id INTEGER,
            audio_url TEXT,
            audio_path TEXT,
            voice_id TEXT,
            video_url TEXT,
            video_path TEXT,
            kling_task_id TEXT,
            final_url TEXT,
            final_path TEXT,
            status TEXT DEFAULT 'pending',
            error_log TEXT,
            created_at TEXT
        )
    """)
    conn.commit()
    conn.close()


def db_insert(table, data):
    init_shorts_db()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cols = ", ".join(data.keys())
    placeholders = ", ".join(["?"] * len(data))
    cur.execute(f"INSERT INTO {table} ({cols}) VALUES ({placeholders})", list(data.values()))
    row_id = cur.lastrowid
    conn.commit()
    conn.close()
    return row_id

def db_update(table, row_id, data):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    sets = ", ".join([f"{k}=?" for k in data.keys()])
    cur.execute(f"UPDATE {table} SET {sets} WHERE id=?", list(data.values()) + [row_id])
    conn.commit()
    conn.close()

def db_get(table, row_id):
    init_shorts_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    row = cur.execute(f"SELECT * FROM {table} WHERE id=? LIMIT 1", (row_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def db_list(table, where="", params=[], limit=50):
    init_shorts_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    q = f"SELECT * FROM {table}"
    if where:
        q += f" WHERE {where}"
    q += f" ORDER BY id DESC LIMIT {limit}"
    rows = cur.execute(q, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def claude_client():
    return anthropic.Anthropic(api_key=CLAUDE_API_KEY, base_url=CLAUDE_PROXY_URL)

def extract_text(msg):
    return "\n".join(b.text for b in msg.content if getattr(b, "type", None) == "text").strip()

def clean_json(text):
    text = text.strip()
    if text.startswith("```"):
        text = text.replace("```json", "").replace("```", "").strip()
    return text

def kling_token():
    now = int(time.time())
    header = base64.urlsafe_b64encode(json.dumps({"alg":"HS256","typ":"JWT"}).encode()).rstrip(b"=").decode()
    payload = base64.urlsafe_b64encode(json.dumps({"iss": KLING_API_KEY, "exp": now+1800, "nbf": now-5}).encode()).rstrip(b"=").decode()
    sig_input = f"{header}.{payload}".encode()
    sig = base64.urlsafe_b64encode(hmac.new(KLING_API_SECRET.encode(), sig_input, hashlib.sha256).digest()).rstrip(b"=").decode()
    return f"{header}.{payload}.{sig}"


class ChannelCreate(BaseModel):
    name: str
    niche: Optional[str] = ""
    language: Optional[str] = "ru"

@router.get("/channels")
def list_channels():
    return {"success": True, "items": db_list("shorts_channels")}

@router.post("/channels")
def create_channel(body: ChannelCreate):
    row_id = db_insert("shorts_channels", {
        "name": body.name,
        "niche": body.niche,
        "language": body.language,
        "status": "active",
        "created_at": datetime.now().isoformat(timespec="seconds")
    })
    return {"success": True, "id": row_id}

@router.get("/channels/{channel_id}")
def get_channel(channel_id: int):
    row = db_get("shorts_channels", channel_id)
    if not row:
        return {"success": False, "error": "not found"}
    return {"success": True, "channel": row}

class AnalyzeRefRequest(BaseModel):
    url: str
    channel_id: Optional[int] = None

@router.post("/analyze-reference")
def analyze_reference(req: AnalyzeRefRequest):
    if not CLAUDE_API_KEY:
        return {"success": False, "error": "CLAUDE_API_KEY not set"}
    extracted_info = ""
    try:
        import sys; sys.path.insert(0, "/root/factory/backend"); from youtube_extractor import extract_youtube_data
        data = extract_youtube_data(req.url)
        extracted_info = json.dumps(data, ensure_ascii=False)[:8000]
    except Exception:
        extracted_info = f"URL: {req.url}"
    prompt = f"""
Ты — эксперт по анализу коротких вертикальных видео.
Проанализируй это видео как профессиональный режиссёр и SMM-стратег.
URL: {req.url}
Данные: {extracted_info}
Извлеки ВОСПРОИЗВОДИМУЮ ФОРМУЛУ этого видео.
Верни строго JSON без markdown:
{{
  "title": "название для библиотеки",
  "platform": "youtube_shorts",
  "hook_type": "вопрос / шок / провокация / обещание / история / факт / демонстрация",
  "hook_text": "текст хука первых 2-3 секунд",
  "pacing": "быстрый / средний / медленный",
  "emotion": "любопытство / восхищение / страх / радость / злость / вдохновение",
  "structure": [
    {{"time": "0-3 сек", "action": "что происходит", "function": "зачем"}},
    {{"time": "3-8 сек", "action": "...", "function": "..."}},
    {{"time": "8-20 сек", "action": "...", "function": "..."}},
    {{"time": "20-40 сек", "action": "...", "function": "..."}},
    {{"time": "40-60 сек", "action": "...", "function": "..."}}
  ],
  "formula": {{
    "hook_pattern": "шаблон хука",
    "retention_mechanic": "как удерживает внимание",
    "twist": "есть ли поворот",
    "cta_type": "тип CTA",
    "repeat_template": "шаблон для повтора в другой нише"
  }},
  "virality_score": 7,
  "why_works": ["причина 1", "причина 2", "причина 3"],
  "niche_fit": ["ниша1", "ниша2"],
  "summary": "3-4 предложения почему работает"
}}"""
    try:
        cl = claude_client()
        msg = cl.messages.create(model=MODEL, max_tokens=2500, temperature=0.3,
            messages=[{"role": "user", "content": prompt}])
        data = json.loads(clean_json(extract_text(msg)))
        row_id = db_insert("shorts_references", {
            "channel_id": req.channel_id,
            "url": req.url,
            "platform": "youtube",
            "formula_json": json.dumps(data.get("formula", {}), ensure_ascii=False),
            "hook_type": data.get("hook_type", ""),
            "pacing": data.get("pacing", ""),
            "emotion": data.get("emotion", ""),
            "structure_json": json.dumps(data.get("structure", []), ensure_ascii=False),
            "raw_analysis_json": json.dumps(data, ensure_ascii=False),
            "created_at": datetime.now().isoformat(timespec="seconds")
        })
        return {"success": True, "id": row_id, "analysis": data}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/references")
def list_references(channel_id: Optional[int] = None):
    if channel_id:
        items = db_list("shorts_references", "channel_id=?", [channel_id])
    else:
        items = db_list("shorts_references")
    for item in items:
        for f in ["formula_json", "structure_json", "raw_analysis_json"]:
            try:
                item[f.replace("_json", "")] = json.loads(item.get(f) or "{}")
            except Exception:
                item[f.replace("_json", "")] = {}
    return {"success": True, "items": items}

@router.get("/references/{ref_id}")
def get_reference(ref_id: int):
    row = db_get("shorts_references", ref_id)
    if not row:
        return {"success": False, "error": "not found"}
    for f in ["formula_json", "structure_json", "raw_analysis_json"]:
        try:
            row[f.replace("_json", "")] = json.loads(row.get(f) or "{}")
        except Exception:
            row[f.replace("_json", "")] = {}
    return {"success": True, "reference": row}

@router.post("/channels/{channel_id}/upload-style-image")
async def upload_style_image(channel_id: int, file: UploadFile = File(...)):
    if not CLAUDE_API_KEY:
        return {"success": False, "error": "CLAUDE_API_KEY not set"}
    channel = db_get("shorts_channels", channel_id)
    if not channel:
        return {"success": False, "error": "channel not found"}
    ext = os.path.splitext(file.filename)[1] or ".jpg"
    fname = f"style_{channel_id}_{int(time.time())}{ext}"
    fpath = os.path.join(UPLOADS_DIR, fname)
    content_bytes = await file.read()
    with open(fpath, "wb") as f:
        f.write(content_bytes)
    img_url = f"/static/uploads/{fname}"
    b64_img = base64.b64encode(content_bytes).decode()
    media_type = file.content_type or "image/jpeg"
    prompt_text = """Ты — арт-директор коротких вертикальных видео.
Проанализируй изображение как референс визуального стиля канала.
Верни строго JSON без markdown:
{
  "style_name": "название стиля",
  "color_palette": {"primary": "#hex", "secondary": "#hex", "accent": "#hex", "background": "#hex"},
  "lighting": "описание освещения",
  "atmosphere": "описание атмосферы",
  "mood": "эмоциональный тон",
  "photography_style": "стиль съёмки",
  "color_grading": "обработка цвета",
  "composition": "правила композиции",
  "leonardo_style_prompt": "style prompt для Leonardo AI на английском",
  "leonardo_negative_prompt": "что исключить",
  "summary": "2-3 предложения описания визуального языка"
}"""
    try:
        cl = claude_client()
        msg = cl.messages.create(
            model="claude-opus-4-6",
            max_tokens=1500,
            messages=[{"role": "user", "content": [
                {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": b64_img}},
                {"type": "text", "text": prompt_text}
            ]}]
        )
        style_data = json.loads(clean_json(extract_text(msg)))
        db_update("shorts_channels", channel_id, {
            "visual_style_json": json.dumps(style_data, ensure_ascii=False),
            "style_image_url": img_url
        })
        return {"success": True, "channel_id": channel_id, "style_image_url": img_url, "visual_style": style_data}
    except Exception as e:
        return {"success": False, "error": str(e)}


class ScenarioRequest(BaseModel):
    channel_id: int
    reference_id: Optional[int] = None
    topic: Optional[str] = ""

@router.post("/generate-scenario")
def generate_scenario(req: ScenarioRequest):
    if not CLAUDE_API_KEY:
        return {"success": False, "error": "CLAUDE_API_KEY not set"}
    channel = db_get("shorts_channels", req.channel_id)
    if not channel:
        return {"success": False, "error": "channel not found"}
    try:
        visual_style = json.loads(channel.get("visual_style_json") or "{}")
    except Exception:
        visual_style = {}
    formula_block = ""
    if req.reference_id:
        ref = db_get("shorts_references", req.reference_id)
        if ref:
            try:
                analysis = json.loads(ref.get("raw_analysis_json") or "{}")
                formula_block = f"""
ФОРМУЛА РЕФЕРЕНСА:
{json.dumps(analysis.get("formula", {}), ensure_ascii=False, indent=2)}
СТРУКТУРА:
{json.dumps(analysis.get("structure", []), ensure_ascii=False, indent=2)}
ТИП ХУКА: {analysis.get("hook_type", "")}
ТЕМП: {analysis.get("pacing", "")}
ЭМОЦИЯ: {analysis.get("emotion", "")}"""
            except Exception:
                pass
    visual_block = ""
    if visual_style:
        visual_block = f"ВИЗУАЛЬНЫЙ СТИЛЬ:\n{json.dumps(visual_style, ensure_ascii=False, indent=2)}"
    prompt = f"""Ты — сценарист коротких вертикальных видео (до 60 секунд).
Канал: {channel.get("name")}
Ниша: {channel.get("niche") or "не задана"}
Язык: {channel.get("language", "ru")}
Тема: {req.topic or "выбери сам исходя из ниши"}
{formula_block}
{visual_block}
Создай НОВЫЙ сценарий используя формулу референса. Не копируй тему.
Верни строго JSON без markdown:
{{
  "title": "название видео",
  "hook": "хук для первых 2 секунд",
  "script": [
    {{"time": "0-3 сек", "action": "...", "voiceover": "..."}},
    {{"time": "3-8 сек", "action": "...", "voiceover": "..."}},
    {{"time": "8-20 сек", "action": "...", "voiceover": "..."}},
    {{"time": "20-40 сек", "action": "...", "voiceover": "..."}},
    {{"time": "40-60 сек", "action": "...", "voiceover": "..."}}
  ],
  "voiceover": "полный текст озвучки одним блоком",
  "visual_style": "описание визуала",
  "cta": "призыв к действию",
  "kling_prompts": [
    "промпт для сцены 1 на английском",
    "промпт для сцены 2",
    "промпт для сцены 3"
  ],
  "estimated_duration": "45-60 сек"
}}"""
    try:
        cl = claude_client()
        msg = cl.messages.create(model=MODEL, max_tokens=2500, temperature=0.5,
            messages=[{"role": "user", "content": prompt}])
        data = json.loads(clean_json(extract_text(msg)))
        row_id = db_insert("shorts_scenarios", {
            "channel_id": req.channel_id,
            "reference_id": req.reference_id,
            "title": data.get("title", ""),
            "hook": data.get("hook", ""),
            "script_json": json.dumps(data.get("script", []), ensure_ascii=False),
            "voiceover": data.get("voiceover", ""),
            "visual_style": data.get("visual_style", ""),
            "cta": data.get("cta", ""),
            "status": "draft",
            "created_at": datetime.now().isoformat(timespec="seconds")
        })
        return {"success": True, "id": row_id, "scenario": data}
    except Exception as e:
        return {"success": False, "error": str(e)}

@router.get("/scenarios")
def list_scenarios(channel_id: Optional[int] = None):
    if channel_id:
        items = db_list("shorts_scenarios", "channel_id=?", [channel_id])
    else:
        items = db_list("shorts_scenarios")
    for item in items:
        try:
            item["script"] = json.loads(item.get("script_json") or "[]")
        except Exception:
            item["script"] = []
    return {"success": True, "items": items}

@router.get("/scenarios/{scenario_id}")
def get_scenario(scenario_id: int):
    row = db_get("shorts_scenarios", scenario_id)
    if not row:
        return {"success": False, "error": "not found"}
    try:
        row["script"] = json.loads(row.get("script_json") or "[]")
    except Exception:
        row["script"] = []
    return {"success": True, "scenario": row}


@router.get("/elevenlabs/voices")
def get_elevenlabs_voices():
    if not ELEVENLABS_API_KEY:
        return {"success": False, "error": "ELEVENLABS_API_KEY not set"}
    try:
        r = requests.get(
            os.getenv("ELEVENLABS_PROXY_URL", "https://api.elevenlabs.io") + "/v1/voices",
            headers={"xi-api-key": ELEVENLABS_API_KEY},
            timeout=15
        )
        if not r.ok:
            return {"success": False, "error": r.text}
        voices = r.json().get("voices", [])
        simplified = [
            {"voice_id": v["voice_id"], "name": v["name"],
             "category": v.get("category", ""), "labels": v.get("labels", {})}
            for v in voices
        ]
        return {"success": True, "voices": simplified}
    except Exception as e:
        return {"success": False, "error": str(e)}

class SetVoiceRequest(BaseModel):
    voice_id: str
    voice_name: str

@router.post("/channels/{channel_id}/set-voice")
def set_channel_voice(channel_id: int, body: SetVoiceRequest):
    channel = db_get("shorts_channels", channel_id)
    if not channel:
        return {"success": False, "error": "channel not found"}
    db_update("shorts_channels", channel_id, {
        "voice_id": body.voice_id,
        "voice_name": body.voice_name
    })
    return {"success": True, "channel_id": channel_id, "voice_id": body.voice_id}

@router.post("/scenarios/{scenario_id}/generate-audio")
def generate_audio(scenario_id: int):
    if not ELEVENLABS_API_KEY:
        return {"success": False, "error": "ELEVENLABS_API_KEY not set"}
    scenario = db_get("shorts_scenarios", scenario_id)
    if not scenario:
        return {"success": False, "error": "scenario not found"}
    voiceover = scenario.get("voiceover", "").strip()
    if not voiceover:
        return {"success": False, "error": "voiceover text is empty"}
    voice_id = "21m00Tcm4TlvDq8ikWAM"
    if scenario.get("channel_id"):
        channel = db_get("shorts_channels", scenario["channel_id"])
        if channel and channel.get("voice_id"):
            voice_id = channel["voice_id"]
    try:
        r = requests.post(
            f"{os.getenv('ELEVENLABS_PROXY_URL', 'https://api.elevenlabs.io')}/v1/text-to-speech/{voice_id}",
            headers={"xi-api-key": ELEVENLABS_API_KEY, "Content-Type": "application/json"},
            json={
                "text": voiceover,
                "model_id": "eleven_multilingual_v2",
                "voice_settings": {"stability": 0.45, "similarity_boost": 0.80, "style": 0.2, "use_speaker_boost": True}
            },
            timeout=120
        )
        if not r.ok:
            return {"success": False, "error": r.text}
        fname = f"audio_{scenario_id}_{int(time.time())}.mp3"
        fpath = os.path.join(AUDIO_DIR, fname)
        with open(fpath, "wb") as f:
            f.write(r.content)
        audio_url = f"/static/audio/{fname}"
        prod_rows = db_list("shorts_productions", "scenario_id=?", [scenario_id], limit=1)
        if prod_rows:
            db_update("shorts_productions", prod_rows[0]["id"], {
                "audio_url": audio_url, "audio_path": fpath,
                "voice_id": voice_id, "status": "audio_ready"
            })
            prod_id = prod_rows[0]["id"]
        else:
            prod_id = db_insert("shorts_productions", {
                "scenario_id": scenario_id,
                "channel_id": scenario.get("channel_id"),
                "audio_url": audio_url, "audio_path": fpath,
                "voice_id": voice_id, "status": "audio_ready",
                "created_at": datetime.now().isoformat(timespec="seconds")
            })
        return {"success": True, "production_id": prod_id, "audio_url": audio_url}
    except Exception as e:
        return {"success": False, "error": str(e)}


class KlingVideoRequest(BaseModel):
    scenario_id: int
    kling_prompt: str
    aspect_ratio: Optional[str] = "9:16"
    duration: Optional[str] = "5"

@router.post("/generate-video-clip")
def generate_video_clip(req: KlingVideoRequest):
    if not KLING_API_KEY or not KLING_API_SECRET:
        return {"success": False, "error": "KLING_API_KEY / KLING_API_SECRET not set"}
    token = kling_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    try:
        r = requests.post(
            "https://api.klingai.com/v1/videos/text2video",
            headers=headers,
            json={
                "model": "kling-v1",
                "prompt": req.kling_prompt,
                "negative_prompt": "blurry, low quality, watermark, text overlay",
                "cfg_scale": 0.5,
                "mode": "std",
                "aspect_ratio": req.aspect_ratio,
                "duration": req.duration
            },
            timeout=90
        )
        if not r.ok:
            return {"success": False, "error": r.text, "status_code": r.status_code}
        resp_data = r.json()
        task_id = resp_data.get("data", {}).get("task_id")
        if not task_id:
            return {"success": False, "error": "task_id not returned", "response": resp_data}
        prod_rows = db_list("shorts_productions", "scenario_id=?", [req.scenario_id], limit=1)
        if prod_rows:
            db_update("shorts_productions", prod_rows[0]["id"], {
                "kling_task_id": task_id, "status": "video_generating"
            })
        else:
            db_insert("shorts_productions", {
                "scenario_id": req.scenario_id,
                "kling_task_id": task_id,
                "status": "video_generating",
                "created_at": datetime.now().isoformat(timespec="seconds")
            })
        return {"success": True, "task_id": task_id}
    except Exception as e:
        return {"success": False, "error": str(e)}

@router.get("/kling-task/{task_id}")
def poll_kling_task(task_id: str, scenario_id: Optional[int] = None):
    if not KLING_API_KEY:
        return {"success": False, "error": "KLING_API_KEY not set"}
    token = kling_token()
    headers = {"Authorization": f"Bearer {token}"}
    try:
        r = requests.get(
            f"https://api.klingai.com/v1/videos/text2video/{task_id}",
            headers=headers, timeout=15
        )
        if not r.ok:
            return {"success": False, "error": r.text}
        data = r.json().get("data", {})
        status = data.get("task_status", "")
        if status == "succeed":
            works = data.get("task_result", {}).get("videos", [])
            video_url = works[0].get("url", "") if works else ""
            if video_url and scenario_id:
                prod_rows = db_list("shorts_productions", "scenario_id=?", [scenario_id], limit=1)
                if prod_rows:
                    db_update("shorts_productions", prod_rows[0]["id"], {
                        "video_url": video_url, "status": "video_ready"
                    })
            return {"success": True, "status": "ready", "video_url": video_url}
        if status == "failed":
            return {"success": False, "status": "failed", "error": data.get("task_status_msg", "")}
        return {"success": True, "status": "processing"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/productions/{prod_id}/assemble")
def assemble_video(prod_id: int):
    prod = db_get("shorts_productions", prod_id)
    if not prod:
        return {"success": False, "error": "production not found"}
    audio_path = prod.get("audio_path", "")
    video_url = prod.get("video_url", "")
    video_path = prod.get("video_path", "")
    if not audio_path or not os.path.exists(audio_path):
        return {"success": False, "error": "audio file not found"}
    if video_url and not video_path:
        vfname = f"clip_{prod_id}_{int(time.time())}.mp4"
        video_path = os.path.join(VIDEO_DIR, vfname)
        try:
            r = requests.get(video_url, timeout=120, stream=True)
            with open(video_path, "wb") as f:
                for chunk in r.iter_content(8192):
                    f.write(chunk)
            db_update("shorts_productions", prod_id, {"video_path": video_path})
        except Exception as e:
            return {"success": False, "error": f"video download failed: {e}"}
    if not video_path or not os.path.exists(video_path):
        vfname = f"blank_{prod_id}.mp4"
        video_path = os.path.join(VIDEO_DIR, vfname)
        subprocess.run([
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "color=c=black:size=1080x1920:rate=30",
            "-t", "60", "-c:v", "libx264", "-pix_fmt", "yuv420p",
            video_path
        ], capture_output=True)
    subtitle_filter = ""
    if prod.get("scenario_id"):
        scenario = db_get("shorts_scenarios", prod["scenario_id"])
        if scenario and scenario.get("voiceover"):
            srt_path = os.path.join(VIDEO_DIR, f"sub_{prod_id}.srt")
            with open(srt_path, "w", encoding="utf-8") as f:
                f.write("1\n00:00:02,000 --> 00:00:58,000\n" + scenario["voiceover"][:500] + "\n")
            subtitle_filter = f",subtitles={srt_path}:force_style='FontName=Arial,FontSize=18,PrimaryColour=&Hffffff,OutlineColour=&H000000,Outline=2,Alignment=2'"
    out_fname = f"final_{prod_id}_{int(time.time())}.mp4"
    out_path = os.path.join(VIDEO_DIR, out_fname)
    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-i", audio_path,
        "-filter_complex", f"[0:v]scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2{subtitle_filter}[v]",
        "-map", "[v]", "-map", "1:a",
        "-c:v", "libx264", "-c:a", "aac",
        "-shortest", "-movflags", "+faststart", "-pix_fmt", "yuv420p",
        out_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
    if result.returncode != 0:
        return {"success": False, "error": "FFmpeg failed", "stderr": result.stderr[-2000:]}
    final_url = f"/static/video/{out_fname}"
    db_update("shorts_productions", prod_id, {
        "final_path": out_path, "final_url": final_url, "status": "complete"
    })
    return {"success": True, "final_url": final_url, "production_id": prod_id}

@router.get("/productions")
def list_productions(channel_id: Optional[int] = None):
    if channel_id:
        items = db_list("shorts_productions", "channel_id=?", [channel_id])
    else:
        items = db_list("shorts_productions")
    return {"success": True, "items": items}

@router.get("/productions/{prod_id}")
def get_production(prod_id: int):
    row = db_get("shorts_productions", prod_id)
    if not row:
        return {"success": False, "error": "not found"}
    return {"success": True, "production": row}
