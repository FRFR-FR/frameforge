#!/usr/bin/env python3
"""Mix line WAVs at authored start times and write outline-only transparent subtitles."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
import numpy as np
from scipy.io import wavfile

CUTSCENE_ROOT = Path(__file__).resolve().parents[1]
if str(CUTSCENE_ROOT) not in sys.path:
    sys.path.insert(0, str(CUTSCENE_ROOT))
from gameforge_cutscene_import import load_project  # noqa: E402


def srt_stamp(seconds: float) -> str:
    total = max(0, round(seconds * 1000))
    hours, rem = divmod(total, 3_600_000)
    minutes, rem = divmod(rem, 60_000)
    secs, millis = divmod(rem, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def ass_stamp(seconds: float) -> str:
    total = max(0, round(seconds * 100))
    hours, rem = divmod(total, 360000)
    minutes, rem = divmod(rem, 6000)
    secs, centis = divmod(rem, 100)
    return f"{hours}:{minutes:02d}:{secs:02d}.{centis:02d}"


def assemble(project_path: Path, voice_manifest_path: Path, alignment_path: Path, out_dir: Path):
    project = load_project(project_path)
    voice_data = json.loads(voice_manifest_path.read_text(encoding="utf-8"))
    alignment = json.loads(alignment_path.read_text(encoding="utf-8"))
    out_dir.mkdir(parents=True, exist_ok=True)
    sample_rate = int(voice_data.get("sample_rate", 24000))
    total_samples = int(round(float(project["render"]["duration_seconds"]) * sample_rate))
    mix = np.zeros(total_samples, dtype=np.float32)
    srt_blocks, ass_events = [], []
    line_by_id = {line["id"]: line for line in alignment.get("lines", [])}

    for record in voice_data["lines"]:
        rate, audio = wavfile.read(record["audio_path"])
        if int(rate) != sample_rate:
            raise ValueError(f"Sample-rate mismatch for {record['id']}: {rate} != {sample_rate}")
        values = audio.astype(np.float32)
        if audio.dtype == np.int16:
            values /= 32768.0
        elif audio.dtype == np.int32:
            values /= 2147483648.0
        offset = int(round(float(record["start"]) * sample_rate))
        finish_sample = offset + len(values)
        if finish_sample > total_samples:
            raise ValueError(f"Dialogue {record['id']} audio runs past the project duration.")
        mix[offset:finish_sample] += values

        aligned = line_by_id.get(record["id"], {})
        start = float(record["start"])
        finish = float(aligned.get("end", start + float(record["duration"])))
        text = str(record["text"]).replace("\n", " ").strip()
        if finish <= start:
            finish = start + float(record["duration"])
        srt_blocks.append(
            f"{len(srt_blocks)+1}\n{srt_stamp(start)} --> {srt_stamp(finish)}\n{text}\n"
        )
        escaped = text.replace("{", "\\{").replace("}", "\\}")
        ass_events.append(
            "Dialogue: 0," + ass_stamp(start) + "," + ass_stamp(finish) +
            ",Default,,0,0,0,," + escaped
        )

    peak = float(np.max(np.abs(mix))) if mix.size else 0.0
    if peak > 0.98:
        mix *= 0.98 / peak
    wav_path = out_dir / "dialogue_mix.wav"
    wavfile.write(str(wav_path), sample_rate, (np.clip(mix, -1, 1) * 32767).astype(np.int16))

    srt_path = out_dir / "subtitles.srt"
    srt_path.write_text("\n".join(srt_blocks) + ("\n" if srt_blocks else ""), encoding="utf-8")
    ass_path = out_dir / "subtitles.ass"
    ass_header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,48,&H00FFFFFF,&H0000FFFF,&H00000000,&HFF000000,-1,0,1,3,1,2,48,48,44,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    ass_path.write_text(ass_header + "\n".join(ass_events) + ("\n" if ass_events else ""), encoding="utf-8")
    return wav_path, srt_path, ass_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True, type=Path)
    parser.add_argument("--voice-manifest", required=True, type=Path)
    parser.add_argument("--alignment", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    for path in assemble(args.project, args.voice_manifest, args.alignment, args.out):
        print(path)


if __name__ == "__main__":
    main()
