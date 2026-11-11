#!/usr/bin/env python3
"""Validate a GAMEFORGE GameSpec and prepare a reproducible project workspace.

This first compiler stage intentionally handles structured specifications.
Natural-language creative generation is a separate pluggable provider stage;
the compiler never fabricates market evidence or pretends a prototype is tested.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[2]
SCHEMA = ROOT / "schemas" / "game-spec.schema.json"


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def validate_spec(spec: dict[str, Any]) -> None:
    schema = load_json(SCHEMA)
    errors = sorted(
        Draft202012Validator(schema).iter_errors(spec),
        key=lambda error: list(error.absolute_path),
    )
    if errors:
        details = "\n".join(
            f"- {'/'.join(map(str, error.absolute_path)) or '<root>'}: {error.message}"
            for error in errors
        )
        raise ValueError("GameSpec validation failed:\n" + details)


def compile_workspace(spec_path: Path, output: Path) -> Path:
    spec = load_json(spec_path)
    validate_spec(spec)
    output.mkdir(parents=True, exist_ok=True)

    normalized = {
        "compiler": "gameforge-brief-compiler",
        "compiler_version": "0.1.0",
        "generation_mode": "full_autopilot",
        "quality_strategy": "adaptive",
        "spec": spec,
        "generation_status": {
            "spec_validated": True,
            "story_generated": False,
            "mechanics_prototyped": False,
            "vertical_slice_playtested": False,
            "market_research_verified": False,
            "release_ready": False,
        },
    }
    (output / "GAME_SPEC.json").write_text(
        json.dumps(normalized, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (output / "NEXT_STEPS.md").write_text(
        "# Generated GAMEFORGE workspace\n\n"
        f"**Project:** {spec['title']}\n\n"
        "The GameSpec passed structural validation. This is not yet a playable game. "
        "The next pipeline stages must generate and review the narrative, prototype "
        "the signature mechanic, create a vertical slice, profile target devices, "
        "and pass the release gates before this project can be called complete.\n",
        encoding="utf-8",
    )
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", required=True, type=Path, help="Path to a GameSpec JSON file")
    parser.add_argument("--out", required=True, type=Path, help="Output workspace directory")
    args = parser.parse_args()
    try:
        result = compile_workspace(args.spec, args.out)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        parser.error(str(exc))
    print(f"Validated GameSpec and created workspace: {result}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
