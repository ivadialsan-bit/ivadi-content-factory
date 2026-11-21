"""CI-only MP4 render with synthetic audio; not a quality test of any TTS voice."""
import json
import shutil
import subprocess
import tempfile
from pathlib import Path
import numpy as np
from reels_lab.audio import RATE, timeline, write_mix
from reels_lab.render import render_video


def main():
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise RuntimeError("FFmpeg and FFprobe are required for MP4 smoke test.")
    story = json.loads(Path(__file__).resolve().parents[1].joinpath(
        "story_890.json").read_text(encoding="utf-8"))
    clips = [np.zeros(round(RATE * 0.45), dtype=np.float32)
             for _ in story["scenes"]]
    schedule = timeline(story, clips)
    with tempfile.TemporaryDirectory(prefix="reels_smoke_") as temporary:
        root = Path(temporary)
        sound = write_mix(clips, schedule, root / "test.wav")
        output = Path("reels_lab/out/ci_synthetic_no_voice.mp4")
        render_video(schedule, sound, output, preview=True)
        result = subprocess.run([
            "ffprobe", "-v", "error", "-show_entries",
            "format=duration:stream=codec_name,width,height",
            "-of", "json", str(output)
        ], capture_output=True, text=True, check=True)
        video = json.loads(result.stdout)
        duration = float(video["format"]["duration"])
        assert abs(duration - schedule["duration"]) < 0.25
        assert any(stream.get("codec_name") == "h264" and
                   stream.get("width") == 540 and stream.get("height") == 960
                   for stream in video["streams"])
        print(f"MP4 SMOKE OK: {output} duration={duration:.2f}s; voice not tested")


if __name__ == "__main__":
    main()
