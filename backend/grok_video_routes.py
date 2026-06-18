import os
import time
import httpx
import base64
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

XAI_API_KEY = os.getenv("XAI_API_KEY", "")
XAI_API_BASE = "https://api.x.ai/v1"

router = APIRouter(prefix="/grok-video", tags=["grok-video"])


class TextToVideoRequest(BaseModel):
    prompt: str
    resolution: str = "480p"
    duration: int = 6
    aspect_ratio: str = "9:16"
    output_filename: Optional[str] = None


class ImageToVideoRequest(BaseModel):
    image_path: str
    prompt: str = ""
    resolution: str = "720p"
    duration: int = 6
    aspect_ratio: str = "9:16"
    output_filename: Optional[str] = None


def poll_video(request_id: str, max_wait: int = 300) -> dict:
    headers = {"Authorization": f"Bearer {XAI_API_KEY}"}
    elapsed = 0
    while elapsed < max_wait:
        with httpx.Client(timeout=30) as client:
            r = client.get(f"{XAI_API_BASE}/videos/{request_id}", headers=headers)
            r.raise_for_status()
            data = r.json()
        status = data.get("status", "")
        if status == "succeeded":
            return data
        elif status == "failed":
            raise RuntimeError(f"Генерация не удалась: {data}")
        time.sleep(5)
        elapsed += 5
    raise TimeoutError("Видео не готово за 300 секунд")


def save_video(result: dict, output_path: str) -> str:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    video_url = result.get("url") or (result.get("video", {}) or {}).get("url")
    if video_url:
        with httpx.Client(timeout=120) as client:
            output.write_bytes(client.get(video_url).content)
    else:
        raise ValueError(f"Нет url в ответе: {list(result.keys())}")
    return str(output)


@router.post("/text-to-video")
async def api_text_to_video(req: TextToVideoRequest):
    try:
        headers = {
            "Authorization": f"Bearer {XAI_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": "grok-imagine-video-1.5",
            "prompt": req.prompt,
            "resolution": req.resolution,
            "duration": req.duration,
            "aspect_ratio": req.aspect_ratio,
        }
        with httpx.Client(timeout=30) as client:
            r = client.post(f"{XAI_API_BASE}/videos/generations", headers=headers, json=payload)
            r.raise_for_status()
            data = r.json()
        request_id = data.get("id") or data.get("request_id")
        result = poll_video(request_id)
        filename = req.output_filename or f"grok_{int(time.time())}.mp4"
        saved = save_video(result, f"/root/factory/media/videos/{filename}")
        return {"status": "ok", "path": saved, "id": request_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/image-to-video")
async def api_image_to_video(req: ImageToVideoRequest):
    try:
        image_data = Path(req.image_path).read_bytes()
        image_b64 = base64.b64encode(image_data).decode("utf-8")
        ext = Path(req.image_path).suffix.lower().lstrip(".")
        mime = "image/jpeg" if ext in ("jpg", "jpeg") else f"image/{ext}"
        headers = {
            "Authorization": f"Bearer {XAI_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": "grok-imagine-video-1.5",
            "prompt": req.prompt,
            "image": f"data:{mime};base64,{image_b64}",
            "resolution": req.resolution,
            "duration": req.duration,
            "aspect_ratio": req.aspect_ratio,
        }
        with httpx.Client(timeout=30) as client:
            r = client.post(f"{XAI_API_BASE}/videos/generations", headers=headers, json=payload)
            r.raise_for_status()
            data = r.json()
        request_id = data.get("id") or data.get("request_id")
        result = poll_video(request_id)
        filename = req.output_filename or f"grok_i2v_{int(time.time())}.mp4"
        saved = save_video(result, f"/root/factory/media/videos/{filename}")
        return {"status": "ok", "path": saved, "id": request_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/test")
async def test_connection():
    try:
        headers = {"Authorization": f"Bearer {XAI_API_KEY}"}
        with httpx.Client(timeout=10) as client:
            r = client.get(f"{XAI_API_BASE}/models", headers=headers)
            r.raise_for_status()
            return {"status": "ok", "balance": "active"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
