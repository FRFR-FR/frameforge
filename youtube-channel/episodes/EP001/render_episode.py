#!/usr/bin/env python3
"""Episode entry point for the shared Kokoro + moving B-roll renderer."""
from pathlib import Path
import subprocess
import sys

EPISODE_DIR = Path(__file__).resolve().parent
RENDERER = EPISODE_DIR.parents[1] / "tools" / "render_episode.py"

if not RENDERER.is_file():
    raise SystemExit(f"Shared renderer not found: {RENDERER}")

subprocess.run(
    [sys.executable, str(RENDERER), "--episode-dir", str(EPISODE_DIR)],
    check=True
)
