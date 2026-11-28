#!/usr/bin/env python3
"""Mux a FrameForge WAV master with an already-rendered silent video using FFmpeg.

The V2 compositor currently exports still frames, not a full picture sequence.
This utility therefore accepts a silent video produced by an existing video
renderer (for example the legacy browser export or Blender pipeline) and adds
the WAV master as its only audio stream.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


def _run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, check=False, capture_output=True, text=True)


def probe_media(path: str | Path, ffprobe: str = "ffprobe") -> dict[str, Any]:
    """Return ffprobe JSON for a local media file, raising useful errors."""
    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(f"Input file does not exist: {source}")
    if not shutil.which(ffprobe):
        raise RuntimeError(f"Could not find {ffprobe!r} on PATH. Install FFmpeg/ffprobe first.")
    command = [
        ffprobe, "-v", "error",
        "-show_entries",
        "format=duration:stream=codec_type,codec_name,duration,duration_ts,time_base,r_frame_rate,sample_rate,channels",
        "-of", "json", str(source),
    ]
    result = _run(command)
    if result.returncode != 0:
        raise RuntimeError("ffprobe could not read " + str(source) + ": " + result.stderr[-3000:])
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise RuntimeError("ffprobe returned invalid JSON for " + str(source)) from error


def _stream_duration(stream: dict[str, Any]) -> float | None:
    duration = stream.get("duration")
    try:
        value = float(duration)
        if value > 0:
            return value
    except (TypeError, ValueError):
        pass
    try:
        ticks = float(stream["duration_ts"])
        numerator, denominator = str(stream["time_base"]).split("/", 1)
        value = ticks * float(numerator) / float(denominator)
        return value if value > 0 else None
    except (KeyError, TypeError, ValueError, ZeroDivisionError):
        return None


def media_duration(probe: dict[str, Any], stream_type: str | None = None) -> float:
    streams = probe.get("streams") or []
    candidates = [
        duration for stream in streams
        if stream_type is None or stream.get("codec_type") == stream_type
        if (duration := _stream_duration(stream)) is not None
    ]
    if candidates:
        return max(candidates)
    try:
        duration = float(probe.get("format", {}).get("duration"))
        if duration > 0:
            return duration
    except (TypeError, ValueError):
        pass
    raise RuntimeError("Could not determine the input media duration from ffprobe.")


def frame_rate(probe: dict[str, Any]) -> float:
    for stream in probe.get("streams") or []:
        if stream.get("codec_type") != "video":
            continue
        value = stream.get("r_frame_rate") or "30/1"
        try:
            numerator, denominator = str(value).split("/", 1)
            rate = float(numerator) / float(denominator)
            if rate > 0:
                return rate
        except (ValueError, ZeroDivisionError):
            continue
    return 30.0


def build_ffmpeg_command(
    video: str | Path,
    audio: str | Path,
    output: str | Path,
    duration_seconds: float,
    *,
    ffmpeg: str = "ffmpeg",
    video_codec: str = "copy",
    loudness_i: float = -16.0,
    true_peak: float = -1.5,
    loudness_range: float = 11.0,
    audio_bitrate: str = "192k",
    overwrite: bool = False,
) -> list[str]:
    if video_codec not in {"copy", "libx264"}:
        raise ValueError("video_codec must be 'copy' or 'libx264'.")
    if not (0 < duration_seconds <= 24 * 60 * 60):
        raise ValueError("Video duration must be between 0 and 24 hours.")
    if not (-24 <= loudness_i <= -12):
        raise ValueError("Integrated loudness target must be between -24 and -12 LUFS.")
    if not (-9 <= true_peak <= 0):
        raise ValueError("True-peak ceiling must be between -9 and 0 dBTP.")
    if not (1 <= loudness_range <= 20):
        raise ValueError("Loudness range must be between 1 and 20 LU.")
    if not re.fullmatch(r"\d{2,3}k", audio_bitrate):
        raise ValueError("Audio bitrate must be written as a value such as 192k.")

    loudnorm = (
        f"loudnorm=I={loudness_i}:TP={true_peak}:LRA={loudness_range}:print_format=summary"
    )
    audio_filter = "aresample=48000:async=1:first_pts=0,apad," + loudnorm
    command = [ffmpeg, "-hide_banner", "-nostdin"]
    if overwrite:
        command.append("-y")
    command.extend([
        "-i", str(video),
        "-i", str(audio),
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-map_metadata", "0",
        "-c:v", video_codec,
    ])
    if video_codec == "libx264":
        command.extend(["-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p"])
    command.extend([
        "-af", audio_filter,
        "-c:a", "aac",
        "-b:a", audio_bitrate,
        "-ar", "48000",
        "-ac", "2",
        "-t", f"{duration_seconds:.6f}",
        "-movflags", "+faststart",
        str(output),
    ])
    return command


def mux_audio_to_video(
    video: str | Path,
    audio: str | Path,
    output: str | Path,
    *,
    ffmpeg: str = "ffmpeg",
    ffprobe: str = "ffprobe",
    video_codec: str = "copy",
    loudness_i: float = -16.0,
    true_peak: float = -1.5,
    loudness_range: float = 11.0,
    audio_bitrate: str = "192k",
    overwrite: bool = False,
) -> dict[str, Any]:
    """Validate inputs, mux the WAV master, then verify streams and duration."""
    video_path, audio_path, output_path = Path(video), Path(audio), Path(output)
    if video_path.resolve() == audio_path.resolve():
        raise ValueError("Video and audio inputs must be different files.")
    if output_path.resolve() in {video_path.resolve(), audio_path.resolve()}:
        raise ValueError("Output path must not overwrite either input.")
    if output_path.exists() and not overwrite:
        raise FileExistsError(f"Output already exists: {output_path}. Use --overwrite to replace it.")

    video_probe = probe_media(video_path, ffprobe)
    audio_probe = probe_media(audio_path, ffprobe)
    video_streams = [s for s in video_probe.get("streams", []) if s.get("codec_type") == "video"]
    audio_streams = [s for s in audio_probe.get("streams", []) if s.get("codec_type") == "audio"]
    if not video_streams:
        raise RuntimeError("The picture input contains no video stream.")
    if not audio_streams:
        raise RuntimeError("The audio master contains no audio stream.")

    duration = media_duration(video_probe, "video")
    command = build_ffmpeg_command(
        video_path, audio_path, output_path, duration,
        ffmpeg=ffmpeg, video_codec=video_codec,
        loudness_i=loudness_i, true_peak=true_peak,
        loudness_range=loudness_range, audio_bitrate=audio_bitrate,
        overwrite=overwrite,
    )
    result = _run(command)
    if result.returncode != 0:
        raise RuntimeError("FFmpeg mux failed:\n" + result.stderr[-5000:])
    if not output_path.is_file() or output_path.stat().st_size == 0:
        raise RuntimeError("FFmpeg returned success but did not create a non-empty output file.")

    output_probe = probe_media(output_path, ffprobe)
    output_video = [s for s in output_probe.get("streams", []) if s.get("codec_type") == "video"]
    output_audio = [s for s in output_probe.get("streams", []) if s.get("codec_type") == "audio"]
    if not output_video or not output_audio:
        raise RuntimeError("Muxed output is missing its video or audio stream.")
    sample_rate = int(output_audio[0].get("sample_rate") or 0)
    channels = int(output_audio[0].get("channels") or 0)
    if sample_rate != 48000 or channels != 2:
        raise RuntimeError(
            f"Muxed audio format mismatch: expected 48000 Hz stereo, got {sample_rate} Hz / {channels} channels."
        )
    output_duration = media_duration(output_probe)
    tolerance = max(0.1, 1.0 / frame_rate(video_probe) + 0.05)
    if abs(output_duration - duration) > tolerance:
        raise RuntimeError(
            f"Output duration mismatch: picture {duration:.3f}s, muxed file {output_duration:.3f}s."
        )

    return {
        "output": str(output_path),
        "size_bytes": output_path.stat().st_size,
        "duration_seconds": output_duration,
        "sample_rate": sample_rate,
        "channels": channels,
        "video_codec": output_video[0].get("codec_name"),
        "audio_codec": output_audio[0].get("codec_name"),
        "ffmpeg_command": command,
        "ffmpeg_stderr": result.stderr[-2000:],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Mux a FrameForge stereo WAV master with an already-rendered silent picture file."
    )
    parser.add_argument("--video", required=True, help="Silent rendered video file (MP4/WebM/MOV).")
    parser.add_argument("--audio", required=True, help="FrameForge WAV master.")
    parser.add_argument("--output", required=True, help="Output MP4 path.")
    parser.add_argument("--video-codec", choices=("copy", "libx264"), default="copy",
                        help="Use copy for compatible MP4 codecs; choose libx264 to convert WebM/VP9 or other incompatible video.")
    parser.add_argument("--loudness-i", type=float, default=-16.0, help="Integrated loudness target in LUFS.")
    parser.add_argument("--true-peak", type=float, default=-1.5, help="True-peak ceiling in dBTP.")
    parser.add_argument("--loudness-range", type=float, default=11.0, help="Target loudness range in LU.")
    parser.add_argument("--audio-bitrate", default="192k", help="AAC bitrate, for example 192k.")
    parser.add_argument("--overwrite", action="store_true", help="Replace the output file if it already exists.")
    args = parser.parse_args(argv)
    try:
        result = mux_audio_to_video(
            args.video, args.audio, args.output,
            video_codec=args.video_codec,
            loudness_i=args.loudness_i,
            true_peak=args.true_peak,
            loudness_range=args.loudness_range,
            audio_bitrate=args.audio_bitrate,
            overwrite=args.overwrite,
        )
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    summary = {key: value for key, value in result.items() if key not in {"ffmpeg_command", "ffmpeg_stderr"}}
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
