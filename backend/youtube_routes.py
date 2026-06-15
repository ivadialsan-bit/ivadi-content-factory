import re
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

    prompt = f"""Ты эксперт по брендингу YouTube Shorts каналов. Создай полный брендинг-пакет для нового канала.

ВАЖНО: Это канал ТОЛЬКО для YouTube Shorts (вертикальные видео 15-60 секунд). Всё оформление, стратегия и контент — только под Shorts формат. Канал автоматизирован через AI.

Ниша: {niche}
Тип канала: {channel_type}
Язык контента: {language}
Дополнительный стиль: {style}

Верни ТОЛЬКО валидный JSON без markdown:
{{
  "channel_names": ["название 1", "название 2", "название 3"],
  "channel_description": "описание канала 150-300 символов с ключевыми словами для SEO — только Shorts канал",
  "keywords": ["ключевое слово 1", "ключевое слово 2", "ключевое слово 3", "ключевое слово 4", "ключевое слово 5"],
  "tone_of_voice": "описание стиля подачи контента в формате 15-60 секунд",
  "color_palette": {{
    "primary": "#HEX цвет",
    "secondary": "#HEX цвет",
    "accent": "#HEX цвет",
    "background": "#HEX цвет"
  }},
  "visual_style": "описание визуального стиля канала",
  "avatar_prompt": "детальный промпт для генерации аватара канала на английском языке для Leonardo AI, 512x512, профессиональный логотип",
  "banner_prompt": "cinematic background image for YouTube channel art, NO TEXT, NO LETTERS, NO WORDS, purely visual, atmospheric, 2560x1440, related to the niche theme, professional, dark moody lighting, ultra detailed, 8k quality",
  "content_pillars": ["столб 1", "столб 2", "столб 3"],
  "posting_strategy": "стратегия публикаций Shorts: сколько в день, в какое время по EST/МСК, как часто",
  "first_10_videos": ["идея Shorts #1 (15-60 сек)", "идея Shorts #2", "идея Shorts #3", "идея Shorts #4", "идея Shorts #5", "идея Shorts #6", "идея Shorts #7", "идея Shorts #8", "идея Shorts #9", "идея Shorts #10"],
  "monetization_plan": "план монетизации канала",
  "ai_verdict": "общая рекомендация и прогноз роста"
}}"""

    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}]
    )
    text = msg.content[0].text.strip()
    # Remove markdown if present
    if text.startswith("```"):
        text = re.sub(r"```[\w]*", "", text).strip()
    try:
        return json.loads(text)
    except:
        # Try to fix truncated JSON
        try:
            # Find last complete field
            match = re.search(r'\{.*\}', text, re.DOTALL)
            if match:
                return json.loads(match.group())
        except:
            pass
        # Build minimal response from partial data
        result = {}
        for field in ["channel_names","channel_description","keywords","tone_of_voice","avatar_prompt","banner_prompt","content_pillars","posting_strategy","first_10_videos","monetization_plan","ai_verdict"]:
            m = re.search(f'"{field}"\s*:\s*(\[.*?\]|".*?")', text, re.DOTALL)
            if m:
                try:
                    result[field] = json.loads(m.group(1))
                except:
                    result[field] = m.group(1).strip('"')
        if result:
            result["color_palette"] = {"primary":"#1A0A2E","secondary":"#C0392B","accent":"#D4AF37","background":"#0D0D0D"}
            return result
        return {"error": "parse error", "raw": text[:300]}

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


