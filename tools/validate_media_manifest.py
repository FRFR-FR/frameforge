#!/usr/bin/env python3
"""Validate a FrameForge media manifest and enforce unique asset identifiers."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    from jsonschema import Draft202012Validator, FormatChecker
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "Missing dependency: install requirements-dev.txt before validating manifests."
    ) from exc

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCHEMA = ROOT / "schemas" / "media-asset-manifest-v1.schema.json"


def validate(manifest_path: Path, schema_path: Path) -> list[str]:
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
    except (OSError, json.JSONDecodeError, Exception) as exc:
        return ["Cannot load manifest or schema: " + str(exc)]

    errors: list[str] = []
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    for error in sorted(validator.iter_errors(data), key=lambda e: list(map(str, e.absolute_path))):
        location = "/".join(str(part) for part in error.absolute_path) or "(root)"
        errors.append(location + ": " + error.message)

    if isinstance(data, dict):
        seen: set[str] = set()
        for asset in data.get("assets", []):
            asset_id = asset.get("id") if isinstance(asset, dict) else None
            if not isinstance(asset_id, str):
                continue
            if asset_id in seen:
                errors.append("Duplicate asset id: " + asset_id)
            seen.add(asset_id)
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path, help="FrameForge media manifest JSON file")
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA, help="JSON Schema path")
    args = parser.parse_args()

    errors = validate(args.manifest, args.schema)
    if errors:
        print("FRAMEFORGE MEDIA MANIFEST VALIDATION FAILED")
        for error in errors:
            print(" - " + error)
        return 1
    print("FRAMEFORGE MEDIA MANIFEST VALIDATION PASSED: " + str(args.manifest))
    return 0


if __name__ == "__main__":
    sys.exit(main())
