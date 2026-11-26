# Ballpoint Pen — FrameForge Kokoro Echo Narration

This project generates the separate voiceover for the 30-second ballpoint-pen explainer.

- Voice: Kokoro Echo, am_echo (American English)
- Model: Kokoro-82M
- Sample rate: 24 kHz, mono
- Output: MP3 at 160 kbps, plus a WAV master
- CTA segment begins at exactly 10.00 seconds in the PCM timeline
- There is no fallback voice. If Echo cannot be loaded, the workflow fails instead of substituting another voice.

## Run in GitHub Actions

Open Actions → FrameForge — Ballpoint Pen Kokoro Echo → Run workflow. The workflow installs Kokoro and its CPU PyTorch runtime, renders the voiceover, verifies the MP3 with FFprobe, uploads an artifact, and commits the generated audio under the output folder.

The model weights are downloaded at runtime from the official Hugging Face model repository. They are not committed to Git.

## Local run

Use Python 3.12, install the CPU PyTorch build, install Kokoro 0.9.4, install FFmpeg and espeak-ng, then run:

    python projects/ballpoint-pen-narrative/generate_echo.py

## Narration

See narration.txt. The timing is split into a 10-second hook, a 3.704-second CTA, and a closing explanation to fill the 30-second master exactly.
