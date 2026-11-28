import shutil
import subprocess
import tempfile
import unittest
import wave
from pathlib import Path

from tools.mux_ffmpeg import build_ffmpeg_command, media_duration, mux_audio_to_video


class FFmpegMuxTests(unittest.TestCase):
    def test_build_command_maps_video_and_audio_and_sets_sync_targets(self):
        command = build_ffmpeg_command(
            "picture.mp4", "master.wav", "final.mp4", 12.345,
            video_codec="libx264", overwrite=True
        )
        self.assertEqual(command[0], "ffmpeg")
        self.assertIn("-y", command)
        self.assertEqual(command[command.index("-map") + 1], "0:v:0")
        self.assertEqual(command[command.index("-map", command.index("-map") + 1) + 1], "1:a:0")
        self.assertIn("loudnorm=I=-16.0:TP=-1.5:LRA=11.0", command[command.index("-af") + 1])
        self.assertIn("aresample=48000:async=1:first_pts=0,apad", command[command.index("-af") + 1])
        self.assertEqual(command[command.index("-ar") + 1], "48000")
        self.assertEqual(command[command.index("-ac") + 1], "2")
        self.assertEqual(command[command.index("-t") + 1], "12.345000")
        self.assertIn("libx264", command)

    def test_rejects_invalid_mux_options(self):
        with self.assertRaises(ValueError):
            build_ffmpeg_command("v.mp4", "a.wav", "o.mp4", 1, video_codec="vp9")
        with self.assertRaises(ValueError):
            build_ffmpeg_command("v.mp4", "a.wav", "o.mp4", 1, loudness_i=-6)
        with self.assertRaises(ValueError):
            build_ffmpeg_command("v.mp4", "a.wav", "o.mp4", 1, audio_bitrate="free")

    def test_media_duration_uses_video_stream_duration(self):
        probe = {
            "format": {"duration": "1.2"},
            "streams": [
                {"codec_type": "video", "duration": "1.0"},
                {"codec_type": "audio", "duration": "1.2"}
            ]
        }
        self.assertEqual(media_duration(probe, "video"), 1.0)
        self.assertEqual(media_duration(probe), 1.2)

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg is not installed")
    def test_end_to_end_mux_produces_synchronized_48khz_stereo_mp4(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            video = root / "silent-picture.mp4"
            audio = root / "audio-master.wav"
            output = root / "finished.mp4"

            subprocess.run([
                "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                "-f", "lavfi", "-i", "color=c=black:s=320x180:r=30:d=1",
                "-an", "-c:v", "mpeg4", "-pix_fmt", "yuv420p", str(video)
            ], check=True, capture_output=True)

            sample_rate = 48000
            samples = 48000
            with wave.open(str(audio), "wb") as wav:
                wav.setnchannels(2)
                wav.setsampwidth(2)
                wav.setframerate(sample_rate)
                frames = bytearray()
                for index in range(samples):
                    # Quiet, deterministic test tone; no external sample asset.
                    import math
                    value = int(3500 * math.sin(2 * math.pi * 440 * index / sample_rate))
                    frames.extend(value.to_bytes(2, "little", signed=True) * 2)
                wav.writeframes(frames)

            result = mux_audio_to_video(video, audio, output, video_codec="copy")
            self.assertTrue(output.is_file())
            self.assertGreater(result["size_bytes"], 1000)
            self.assertEqual(result["sample_rate"], 48000)
            self.assertEqual(result["channels"], 2)
            self.assertEqual(result["audio_codec"], "aac")
            self.assertAlmostEqual(result["duration_seconds"], 1.0, delta=0.1)


if __name__ == "__main__":
    unittest.main()
