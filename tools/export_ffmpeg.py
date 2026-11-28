#!/usr/bin/env python3
"""Encode a merged FrameForge PNG sequence to MP4 using a zero-cost FFmpeg profile."""
from __future__ import annotations

import argparse
import json
import math
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

PROFILES: dict[str, tuple[int, int]] = {
    "720p-horizontal": (1280, 720),
    "720p-vertical": (720, 1280),
    "1080p-horizontal": (1920, 1080),
    "1080p-vertical": (1080, 1920),
}
ALLOWED_FPS = (24, 25, 30, 50, 60)


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, capture_output=True, text=True, check=False)


def probe(path: str | Path, ffprobe: str = "ffprobe") -> dict[str, Any]:
    if not shutil.which(ffprobe):
        raise RuntimeError(f"Could not find {ffprobe!r} on PATH. Install FFmpeg/ffprobe first.")
    result = run([
        ffprobe, "-v", "error", "-count_frames",
        "-show_entries",
        "format=duration,format_name,size:stream=codec_type,codec_name,width,height,pix_fmt,avg_frame_rate,r_frame_rate,nb_read_frames,sample_rate,channels",
        "-of", "json", str(path),
    ])
    if result.returncode:
        raise RuntimeError("ffprobe failed: " + result.stderr[-3000:])
    return json.loads(result.stdout)


def parse_rate(value: str | None) -> float | None:
    if not value or value in {"0/0", "N/A"}:
        return None
    try:
        numerator, denominator = value.split("/", 1)
        den = float(denominator)
        return float(numerator) / den if den else None
    except (ValueError, ZeroDivisionError):
        return None


def build_command(
    frames_dir: str | Path,
    output: str | Path,
    total_frames: int,
    *,
    profile: str = "720p-horizontal",
    fps: int = 30,
    audio: str | Path | None = None,
    crf: int = 18,
    preset: str = "medium",
    audio_bitrate: str = "192k",
    ffmpeg: str = "ffmpeg",
    overwrite: bool = False,
) -> list[str]:
    if profile not in PROFILES:
        raise ValueError(f"Unknown export profile {profile!r}.")
    if fps not in ALLOWED_FPS:
        raise ValueError(f"FPS must be one of {', '.join(map(str, ALLOWED_FPS))}.")
    if not (1 <= total_frames <= 2_000_000):
        raise ValueError("Frame count must be between 1 and 2,000,000.")
    if not (0 <= crf <= 35):
        raise ValueError("CRF must be between 0 and 35.")
    if preset not in {"ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow"}:
        raise ValueError("Unsupported x264 preset.")
    if not (64 <= int(audio_bitrate[:-1]) <= 512 and audio_bitrate.endswith("k")):
        raise ValueError("Audio bitrate must be between 64k and 512k.")
    width, height = PROFILES[profile]
    command = [ffmpeg, "-hide_banner", "-nostdin"]
    command.append("-y" if overwrite else "-n")
    command.extend([
        "-framerate", str(fps),
        "-start_number", "0",
        "-i", str(Path(frames_dir) / "frame_%06d.png"),
    ])
    if audio is not None:
        command.extend(["-i", str(audio)])
    command.extend([
        "-map", "0:v:0",
        "-vf", f"scale={width}:{height}:force_original_aspect_ratio=decrease:flags=lanczos,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1",
        "-r", str(fps),
        "-fps_mode", "cfr",
        "-frames:v", str(total_frames),
        "-c:v", "libx264",
        "-preset", preset,
        "-crf", str(crf),
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
    ])
    if audio is not None:
        command.extend([
            "-map", "1:a:0",
            "-af", "aresample=48000:async=1:first_pts=0,apad",
            "-c:a", "aac",
            "-b:a", audio_bitrate,
            "-ar", "48000",
            "-ac", "2",
        ])
    else:
        command.append("-an")
    command.extend(["-t", f"{total_frames / fps:.9f}", str(output)])
    return command


