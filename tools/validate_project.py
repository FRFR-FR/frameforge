#!/usr/bin/env python3
"""Validate a FrameForge V2 project against its schema and cross-references."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

try:
    from jsonschema import Draft202012Validator, FormatChecker
except ImportError as exc:  # pragma: no cover - exercised by the CLI environment
    raise SystemExit(
        "Missing dependency: install requirements-dev.txt before validating projects."
    ) from exc

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCHEMA = ROOT / "schemas" / "frameforge-project-v2.schema.json"


def _unique_ids(items: list[dict[str, Any]], label: str, errors: list[str]) -> set[str]:
    seen: set[str] = set()
    for item in items:
        item_id = item.get("id")
        if not isinstance(item_id, str):
            continue
        if item_id in seen:
            errors.append("Duplicate " + label + " id: " + item_id)
        seen.add(item_id)
    return seen


def semantic_errors(data: dict[str, Any]) -> list[str]:
    """Check references and timeline bounds that are awkward to express in JSON Schema."""
    errors: list[str] = []
    assets = data.get("assets", [])
    sequences = data.get("sequences", [])
    asset_ids = _unique_ids(assets, "asset", errors)
    sequence_ids = _unique_ids(sequences, "sequence", errors)

    all_clip_ids: set[str] = set()
    for sequence in sequences:
        sequence_id = sequence.get("id", "(unknown sequence)")
        duration = sequence.get("duration_frames", 0)
        tracks = sequence.get("tracks", [])
        _unique_ids(tracks, "track in " + str(sequence_id), errors)
        for track in tracks:
            clips = track.get("clips", [])
            _unique_ids(clips, "clip in " + str(sequence_id) + "/" + str(track.get("id", "?")), errors)
            for clip in clips:
                clip_id = clip.get("id")
                if isinstance(clip_id, str):
                    if clip_id in all_clip_ids:
                        errors.append("Clip id is not project-unique: " + clip_id)
                    all_clip_ids.add(clip_id)

                start = clip.get("start_frame", 0)
                length = clip.get("duration_frames", 0)
                if isinstance(start, int) and isinstance(length, int) and start + length > duration:
                    errors.append(
                        "Clip " + str(clip_id) + " ends after sequence " +
                        str(sequence_id) + " duration (" + str(start + length) +
                        " > " + str(duration) + " frames)."
                    )

                if clip.get("kind") == "asset" and clip.get("asset_id") not in asset_ids:
                    errors.append(
                        "Clip " + str(clip_id) + " references missing asset: " +
                        str(clip.get("asset_id"))
                    )
                if clip.get("kind") == "sequence" and clip.get("sequence_id") not in sequence_ids:
                    errors.append(
                        "Clip " + str(clip_id) + " references missing sequence: " +
                        str(clip.get("sequence_id"))
                    )

    research = data.get("research", {})
    source_ids = _unique_ids(research.get("sources", []), "research source", errors)
    claim_ids = _unique_ids(research.get("claims", []), "research claim", errors)
    for claim in research.get("claims", []):
        for source_id in claim.get("source_ids", []):
            if source_id not in source_ids:
                errors.append(
                    "Research claim " + str(claim.get("id")) +
                    " references missing research source: " + str(source_id)
                )
    for sequence in sequences:
        for track in sequence.get("tracks", []):
            for clip in track.get("clips", []):
                for claim_id in clip.get("evidence_claim_ids", []):
                    if claim_id not in claim_ids:
                        errors.append(
                            "Clip " + str(clip.get("id")) +
                            " references missing evidence claim: " + str(claim_id)
                        )
    return errors


def validate(project_path: Path, schema_path: Path) -> list[str]:
    errors: list[str] = []
    try:
        data = json.loads(project_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return ["Cannot read project JSON: " + str(exc)]

    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
    except (OSError, json.JSONDecodeError, Exception) as exc:
        return ["Cannot load or validate project schema: " + str(exc)]

    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    for error in sorted(validator.iter_errors(data), key=lambda e: list(map(str, e.absolute_path))):
        location = "/".join(str(part) for part in error.absolute_path) or "(root)"
        errors.append(location + ": " + error.message)

    if isinstance(data, dict):
        errors.extend(semantic_errors(data))
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path, help="FrameForge V2 project JSON file")
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA, help="JSON Schema path")
    args = parser.parse_args()

    errors = validate(args.project, args.schema)
    if errors:
        print("FRAMEFORGE PROJECT VALIDATION FAILED")
        for error in errors:
            print(" - " + error)
        return 1
    print("FRAMEFORGE PROJECT VALIDATION PASSED: " + str(args.project))
    return 0


if __name__ == "__main__":
    sys.exit(main())
