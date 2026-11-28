#!/usr/bin/env python3
"""Technical QA for FrameForge MP4 exports using FFprobe and FFmpeg."""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, capture_output=True, text=True, check=False)


def parse_rate(value: str | None) -> float | None:
    if not value or value in {"0/0", "N/A"}:
        return None
    try:
        numerator, denominator = value.split("/", 1)
        denominator_value = float(denominator)
        return float(numerator) / denominator_value if denominator_value else None
    except (ValueError, ZeroDivisionError):
        return None


def seconds(value: Any) -> float | None:
    try:
        result = float(value)
        return result if result >= 0 else None
    except (TypeError, ValueError):
        return None


def probe_media(path: str | Path, ffprobe: str = "ffprobe") -> dict[str, Any]:
    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(f"Video file does not exist: {source}")
    if not shutil.which(ffprobe):
        raise RuntimeError(f"Could not find {ffprobe!r} on PATH.")
    result = run([
        ffprobe, "-v", "error", "-count_frames", "-show_streams", "-show_format",
        "-of", "json", str(source),
    ])
    if result.returncode:
        raise RuntimeError("ffprobe failed: " + result.stderr[-3000:])
    return json.loads(result.stdout)


def detect_black_freeze_audio(
    path: str | Path,
    *,
    ffmpeg: str = "ffmpeg",
    black_duration: float = 0.5,
    freeze_duration: float = 2.0,
) -> dict[str, Any]:
    filters = f"blackdetect=d={black_duration}:pix_th=0.10,freezedetect=n=-60dB:d={freeze_duration}"
    command = [ffmpeg, "-hide_banner", "-nostdin", "-i", str(path), "-vf", filters]
    probe = probe_media(path)
    has_audio = any(stream.get("codec_type") == "audio" for stream in probe.get("streams", []))
    if has_audio:
        command.extend(["-af", "volumedetect"])
    command.extend(["-f", "null", "-"])
    result = run(command)
    log = result.stderr
    if result.returncode:
        raise RuntimeError("FFmpeg decode/analysis failed: " + log[-4000:])
    black = []
    for match in re.finditer(r"black_start:([-\d.]+)\s+black_end:([-\d.]+|N/A)\s+black_duration:([-\d.]+)", log):
        black.append({
            "start_seconds": float(match.group(1)),
            "end_seconds": seconds(match.group(2)),
            "duration_seconds": float(match.group(3)),
        })
    freezes = []
    starts = [float(value) for value in re.findall(r"freeze_start:\s*([-\d.]+)", log)]
    durations = [float(value) for value in re.findall(r"freeze_duration:\s*([-\d.]+)", log)]
    for index, start in enumerate(starts):
        duration = durations[index] if index < len(durations) else None
        freezes.append({"start_seconds": start, "duration_seconds": duration})
    peak_match = re.search(r"max_volume:\s*([-\d.]+|-\s*inf)\s*dB", log)
    mean_match = re.search(r"mean_volume:\s*([-\d.]+|-\s*inf)\s*dB", log)
    return {
        "black_segments": black,
        "freeze_segments": freezes,
        "audio_peak_dbfs": None if not peak_match or "inf" in peak_match.group(1) else float(peak_match.group(1).replace(" ", "")),
        "audio_mean_dbfs": None if not mean_match or "inf" in mean_match.group(1) else float(mean_match.group(1).replace(" ", "")),
        "analysis_log_tail": log[-1200:],
    }


def load_expected(path: str | Path | None) -> dict[str, Any]:
    if not path:
        return {}
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if data.get("format") == "frameforge-render-frames":
        return {
            "width": data.get("width"),
            "height": data.get("height"),
            "fps": data.get("fps"),
            "frame_count": data.get("total_frames"),
        }
    return data


