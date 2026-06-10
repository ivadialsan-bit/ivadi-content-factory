import re
import os
import uuid
import subprocess
import requests
from urllib.parse import urlparse, parse_qs
from yt_dlp import YoutubeDL
from youtube_transcript_api import YouTubeTranscriptApi

import sys
sys.path.insert(0, "/root/factory")
from config import ELEVENLABS_API_KEY


ELEVENLABS_STT_PROXY = "https://elevenlabs-proxy.ivadialsan.workers.dev/v1/speech-to-text"


def extract_youtube_id(url: str):
    patterns = [
        r"youtube\.com/shorts/([^?&/]+)",
        r"youtube\.com/watch\?v=([^?&]+)",
        r"youtu\.be/([^?&/]+)"
    ]

    for pattern in patterns:
        m = re.search(pattern, url)
        if m:
            return m.group(1)

    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    if "v" in qs:
        return qs["v"][0]

    return None


def get_youtube_metadata(url: str):
    opts = {
        "quiet": True,
        "skip_download": True,
        "no_warnings": True
    }

    with YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)

    return {
        "title": info.get("title"),
        "description": info.get("description"),
        "channel": info.get("uploader") or info.get("channel"),
        "duration": info.get("duration"),
        "view_count": info.get("view_count"),
        "like_count": info.get("like_count"),
        "upload_date": info.get("upload_date"),
        "webpage_url": info.get("webpage_url"),
        "thumbnail": info.get("thumbnail")
    }


def get_youtube_transcript(video_id: str):
    if not video_id:
        return None

    try:
        transcript = YouTubeTranscriptApi.get_transcript(
            video_id,
            languages=["ru", "en"]
        )
        return " ".join([x.get("text", "") for x in transcript]).strip()
    except Exception:
        return None


def download_youtube_audio(url: str):
    uid = uuid.uuid4().hex[:10]
    base = f"/tmp/yt_audio_{uid}"
    out_template = base + ".%(ext)s"

    opts = {
        "format": "ba",
        "outtmpl": out_template,
        "quiet": True,
        "no_warnings": True
    }

    with YoutubeDL(opts) as ydl:
        ydl.extract_info(url, download=True)

    for ext in ["webm", "m4a", "mp3", "opus"]:
        path = f"{base}.{ext}"
        if os.path.exists(path):
            return path

    return None


def convert_to_wav(input_path: str):
    wav_path = input_path.rsplit(".", 1)[0] + ".wav"

    cmd = [
        "ffmpeg",
        "-y",
        "-i", input_path,
        "-ar", "16000",
        "-ac", "1",
        wav_path
    ]

    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

    return wav_path


def transcribe_with_elevenlabs(wav_path: str):
    headers = {
        "xi-api-key": ELEVENLABS_API_KEY
    }

    with open(wav_path, "rb") as f:
        files = {
            "file": ("audio.wav", f, "audio/wav")
        }
        data = {
            "model_id": "scribe_v1"
        }

        r = requests.post(
            ELEVENLABS_STT_PROXY,
            headers=headers,
            files=files,
            data=data,
            timeout=180
        )

    r.raise_for_status()
    result = r.json()

    return {
        "text": result.get("text", ""),
        "language_code": result.get("language_code"),
        "language_probability": result.get("language_probability"),
        "words": result.get("words", [])[:2000]
    }


def transcribe_youtube_audio(url: str):
    audio_path = None
    wav_path = None

    try:
        audio_path = download_youtube_audio(url)
        if not audio_path:
            return None

        wav_path = convert_to_wav(audio_path)
        return transcribe_with_elevenlabs(wav_path)

    finally:
        for p in [audio_path, wav_path]:
            try:
                if p and os.path.exists(p):
                    os.remove(p)
            except Exception:
                pass


def extract_youtube_data(url: str):
    video_id = extract_youtube_id(url)
    metadata = {}
    transcript = None
    stt = None
    errors = []

    try:
        metadata = get_youtube_metadata(url)
    except Exception as e:
        errors.append("metadata: " + str(e)[:300])

    try:
        transcript = get_youtube_transcript(video_id)
    except Exception as e:
        errors.append("youtube_transcript: " + str(e)[:300])

    if not transcript:
        try:
            stt = transcribe_youtube_audio(url)
            if stt and stt.get("text"):
                transcript = stt.get("text")
        except Exception as e:
            errors.append("elevenlabs_stt: " + str(e)[:300])

    confidence = "low"
    transcript_source = None

    if transcript and len(transcript) > 100:
        confidence = "high"
        transcript_source = "elevenlabs_stt" if stt else "youtube_subtitles"
    elif metadata.get("title") or metadata.get("description"):
        confidence = "medium"

    return {
        "platform": "youtube",
        "video_id": video_id,
        "metadata": metadata,
        "transcript": transcript,
        "transcript_source": transcript_source,
        "stt": stt,
        "has_transcript": bool(transcript),
        "confidence": confidence,
        "errors": errors
    }
