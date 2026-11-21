"""Sample-accurate phrase timing and simple royalty-free synthesized sound effects."""
import math
import wave
from pathlib import Path
import numpy as np

RATE = 48000


def read_mono_pcm(path: Path):
    with wave.open(str(path), "rb") as w:
        if (w.getnchannels(), w.getframerate(), w.getsampwidth()) != (1, RATE, 2):
            raise ValueError(f"Expected mono 48kHz PCM16 WAV: {path}")
        data = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2")
        return data.astype(np.float32) / 32768.0


def timeline(story, clips, gap=0.52, lead=0.28, tail=1.35):
    if len(story["scenes"]) != len(clips):
        raise ValueError("Every scene must have exactly one speech clip.")
    t = lead
    scenes = []
    for item, clip in zip(story["scenes"], clips):
        duration = len(clip) / RATE
        if duration < 0.05:
            raise ValueError("Speech segment is empty.")
        scenes.append({**item, "start": round(t, 4),
                       "voice_duration": round(duration, 4),
                       "duration": round(duration + gap, 4)})
        t += duration + gap
    scenes[-1]["duration"] += tail
    return {"title": story["title"], "scenes": scenes,
            "duration": round(t + tail, 4)}


def _click(n):
    t = np.arange(n, dtype=np.float32) / RATE
    # Short, soft descending harmonic; generated in code, no third-party sample.
    envelope = np.exp(-54 * t)
    wave1 = np.sin(2 * np.pi * (960 * t - 210 * t * t))
    return 0.045 * envelope * wave1


def _sweep(n):
    t = np.arange(n, dtype=np.float32) / RATE
    phase = 2 * np.pi * (220 * t + 280 * t * t)
    envelope = np.sin(np.pi * np.clip(t / (n / RATE), 0, 1)) ** 2
    return 0.025 * envelope * np.sin(phase)


def write_mix(clips, schedule, target: Path):
    size = math.ceil(RATE * schedule["duration"])
    mixed = np.zeros(size, dtype=np.float32)
    for clip, scene in zip(clips, schedule["scenes"]):
        start = round(RATE * scene["start"])
        end = min(start + len(clip), size)
        mixed[start:end] += 0.85 * clip[:end - start]
        n = min(round(0.12 * RATE), size - start)
        if n:
            mixed[start:start + n] += _click(n)
    # One restrained transition accent before the final offer.
    offer_start = round(schedule["scenes"][-1]["start"] * RATE)
    n = min(round(0.30 * RATE), size - offer_start)
    if n:
        mixed[offer_start:offer_start + n] += _sweep(n)
    pcm = (np.clip(mixed, -0.96, 0.96) * 32767).astype("<i2")
    target.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(target), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(pcm.tobytes())
    return target
