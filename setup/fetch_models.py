#!/usr/bin/env python3
"""Opt-in prefetch of Pocket TTS weights/voice assets and the English WhisperX aligner."""
from __future__ import annotations
import argparse
import sys
from pathlib import Path

VOICES = (
    "eponine", "george", "azelma", "bill_boerst", "jean",
    "michael", "peter_yearsley", "stuart_bell", "charles",
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Downloads GAMEFORGE speech/alignment model assets into the local model caches."
    )
    parser.add_argument("--voice-test-text", default="GAMEFORGE audio setup is ready.")
    args = parser.parse_args()

    try:
        from pocket_tts import TTSModel
        import whisperx
    except Exception as exc:
        print(f"Missing Python dependency: {exc}", file=sys.stderr)
        return 2

    print("Loading Kyutai Pocket TTS model (this downloads model weights on first run)...", flush=True)
    model = TTSModel.load_model()
    for voice in VOICES:
        print(f"Preparing approved voice: {voice}", flush=True)
        state = model.get_state_for_audio_prompt(voice)
        audio = model.generate_audio(state, args.voice_test_text)
        if audio is None or len(audio) == 0:
            raise RuntimeError(f"Kyutai returned empty test audio for voice '{voice}'.")
        del audio, state

    print("Loading the English WhisperX alignment model (this downloads model data on first run)...", flush=True)
    align_model, metadata = whisperx.load_align_model(language_code="en", device="cpu")
    if align_model is None or metadata is None:
        raise RuntimeError("WhisperX English aligner did not initialise.")
    del align_model, metadata

    print("Model prefetch completed. Weights and voice data remain in the local user cache.")
    print("Review the voice/model licensing notes in gameforge/cutscenes/VOICE_LICENSES.md before commercial release.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
