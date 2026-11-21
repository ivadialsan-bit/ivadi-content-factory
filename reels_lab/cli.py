"""Run from repository root: python -m reels_lab.cli --engine edge."""
import argparse
import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from .audio import read_mono_pcm, timeline, write_mix
from .voice import Voice
from .render import render_video


def ffprobe(path):
    exe = shutil.which("ffprobe")
    if not exe:
        raise RuntimeError("ffprobe executable is not on PATH.")
    result = subprocess.run(
        [exe, "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True, check=True)
    return float(result.stdout.strip())


def main(argv=None):
    p = argparse.ArgumentParser(description="Free code-only Reels pipeline")
    p.add_argument("--engine", choices=("edge", "qwen", "chatterbox", "external"), default="edge")
    p.add_argument("--device", choices=("cuda", "cpu", "mps"), default="cuda")
    p.add_argument("--external-dir", type=Path)
    p.add_argument("--story", type=Path, default=Path(__file__).with_name("story_890.json"))
    p.add_argument("--font", type=Path)
    p.add_argument("--output", type=Path, default=Path("reels_lab/out/reels_890.mp4"))
    p.add_argument("--preview", action="store_true")
    p.add_argument("--dry-run", action="store_true", help="Check config only, no voice or render")
    args = p.parse_args(argv)
    story = json.loads(args.story.read_text(encoding="utf-8"))
    if not story.get("scenes") or any(not s.get("spoken") or not s.get("headline") for s in story["scenes"]):
        raise ValueError("Invalid storyboard; each scene needs spoken and headline.")
    if args.dry_run:
        print(json.dumps({"valid": True, "scenes": len(story["scenes"]),
                          "engine": args.engine, "offer_status": story.get("offer_status")},
                         ensure_ascii=False))
        return
    with tempfile.TemporaryDirectory(prefix="reels_voice_") as name:
        workspace = Path(name)
        voice = Voice(args.engine, args.device, args.external_dir)
        segment_files = []
        for number, scene in enumerate(story["scenes"], start=1):
            path = workspace / f"{number:02d}.wav"
            voice.synthesize(scene["spoken"], number, path)
            segment_files.append(path)
        clips = [read_mono_pcm(path) for path in segment_files]
        schedule = timeline(story, clips)
        sound_file = write_mix(clips, schedule, workspace / "sound.wav")
        output = render_video(schedule, sound_file, args.output,
                              preview=args.preview,
                              font_file=str(args.font) if args.font else None)
        verified_duration = ffprobe(output)
        if abs(verified_duration - schedule["duration"]) > 0.25:
            raise RuntimeError("MP4 duration differs from scheduled timeline.")
        report = {"rendered": True, "file": str(output), "engine": args.engine,
                  "duration": verified_duration, "scenes": schedule["scenes"],
                  "preview": args.preview, "voice_tested_by_human": False,
                  "offer_status": story.get("offer_status")}
        report_file = output.with_suffix(".report.json")
        report_file.write_text(json.dumps(report, ensure_ascii=False, indent=2),
                               encoding="utf-8")
        print(json.dumps({"output": str(output), "duration": verified_duration,
                          "report": str(report_file)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
