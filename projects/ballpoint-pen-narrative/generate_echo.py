#!/usr/bin/env python3
"""FrameForge narration render: Kokoro-82M American-English Echo (am_echo).

Creates a separate 30.00-second MP3 and WAV master. The CTA segment begins at
exactly 10.00 seconds in the assembled PCM timeline. There is no voice fallback.
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
LANG_CODE = "a"
MODEL_REPO = "hexgrad/Kokoro-82M"
SAMPLE_RATE = 24_000
TOTAL_SECONDS = 30.0

SEGMENTS = [
    {
        "id": "hook",
        "start": 0.0,
        "duration": 10.0,
        "text": (
            "This tiny steel ball does almost all the work inside your pen. "
            "The barrel merely stores ink; the real mechanism hides right down "
            "in this tiny tip."
        ),
    },
    {
        "id": "cta",
        "start": 10.0,
        "duration": 10.0 / 2.7,
        "text": "Tap like and subscribe. Follow for more tiny engineering.",
    },
    {
        "id": "explainer",
        "start": 10.0 + (10.0 / 2.7),
        "duration": TOTAL_SECONDS - 10.0 - (10.0 / 2.7),
        "text": (
            "Ink runs through a narrow channel to the socket. Paper friction "
            "rolls the ball across the surface. It picks up ink inside, then "
            "rolls onto paper. A tight gap meters flow; thick ink resists leaks. "
            "That tiny sphere is a rolling ink valve. Good luck."
        ),
    },
]


def run_checked(args: list[str]) -> None:
    result = subprocess.run(args, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode:
        raise RuntimeError(f"Command failed: {' '.join(args)}\n{result.stderr[-6000:]}")


def as_numpy(audio: object) -> np.ndarray:
    if hasattr(audio, "detach"):
        audio = audio.detach().cpu().numpy()
    arr = np.asarray(audio, dtype=np.float32).reshape(-1)
    if arr.size == 0 or not np.isfinite(arr).all():
        raise RuntimeError("Kokoro returned empty or non-finite audio.")
    return arr


def synthesize(pipeline: KPipeline, text: str) -> np.ndarray:
    chunks: list[np.ndarray] = []
    for _graphemes, _phonemes, audio in pipeline(text, voice=VOICE, speed=1.0):
        if audio is not None:
            part = as_numpy(audio)
            if part.size:
                chunks.append(part)
    if not chunks:
        raise RuntimeError("Kokoro returned no speech audio. Echo was not substituted.")
    return np.concatenate(chunks)


def fit_to_duration(audio: np.ndarray, duration: float, label: str, temp_dir: Path) -> np.ndarray:
    raw_path = temp_dir / f"{label}-raw.wav"
    fit_path = temp_dir / f"{label}-fit.wav"
    sf.write(raw_path, audio, SAMPLE_RATE, subtype="PCM_16")
    source_duration = len(audio) / SAMPLE_RATE
    tempo = source_duration / duration
    if not 0.50 <= tempo <= 2.00:
        raise RuntimeError(
            f"{label}: Kokoro speech duration {source_duration:.2f}s cannot be fitted "
            f"naturally into {duration:.2f}s (atempo={tempo:.2f})."
        )
    run_checked([
        "ffmpeg", "-y", "-v", "error", "-i", str(raw_path),
        "-af", (
            f"atempo={tempo:.8f},apad=whole_dur={duration:.6f},"
            f"atrim=duration={duration:.6f}"
        ),
        "-ar", str(SAMPLE_RATE), "-ac", "1", "-c:a", "pcm_s16le", str(fit_path),
    ])
    fitted, sr = sf.read(fit_path, dtype="float32")
    if sr != SAMPLE_RATE:
        raise RuntimeError(f"{label}: unexpected sample rate {sr}")
    fitted = np.asarray(fitted, dtype=np.float32).reshape(-1)
    expected = int(round(duration * SAMPLE_RATE))
    if len(fitted) > expected:
        fitted = fitted[:expected]
    elif len(fitted) < expected:
        fitted = np.pad(fitted, (0, expected - len(fitted)))
    fade = min(int(0.012 * SAMPLE_RATE), len(fitted) // 4)
    if fade:
        fitted[:fade] *= np.linspace(0.0, 1.0, fade, dtype=np.float32)
        fitted[-fade:] *= np.linspace(1.0, 0.0, fade, dtype=np.float32)
    return fitted


def probe_audio(path: Path) -> dict:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries",
         "format=duration,size:stream=codec_name,sample_rate,channels",
         "-of", "json", str(path)],
        text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    if result.returncode:
        raise RuntimeError(f"ffprobe failed: {result.stderr}")
    return json.loads(result.stdout)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="projects/ballpoint-pen-narrative/output")
    args = parser.parse_args()

    for binary in ("ffmpeg", "ffprobe"):
        if shutil.which(binary) is None:
            raise SystemExit(f"Required executable not found: {binary}")

    torch.set_num_threads(max(1, min(4, torch.get_num_threads())))
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Loading {MODEL_REPO}; voice={VOICE}; language={LANG_CODE}", flush=True)
    pipeline = KPipeline(lang_code=LANG_CODE)

    rendered: list[np.ndarray] = []
    with tempfile.TemporaryDirectory(prefix="frameforge-kokoro-echo-") as tmp:
        tmp_path = Path(tmp)
        for segment in SEGMENTS:
            print(f"Synthesizing {segment['id']} ({segment['duration']:.3f}s slot)", flush=True)
            generated = synthesize(pipeline, segment["text"])
            rendered.append(fit_to_duration(generated, segment["duration"], segment["id"], tmp_path))

    pcm = np.concatenate(rendered)
    expected_samples = int(round(TOTAL_SECONDS * SAMPLE_RATE))
    if len(pcm) != expected_samples:
        raise RuntimeError(f"Expected {expected_samples} samples, got {len(pcm)}")

    wav_path = out_dir / "ballpoint-pen-narration-echo.wav"
    mp3_path = out_dir / "ballpoint-pen-narration-echo.mp3"
    sf.write(wav_path, pcm, SAMPLE_RATE, subtype="PCM_16")
    run_checked([
        "ffmpeg", "-y", "-v", "error", "-i", str(wav_path),
        "-map_metadata", "-1", "-codec:a", "libmp3lame", "-b:a", "160k",
        "-ar", str(SAMPLE_RATE), "-ac", "1", "-write_xing", "1", str(mp3_path),
    ])

    info = probe_audio(mp3_path)
    streams = info.get("streams", [])
    if not streams or streams[0].get("codec_name") != "mp3":
        raise RuntimeError(f"MP3 verification failed: {info}")
    actual_duration = float(info.get("format", {}).get("duration", 0.0))
    if not 29.90 <= actual_duration <= 30.15:
        raise RuntimeError(f"Unexpected MP3 duration {actual_duration:.3f}s")

    metadata = {
        "status": "PASS",
        "voice": "Kokoro Echo (am_echo)",
        "model": MODEL_REPO,
        "language": "American English",
        "sample_rate": SAMPLE_RATE,
        "channels": 1,
        "wav_duration_seconds": len(pcm) / SAMPLE_RATE,
        "mp3_duration_seconds": actual_duration,
        "mp3_bitrate": "160 kbps",
        "cta_start_seconds": 10.0,
        "segments": [
            {"id": x["id"], "start": x["start"], "duration": x["duration"]}
            for x in SEGMENTS
        ],
    }
    (out_dir / "timing.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(metadata, indent=2), flush=True)
    print(f"MP3_READY={mp3_path.resolve()}", flush=True)


if __name__ == "__main__":
    main()
