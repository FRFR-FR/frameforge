"""Import shim for running the audio subcommands directly from the repository root."""
from __future__ import annotations
import sys
from pathlib import Path
CUTSCENE_ROOT = Path(__file__).resolve().parent
if str(CUTSCENE_ROOT) not in sys.path:
    sys.path.insert(0, str(CUTSCENE_ROOT))
from contracts import load_json, validate_project  # noqa: E402


def load_project(path: str | Path) -> dict:
    project = load_json(path)
    return validate_project(project)
