"""FFmpeg streaming renderer: voice timeline -> animated MP4."""
import shutil
import subprocess
from pathlib import Path
from .graphics import frame


def render_video(schedule, sound_file, target, *, preview=False, font_file=None):
    exe = shutil.which("ffmpeg")
    if not exe:
        raise RuntimeError("ffmpeg executable is not on PATH.")
    width, height, fps = (540, 960, 15) if preview else (1080, 1920, 30)
    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    command = [
        exe, "-hide_banner", "-loglevel", "error", "-y",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s:v", f"{width}x{height}",
        "-r", str(fps), "-i", "pipe:0", "-i", str(sound_file),
        "-c:v", "libx264", "-preset", "veryfast" if preview else "medium",
        "-crf", "25" if preview else "19", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        "-af", "loudnorm=I=-16:TP=-1.5:LRA=7",
        "-movflags", "+faststart", "-shortest", str(target),
    ]
    process = subprocess.Popen(command, stdin=subprocess.PIPE,
                               stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    try:
        frames = round(schedule["duration"] * fps)
        for i in range(frames):
            picture = frame(schedule, i / fps, width, height, font_file)
            process.stdin.write(picture.tobytes())
        process.stdin.close()
        errors = process.stderr.read().decode("utf-8", "replace")
        if process.wait() != 0:
            raise RuntimeError(f"ffmpeg render failed: {errors[-1800:]}")
    except Exception:
        if process.stdin and not process.stdin.closed:
            process.stdin.close()
        process.kill()
        process.wait()
        raise
    return target
