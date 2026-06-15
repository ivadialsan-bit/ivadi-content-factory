from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from database import get_db
from models import YouTubeAccount, YouTubeVideo
import anthropic
import os, json, tempfile, shutil, requests
from datetime import datetime
from dotenv import load_dotenv
from urllib.parse import urlencode

load_dotenv()

router = APIRouter(prefix="/api/youtube", tags=["youtube"])

CLIENT_ID = os.getenv("YOUTUBE_CLIENT_ID")
CLIENT_SECRET = os.getenv("YOUTUBE_CLIENT_SECRET")
REDIRECT_URI = os.getenv("YOUTUBE_REDIRECT_URI")
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")
CLAUDE_PROXY_URL = os.getenv("CLAUDE_PROXY_URL")

SCOPES = "https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/youtube.readonly"

@router.get("/oauth/start")
def oauth_start():
    params = {
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": SCOPES,
        "access_type": "offline",
        "prompt": "consent"
    }
    auth_url = "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(params)
    return {"auth_url": auth_url}

@router.get("/oauth/callback")
def oauth_callback(code: str, db: Session = Depends(get_db)):
    try:
        token_resp = requests.post("https://oauth2.googleapis.com/token", data={
            "code": code,
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "redirect_uri": REDIRECT_URI,
            "grant_type": "authorization_code"
        })
        tokens = token_resp.json()
        if "error" in tokens:
            raise HTTPException(status_code=400, detail=str(tokens))

        access_token = tokens["access_token"]
        ch_resp = requests.get(
            "https://www.googleapis.com/youtube/v3/channels",
            params={"part": "snippet", "mine": True},
            headers={"Authorization": f"Bearer {access_token}"}
        ).json()

        channel_id = ch_resp["items"][0]["id"] if ch_resp.get("items") else "unknown"
        channel_name = ch_resp["items"][0]["snippet"]["title"] if ch_resp.get("items") else "Unknown"

        existing = db.query(YouTubeAccount).filter_by(channel_id=channel_id).first()
        if existing:
            existing.tokens_json = json.dumps(tokens)
            existing.channel_name = channel_name
            existing.status = "connected"
            existing.updated_at = datetime.utcnow()
        else:
            acc = YouTubeAccount(
                channel_id=channel_id,
                channel_name=channel_name,
                tokens_json=json.dumps(tokens),
                status="connected"
            )
            db.add(acc)
        db.commit()
        return RedirectResponse(url="/?page=youtube&connected=1")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/accounts")
def get_accounts(db: Session = Depends(get_db)):
    accounts = db.query(YouTubeAccount).all()
    return [{"id": a.id, "channel_id": a.channel_id, "channel_name": a.channel_name, "status": a.status, "created_at": str(a.created_at)} for a in accounts]

@router.delete("/accounts/{account_id}")
def delete_account(account_id: int, db: Session = Depends(get_db)):
    acc = db.query(YouTubeAccount).filter_by(id=account_id).first()
    if not acc:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(acc)
    db.commit()
    return {"ok": True}

