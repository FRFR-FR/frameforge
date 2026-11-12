#!/usr/bin/env python3
"""Generate only allowlisted GAMEFORGE character dialogue with Kyutai Pocket TTS."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
import numpy as np
from scipy.io import wavfile

CUTSCENE_ROOT = Path(__file__).resolve().parents[1]
if str(CUTSCENE_ROOT) not in sys.path:
    sys.path.insert(0, str(CUTSCENE_ROOT))
from gameforge_cutscene_import import load_project  # noqa: E402


def generate(project_path: Path, output_dir: Path) -> Path:
    from pocket_tts import TTSModel

    project = load_project(project_path)
    lines = sorted(project["dialogue"], key=lambda x: (float(x["start"]), x["id"]))
    output_dir.mkdir(parents=True, exist_ok=True)
    lines_dir = output_dir / "lines"
    lines_dir.mkdir(parents=True, exist_ok=True)
    if not lines:
        path = output_dir / "voice_manifest.json"
        path.write_text(json.dumps({"provider": "kyutai-pocket-tts", "sample_rate": 24000, "lines": []}, indent=2) + "\n", encoding="utf-8")
        return path

    model = TTSModel.load_model()
    states: dict[str, object] = {}
    records = []
    for line in lines:
        voice = str(line["voice"]).lower()
        if voice not in {"eponine", "george", "azelma", "bill_boerst", "jean", "michael", "peter_yearsley", "stuart_bell", "charles"}:
            raise ValueError(f"Blocked non-allowlisted voice: {voice}")
        if voice not in states:
            states[voice] = model.get_state_for_audio_prompt(voice)
        audio = model.generate_audio(states[voice], str(line["text"]))
        audio_np = audio.detach().cpu().numpy() if hasattr(audio, "detach") else np.asarray(audio)
        audio_np = np.asarray(audio_np, dtype=np.float32).reshape(-1)
        if audio_np.size == 0:
            raise RuntimeError(f"Pocket TTS returned empty audio for {line['id']}")
        sample_rate = int(model.sample_rate)
        wav_path = lines_dir / f"{line['id']}.wav"
        pcm16 = np.clip(audio_np, -1.0, 1.0)
        wavfile.write(str(wav_path), sample_rate, (pcm16 * 32767.0).astype(np.int16))
        duration = float(len(pcm16)) / sample_rate
        records.append({
            "id": line["id"], "character_id": line["character_id"], "voice": voice,
            "text": line["text"], "start": float(line["start"]), "audio_path": str(wav_path.resolve()),
            "sample_rate": sample_rate, "samples": int(len(pcm16)), "duration": duration,
        })
        print(f"Generated {line['id']} ({voice}) — {duration:.3f}s")

    manifest = {"provider": "kyutai-pocket-tts", "language": "english", "sample_rate": int(model.sample_rate), "lines": records}
    path = output_dir / "voice_manifest.json"
    path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    print(generate(args.project, args.out))


if __name__ == "__main__":
    main()
