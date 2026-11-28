#!/usr/bin/env python3
"""Generate the 53-second Great Emu War narration using Kokoro Echo only.

Voice: Kokoro-82M am_echo (American English).
Outputs a 24 kHz mono WAV master, a 160 kbps MP3, and a timing report.
There is no fallback voice. The two requested dramatic pauses and the two
slow-down lines are handled as separate synthesis segments.
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
TARGET_SECONDS = 53.0

# These are the supplied words, divided only to control the requested pauses
# and delivery. The quote intro is omitted only if the complete read needs
# excessive acceleration; the full quotation itself is always retained.
SEGMENTS = [
    {"id": "hook", "section": "hook",
     "text": "In 1932, the Australian army went to war... and lost.",
     "speed": 1.00, "pause_after": 0.42},
    {"id": "hook_payoff", "section": "hook",
     "text": "To birds. Stay to the end, because the general's confession is unbelievable.",
     "speed": 1.00, "pause_after": 0.10},

    {"id": "setting", "section": "setting",
     "text": "Western Australia. Twenty thousand emus are eating the farmers' wheat. The farmers, all war veterans, beg the army for help.",
     "speed": 1.00, "pause_after": 0.10},

    {"id": "plan", "section": "plan",
     "text": "The army's plan? Three soldiers. Two machine guns. Ten thousand bullets. Easy win... right?",
     "speed": 1.00, "pause_after": 0.42},

    {"id": "day_one_cta", "section": "day_one",
     "text": "Day one: the emus split into tiny groups. Impossible to hit. If you're enjoying this, like and subscribe!",
     "speed": 1.00, "pause_after": 0.10},

    {"id": "truck_comment", "section": "truck",
     "text": "So they mounted the gun on a truck. But emus run fifty kilometres an hour, and the truck bounced too much to aim. Comment now: army or emus, who wins round two?",
     "speed": 1.02, "pause_after": 0.10},

    {"id": "retreat", "section": "retreat",
     "text": "It gets worse. Within a week, the army retreated. Then they came back for round two... and got the same result.",
     "speed": 1.00, "pause_after": 0.10},

    {"id": "tally_setup", "section": "tally",
     "text": "Almost ten thousand bullets later, the emus were still eating.",
     "speed": 1.00, "pause_after": 0.08},
    {"id": "score", "section": "tally",
     "text": "Army, zero. Emus, one.",
     "speed": 0.86, "pause_after": 0.18},
    {"id": "confession_setup", "section": "quote",
     "text": "Now... the general's confession.",
     "speed": 0.94, "pause_after": 0.10},

    {"id": "quote_lead", "section": "quote",
     "text": "Major Meredith wrote in his own report:",
     "speed": 1.00, "pause_after": 0.06,
     "omit_if_tight": True},
    {"id": "quote", "section": "quote",
     "text": "If we had a military division with the bullet-carrying capacity of these birds, it would face any army in the world.",
     "speed": 0.96, "pause_after": 0.12},

    {"id": "final_payoff", "section": "outro",
     "text": "The emus won.",
     "speed": 0.86, "pause_after": 0.14},
    {"id": "follow", "section": "outro",
     "text": "Follow for more crazy true stories.",
     "speed": 1.00, "pause_after": 0.0},
]


def run_checked(args: list[str]) -> None:
    result = subprocess.run(
        args, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    if result.returncode:
        raise RuntimeError(
            f"Command failed: {' '.join(args)}\\n{result.stderr[-6000:]}"
        )


def as_numpy(audio: object) -> np.ndarray:
    if hasattr(audio, "detach"):
        audio = audio.detach().cpu().numpy()
    array = np.asarray(audio, dtype=np.float32).reshape(-1)
    if array.size == 0 or not np.isfinite(array).all():
        raise RuntimeError("Kokoro returned empty or non-finite audio.")
    return array


def synthesize(pipeline: KPipeline, text: str, speed: float) -> np.ndarray:
    chunks: list[np.ndarray] = []
    for _graphemes, _phonemes, audio in pipeline(
        text, voice=VOICE, speed=speed
    ):
        if audio is not None:
            part = as_numpy(audio)
            if part.size:
                chunks.append(part)
    if not chunks:
        raise RuntimeError(
            "Kokoro Echo returned no audio. No substitute voice will be used."
        )
    return np.concatenate(chunks)


def build_mix(rendered: dict[str, np.ndarray], active: list[dict]):
    pieces: list[np.ndarray] = []
    reports: list[dict] = []
    cursor = 0

    for segment in active:
        audio = rendered[segment["id"]]
        start = cursor
        pieces.append(audio)
        cursor += len(audio)
        end = cursor
        pause_samples = int(round(segment["pause_after"] * SAMPLE_RATE))
        if pause_samples:
            pieces.append(np.zeros(pause_samples, dtype=np.float32))
            cursor += pause_samples

        reports.append({
            "id": segment["id"],
            "section": segment["section"],
            "text": segment["text"],
            "kokoro_speed": segment["speed"],
            "source_start_seconds": round(start / SAMPLE_RATE, 4),
            "source_end_seconds": round(end / SAMPLE_RATE, 4),
            "pause_after_seconds": segment["pause_after"],
        })

    return np.concatenate(pieces), reports


def probe_audio(path: Path) -> dict:
    result = subprocess.run(
        [
            "ffprobe", "-v", "error", "-show_entries",
            "format=duration,size:stream=codec_name,sample_rate,channels,bit_rate",
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
        "--output-dir", default="projects/great-emu-war-narrative/output"
    )
    args = parser.parse_args()

    for binary in ("ffmpeg", "ffprobe"):
        if shutil.which(binary) is None:
            raise SystemExit(f"Required executable not found: {binary}")

    torch.set_num_threads(max(1, min(4, torch.get_num_threads())))
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(
        f"Loading {MODEL_REPO}; voice={VOICE}; language={LANG_CODE}",
        flush=True,
    )
    pipeline = KPipeline(lang_code=LANG_CODE)

    rendered: dict[str, np.ndarray] = {}
    for segment in SEGMENTS:
        print(f"Synthesizing {segment['id']}", flush=True)
        rendered[segment["id"]] = synthesize(
            pipeline, segment["text"], segment["speed"]
        )

    active = list(SEGMENTS)
    mixed, segment_reports = build_mix(rendered, active)
    source_duration = len(mixed) / SAMPLE_RATE
    tempo = source_duration / TARGET_SECONDS
    quote_intro_omitted = False

    # The user's note allows removing the quote setup when it is too rushed.
    if tempo > 1.16:
        active = [s for s in active if not s.get("omit_if_tight")]
        mixed, segment_reports = build_mix(rendered, active)
        source_duration = len(mixed) / SAMPLE_RATE
        tempo = source_duration / TARGET_SECONDS
        quote_intro_omitted = True
        print("Tight quote fit: removed the lead-in; retaining the complete quote.", flush=True)

    if not 0.78 <= tempo <= 1.28:
        raise RuntimeError(
            f"Natural read would require atempo={tempo:.3f}; refusing an "
            "excessive speed change for the requested deadpan delivery."
        )

    # Write the source mix, then use pitch-preserving atempo to hit exactly 53s.
    with tempfile.TemporaryDirectory(prefix="frameforge-emu-echo-") as tmp:
        raw_path = Path(tmp) / "source-mix.wav"
        sf.write(raw_path, mixed, SAMPLE_RATE, subtype="PCM_16")

        wav_path = output_dir / "great-emu-war-narration-kokoro-echo.wav"
        mp3_path = output_dir / "great-emu-war-narration-kokoro-echo.mp3"

        filter_chain = (
            f"atempo={tempo:.8f},"
            f"apad=whole_dur={TARGET_SECONDS:.6f},"
            f"atrim=duration={TARGET_SECONDS:.6f},"
            "afade=t=in:d=0.018,"
            f"afade=t=out:st={TARGET_SECONDS - 0.045:.6f}:d=0.045"
        )
        run_checked([
            "ffmpeg", "-y", "-v", "error", "-i", str(raw_path),
            "-af", filter_chain, "-ar", str(SAMPLE_RATE), "-ac", "1",
            "-c:a", "pcm_s16le", str(wav_path),
        ])
        run_checked([
            "ffmpeg", "-y", "-v", "error", "-i", str(wav_path),
            "-map_metadata", "-1", "-codec:a", "libmp3lame", "-b:a", "160k",
            "-ar", str(SAMPLE_RATE), "-ac", "1", "-write_xing", "1",
            str(mp3_path),
        ])

    wav_data, wav_rate = sf.read(wav_path, dtype="float32")
    expected_samples = int(round(TARGET_SECONDS * SAMPLE_RATE))
    if wav_rate != SAMPLE_RATE or len(wav_data) != expected_samples:
        raise RuntimeError(
            f"WAV duration/sample verification failed: rate={wav_rate}, "
            f"samples={len(wav_data)}, expected={expected_samples}"
        )

    info = probe_audio(mp3_path)
    streams = info.get("streams", [])
    if not streams or streams[0].get("codec_name") != "mp3":
        raise RuntimeError(f"MP3 verification failed: {info}")
    actual_duration = float(info.get("format", {}).get("duration", 0.0))
    if not 52.90 <= actual_duration <= 53.12:
        raise RuntimeError(f"Unexpected MP3 duration: {actual_duration:.3f}s")
    if mp3_path.stat().st_size < 100_000:
        raise RuntimeError("MP3 is unexpectedly small; refusing an empty render.")

    # Convert segment boundaries into final-timeline times after global tempo fit.
    for report in segment_reports:
        report["final_start_seconds"] = round(
            report["source_start_seconds"] / tempo, 4
        )
        report["final_end_seconds"] = round(
            report["source_end_seconds"] / tempo, 4
        )

    metadata = {
        "status": "PASS",
        "title": "The Great Emu War",
        "voice": "Kokoro Echo (am_echo)",
        "model": MODEL_REPO,
        "language": "American English",
        "sample_rate_hz": SAMPLE_RATE,
        "channels": 1,
        "target_duration_seconds": TARGET_SECONDS,
        "wav_duration_seconds": len(wav_data) / wav_rate,
        "mp3_duration_seconds": actual_duration,
        "mp3_bitrate": "160 kbps",
        "source_mix_duration_seconds": round(source_duration, 4),
        "final_global_atempo": round(tempo, 4),
        "quote_intro_omitted_for_pacing": quote_intro_omitted,
        "pause_after_lost_seconds": 0.42,
        "pause_after_easy_win_right_seconds": 0.42,
        "slow_delivery_lines": ["Army, zero. Emus, one.", "The emus won."],
        "segments": segment_reports,
        "files": {
            "mp3": mp3_path.name,
            "wav": wav_path.name,
        },
        "mp3_size_bytes": mp3_path.stat().st_size,
        "wav_size_bytes": wav_path.stat().st_size,
    }
    (output_dir / "timing.json").write_text(
        json.dumps(metadata, indent=2) + "\\n", encoding="utf-8"
    )
    print(json.dumps(metadata, indent=2), flush=True)
    print(f"MP3_READY={mp3_path.resolve()}", flush=True)


if __name__ == "__main__":
    main()
