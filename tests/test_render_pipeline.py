from __future__ import annotations

import json
import shutil
import struct
import subprocess
import tempfile
import unittest
import wave
import zlib
import zipfile
from pathlib import Path

from tools.merge_render_chunks import merge_chunks, png_dimensions
from tools.export_ffmpeg import PROFILES, build_command, encode_sequence
from tools.qa_render import qa_video
from tools.create_review import create_review
from tools.package_delivery import build_delivery_package


def make_png(width: int, height: int, color: tuple[int, int, int]) -> bytes:
    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xffffffff)
    raw = b"".join(b"\x00" + bytes(color) * width for _ in range(height))
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw))
        + chunk(b"IEND", b"")
    )


def write_chunk(
    path: Path,
    *,
    job_id: str = "job-1",
    chunk_index: int = 0,
    start: int = 0,
    end: int = 2,
    total: int = 4,
    width: int = 32,
    height: int = 18,
    fps: int = 30,
    colors: list[tuple[int, int, int]] | None = None,
) -> None:
    colors = colors or [(20 + start, 80, 160), (30 + start, 100, 180)]
    manifest = {
        "format": "frameforge-render-chunk",
        "version": 1,
        "job_id": job_id,
        "project_id": "project-1",
        "project_signature": "sig-1",
        "chunk_index": chunk_index,
        "start_frame": start,
        "end_frame_exclusive": end,
        "total_frames": total,
        "chunk_count": 2,
        "width": width,
        "height": height,
        "fps": fps,
        "frame_count": end - start,
    }
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_STORED) as archive:
        archive.writestr("chunk-manifest.json", json.dumps(manifest))
        for frame, color in zip(range(start, end), colors, strict=True):
            archive.writestr(f"frames/frame_{frame:06d}.png", make_png(width, height, color))


def make_v2_project(path: Path) -> dict:
    project = {
        "format": "frameforge-project",
        "schema_version": 2,
        "project": {
            "id": "project-1",
            "name": "Test delivery",
            "created_at": "2026-11-28T00:00:00Z",
            "updated_at": "2026-11-28T00:01:00Z",
        },
        "settings": {"width": 1280, "height": 720, "fps": 30, "color_space": "srgb"},
        "assets": [
            {
                "id": "asset-approved",
                "uri": "local:approved.png",
                "media_type": "image",
                "label": "Approved diagram",
                "provenance": {
                    "source_type": "procedural",
                    "source_title": "Original diagram",
                    "creator": "Project owner",
                },
                "rights": {
                    "status": "approved",
                    "attribution_required": False,
                    "review_basis": "Original artwork created for this project.",
                    "reviewed_by": "Project owner",
                    "reviewed_at": "2026-11-28T00:00:00Z",
                    "restrictions": [],
                },
            },
            {
                "id": "asset-pending",
                "uri": "local:unknown.wav",
                "media_type": "audio",
                "label": "Unreviewed sound",
                "provenance": {"source_type": "unknown"},
                "rights": {
                    "status": "pending",
                    "attribution_required": True,
                    "license_name": "Unverified",
                },
            },
        ],
        "sequences": [
            {
                "id": "sequence-1",
                "name": "Main",
                "width": 1280,
                "height": 720,
                "fps": 30,
                "duration_frames": 1,
                "tracks": [],
            }
        ],
    }
    path.write_text(json.dumps(project, indent=2), encoding="utf-8")
    return project


