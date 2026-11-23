#!/usr/bin/env bash
set -euo pipefail
# Install official F5-TTS inference package into the active Python environment.
# Use Python 3.10+ and install a PyTorch build matching your machine first.
python -m pip install --upgrade pip
python -m pip install f5-tts
python -c "from f5_tts.api import F5TTS; print('F5-TTS package import: OK')"
