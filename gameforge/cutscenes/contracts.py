"""Validation and adaptive CPU-render policy for GAMEFORGE cutscenes."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
SCHEMA_PATH = ROOT / "config" / "project.schema.json"
VOICE_PATH = ROOT / "config" / "voices.json"
PROFILES = {
    "low": {"samples": 8, "threads_cap": 2, "resolution": (1280, 720), "description": "CPU-first low-end profile"},
    "balanced": {"samples": 16, "threads_cap": 4, "resolution": (1920, 1080), "description": "Balanced render profile"},
    "high": {"samples": 32, "threads_cap": 8, "resolution": (1920, 1080), "description": "High-sample CPU render profile"},
}
MAX_WIDTH, MAX_HEIGHT, MAX_FPS, MAX_SECONDS = 1920, 1080, 30, 600


def load_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def allowed_voice_ids() -> set[str]:
    data = load_json(VOICE_PATH)
    return {item["id"] for item in data["allowed_voices"]}


def validate_project(project: dict[str, Any]) -> dict[str, Any]:
    # Blender ships its own Python runtime and may not have jsonschema installed.
    # Use the JSON Schema validator where available; the explicit policy checks
    # below remain mandatory in both Blender and system Python.
    try:
        from jsonschema import Draft202012Validator
    except ImportError:
        Draft202012Validator = None
    if Draft202012Validator is not None:
        schema = load_json(SCHEMA_PATH)
        errors = sorted(Draft202012Validator(schema).iter_errors(project), key=lambda e: list(e.absolute_path))
        if errors:
            detail = "\n".join(f"- {'/'.join(map(str, e.absolute_path)) or '<root>'}: {e.message}" for e in errors)
            raise ValueError("Cutscene manifest failed schema validation:\n" + detail)

    render = project["render"]
    if render["width"] > MAX_WIDTH or render["height"] > MAX_HEIGHT:
        raise ValueError("GAMEFORGE cutscenes are capped at 1920x1080 (1080p).")
    if render["fps"] > MAX_FPS:
        raise ValueError("GAMEFORGE cutscene frame rate is capped at 30 FPS.")
    if render["duration_seconds"] > MAX_SECONDS:
        raise ValueError("A single GAMEFORGE cutscene may not exceed 600 seconds.")
    if (render["width"], render["height"]) not in {(1280, 720), (1920, 1080)}:
        raise ValueError("Select exactly 1280x720 (720p) or 1920x1080 (1080p).")
    profile = render.get("profile", "balanced")
    if profile not in PROFILES:
        raise ValueError(f"Unsupported render profile: {profile}")

    voice_ids = allowed_voice_ids()
    character_ids: set[str] = set()
    character_voice: dict[str, str] = {}
    for character in project["characters"]:
        if character["id"] in character_ids:
            raise ValueError(f"Duplicate character id: {character['id']}")
        character_ids.add(character["id"])
        if character["voice"] not in voice_ids:
            raise ValueError(f"Voice '{character['voice']}' is not on the approved Kyutai voice allowlist.")
        character_voice[character["id"]] = character["voice"]
    line_ids: set[str] = set()
    for line in project["dialogue"]:
        if line["id"] in line_ids:
            raise ValueError(f"Duplicate dialogue id: {line['id']}")
        line_ids.add(line["id"])
        if line["character_id"] not in character_ids:
            raise ValueError(f"Dialogue line {line['id']} references an unknown character.")
        if line["voice"] not in voice_ids:
            raise ValueError(f"Dialogue line {line['id']} uses a voice outside the allowlist.")
        if line["voice"] != character_voice[line["character_id"]]:
            raise ValueError(f"Dialogue line {line['id']} voice does not match its character's assigned voice.")
        if line["start"] >= render["duration_seconds"]:
            raise ValueError(f"Dialogue line {line['id']} starts after the end of the cutscene.")
    return project


def render_policy(project: dict[str, Any], cpu_count: int | None = None) -> dict[str, Any]:
    import os
    render = project["render"]
    profile = PROFILES[render.get("profile", "balanced")]
    cores = cpu_count or os.cpu_count() or 2
    return {
        "device": "CPU",
        "threads": max(1, min(int(cores), profile["threads_cap"])),
        "samples": min(int(render.get("samples", profile["samples"])), profile["samples"]),
        "width": min(int(render["width"]), MAX_WIDTH),
        "height": min(int(render["height"]), MAX_HEIGHT),
        "fps": min(int(render["fps"]), MAX_FPS),
        "tile_size": 128,
        "denoising": True,
        "profile": render.get("profile", "balanced"),
        "policy_description": profile["description"],
    }
