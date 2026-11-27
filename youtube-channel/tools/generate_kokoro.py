#!/usr/bin/env python3
"""Generate English narration with Kokoro Echo and a timed SRT sidecar."""
from pathlib import Path
import argparse
import json
import re
import subprocess
import textwrap

import numpy as np
import soundfile as sf
import torch
from kokoro import KPipeline

SR = 24000
VOICE = "am_echo"
SPEED = 0.96
SENTENCE_GAP = 0.18
SECTION_GAP = 0.42


def parse_sections(path: Path):
    lines = path.read_text(encoding="utf-8").splitlines()
    sections = []
    current = None
    for line in lines:
        match = re.match(r"^##\s+(\d{2})\s+[—-]\s+(.+)$", line.strip())
        if match:
            if current and current["text"].strip():
                sections.append(current)
            current = {
                "id": f"section_{int(match.group(1)):02d}",
                "title": match.group(2).strip(),
                "text": ""
            }
            continue
        if current is None:
            continue
        if (
            not line.strip()
            or line.strip().startswith("#")
            or line.strip().startswith(("Channel:", "Target export:", "Voice:", "Subtitles:"))
        ):
            continue
        current["text"] += " " + line.strip()
    if current and current["text"].strip():
        sections.append(current)
    for section in sections:
        section["text"] = re.sub(r"\s+", " ", section["text"]).strip()
    if len(sections) != 10:
        raise RuntimeError(f"Expected ten numbered narration sections, found {len(sections)}.")
    return sections


def split_sentences(text):
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+", text.strip()) if part.strip()]


def synthesize(pipeline, text):
    chunks = []
    for _, _, audio in pipeline(text, voice=VOICE, speed=SPEED):
        if hasattr(audio, "detach"):
            audio = audio.detach().cpu().numpy()
        samples = np.asarray(audio, dtype=np.float32).reshape(-1)
        if samples.size:
            chunks.append(samples)
    if not chunks:
        raise RuntimeError(f"Kokoro returned no audio for: {text[:100]}")
    return np.concatenate(chunks)


def srt_timestamp(seconds):
    milliseconds = max(0, int(round(seconds * 1000)))
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, millis = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def caption_lines(text, width=44):
    return textwrap.wrap(
        text,
        width=width,
        break_long_words=False,
        break_on_hyphens=False
    ) or [text]


def write_srt(sentence_rows, path):
    cues = []
    index = 1
    for row in sentence_rows:
        lines = caption_lines(row["text"])
        groups = [lines[pos:pos + 2] for pos in range(0, len(lines), 2)]
        start = float(row["start_seconds"])
        end = float(row["end_seconds"])
        if len(groups) == 1:
            cues.append((start, end, "\n".join(groups[0])))
            continue
        weights = [sum(len(line.split()) for line in group) for group in groups]
        total_weight = max(1, sum(weights))
        cursor = start
        for group_index, (group, weight) in enumerate(zip(groups, weights)):
            segment_end = end if group_index == len(groups) - 1 else cursor + (end - start) * weight / total_weight
            if segment_end <= cursor:
                segment_end = cursor + 0.2
            cues.append((cursor, segment_end, "\n".join(group)))
            cursor = segment_end

    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for start, end, caption in cues:
            handle.write(f"{index}\n")
            handle.write(f"{srt_timestamp(start)} --> {srt_timestamp(end)}\n")
            handle.write(caption + "\n\n")
            index += 1


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--episode-dir", required=True)
    args = parser.parse_args()

    root = Path(args.episode_dir).resolve()
    output = root / "output"
    audio_dir = output / "audio"
    output.mkdir(parents=True, exist_ok=True)
    audio_dir.mkdir(parents=True, exist_ok=True)

    sections = parse_sections(root / "narration.md")
    print(f"Loading Kokoro English pipeline; provider=Kokoro-82M voice={VOICE}", flush=True)
    torch.set_num_threads(max(1, min(4, torch.get_num_threads())))
    pipeline = KPipeline(lang_code="a")

    full_parts = []
    full_cursor = 0.0
    sentence_gap = np.zeros(int(SENTENCE_GAP * SR), dtype=np.float32)
    section_gap = np.zeros(int(SECTION_GAP * SR), dtype=np.float32)
    sentence_rows = []
    section_rows = []

    for section_index, section in enumerate(sections, start=1):
        section_parts = []
        section_start = full_cursor
        section_sentences = split_sentences(section["text"])

        for sentence_index, sentence in enumerate(section_sentences, start=1):
            wave = synthesize(pipeline, sentence)
            start = full_cursor
            section_parts.append(wave)
            full_parts.append(wave)
            seconds = len(wave) / SR
            end = start + seconds
            sentence_rows.append({
                "section_id": section["id"],
                "sentence_index": sentence_index,
                "text": sentence,
                "start_seconds": round(start, 3),
                "end_seconds": round(end, 3),
                "duration_seconds": round(seconds, 3)
            })
            full_cursor = end
            if sentence_index < len(section_sentences):
                section_parts.append(sentence_gap)
                full_parts.append(sentence_gap)
                full_cursor += SENTENCE_GAP

        if section_index < len(sections):
            section_parts.append(section_gap)

        section_wave = np.concatenate(section_parts) if section_parts else np.zeros(1, dtype=np.float32)
        section_path = audio_dir / f"{section['id']}_echo.wav"
        sf.write(section_path, section_wave, SR, subtype="PCM_16")
        section_duration = len(section_wave) / SR
        section_rows.append({
            "id": section["id"],
            "title": section["title"],
            "audio_file": str(section_path.relative_to(root)),
            "duration_seconds": round(section_duration, 3),
            "start_seconds": round(section_start, 3)
        })

        if section_index < len(sections):
            full_parts.append(section_gap)
            full_cursor += SECTION_GAP

        print(f"Echo voice section {section_index}/10: {section_duration:.1f}s", flush=True)

    combined = np.concatenate(full_parts)
    wav_path = output / "narration_echo_kokoro.wav"
    mp3_path = output / "narration_echo_kokoro.mp3"
    srt_path = output / "narration_echo_kokoro.srt"

    sf.write(wav_path, combined, SR, subtype="PCM_16")
    subprocess.run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-i", str(wav_path),
        "-c:a", "libmp3lame", "-b:a", "192k", "-ar", "48000",
        str(mp3_path)
    ], check=True)
    write_srt(sentence_rows, srt_path)

    metadata = {
        "provider": "Kokoro-82M",
        "voice_id": VOICE,
        "voice_name": "Echo",
        "language": "American English",
        "pipeline": "Kokoro English pipeline (lang_code=a)",
        "speed": SPEED,
        "sample_rate_hz": SR,
        "duration_seconds": round(len(combined) / SR, 3),
        "wav": wav_path.name,
        "wav_size_bytes": wav_path.stat().st_size,
        "wav_size_mb_decimal": round(wav_path.stat().st_size / 1_000_000, 2),
        "mp3": mp3_path.name,
        "mp3_size_bytes": mp3_path.stat().st_size,
        "mp3_size_mb_decimal": round(mp3_path.stat().st_size / 1_000_000, 2),
        "srt": srt_path.name,
        "srt_size_bytes": srt_path.stat().st_size,
        "subtitles": "Timed SRT generated from actual Kokoro sentence timings; burned into the final master.",
        "sections": section_rows,
        "sentences": sentence_rows
    }
    (output / "kokoro_narration_report.json").write_text(
        json.dumps(metadata, indent=2),
        encoding="utf-8"
    )
    print(json.dumps(metadata, indent=2), flush=True)


if __name__ == "__main__":
    main()
