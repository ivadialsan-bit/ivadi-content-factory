"""TTS adapters. Heavy engines are optional and isolated from the base install."""
import asyncio
import shutil
import subprocess
from pathlib import Path


def _ffmpeg():
    exe = shutil.which("ffmpeg")
    if not exe:
        raise RuntimeError("FFmpeg not found on PATH. Install FFmpeg first.")
    return exe


def _normalize(source: Path, target: Path):
    target.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [_ffmpeg(), "-hide_banner", "-loglevel", "error", "-y",
         "-i", str(source), "-ac", "1", "-ar", "48000",
         "-c:a", "pcm_s16le", str(target)],
        check=True,
    )


class Voice:
    def __init__(self, engine: str, device: str = "cuda", source_dir=None):
        self.engine = engine
        self.source_dir = Path(source_dir) if source_dir else None
        self.device = device
        self.model = None
        if engine in ("qwen", "chatterbox"):
            try:
                import torch
            except ImportError as exc:
                raise RuntimeError("Install optional voice dependencies in a dedicated venv.") from exc
            if device == "cuda" and not torch.cuda.is_available():
                raise RuntimeError("CUDA GPU unavailable. Use --device cpu explicitly (slow and memory-intensive), or --engine edge.")
            if engine == "qwen":
                from qwen_tts import Qwen3TTSModel
                self.model = Qwen3TTSModel.from_pretrained(
                    "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign",
                    device_map="cuda:0" if device == "cuda" else "cpu",
                    dtype=torch.float16 if device == "cuda" else torch.float32,
                    attn_implementation="sdpa",
                )
            else:
                from chatterbox.mtl_tts import ChatterboxMultilingualTTS
                self.model = ChatterboxMultilingualTTS.from_pretrained(
                    device=device, t3_model="v3"
                )
        elif engine not in ("edge", "external"):
            raise ValueError("Engine must be edge, qwen, chatterbox or external")

    def synthesize(self, text: str, number: int, target: Path):
        target = Path(target)
        temp = target.with_suffix(".raw.wav")
        if self.engine == "external":
            if not self.source_dir:
                raise ValueError("--external-dir is required for external audio.")
            source = self.source_dir / f"{number:02d}.wav"
            if not source.is_file():
                raise FileNotFoundError(f"Missing speech clip: {source}")
            _normalize(source, target)
            return

        if self.engine == "edge":
            try:
                import edge_tts
            except ImportError as exc:
                raise RuntimeError("Install edge-tts in the current environment.") from exc
            mp3 = target.with_suffix(".mp3")
            async def save():
                communicator = edge_tts.Communicate(
                    text, voice="ru-RU-SvetlanaNeural", rate="-8%"
                )
                await communicator.save(str(mp3))
            asyncio.run(save())
            try:
                _normalize(mp3, target)
            finally:
                mp3.unlink(missing_ok=True)
            return

        if self.engine == "qwen":
            import soundfile as sf
            wavs, rate = self.model.generate_voice_design(
                text=text, language="Russian",
                instruct="Женский голос, спокойный, живой, ясная русская дикция. "
                         "Естественная речь с короткими смысловыми паузами, без рекламы на повышенных тонах."
            )
            sf.write(str(temp), wavs[0], rate)
        else:
            import torchaudio
            speech = self.model.generate(text, language_id="ru")
            torchaudio.save(str(temp), speech.cpu(), self.model.sr)

        try:
            _normalize(temp, target)
        finally:
            temp.unlink(missing_ok=True)
