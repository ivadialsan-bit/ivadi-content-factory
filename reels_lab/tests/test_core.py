import tempfile
import unittest
import wave
from pathlib import Path
import numpy as np
from reels_lab.audio import RATE, read_mono_pcm, timeline, write_mix
from reels_lab.graphics import frame


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.story = {"title": "Test", "scenes": [
            {"type": "hook", "headline": "ИИ ПИШЕТ ВОДУ?", "spoken": "One", "label": "Test"},
            {"type": "offer", "headline": "30 РАБОЧИХ ПРОМПТОВ", "spoken": "Two", "label": "Test"}
        ]}
        self.clips = [np.zeros(RATE // 3, dtype=np.float32),
                      np.zeros(RATE // 2, dtype=np.float32)]

    def test_monotonic_timing(self):
        t = timeline(self.story, self.clips)
        self.assertEqual(len(t["scenes"]), 2)
        self.assertGreater(t["scenes"][1]["start"], t["scenes"][0]["start"])
        self.assertGreater(t["duration"], sum(len(c)/RATE for c in self.clips))

    def test_audio_output_properties(self):
        t = timeline(self.story, self.clips)
        with tempfile.TemporaryDirectory() as td:
            dest = write_mix(self.clips, t, Path(td) / "mixed.wav")
            with wave.open(str(dest), "rb") as wav:
                self.assertEqual(wav.getframerate(), RATE)
                self.assertEqual(wav.getnchannels(), 1)
                self.assertAlmostEqual(wav.getnframes()/RATE, t["duration"], delta=0.01)
            actual = read_mono_pcm(dest)
            self.assertEqual(actual.ndim, 1)
            self.assertLessEqual(float(np.max(np.abs(actual))), 0.961)

    def test_frame_size(self):
        t = timeline(self.story, self.clips)
        picture = frame(t, 0.5, 360, 640)
        self.assertEqual(picture.size, (360, 640))
        self.assertNotEqual(picture.getpixel((0, 0)), picture.getpixel((180, 480)))


if __name__ == "__main__":
    unittest.main()