@router.post("/generate-seo")
def generate_seo(data: dict):
    topic = data.get("topic", "")
    niche = data.get("niche", "")
    description_hint = data.get("description_hint", "")
    client = anthropic.Anthropic(api_key=CLAUDE_API_KEY, base_url=CLAUDE_PROXY_URL)
    prompt = f"""Ты эксперт по YouTube SEO. Создай SEO-пакет для YouTube Shorts видео.

Тема видео: {topic}
Ниша: {niche}
Краткое описание: {description_hint}

Верни ТОЛЬКО валидный JSON без markdown и пояснений:
{{
  "titles": ["Вариант заголовка 1 (хук + ключевое слово + интрига, до 100 символов)", "Вариант заголовка 2"],
  "description": "Описание видео с ключевыми словами, 150-300 символов.",
  "tags": ["тег1","тег2","тег3","тег4","тег5","тег6","тег7","тег8","тег9","тег10"],
  "thumbnail_prompts": ["Детальный промпт для превью 1 на английском", "Детальный промпт для превью 2 на английском"],
  "category_id": "22"
}}"""
    msg = client.messages.create(model="claude-sonnet-4-6", max_tokens=1000, messages=[{"role": "user", "content": prompt}])
    text = msg.content[0].text.strip()
    try:
        return json.loads(text)
    except:
        import re
        # Try to extract valid JSON even if truncated
        try:
            match = re.search(r'\{.*\}', text, re.DOTALL)
            if match:
                return json.loads(match.group())
        except:
            pass
        # Return partial result with what we have
        try:
            niches = re.findall(r'\{[^{}]*"name"[^{}]*\}', text, re.DOTALL)
            parsed = [json.loads(n) for n in niches if n]
            if parsed:
                return {"niches": parsed, "ai_verdict": "Анализ получен частично.", "updated_at": "2026"}
        except:
            pass
        return {"error": "parse error", "raw": text[:500]}