@router.post("/profiles")
def save_profile(data: dict, db: Session = Depends(get_db)):
    from models import YouTubeChannelProfile
    profile = YouTubeChannelProfile(
        account_id=data.get("account_id"),
        name=data.get("name", "Новый канал"),
        niche=data.get("niche"),
        channel_type=data.get("channel_type"),
        language=data.get("language"),
        branding_json=json.dumps(data.get("branding", {})),
        avatar_url=data.get("avatar_url"),
        banner_url=data.get("banner_url"),
        status="active"
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return {"id": profile.id, "name": profile.name}

@router.get("/profiles")
def get_profiles(db: Session = Depends(get_db)):
    from models import YouTubeChannelProfile
    profiles = db.query(YouTubeChannelProfile).order_by(YouTubeChannelProfile.created_at.desc()).all()
    result = []
    for p in profiles:
        branding = json.loads(p.branding_json) if p.branding_json else {}
        result.append({
            "id": p.id,
            "account_id": p.account_id,
            "name": p.name,
            "niche": p.niche,
            "channel_type": p.channel_type,
            "language": p.language,
            "avatar_url": p.avatar_url,
            "banner_url": p.banner_url,
            "autopilot_enabled": p.autopilot_enabled,
            "status": p.status,
            "created_at": str(p.created_at),
            "channel_names": branding.get("channel_names", []),
            "posting_strategy": branding.get("posting_strategy", ""),
            "content_pillars": branding.get("content_pillars", []),
            "first_10_videos": branding.get("first_10_videos", []),
            "monetization_plan": branding.get("monetization_plan", ""),
            "ai_verdict": branding.get("ai_verdict", ""),
            "color_palette": branding.get("color_palette", {}),
            "keywords": branding.get("keywords", []),
            "channel_description": branding.get("channel_description", ""),
            "tone_of_voice": branding.get("tone_of_voice", "")
        })
    return result

@router.get("/profiles/{profile_id}")
def get_profile(profile_id: int, db: Session = Depends(get_db)):
    from models import YouTubeChannelProfile
    p = db.query(YouTubeChannelProfile).filter_by(id=profile_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Not found")
    branding = json.loads(p.branding_json) if p.branding_json else {}
    return {"id": p.id, "name": p.name, "niche": p.niche, "branding": branding,
            "avatar_url": p.avatar_url, "banner_url": p.banner_url,
            "autopilot_enabled": p.autopilot_enabled}

@router.post("/profiles/{profile_id}/generate-plan")
def generate_content_plan(profile_id: int, db: Session = Depends(get_db)):
    from models import YouTubeChannelProfile, YouTubeContentPlan
    p = db.query(YouTubeChannelProfile).filter_by(id=profile_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Not found")
    branding = json.loads(p.branding_json) if p.branding_json else {}

    client = anthropic.Anthropic(api_key=CLAUDE_API_KEY, base_url=CLAUDE_PROXY_URL)
    prompt = f"""Ты контент-стратег YouTube Shorts. Создай детальный план на 4 недели ТОЛЬКО для YouTube Shorts (вертикальные видео 15-60 секунд).

ВАЖНО: Никаких длинных видео. Только Shorts 15-60 секунд. Канал полностью автоматизирован через AI — озвучка ElevenLabs, видеоряд Kling AI, монтаж FFmpeg.

Канал: {p.name}
Ниша: {p.niche}
Тип: {p.channel_type}
Язык: {p.language}
Контентные столбы: {', '.join(branding.get('content_pillars', []))}
Tone of voice: {branding.get('tone_of_voice', '')}
Первые идеи: {', '.join(branding.get('first_10_videos', [])[:5])}

Верни ТОЛЬКО валидный JSON:
{{
  "weeks": [
    {{
      "week": 1,
      "theme": "тема недели",
      "goal": "цель недели",
      "videos": [
        {{
          "day": "Monday",
          "title": "название видео",
          "type": "Short/Long",
          "hook": "хук первых 3 секунд",
          "description": "краткое описание",
          "publish_time": "15:00 EST",
          "seo_focus": "главное ключевое слово"
        }}
      ],
      "weekly_tip": "совет недели для роста"
    }}
  ],
  "30_day_kpi": {{
    "target_subscribers": 500,
    "target_views": 50000,
    "target_watch_hours": 200,
    "videos_to_publish": 16
  }},
  "autopilot_rules": [
    "правило 1 для автопилота",
    "правило 2"
  ]
}}"""

    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}]
    )
    text = msg.content[0].text.strip()
    try:
        plan_data = json.loads(text)
    except:
        import re
        match = re.search(r'\{.*\}', text, re.DOTALL)
        plan_data = json.loads(match.group()) if match else {"error": "parse error"}

    plan = YouTubeContentPlan(
        profile_id=profile_id,
        account_id=p.account_id,
        week_number=1,
        plan_json=json.dumps(plan_data),
        status="active"
    )
    db.add(plan)
    db.commit()
    return plan_data