def qa_video(
    path: str | Path,
    *,
    ffmpeg: str = "ffmpeg",
    ffprobe: str = "ffprobe",
    expected: dict[str, Any] | None = None,
    expect_audio: bool = False,
    black_min_duration: float = 0.5,
    freeze_min_duration: float = 2.0,
    strict_freeze: bool = False,
    sync_markers_path: str | Path | None = None,
) -> dict[str, Any]:
    expected = expected or {}
    source = Path(path)
    info = probe_media(source, ffprobe)
    videos = [stream for stream in info.get("streams", []) if stream.get("codec_type") == "video"]
    audios = [stream for stream in info.get("streams", []) if stream.get("codec_type") == "audio"]
    errors: list[str] = []
    warnings: list[str] = []
    checks: dict[str, Any] = {}

    if not videos:
        errors.append("No video stream is present.")
        video = {}
    else:
        video = videos[0]
    duration = seconds(video.get("duration")) or seconds(info.get("format", {}).get("duration"))
    fps = parse_rate(video.get("avg_frame_rate")) or parse_rate(video.get("r_frame_rate"))
    frames = int(video.get("nb_read_frames") or video.get("nb_frames") or 0) if video else 0
    width = int(video.get("width") or 0) if video else 0
    height = int(video.get("height") or 0) if video else 0
    checks["stream_metadata"] = {
        "width": width, "height": height, "fps": fps, "frame_count": frames,
        "duration_seconds": duration, "video_codec": video.get("codec_name"),
        "audio_stream": bool(audios), "audio_codec": audios[0].get("codec_name") if audios else None,
        "file_size_bytes": source.stat().st_size,
        "file_size_mb": round(source.stat().st_size / (1024 * 1024), 2),
    }

    for key, actual in (("width", width), ("height", height), ("frame_count", frames)):
        target = expected.get(key)
        if target is not None and int(target) != actual:
            errors.append(f"Expected {key}={target}, but file contains {actual}.")
    target_fps = expected.get("fps")
    if target_fps is not None and (fps is None or abs(float(target_fps) - fps) > 0.02):
        errors.append(f"Expected {target_fps} FPS, but file reports {fps}.")
    if not duration or duration <= 0:
        errors.append("Video duration is missing or zero.")
    target_duration = expected.get("duration_seconds")
    if target_duration is not None and duration is not None and abs(float(target_duration) - duration) > max(0.1, 1 / (fps or 30) + 0.03):
        errors.append(f"Duration mismatch: expected {target_duration}s, got {duration}s.")
    if expect_audio and not audios:
        errors.append("An audio stream was expected but none is present.")
    if not expect_audio and not audios:
        warnings.append("Export contains no audio stream.")

    decoded = run([ffmpeg, "-hide_banner", "-nostdin", "-v", "error", "-i", str(source), "-f", "null", "-"])
    if decoded.returncode:
        errors.append("Full media decode failed: " + decoded.stderr[-1500:])
    checks["full_decode"] = {"passed": decoded.returncode == 0, "stderr_tail": decoded.stderr[-500:]}

    analysis = detect_black_freeze_audio(
        source, ffmpeg=ffmpeg, black_duration=black_min_duration, freeze_duration=freeze_min_duration
    )
    checks["black_segments"] = analysis["black_segments"]
    checks["freeze_segments"] = analysis["freeze_segments"]
    if analysis["black_segments"]:
        errors.append(f"Detected {len(analysis['black_segments'])} black segment(s) lasting at least {black_min_duration}s.")
    if analysis["freeze_segments"]:
        message = f"Detected {len(analysis['freeze_segments'])} possible frozen segment(s) lasting at least {freeze_min_duration}s."
        if strict_freeze:
            errors.append(message)
        else:
            warnings.append(message)
    if audios:
        checks["audio_levels"] = {
            "sample_peak_dbfs": analysis["audio_peak_dbfs"],
            "mean_dbfs": analysis["audio_mean_dbfs"],
        }
        peak = analysis["audio_peak_dbfs"]
        mean = analysis["audio_mean_dbfs"]
        if peak is not None and peak > -0.1:
            errors.append(f"Audio sample peak is too close to digital full scale ({peak} dBFS).")
        if mean is not None and mean < -60:
            warnings.append(f"Audio mean level is very low ({mean} dBFS).")

    if sync_markers_path:
        marker_data = json.loads(Path(sync_markers_path).read_text(encoding="utf-8"))
        markers = marker_data.get("markers", [])
        marker_results = []
        for marker in markers:
            video_frame = int(marker["video_frame"])
            audio_seconds = float(marker["audio_seconds"])
            video_seconds = video_frame / (fps or 30)
            delta = abs(video_seconds - audio_seconds)
            marker_results.append({
                "label": str(marker.get("label") or "marker"),
                "video_seconds": video_seconds,
                "declared_audio_seconds": audio_seconds,
                "delta_seconds": delta,
                "within_one_frame": delta <= 1 / (fps or 30) + 1e-6,
            })
            if delta > 1 / (fps or 30) + 1e-6:
                errors.append(f"Declared sync marker {marker.get('label', '')!r} differs by {delta:.3f}s.")
        checks["declared_sync_markers"] = {
            "markers": marker_results,
            "note": "Compares user-supplied video-frame and audio-time marker metadata; does not detect a sync tone in the media waveform.",
        }

    return {
        "format": "frameforge-technical-qa",
        "version": 1,
        "input": str(source),
        "passed": not errors,
        "errors": errors,
        "warnings": warnings,
        "checks": checks,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="MP4 or other FFmpeg-readable export.")
    parser.add_argument("--expected-manifest", help="Optional render-frames.json or expected metadata JSON.")
    parser.add_argument("--expect-audio", action="store_true")
    parser.add_argument("--expected-width", type=int)
    parser.add_argument("--expected-height", type=int)
    parser.add_argument("--expected-fps", type=float)
    parser.add_argument("--expected-frames", type=int)
    parser.add_argument("--expected-duration", type=float)
    parser.add_argument("--black-min-duration", type=float, default=0.5)
    parser.add_argument("--freeze-min-duration", type=float, default=2.0)
    parser.add_argument("--strict-freeze", action="store_true", help="Treat possible frozen holds as failures, not warnings.")
    parser.add_argument("--sync-markers", help="Optional JSON with markers: label, video_frame, audio_seconds.")
    parser.add_argument("--json-out", help="Write the QA JSON report to this path.")
    args = parser.parse_args(argv)
    try:
        expected = load_expected(args.expected_manifest)
        for key, value in (
            ("width", args.expected_width),
            ("height", args.expected_height),
            ("fps", args.expected_fps),
            ("frame_count", args.expected_frames),
            ("duration_seconds", args.expected_duration),
        ):
            if value is not None:
                expected[key] = value
        report = qa_video(
            args.input, expected=expected, expect_audio=args.expect_audio,
            black_min_duration=args.black_min_duration, freeze_min_duration=args.freeze_min_duration,
            strict_freeze=args.strict_freeze, sync_markers_path=args.sync_markers,
        )
    except Exception as error:
        print("ERROR: " + str(error), file=sys.stderr)
        return 1
    output = json.dumps(report, indent=2)
    print(output)
    if args.json_out:
        Path(args.json_out).write_text(output + "\n", encoding="utf-8")
    return 0 if report["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