def encode_sequence(
    frames_dir: str | Path,
    output: str | Path,
    *,
    manifest_path: str | Path | None = None,
    profile: str = "720p-horizontal",
    fps: int | None = None,
    audio: str | Path | None = None,
    crf: int = 18,
    preset: str = "medium",
    audio_bitrate: str = "192k",
    ffmpeg: str = "ffmpeg",
    ffprobe: str = "ffprobe",
    overwrite: bool = False,
) -> dict[str, Any]:
    directory = Path(frames_dir)
    if not directory.is_dir():
        raise FileNotFoundError(f"Frame directory does not exist: {directory}")
    state_file = Path(manifest_path) if manifest_path else directory.parent / "render-frames.json"
    if not state_file.is_file():
        raise FileNotFoundError(f"Render manifest does not exist: {state_file}")
    state = json.loads(state_file.read_text(encoding="utf-8"))
    if state.get("format") != "frameforge-render-frames" or state.get("complete") is not True:
        raise RuntimeError("The render frame manifest is not complete. Merge all frame chunks first.")
    total = int(state.get("total_frames") or 0)
    missing = state.get("missing_frames") or []
    if missing:
        raise RuntimeError(f"The render frame manifest has {len(missing)} missing frames.")
    selected_fps = int(fps or round(float(state.get("fps") or 30)))
    if selected_fps not in ALLOWED_FPS:
        raise ValueError("Selected project FPS must be 24, 25, 30, 50 or 60.")
    expected_size = (int(state.get("width") or 0), int(state.get("height") or 0))
    for frame in range(total):
        path = directory / f"frame_{frame:06d}.png"
        if not path.is_file() or path.stat().st_size < 24:
            raise RuntimeError(f"Frame {frame} is missing or empty: {path}")
        header = path.read_bytes()[:24]
        if header[:8] != b"\x89PNG\r\n\x1a\n" or header[12:16] != b"IHDR":
            raise RuntimeError(f"Frame {frame} is not a valid PNG.")
        dimensions = (int.from_bytes(header[16:20], "big"), int.from_bytes(header[20:24], "big"))
        if dimensions != expected_size:
            raise RuntimeError(f"Frame {frame} has dimensions {dimensions}; expected {expected_size}.")
    if audio is not None and not Path(audio).is_file():
        raise FileNotFoundError(f"Audio master does not exist: {audio}")
    destination = Path(output)
    if destination.exists() and not overwrite:
        raise FileExistsError(f"Output already exists: {destination}. Pass --overwrite to replace it.")
    if not shutil.which(ffmpeg):
        raise RuntimeError(f"Could not find {ffmpeg!r} on PATH.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    command = build_command(
        directory, destination, total, profile=profile, fps=selected_fps,
        audio=audio, crf=crf, preset=preset, audio_bitrate=audio_bitrate,
        ffmpeg=ffmpeg, overwrite=overwrite,
    )
    result = run(command)
    if result.returncode:
        raise RuntimeError("FFmpeg export failed: " + result.stderr[-5000:])
    if not destination.is_file() or destination.stat().st_size == 0:
        raise RuntimeError("FFmpeg completed without producing a non-empty MP4.")
    output_probe = probe(destination, ffprobe)
    videos = [item for item in output_probe.get("streams", []) if item.get("codec_type") == "video"]
    audios = [item for item in output_probe.get("streams", []) if item.get("codec_type") == "audio"]
    if not videos:
        raise RuntimeError("Encoded MP4 has no video stream.")
    video = videos[0]
    width, height = PROFILES[profile]
    actual_fps = parse_rate(video.get("avg_frame_rate"))
    actual_frames = int(video.get("nb_read_frames") or 0)
    if int(video.get("width") or 0) != width or int(video.get("height") or 0) != height:
        raise RuntimeError("Encoded video dimensions do not match the selected export profile.")
    if actual_fps is None or abs(actual_fps - selected_fps) > 0.01:
        raise RuntimeError(f"Encoded frame rate does not match {selected_fps} FPS.")
    if actual_frames != total:
        raise RuntimeError(f"Encoded frame count mismatch: expected {total}, got {actual_frames}.")
    if audio is not None and not audios:
        raise RuntimeError("An audio input was supplied, but the MP4 has no audio stream.")
    if audio is None and audios:
        raise RuntimeError("Silent export unexpectedly contains an audio stream.")
    duration = float(output_probe.get("format", {}).get("duration") or total / selected_fps)
    return {
        "output": str(destination),
        "profile": profile,
        "width": width,
        "height": height,
        "fps": selected_fps,
        "frame_count": actual_frames,
        "duration_seconds": duration,
        "video_codec": video.get("codec_name"),
        "audio_codec": audios[0].get("codec_name") if audios else None,
        "audio_stream": bool(audios),
        "size_bytes": destination.stat().st_size,
        "size_mb": round(destination.stat().st_size / (1024 * 1024), 2),
        "ffmpeg_command": command,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frames-dir", required=True, help="Directory containing frame_000000.png, frame_000001.png, …")
    parser.add_argument("--output", required=True, help="Output MP4 path.")
    parser.add_argument("--profile", choices=tuple(PROFILES), default="720p-horizontal")
    parser.add_argument("--fps", type=int, choices=ALLOWED_FPS, help="Override the project FPS.")
    parser.add_argument("--audio", help="Optional FrameForge WAV master.")
    parser.add_argument("--crf", type=int, default=18, help="H.264 quality value, 0–35 (lower is larger/higher quality).")
    parser.add_argument("--preset", choices=("ultrafast","superfast","veryfast","faster","fast","medium","slow"), default="medium")
    parser.add_argument("--audio-bitrate", default="192k")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args(argv)
    try:
        report = encode_sequence(
            args.frames_dir, args.output, profile=args.profile, fps=args.fps,
            audio=args.audio, crf=args.crf, preset=args.preset,
            audio_bitrate=args.audio_bitrate, overwrite=args.overwrite,
        )
    except Exception as error:
        print("ERROR: " + str(error), file=sys.stderr)
        return 1
    report.pop("ffmpeg_command", None)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