class RenderQueueMergeTests(unittest.TestCase):
    def test_chunk_merge_is_resumable_and_skips_identical_reimports(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            first = root / "chunk-0001.zip"
            second = root / "chunk-0002.zip"
            write_chunk(first, chunk_index=0, start=0, end=2, total=4)
            write_chunk(second, chunk_index=1, start=2, end=4, total=4)
            output = root / "frames"

            initial = merge_chunks([first], output)
            self.assertEqual(initial["added_frames"], 2)
            self.assertFalse(initial["complete"])
            resumed = merge_chunks([second], output)
            self.assertEqual(resumed["added_frames"], 2)
            self.assertEqual(resumed["frame_count"], 4)
            self.assertEqual(resumed["missing_frames"], 0)
            self.assertTrue(resumed["complete"])

            repeated = merge_chunks([first, second], output)
            self.assertEqual(repeated["added_frames"], 0)
            self.assertEqual(repeated["skipped_frames"], 4)
            self.assertTrue(repeated["complete"])
            for frame in range(4):
                self.assertEqual(png_dimensions((output / "frames" / f"frame_{frame:06d}.png").read_bytes()), (32, 18))

    def test_chunk_merge_rejects_conflicting_duplicate_frames(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            one = root / "one.zip"
            two = root / "two.zip"
            write_chunk(one, chunk_index=0, start=0, end=2, total=4)
            write_chunk(two, chunk_index=1, start=0, end=2, total=4, colors=[(255, 0, 0), (0, 255, 0)])
            output = root / "frames"
            merge_chunks([one], output)
            with self.assertRaisesRegex(ValueError, "different content"):
                merge_chunks([two], output)

    def test_chunk_merge_rejects_inconsistent_render_signature(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            one = root / "one.zip"
            two = root / "two.zip"
            write_chunk(one, chunk_index=0, start=0, end=2, total=4)
            write_chunk(two, chunk_index=1, start=2, end=4, total=4, job_id="different-job")
            with self.assertRaisesRegex(ValueError, "job_id"):
                merge_chunks([one, two], root / "frames")

    def test_chunk_merge_rejects_traversal_entries(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "bad.zip"
            manifest = {
                "format": "frameforge-render-chunk", "version": 1,
                "job_id": "job-1", "project_id": "project-1", "project_signature": "sig-1",
                "chunk_index": 0, "start_frame": 0, "end_frame_exclusive": 1, "total_frames": 1,
                "width": 32, "height": 18, "fps": 30, "frame_count": 1,
            }
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("chunk-manifest.json", json.dumps(manifest))
                archive.writestr("../escape.txt", "no")
            with self.assertRaisesRegex(ValueError, "unsafe archive path"):
                merge_chunks([path], Path(temp) / "frames")


class ExportProfileTests(unittest.TestCase):
    def test_profiles_are_explicit_and_vertical_and_horizontal(self) -> None:
        self.assertEqual(PROFILES["720p-horizontal"], (1280, 720))
        self.assertEqual(PROFILES["720p-vertical"], (720, 1280))
        command = build_command("frames", "out.mp4", 90, profile="720p-vertical", fps=30)
        self.assertIn("scale=720:1280:force_original_aspect_ratio=decrease:flags=lanczos,pad=720:1280", command)
        self.assertIn("-frames:v", command)
        with self.assertRaises(ValueError):
            build_command("frames", "out.mp4", 90, profile="4k")

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg is not installed")
    def test_export_encodes_frames_audio_and_verifies_output_streams(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            frame_dir = root / "frames"
            frame_dir.mkdir()
            for frame in range(12):
                color = (20 + frame * 12, 40 + frame * 6, 120 + frame * 4)
                (frame_dir / f"frame_{frame:06d}.png").write_bytes(make_png(160, 90, color))
            state = {
                "format": "frameforge-render-frames",
                "complete": True,
                "width": 160, "height": 90, "fps": 30,
                "total_frames": 12, "missing_frames": [],
            }
            (root / "render-frames.json").write_text(json.dumps(state), encoding="utf-8")
            audio = root / "tone.wav"
            sample_rate = 48000
            sample_count = 19200
            import math
            with wave.open(str(audio), "wb") as output:
                output.setnchannels(2)
                output.setsampwidth(2)
                output.setframerate(sample_rate)
                samples = bytearray()
                for index in range(sample_count):
                    value = int(3500 * math.sin(2 * math.pi * 440 * index / sample_rate))
                    samples.extend(value.to_bytes(2, "little", signed=True) * 2)
                output.writeframes(samples)
            mp4 = root / "final.mp4"
            report = encode_sequence(frame_dir, mp4, audio=audio, profile="720p-horizontal", crf=25, preset="ultrafast")
            self.assertTrue(mp4.is_file())
            self.assertEqual(report["width"], 1280)
            self.assertEqual(report["height"], 720)
            self.assertEqual(report["fps"], 30)
            self.assertEqual(report["frame_count"], 12)
            self.assertTrue(report["audio_stream"])
            self.assertGreater(report["size_mb"], 0)


class TechnicalQATests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg is not installed")
    def test_known_good_dynamic_video_passes_metadata_and_decode_qa(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            video = Path(temp) / "good.mp4"
            subprocess.run([
                "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                "-f", "lavfi", "-i", "testsrc2=size=320x180:rate=30:duration=1.2",
                "-c:v", "libx264", "-pix_fmt", "yuv420p", str(video),
            ], check=True, capture_output=True)
            result = qa_video(video, expected={
                "width": 320, "height": 180, "fps": 30, "frame_count": 36,
            })
            self.assertTrue(result["passed"], result["errors"])
            self.assertTrue(result["checks"]["full_decode"]["passed"])
            self.assertEqual(result["checks"]["black_segments"], [])

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg is not installed")
    def test_known_bad_black_video_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            video = Path(temp) / "black.mp4"
            subprocess.run([
                "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                "-f", "lavfi", "-i", "color=c=black:s=320x180:r=30:d=1",
                "-c:v", "libx264", "-pix_fmt", "yuv420p", str(video),
            ], check=True, capture_output=True)
            result = qa_video(video, black_min_duration=0.4)
            self.assertFalse(result["passed"])
            self.assertTrue(any("black segment" in error for error in result["errors"]))

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg is not installed")
    def test_expected_audio_flag_catches_missing_audio_stream(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            video = Path(temp) / "silent.mp4"
            subprocess.run([
                "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                "-f", "lavfi", "-i", "testsrc2=size=320x180:rate=30:duration=1",
                "-c:v", "libx264", "-pix_fmt", "yuv420p", str(video),
            ], check=True, capture_output=True)
            result = qa_video(video, expect_audio=True)
            self.assertFalse(result["passed"])
            self.assertTrue(any("audio stream was expected" in error for error in result["errors"]))


class ReviewAndPackageTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg is not installed")
    def test_review_tool_builds_contact_sheet_html_and_review_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            video = root / "review.mp4"
            subprocess.run([
                "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                "-f", "lavfi", "-i", "testsrc2=size=320x180:rate=30:duration=3",
                "-c:v", "libx264", "-pix_fmt", "yuv420p", str(video),
            ], check=True, capture_output=True)
            output = root / "review"
            report = create_review(video, output, sample_interval=1, max_scene_previews=5)
            self.assertTrue((output / "contact-sheet.jpg").is_file())
            self.assertTrue((output / "review.html").is_file())
            self.assertTrue((output / "review.json").is_file())
            self.assertEqual(report["media"]["width"], 320)
            self.assertTrue(report["human_review_required"])

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg is not installed")
    def test_delivery_package_contains_media_project_manifest_and_rights_notes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            video = root / "final.mp4"
            subprocess.run([
                "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                "-f", "lavfi", "-i", "testsrc2=size=320x180:rate=30:duration=1",
                "-c:v", "libx264", "-pix_fmt", "yuv420p", str(video),
            ], check=True, capture_output=True)
            project_path = root / "project.json"
            project = make_v2_project(project_path)
            output = root / "delivery.zip"
            report = build_delivery_package(video, project_path, output)
            self.assertTrue(output.is_file())
            self.assertGreater(report["final_media"]["size_mb"], 0)
            self.assertEqual(report["asset_count"], 2)
            self.assertGreaterEqual(report["rights_warnings"], 1)
            with zipfile.ZipFile(output) as archive:
                names = set(archive.namelist())
                self.assertIn("delivery/final.mp4", names)
                self.assertIn("project/project.json", names)
                self.assertIn("project/asset_manifest.json", names)
                self.assertIn("attribution.txt", names)
                self.assertIn("render_report.json", names)
                attribution = archive.read("attribution.txt").decode()
                self.assertIn("PENDING / UNRESOLVED ITEMS", attribution)
                self.assertIn("Unreviewed sound", attribution)


if __name__ == "__main__":
    unittest.main()
