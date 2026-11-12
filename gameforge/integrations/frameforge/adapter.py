"""Validate and translate FrameForge cinematic manifests for Godot playback."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any
from jsonschema import Draft202012Validator

SCHEMA = Path(__file__).with_name("manifest.schema.json")

def validate_manifest(manifest: dict[str, Any]) -> None:
    schema=json.loads(SCHEMA.read_text(encoding="utf-8"))
    errors=list(Draft202012Validator(schema).iter_errors(manifest))
    if errors:
        raise ValueError("Invalid FrameForge manifest: "+"; ".join(error.message for error in errors))
    duration=float(manifest["duration_seconds"])
    for shot in manifest["shots"]:
        if shot["start"] + shot["duration"] > duration + 1e-6:
            raise ValueError(f"Shot {shot['shot_id']} exceeds cinematic duration.")
    for cue in manifest["cues"]:
        if cue["start"] > duration + 1e-6 or cue.get("duration", 0) + cue["start"] > duration + 1e-6:
            raise ValueError(f"Cue {cue['cue_id']} exceeds cinematic duration.")
    _assert_no_duplicate_ids(manifest)

def _assert_no_duplicate_ids(manifest: dict[str, Any]) -> None:
    for field, key in (("shots","shot_id"),("cues","cue_id")):
        ids=[item[key] for item in manifest[field]]
        if len(ids)!=len(set(ids)):
            raise ValueError(f"Duplicate {key} values.")

def to_runtime_timeline(manifest: dict[str, Any]) -> dict[str, Any]:
    validate_manifest(manifest)
    cues=sorted(manifest["cues"],key=lambda cue:(float(cue["start"]),cue["kind"],cue["cue_id"]))
    return {"cinematic_id":manifest["cinematic_id"],"duration_seconds":manifest["duration_seconds"],
      "shots":manifest["shots"],"events":[{"at":cue["start"],"type":cue["kind"],"id":cue["cue_id"],"data":cue} for cue in cues]}

def convert_file(source: Path, destination: Path) -> None:
    manifest=json.loads(source.read_text(encoding="utf-8"))
    timeline=to_runtime_timeline(manifest)
    destination.parent.mkdir(parents=True,exist_ok=True)
    destination.write_text(json.dumps(timeline,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
