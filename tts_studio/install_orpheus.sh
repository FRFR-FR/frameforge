#!/usr/bin/env bash
set -euo pipefail
# Orpheus official inference stack. A compatible CUDA GPU is normally needed
# for the official vLLM inference route. Check the upstream README for updates.
python -m pip install --upgrade pip
python -m pip install orpheus-speech "vllm==0.7.3"
python -c "from orpheus_tts import OrpheusModel; print('Orpheus package import: OK')"
