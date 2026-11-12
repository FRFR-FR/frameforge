#!/usr/bin/env python3
"""Force-align generated speech to the supplied text and create face/subtitle cues."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
from typing import Any
import numpy as np

CUTSCENE_ROOT = Path(__file__).resolve().parents[1]
if str(CUTSCENE_ROOT) not in sys.path:
    sys.path.insert(0, str(CUTSCENE_ROOT))
from gameforge_cutscene_import import load_project  # noqa: E402


def viseme_for_character(char: str) -> tuple[str, float]:
    c = char.lower()
    if c in "bmp":
        return "closed", 0.02
    if c in "fv":
        return "teeth", 0.12
    if c in "aeiou":
        return "open", 0.72 if c == "a" else 0.48
    if c in "wy":
        return "round", 0.35
    if c.isalpha():
        return "neutral", 0.18
    return "neutral", 0.08


def align(project_path: Path, voice_manifest_path: Path, output_path: Path, device: str = "cpu") -> Path:
    project = load_project(project_path)
    voice_data = json.loads(voice_manifest_path.read_text(encoding="utf-8"))
    if not voice_data["lines"]:
        output = {"alignment": "empty-dialogue", "lines": [], "visemes": []}
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
        return output_path

    import whisperx
    align_model, metadata = whisperx.load_align_model(language_code="en", device=device)
    aligned_lines: list[dict[str, Any]] = []
    all_visemes: list[dict[str, Any]] = []
    for record in voice_data["lines"]:
        audio_path = record["audio_path"]
        waveform = whisperx.load_audio(audio_path)
        duration = float(len(waveform)) / 16000.0
        segment = [{"start": 0.0, "end": duration, "text": record["text"]}]
        result = whisperx.align(
            segment, align_model, metadata, waveform, device,
            return_char_alignments=True, print_progress=False
        )
        chars = []
        for seg in result.get("segments", []):
            chars.extend(seg.get("chars") or [])
        if not chars:
            raise RuntimeError(
                f"WhisperX produced no character-level timestamps for {record['id']}; "
                "cannot create audio-grounded facial animation cues."
            )
        line_visemes = []
        for item in chars:
            char = str(item.get("char", ""))
            start, end = item.get("start"), item.get("end")
            if start is None or end is None or float(end) < float(start):
                continue
            viseme, opening = viseme_for_character(char)
            cue = {
                "character_id": record["character_id"], "dialogue_id": record["id"],
                "at": float(record["start"]) + float(start), "end": float(record["start"]) + float(end),
                "viseme": viseme, "jaw_open": opening, "source_char": char,
            }
            line_visemes.append(cue)
            all_visemes.append(cue)
        if not line_visemes:
            raise RuntimeError(f"No usable forced-alignment cues for {record['id']}")
        aligned_lines.append({
            "id": record["id"], "character_id": record["character_id"],
            "start": float(record["start"]), "audio_duration": float(record["duration"]),
            "end": float(record["start"]) + float(record["duration"]),
            "text": record["text"], "word_segments": result.get("word_segments", []),
            "character_cues": line_visemes,
        })

    output = {
        "alignment": "whisperx_forced_character_alignment", "device": device, "language": "en",
        "note": "Character-level acoustic alignment drives approximate viseme classes. Review facial sync before release.",
        "lines": aligned_lines, "visemes": sorted(all_visemes, key=lambda x: x["at"]),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True, type=Path)
    parser.add_argument("--voice-manifest", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--device", choices=("cpu",), default="cpu")
    args = parser.parse_args()
    print(align(args.project, args.voice_manifest, args.out, args.device))


if __name__ == "__main__":
    main()
