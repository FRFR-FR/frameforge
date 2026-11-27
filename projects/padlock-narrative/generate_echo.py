#!/usr/bin/env python3
"""Render the 30-second padlock short with Kokoro Echo (am_echo).

Every line is fitted to its supplied slot. The CTA begins at 10.000 seconds.
There is deliberately no fallback voice: a Kokoro failure fails the render.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

import numpy as np
import soundfile as sf
import torch
from kokoro import KPipeline

VOICE = "am_echo"
MODEL_REPO = "hexgrad/Kokoro-82M"
SAMPLE_RATE = 24_000
TOTAL_SECONDS = 30.0

# Exact timings from the supplied Padlock narration script.
SEGMENTS = [
    {"id": "hook", "start": 0.0, "end": 3.0,
     "text": "This lock is useless. Anyone can just pull it open."},
    {"id": "bolt", "start": 3.0, "end": 6.0,
     "text": "So add a bolt to hold the shackle down."},
    {"id": "pushback", "start": 6.0, "end": 8.0,
     "text": "Now someone pushes the bolt back."},
    {"id": "spring", "start": 8.0, "end": 10.0,
     "text": "Fix that with a spring."},
    {"id": "cta", "start": 10.0, "end": 13.0,
     "text": "Like and subscribe, because a thin shim beats that spring."},
    {"id": "plug", "start": 13.0, "end": 16.0,
     "text": "So hide the bolt behind a plug that must turn."},
    {"id": "turn", "start": 16.0, "end": 18.5,
     "text": "But now anyone can turn it."},
    {"id": "pins", "start": 18.5, "end": 21.0,
     "text": "Add spring-loaded pins that block the plug."},
    {"id": "blocked", "start": 21.0, "end": 23.5,
     "text": "Now nobody can turn it,"},
    {"id": "key", "start": 23.5, "end": 27.0,
     "text": "except the right key, which lifts every pin to the exact height."},
    {"id": "close", "start": 27.0, "end": 30.0,
     "text": "Plug turns, bolt slides, lock opens. That's your padlock."},
]


def run_checked(args: list[str]) -> None:
    result = subprocess.run(
        args, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    if result.returncode:
        raise RuntimeError(
            f"Command failed: {' '.join(args)}\n{result.stderr[-6000:]}"
        )


def as_numpy(audio: object) -> np.ndarray:
    if hasattr(audio, "detach"):
        audio = audio.detach().cpu().numpy()
    array = np.asarray(audio, dtype=np.float32).reshape(-1)
    if array.size == 0 or not np.isfinite(array).all():
        raise RuntimeError("Kokoro returned empty or non-finite audio.")
    return array


def synthesize(pipeline: KPipeline, text: str) -> np.ndarray:
    chunks: list[np.ndarray] = []
    for _graphemes, _phonemes, audio in pipeline(
        text, voice=VOICE, speed=1.0
    ):
        if audio is not None:
            part = as_numpy(audio)
            if part.size:
                chunks.append(part)
    if not chunks:
        raise RuntimeError(
            "Kokoro Echo returned no audio; no substitute voice will be used."
        )
    return np.concatenate(chunks)


def fit_to_duration(
    audio: np.ndarray, duration: float, label: str, temp_dir: Path
) -> tuple[np.ndarray, dict]:
    raw_path = temp_dir / f"{label}-raw.wav"
    fit_path = temp_dir / f"{label}-fit.wav"
    sf.write(raw_path, audio, SAMPLE_RATE, subtype="PCM_16")

    source_duration = len(audio) / SAMPLE_RATE
    tempo = source_duration / duration
    if not 0.50 <= tempo <= 2.00:
        raise RuntimeError(
            f"{label}: Kokoro speech is {source_duration:.2f}s for a "
            f"{duration:.2f}s slot (atempo={tempo:.2f}); refusing an "
            "extreme speed change."
        )

    run_checked([
        "ffmpeg", "-y", "-v", "error", "-i", str(raw_path),
        "-af", (
            f"atempo={tempo:.8f},apad=whole_dur={duration:.6f},"
            f"atrim=duration={duration:.6f}"
        ),
        "-ar", str(SAMPLE_RATE), "-ac", "1",
        "-c:a", "pcm_s16le", str(fit_path),
    ])

    fitted, rate = sf.read(fit_path, dtype="float32")
    if rate != SAMPLE_RATE:
        raise RuntimeError(f"{label}: unexpected sample rate {rate}")
    fitted = np.asarray(fitted, dtype=np.float32).reshape(-1)

    expected = int(round(duration * SAMPLE_RATE))
    if len(fitted) > expected:
        fitted = fitted[:expected]
    elif len(fitted) < expected:
        fitted = np.pad(fitted, (0, expected - len(fitted)))

    # Tiny edge fades avoid clicks at the exact narration edit points.
    fade = min(int(0.012 * SAMPLE_RATE), len(fitted) // 4)
    if fade:
        fitted[:fade] *= np.linspace(0.0, 1.0, fade, dtype=np.float32)
        fitted[-fade:] *= np.linspace(1.0, 0.0, fade, dtype=np.float32)

    report = {
        "source_duration_seconds": round(source_duration, 4),
        "slot_duration_seconds": duration,
        "atempo": round(tempo, 4),
    }
    return fitted, report


def probe_audio(path: Path) -> dict:
    result = subprocess.run(
        [
            "ffprobe", "-v", "error", "-show_entries",
            "format=duration,size:stream=codec_name,sample_rate,channels",
            "-of", "json", str(path),
        ],
        text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    if result.returncode:
        raise RuntimeError(f"ffprobe failed: {result.stderr}")
    return json.loads(result.stdout)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-dir", default="projects/padlock-narrative/output"
    )
    args = parser.parse_args()

    for binary in ("ffmpeg", "ffprobe"):
        if shutil.which(binary) is None:
            raise SystemExit(f"Required executable not found: {binary}")

    torch.set_num_threads(max(1, min(4, torch.get_num_threads())))
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(
        f"Loading {MODEL_REPO}; voice={VOICE}; language=American English",
        flush=True,
    )
    pipeline = KPipeline(lang_code="a")

    rendered: list[np.ndarray] = []
    segment_reports: list[dict] = []
    with tempfile.TemporaryDirectory(prefix="frameforge-padlock-echo-") as tmp:
        temp_dir = Path(tmp)
        for segment in SEGMENTS:
            duration = segment["end"] - segment["start"]
            print(
                f"Synthesizing {segment['id']} "
                f"({segment['start']:.2f}-{segment['end']:.2f}s)",
                flush=True,
            )
            generated = synthesize(pipeline, segment["text"])
            fitted, timing = fit_to_duration(
                generated, duration, segment["id"], temp_dir
            )
            rendered.append(fitted)
            segment_reports.append({
                "id": segment["id"],
                "start_seconds": segment["start"],
                "end_seconds": segment["end"],
                "text": segment["text"],
                **timing,
            })

    pcm = np.concatenate(rendered)
    expected_samples = int(round(TOTAL_SECONDS * SAMPLE_RATE))
    if len(pcm) != expected_samples:
        raise RuntimeError(
            f"Expected {expected_samples} PCM samples, received {len(pcm)}"
        )

    wav_path = output_dir / "padlock-narration-kokoro-echo.wav"
    mp3_path = output_dir / "padlock-narration-kokoro-echo.mp3"
    sf.write(wav_path, pcm, SAMPLE_RATE, subtype="PCM_16")
    run_checked([
        "ffmpeg", "-y", "-v", "error", "-i", str(wav_path),
        "-map_metadata", "-1", "-codec:a", "libmp3lame", "-b:a", "160k",
        "-ar", str(SAMPLE_RATE), "-ac", "1", "-write_xing", "1",
        str(mp3_path),
    ])

    info = probe_audio(mp3_path)
    streams = info.get("streams", [])
    if not streams or streams[0].get("codec_name") != "mp3":
        raise RuntimeError(f"MP3 verification failed: {info}")
    actual_duration = float(info.get("format", {}).get("duration", 0.0))
    if not 29.90 <= actual_duration <= 30.15:
        raise RuntimeError(
            f"Unexpected MP3 duration: {actual_duration:.3f}s"
        )

    metadata = {
        "status": "PASS",
        "voice": "Kokoro Echo (am_echo)",
        "model": MODEL_REPO,
        "language": "American English",
        "sample_rate_hz": SAMPLE_RATE,
        "channels": 1,
        "wav_duration_seconds": len(pcm) / SAMPLE_RATE,
        "mp3_duration_seconds": actual_duration,
        "mp3_bitrate": "160 kbps",
        "cta_start_seconds": 10.0,
        "segment_count": len(SEGMENTS),
        "segments": segment_reports,
        "files": {
            "mp3": mp3_path.name,
            "wav": wav_path.name,
        },
    }
    (output_dir / "timing.json").write_text(
        json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(metadata, indent=2), flush=True)
    print(f"MP3_READY={mp3_path.resolve()}", flush=True)


if __name__ == "__main__":
    main()
