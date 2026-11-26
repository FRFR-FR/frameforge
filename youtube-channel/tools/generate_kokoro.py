#!/usr/bin/env python3
"""Generate EP001 narration with Kokoro's American-English male Echo voice."""
from pathlib import Path
import argparse, json, re, subprocess
import numpy as np
import soundfile as sf
import torch
from kokoro import KPipeline

SR = 24000
VOICE = "am_echo"
SPEED = 0.96

def parse_sections(path: Path):
    lines = path.read_text(encoding="utf-8").splitlines()
    sections = []
    current = None
    for line in lines:
        m = re.match(r"^##\s+(\d{2})\s+[—-]\s+(.+)$", line.strip())
        if m:
            if current and current["text"].strip():
                sections.append(current)
            current = {"id": f"section_{int(m.group(1)):02d}", "title": m.group(2).strip(), "text": ""}
            continue
        if current is None:
            continue
        if not line.strip() or line.strip().startswith("#") or line.strip().startswith("Channel:") or line.strip().startswith("Target export:") or line.strip().startswith("Voice:"):
            continue
        current["text"] += " " + line.strip()
    if current and current["text"].strip():
        sections.append(current)
    for sec in sections:
        sec["text"] = re.sub(r"\s+", " ", sec["text"]).strip()
    if not sections:
        raise RuntimeError(f"No numbered narration sections found in {path}")
    return sections

def sentences(text):
    # Keep punctuation with each sentence so Kokoro receives natural prosody.
    bits = re.split(r"(?<=[.!?])\s+", text.strip())
    return [b.strip() for b in bits if b.strip()]

def synthesize(pipeline, text):
    waves = []
    for _, _, audio in pipeline(text, voice=VOICE, speed=SPEED):
        if hasattr(audio, "detach"):
            audio = audio.detach().cpu().numpy()
        arr = np.asarray(audio, dtype=np.float32).reshape(-1)
        if arr.size:
            waves.append(arr)
    if not waves:
        raise RuntimeError(f"Kokoro returned no audio for sentence: {text[:100]}")
    return np.concatenate(waves)

def srt_time(value):
    ms = max(0, int(round(value * 1000)))
    h, rem = divmod(ms, 3_600_000)
    m, rem = divmod(rem, 60_000)
    s, ms = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

def wrap_caption(text, limit=46):
    words = text.split()
    lines, current = [], ""
    for word in words:
        candidate = (current + " " + word).strip()
        if len(candidate) > limit and current:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    if len(lines) <= 2:
        return "\n".join(lines)
    # If a long sentence needs more than two lines, balance it into two readable lines.
    midpoint = (len(words) + 1) // 2
    return " ".join(words[:midpoint]) + "\n" + " ".join(words[midpoint:])

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--episode-dir", required=True)
    args = ap.parse_args()
    root = Path(args.episode_dir).resolve()
    output = root / "output"
    audio_dir = output / "audio"
    output.mkdir(parents=True, exist_ok=True)
    audio_dir.mkdir(parents=True, exist_ok=True)
    source = root / "narration.md"
    sections = parse_sections(source)

    print(f"Loading Kokoro English pipeline; voice={VOICE}", flush=True)
    torch.set_num_threads(max(1, min(4, torch.get_num_threads())))
    pipeline = KPipeline(lang_code="a")

    full_parts = []
    full_cursor = 0.0
    gap_between_sentences = np.zeros(int(0.18 * SR), dtype=np.float32)
    gap_between_sections = np.zeros(int(0.42 * SR), dtype=np.float32)
    srt_lines = []
    sentence_rows = []
    section_rows = []
    cue = 1

    for sec_index, sec in enumerate(sections, start=1):
        section_parts = []
        section_start = full_cursor
        for sent_index, sentence in enumerate(sentences(sec["text"]), start=1):
            wave = synthesize(pipeline, sentence)
            start = full_cursor
            section_parts.append(wave)
            full_parts.append(wave)
            duration = len(wave) / SR
            end = start + duration
            sentence_rows.append({
                "section_id": sec["id"], "sentence_index": sent_index,
                "text": sentence, "start_seconds": round(start, 3),
                "end_seconds": round(end, 3), "duration_seconds": round(duration, 3)
            })
            srt_lines.extend([
                str(cue),
                f"{srt_time(start)} --> {srt_time(end)}",
                wrap_caption(sentence),
                ""
            ])
            cue += 1
            full_cursor = end
            if sent_index < len(sentences(sec["text"])):
                section_parts.append(gap_between_sentences)
                full_parts.append(gap_between_sentences)
                full_cursor += len(gap_between_sentences) / SR

        # Keep the inter-section pause inside each section WAV so the B-roll timeline
        # duration exactly matches the combined narration timeline.
        if sec_index < len(sections):
            section_parts.append(gap_between_sections)
        section_wave = np.concatenate(section_parts) if section_parts else np.zeros(1, dtype=np.float32)
        section_path = audio_dir / f"{sec['id']}_echo.wav"
        sf.write(section_path, section_wave, SR, subtype="PCM_16")
        section_duration = len(section_wave) / SR
        section_rows.append({
            "id": sec["id"], "title": sec["title"],
            "audio_file": str(section_path.relative_to(root)),
            "duration_seconds": round(section_duration, 3),
            "start_seconds": round(section_start, 3)
        })
        if sec_index < len(sections):
            full_parts.append(gap_between_sections)
            full_cursor += len(gap_between_sections) / SR
        print(f"Echo voice section {sec_index}/{len(sections)}: {section_duration:.1f}s", flush=True)

    combined = np.concatenate(full_parts)
    wav_path = output / "narration_echo_kokoro.wav"
    mp3_path = output / "narration_echo_kokoro.mp3"
    sf.write(wav_path, combined, SR, subtype="PCM_16")
    subprocess.run([
        "ffmpeg", "-y", "-i", str(wav_path), "-c:a", "libmp3lame",
        "-b:a", "192k", "-ar", "48000", str(mp3_path)
    ], check=True)

    (output / "captions_echo_kokoro.srt").write_text("\n".join(srt_lines), encoding="utf-8")
    metadata = {
        "provider": "Kokoro-82M",
        "voice_id": VOICE,
        "voice_name": "Echo",
        "language": "American English",
        "speed": SPEED,
        "sample_rate_hz": SR,
        "duration_seconds": round(len(combined) / SR, 3),
        "wav": wav_path.name,
        "wav_size_bytes": wav_path.stat().st_size,
        "mp3": mp3_path.name,
        "mp3_size_bytes": mp3_path.stat().st_size,
        "caption_timing": "Sentence-level timestamps taken from the actual synthesized sentence audio",
        "sections": section_rows,
        "sentences": sentence_rows
    }
    (output / "kokoro_narration_report.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(json.dumps(metadata, indent=2), flush=True)

if __name__ == "__main__":
    main()