@router.post("/upload")
async def upload_video(
    account_id: int = Form(...),
    title: str = Form(...),
    description: str = Form(...),
    tags: str = Form(""),
    category_id: str = Form("22"),
    privacy: str = Form("public"),
    video_file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    acc = db.query(YouTubeAccount).filter_by(id=account_id).first()
    if not acc:
        raise HTTPException(status_code=404, detail="Account not found")
    tokens = json.loads(acc.tokens_json)
    access_token = tokens["access_token"]

    suffix = os.path.splitext(video_file.filename)[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(video_file.file, tmp)
        tmp_path = tmp.name

    try:
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload
        from google.oauth2.credentials import Credentials

        creds = Credentials(
            token=access_token,
            refresh_token=tokens.get("refresh_token"),
            token_uri="https://oauth2.googleapis.com/token",
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET
        )
        yt = build("youtube", "v3", credentials=creds)
        tags_list = [t.strip() for t in tags.split(",") if t.strip()]
        body = {
            "snippet": {"title": title, "description": description, "tags": tags_list, "categoryId": category_id},
            "status": {"privacyStatus": privacy}
        }
        media = MediaFileUpload(tmp_path, chunksize=-1, resumable=True)
        request = yt.videos().insert(part="snippet,status", body=body, media_body=media)
        response = None
        while response is None:
            _, response = request.next_chunk()
        video_id = response["id"]
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        vid = YouTubeVideo(
            account_id=account_id, youtube_video_id=video_id,
            title=title, description=description, tags=tags,
            category_id=category_id, privacy=privacy,
            video_url=video_url, status="published"
        )
        db.add(vid)
        db.commit()
        return {"ok": True, "video_id": video_id, "video_url": video_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        os.unlink(tmp_path)

@router.get("/videos")
def get_videos(db: Session = Depends(get_db)):
    videos = db.query(YouTubeVideo).order_by(YouTubeVideo.created_at.desc()).all()
    return [{"id": v.id, "account_id": v.account_id, "youtube_video_id": v.youtube_video_id,
             "title": v.title, "video_url": v.video_url, "status": v.status,
             "created_at": str(v.created_at)} for v in videos]

@router.post("/analyze-niches")
def analyze_niches(data: dict = {}):
    client = anthropic.Anthropic(api_key=CLAUDE_API_KEY, base_url=CLAUDE_PROXY_URL)
    focus = data.get("focus", "faceless English YouTube Shorts")
    prompt = f"""Ты эксперт по YouTube Shorts монетизации и росту каналов. Проанализируй топовые ниши для зарубежного YouTube Shorts ({focus}).

Верни ТОЛЬКО валидный JSON без markdown:
{{
  "updated_at": "2026",
  "niches": [
    {{
      "name": "название ниши на английском",
      "emoji": "эмодзи",
      "description": "1-2 предложения что это",
      "entry_difficulty": 3,
      "growth_potential": 9,
      "competition": "low",
      "monetization": "high",
      "avg_views_per_short": "10K-500K",
      "time_to_1k_subs": "2-4 недели",
      "content_ideas": ["идея 1", "идея 2", "идея 3"],
      "top_channels_example": ["канал 1", "канал 2"],
      "tools_needed": ["инструмент 1", "инструмент 2"],
      "why_now": "почему именно сейчас эта ниша перспективна",
      "best_for": "faceless",
      "monetization_methods": ["метод 1", "метод 2"]
    }}
  ],
  "ai_verdict": "общий вывод и рекомендация с чего начать"
}}

Включи 4 ниши. Приоритет: простота входа + высокий потенциал. Фокус на faceless каналах которые легко масштабировать."""

    msg = client.messages.create(model="claude-sonnet-4-6", max_tokens=2000, messages=[{"role": "user", "content": prompt}])
    text = msg.content[0].text.strip()
    try:
        return json.loads(text)
    except:
        import re
        # Try to extract valid JSON even if truncated
        try:
            match = re.search(r'\{.*\}', text, re.DOTALL)
            if match:
                return json.loads(match.group())
        except:
            pass
        # Return partial result with what we have
        try:
            niches = re.findall(r'\{[^{}]*"name"[^{}]*\}', text, re.DOTALL)
            parsed = [json.loads(n) for n in niches if n]
            if parsed:
                return {"niches": parsed, "ai_verdict": "Анализ получен частично.", "updated_at": "2026"}
        except:
            pass
        return {"error": "parse error", "raw": text[:500]}

@router.get("/accounts/{account_id}/stats")
def get_account_stats(account_id: int, db: Session = Depends(get_db)):
    import subprocess
    acc = db.query(YouTubeAccount).filter_by(id=account_id).first()
    if not acc:
        raise HTTPException(status_code=404, detail="Not found")
    tokens = json.loads(acc.tokens_json)
    access_token = tokens.get("access_token")

    def yt_request(token):
        cmd = [
            "curl", "-s", "--max-time", "10",
            "https://www.googleapis.com/youtube/v3/channels?part=statistics,snippet&mine=true",
            "-H", f"Authorization: Bearer {token}"
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        return json.loads(result.stdout)

    try:
        data = yt_request(access_token)

        if data.get("error", {}).get("code") == 401 and tokens.get("refresh_token"):
            ref_cmd = [
                "curl", "-s", "--max-time", "10",
                "-X", "POST", "https://oauth2.googleapis.com/token",
                "-d", f"client_id={CLIENT_ID}&client_secret={CLIENT_SECRET}&refresh_token={tokens['refresh_token']}&grant_type=refresh_token"
            ]
            ref_result = subprocess.run(ref_cmd, capture_output=True, text=True, timeout=15)
            new_tokens = json.loads(ref_result.stdout)
            if "access_token" in new_tokens:
                tokens["access_token"] = new_tokens["access_token"]
                acc.tokens_json = json.dumps(tokens)
                db.commit()
                access_token = new_tokens["access_token"]
                data = yt_request(access_token)

        if not data.get("items"):
            return {"error": "No channel data", "raw": str(data)[:200]}

        item = data["items"][0]
        stats = item.get("statistics", {})
        snippet = item.get("snippet", {})

        return {
            "subscribers": int(stats.get("subscriberCount", 0)),
            "views": int(stats.get("viewCount", 0)),
            "videos": int(stats.get("videoCount", 0)),
            "title": snippet.get("title", ""),
            "description": snippet.get("description", ""),
            "thumbnail": snippet.get("thumbnails", {}).get("default", {}).get("url", ""),
            "created_at": snippet.get("publishedAt", "")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/generate-branding")
def generate_branding(data: dict):
    niche = data.get("niche", "")
    channel_type = data.get("channel_type", "faceless")
    language = data.get("language", "English")
    style = data.get("style", "")

    client = anthropic.Anthropic(api_key=CLAUDE_API_KEY, base_url=CLAUDE_PROXY_URL)

    prompt = f"""Ты эксперт по брендингу YouTube каналов. Создай полный брендинг-пакет для нового канала.

Ниша: {niche}
Тип канала: {channel_type}
Язык контента: {language}
Дополнительный стиль: {style}

Верни ТОЛЬКО валидный JSON без markdown:
{{
  "channel_names": ["название 1", "название 2", "название 3"],
  "channel_description": "описание канала 150-300 символов с ключевыми словами для SEO",
  "keywords": ["ключевое слово 1", "ключевое слово 2", "ключевое слово 3", "ключевое слово 4", "ключевое слово 5"],
  "tone_of_voice": "описание стиля подачи контента",
  "color_palette": {{
    "primary": "#HEX цвет",
    "secondary": "#HEX цвет",
    "accent": "#HEX цвет",
    "background": "#HEX цвет"
  }},
  "visual_style": "описание визуального стиля канала",
  "avatar_prompt": "детальный промпт для генерации аватара канала на английском языке для Leonardo AI, 512x512, профессиональный логотип",
  "banner_prompt": "детальный промпт для генерации баннера канала на английском языке для Leonardo AI, 2560x1440, YouTube channel art",
  "content_pillars": ["столб 1", "столб 2", "столб 3"],
  "posting_strategy": "стратегия публикаций: частота, время, форматы",
  "first_10_videos": ["идея видео 1", "идея видео 2", "идея видео 3", "идея видео 4", "идея видео 5", "идея видео 6", "идея видео 7", "идея видео 8", "идея видео 9", "идея видео 10"],
  "monetization_plan": "план монетизации канала",
  "ai_verdict": "общая рекомендация и прогноз роста"
}}"""

    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}]
    )
    text = msg.content[0].text.strip()
    try:
        return json.loads(text)
    except:
        import re
        match = re.search(r'\{.*\}', text, re.DOTALL)
        return json.loads(match.group()) if match else {"error": "parse error", "raw": text[:300]}

@router.post("/generate-image")
def generate_image(data: dict):
    prompt = data.get("prompt", "")
    width = data.get("width", 512)
    height = data.get("height", 512)

    LEONARDO_API_KEY = os.getenv("LEONARDO_API_KEY")

    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "authorization": f"Bearer {LEONARDO_API_KEY}"
    }

    gen_payload = {
        "prompt": prompt,
        "width": width,
        "height": height,
        "num_images": 1,
        "modelId": "b24e16ff-06e3-43eb-8d33-4416c2d75876"
    }

    import subprocess, time

    cmd = ["curl", "-s", "--max-time", "30",
           "-X", "POST", "https://cloud.leonardo.ai/api/rest/v1/generations",
           "-H", f"authorization: Bearer {LEONARDO_API_KEY}",
           "-H", "content-type: application/json",
           "-d", json.dumps(gen_payload)]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=35)
    gen_data = json.loads(result.stdout)
    gen_id = gen_data.get("sdGenerationJob", {}).get("generationId")

    if not gen_id:
        return {"error": "No generation ID", "raw": result.stdout[:200]}

    # Poll for result
    for _ in range(20):
        time.sleep(3)
        poll_cmd = ["curl", "-s", "--max-time", "10",
                    f"https://cloud.leonardo.ai/api/rest/v1/generations/{gen_id}",
                    "-H", f"authorization: Bearer {LEONARDO_API_KEY}"]
        poll_result = subprocess.run(poll_cmd, capture_output=True, text=True, timeout=15)
        poll_data = json.loads(poll_result.stdout)
        images = poll_data.get("generations_by_pk", {}).get("generated_images", [])
        if images:
            return {"url": images[0]["url"], "generation_id": gen_id}

    return {"error": "Generation timeout"}