@router.get("/profiles/{profile_id}/plans")
def get_plans(profile_id: int, db: Session = Depends(get_db)):
    from models import YouTubeContentPlan
    plans = db.query(YouTubeContentPlan).filter_by(profile_id=profile_id).order_by(YouTubeContentPlan.created_at.desc()).all()
    return [{"id": p.id, "plan": json.loads(p.plan_json) if p.plan_json else {}, "created_at": str(p.created_at)} for p in plans]

@router.patch("/profiles/{profile_id}/autopilot")
def toggle_autopilot(profile_id: int, data: dict, db: Session = Depends(get_db)):
    from models import YouTubeChannelProfile
    p = db.query(YouTubeChannelProfile).filter_by(id=profile_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Not found")
    p.autopilot_enabled = data.get("enabled", False)
    p.updated_at = datetime.utcnow()
    db.commit()
    return {"autopilot_enabled": p.autopilot_enabled}


@router.post("/generate-banner-with-text")
def generate_banner_with_text(data: dict):
    import subprocess, time, tempfile, base64
    from PIL import Image, ImageDraw, ImageFont
    import urllib.request
    import io

    bg_prompt = data.get("bg_prompt", "")
    channel_name = data.get("channel_name", "")
    tagline = data.get("tagline", "")
    primary_color = data.get("primary_color", "#ffffff")
    bg_color = data.get("bg_color", "#0D0D0D")

    LEONARDO_API_KEY = os.getenv("LEONARDO_API_KEY")

    # Step 1: Generate background via Leonardo
    gen_payload = {
        "prompt": bg_prompt + ", NO TEXT, NO LETTERS, NO WORDS, cinematic background only",
        "width": 1472,
        "height": 832,
        "num_images": 1,
        "modelId": "b24e16ff-06e3-43eb-8d33-4416c2d75876"
    }

    cmd = ["curl", "-s", "--max-time", "30",
           "-X", "POST", "https://cloud.leonardo.ai/api/rest/v1/generations",
           "-H", f"authorization: Bearer {LEONARDO_API_KEY}",
           "-H", "content-type: application/json",
           "-d", json.dumps(gen_payload)]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=35)
    gen_data = json.loads(result.stdout)
    gen_id = gen_data.get("sdGenerationJob", {}).get("generationId")

    if not gen_id:
        return {"error": "No generation ID"}

    # Poll
    bg_url = None
    for _ in range(20):
        time.sleep(3)
        poll_cmd = ["curl", "-s", "--max-time", "10",
                    f"https://cloud.leonardo.ai/api/rest/v1/generations/{gen_id}",
                    "-H", f"authorization: Bearer {LEONARDO_API_KEY}"]
        poll_result = subprocess.run(poll_cmd, capture_output=True, text=True, timeout=15)
        poll_data = json.loads(poll_result.stdout)
        images = poll_data.get("generations_by_pk", {}).get("generated_images", [])
        if images:
            bg_url = images[0]["url"]
            break

    if not bg_url:
        return {"error": "Background generation timeout"}

    # Step 2: Download background via curl
    dl_cmd = ["curl", "-s", "--max-time", "15", "-L",
               "-H", "User-Agent: Mozilla/5.0",
               bg_url]
    dl_result = subprocess.run(dl_cmd, capture_output=True, timeout=20)
    bg_data = dl_result.stdout

    img = Image.open(io.BytesIO(bg_data)).convert("RGBA")
    img = img.resize((1546, 873), Image.LANCZOS)

    # Step 3: Dark overlay for text readability
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 140))
    img = Image.alpha_composite(img, overlay)

    draw = ImageDraw.Draw(img)
    W, H = img.size

    FONTS_DIR = "/root/factory/backend/fonts"

    def hex_to_rgb(h):
        h = h.lstrip('#')
        return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

    accent_rgb = hex_to_rgb(primary_color) + (255,)
    white_rgb = (255, 255, 255, 255)

    try:
        font_title = ImageFont.truetype(f"{FONTS_DIR}/Montserrat-Bold.ttf", 96)
        font_tagline = ImageFont.truetype(f"{FONTS_DIR}/Montserrat-Regular.ttf", 36)
        font_letter_spacing = ImageFont.truetype(f"{FONTS_DIR}/Montserrat-Bold.ttf", 14)
    except:
        try:
            font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 96)
            font_tagline = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 36)
            font_letter_spacing = font_tagline
        except:
            font_title = ImageFont.load_default()
            font_tagline = ImageFont.load_default()
            font_letter_spacing = font_tagline

    # Strong gradient overlay - bottom 60% darker
    gradient = Image.new("RGBA", img.size, (0,0,0,0))
    grad_draw = ImageDraw.Draw(gradient)
    for i in range(H):
        alpha = int(180 * (i / H) ** 0.6)
        grad_draw.line([(0, i), (W, i)], fill=(0, 0, 0, min(alpha, 200)))
    img = Image.alpha_composite(img, gradient)

    # Left-side dark panel for text
    panel = Image.new("RGBA", img.size, (0,0,0,0))
    panel_draw = ImageDraw.Draw(panel)
    panel_draw.rectangle([(0, 0), (W, H)], fill=(0, 0, 0, 100))
    img = Image.alpha_composite(img, panel)

    draw = ImageDraw.Draw(img)

    # Accent bar - left side vertical
    bar_w = 8
    bar_h = 160
    bar_x = W // 2 - 320
    bar_y = H // 2 - bar_h // 2
    accent_color_full = hex_to_rgb(primary_color) + (255,)
    draw.rectangle([(bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h)], fill=accent_color_full)

    # Channel name
    if channel_name:
        name_upper = channel_name.upper()
        bbox = draw.textbbox((0, 0), name_upper, font=font_title)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        x = (W - tw) // 2
        y = H // 2 - th // 2 - 25

        # Multi-layer shadow for depth
        for offset in [(6,6), (4,4), (2,2)]:
            draw.text((x + offset[0], y + offset[1]), name_upper, font=font_title, fill=(0,0,0,160))

        # Main text white
        draw.text((x, y), name_upper, font=font_title, fill=(255,255,255,255))

        # Accent color highlight on first letter
        first_bbox = draw.textbbox((x, y), name_upper[0], font=font_title)
        draw.text((x, y), name_upper[0], font=font_title, fill=accent_color_full)

    # Tagline below
    if tagline:
        tag_upper = tagline.upper()
        bbox2 = draw.textbbox((0, 0), tag_upper, font=font_tagline)
        tw2 = bbox2[2] - bbox2[0]
        x2 = (W - tw2) // 2
        y2 = H // 2 + 55

        # Tagline with accent color
        draw.text((x2 + 2, y2 + 2), tag_upper, font=font_tagline, fill=(0,0,0,180))
        draw.text((x2, y2), tag_upper, font=font_tagline, fill=accent_color_full)

    # Bottom accent line full width
    line_y = H // 2 + 105
    draw.rectangle([(W//2 - 250, line_y), (W//2 + 250, line_y + 3)], fill=(255,255,255,120))

    # Small dots decoration
    dot_y = line_y + 20
    for i in range(5):
        dot_x = W//2 - 40 + i * 20
        r = 3 if i == 2 else 2
        draw.ellipse([(dot_x-r, dot_y-r), (dot_x+r, dot_y+r)], fill=accent_color_full)

    # Save to temp file
    img_rgb = img.convert("RGB")
    buf = io.BytesIO()
    img_rgb.save(buf, format="JPEG", quality=95)
    buf.seek(0)
    b64 = base64.b64encode(buf.read()).decode()

    return {
        "bg_url": bg_url,
        "banner_base64": b64,
        "banner_data_url": f"data:image/jpeg;base64,{b64}"
    }
