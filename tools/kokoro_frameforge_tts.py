#!/usr/bin/env python3
"""Create a timestamped FrameForge voiceover with Kokoro's am_echo voice."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path
from typing import Any

import numpy as np
import soundfile as sf
from kokoro import KPipeline

SAMPLE_RATE = 24_000
TIME_RE = re.compile(r"^\s*(\d+):(\d+(?:\.\d+)?)\s+(.+?)\s*$")


def timestamp_seconds(minutes: str, seconds: str) -> float:
    return int(minutes) * 60.0 + float(seconds)


def parse_timeline(path: Path, total_duration: float) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        match = TIME_RE.match(raw)
        if not match:
            continue
        start = timestamp_seconds(match.group(1), match.group(2))
        text = match.group(3).strip()
        # Parenthetical entries are production directions, not spoken narration.
        events.append({
            "start": start,
            "text": "" if text.startswith("(") else text,
            "line_number": line_number,
        })

    if not events:
        raise ValueError("No timestamped narration lines were found in the input script.")

    previous = -1.0
    for event in events:
        if event["start"] <= previous:
            raise ValueError("Timestamped script entries must be in strictly increasing order.")
        if event["start"] >= total_duration:
            raise ValueError(f"Script event at {event['start']:.2f}s is outside the target duration.")
        previous = event["start"]

    spoken = []
    for index, event in enumerate(events):
        if not event["text"]:
            continue
        next_start = events[index + 1]["start"] if index + 1 < len(events) else total_duration
        spoken.append({
            **event,
            "end_limit": min(next_start, total_duration),
        })
    if not spoken:
        raise ValueError("The script contains no spoken lines.")
    return spoken


def to_numpy(audio: Any) -> np.ndarray:
    if hasattr(audio, "detach"):
        audio = audio.detach().cpu().numpy()
    result = np.asarray(audio, dtype=np.float32).reshape(-1)
    if result.size == 0:
        raise ValueError("Kokoro returned an empty audio segment.")
    return result


def synthesize_line(pipeline: KPipeline, text: str, speed: float) -> np.ndarray:
    chunks = []
    for _graphemes, _phonemes, audio in pipeline(
        text,
        voice="am_echo",
        speed=speed,
        split_pattern=r"\n+",
    ):
        if audio is not None:
            chunks.append(to_numpy(audio))
    if not chunks:
        raise RuntimeError(f"Kokoro produced no speech for: {text}")
    return np.concatenate(chunks)


def synthesize_to_fit(pipeline: KPipeline, text: str, max_seconds: float) -> tuple[np.ndarray, float]:
    speed = 1.0
    audio = synthesize_line(pipeline, text, speed)
    for _ in range(4):
        duration = len(audio) / SAMPLE_RATE
        if duration <= max_seconds:
            return audio, speed
        # Re-synthesize rather than cutting off the end of a spoken word.
        speed = min(1.45, max(speed + 0.04, speed * (duration / max_seconds) * 1.015))
        audio = synthesize_line(pipeline, text, speed)
    duration = len(audio) / SAMPLE_RATE
    if duration > max_seconds:
        raise RuntimeError(
            f"Line could not fit its {max_seconds:.2f}s slot without clipping "
            f"(speech is {duration:.2f}s at speed {speed:.2f})."
        )
    return audio, speed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--duration", type=float, default=30.0)
    args = parser.parse_args()

    if not args.input.is_file():
        raise FileNotFoundError(args.input)
    args.out_dir.mkdir(parents=True, exist_ok=True)

    segments = parse_timeline(args.input, args.duration)
    pipeline = KPipeline(lang_code="a")
    master = np.zeros(int(round(args.duration * SAMPLE_RATE)), dtype=np.float32)
    report = []

    for segment in segments:
        start = float(segment["start"])
        end_limit = float(segment["end_limit"])
        max_seconds = end_limit - start - 0.035
        if max_seconds <= 0:
            raise ValueError(f"No room for narration starting at {start:.2f}s.")

        audio, speed = synthesize_to_fit(pipeline, segment["text"], max_seconds)
        start_sample = int(round(start * SAMPLE_RATE))
        end_sample = start_sample + len(audio)
        if end_sample > len(master):
            raise RuntimeError("A spoken segment extends beyond the requested audio duration.")

        # Short edge fades prevent clicks without changing the spoken timing.
        fade = min(int(0.012 * SAMPLE_RATE), len(audio) // 4)
        if fade > 0:
            audio = audio.copy()
            audio[:fade] *= np.linspace(0.0, 1.0, fade, dtype=np.float32)
            audio[-fade:] *= np.linspace(1.0, 0.0, fade, dtype=np.float32)

        master[start_sample:end_sample] += audio
        report.append({
            "start_seconds": round(start, 3),
            "spoken_end_seconds": round(end_sample / SAMPLE_RATE, 3),
            "speed": round(speed, 3),
            "text": segment["text"],
            "source_line": segment["line_number"],
        })

    peak = float(np.max(np.abs(master))) if master.size else 0.0
    if peak > 0.0:
        master *= min(1.0, 0.89 / peak)

    mono_24k = args.out_dir / "wombat_cubes_echo_temp_24k_mono.wav"
    wav_48k = args.out_dir / "wombat_cubes_echo_30s_48k_stereo.wav"
    mp3_48k = args.out_dir / "wombat_cubes_echo_30s_192k.mp3"
    sf.write(mono_24k, master, SAMPLE_RATE, subtype="PCM_16")

    subprocess.run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-i", str(mono_24k),
        "-af", "aresample=48000",
        "-ac", "2", "-c:a", "pcm_s16le",
        "-t", f"{args.duration:.3f}",
        str(wav_48k),
    ], check=True)
    subprocess.run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-i", str(wav_48k),
        "-c:a", "libmp3lame", "-b:a", "192k",
        "-ar", "48000", "-ac", "2",
        "-t", f"{args.duration:.3f}",
        str(mp3_48k),
    ], check=True)
    mono_24k.unlink(missing_ok=True)

    metadata = {
        "project": "FrameForge",
        "script_title": "Wombat Cubes",
        "voice_engine": "Kokoro",
        "voice_id": "am_echo",
        "language": "American English",
        "duration_seconds": args.duration,
        "sample_rate_hz": 48000,
        "channels": 2,
        "narration_only": True,
        "production_note": "Parenthetical directions and sound-effect cues are not spoken or synthesized.",
        "segments": report,
    }
    (args.out_dir / "wombat_cubes_echo_timing.json").write_text(
        json.dumps(metadata, indent=2), encoding="utf-8"
    )

    print(json.dumps({
        "wav": str(wav_48k),
        "mp3": str(mp3_48k),
        "duration_seconds": args.duration,
        "voice": "am_echo",
        "segments": len(report),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
