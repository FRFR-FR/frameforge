#!/usr/bin/env python3
"""Fail-closed preproduction validator for the BROWN feature-film pipeline."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = Path(__file__).resolve().parent / "featurefilm_manifest.json"
REQUIRED_CHARACTER_COUNT = 65

def read_json(path: Path, errors: list[str]):
    if not path.is_file():
        errors.append(f"Missing required file: {path.relative_to(ROOT)}")
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        errors.append(f"Invalid JSON in {path.relative_to(ROOT)}: {exc}")
        return None

def existing_repo_file(value, field: str, errors: list[str]) -> bool:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{field}: missing repository-relative file path")
        return False
    path = (ROOT / value).resolve()
    try:
        path.relative_to(ROOT.resolve())
    except ValueError:
        errors.append(f"{field}: path escapes repository: {value}")
        return False
    if not path.is_file():
        errors.append(f"{field}: file does not exist: {value}")
        return False
    return True

def validate() -> dict:
    errors: list[str] = []
    notes: list[str] = []
    manifest = read_json(MANIFEST_PATH, errors)
    if not manifest:
        return {"ready": False, "errors": errors, "notes": notes}

    expected = {
        "runtime_seconds": 14400,
        "segment_count": 240,
        "segment_duration_seconds": 60,
    }
    for key, value in expected.items():
        if manifest.get(key) != value:
            errors.append(f"Manifest {key} must be {value}; found {manifest.get(key)!r}")
    render = manifest.get("render", {})
    for key, value in {"width": 1280, "height": 720, "fps": 20,
                       "frames_per_segment": 1200, "total_frames": 288000}.items():
        if render.get(key) != value:
            errors.append(f"Render setting {key} must be {value}; found {render.get(key)!r}")
    if manifest.get("scheduling", {}).get("max_parallel_segments") != 3:
        errors.append("Maximum parallel segments must remain exactly 3")

    paths = manifest.get("paths", {})
    existing_repo_file(paths.get("source_book_pdf"), "source Book One PDF", errors)
    existing_repo_file(paths.get("story_bible_pdf"), "source story bible PDF", errors)
    story = read_json(ROOT / paths.get("story_breakdown", "production/story_breakdown.json"), errors)
    assets = read_json(ROOT / paths.get("asset_registry", "production/asset_registry.json"), errors)
    approvals = read_json(ROOT / paths.get("approvals", "production/approvals.json"), errors)

    expected_chapters = set(["PROLOGUE"] + [f"CHAPTER_{i:02d}" for i in range(1, 73)])
    scene_ids: set[str] = set()
    linked_asset_ids: set[str] = set()
    if story:
        scenes = story.get("scenes", [])
        covered: set[str] = set()
        for index, scene in enumerate(scenes):
            label = f"story_breakdown.scenes[{index}]"
            chapter = scene.get("chapter_id")
            if chapter not in expected_chapters:
                errors.append(f"{label}: invalid chapter_id {chapter!r}")
            else:
                covered.add(chapter)
            sid = scene.get("scene_id")
            if not isinstance(sid, str) or not sid.strip() or sid in scene_ids:
                errors.append(f"{label}: scene_id must be non-empty and unique")
            else:
                scene_ids.add(sid)
            for field in ("source_summary", "action_plan", "continuity_notes"):
                if not isinstance(scene.get(field), str) or not scene[field].strip():
                    errors.append(f"{label}: {field} is required")
            for field in ("dialogue_beats", "character_ids", "location_ids", "asset_ids"):
                if not isinstance(scene.get(field), list):
                    errors.append(f"{label}: {field} must be an array")
            linked_asset_ids.update(scene.get("asset_ids", []) if isinstance(scene.get("asset_ids"), list) else [])
        missing = sorted(expected_chapters - covered)
        if missing:
            errors.append("Source breakdown does not cover: " + ", ".join(missing))
        if not scenes:
            errors.append("Source breakdown contains no scene records")

    asset_ids: set[str] = set()
    character_count = 0
    required_categories = set(manifest.get("required_asset_categories", []))
    if assets:
        categories = {item.get("category_id"): item for item in assets.get("categories", [])}
        missing_categories = sorted(required_categories - set(categories))
        if missing_categories:
            errors.append("Asset registry missing categories: " + ", ".join(missing_categories))
        for category_id in sorted(required_categories):
            category = categories.get(category_id)
            if not category:
                continue
            items = category.get("items", [])
            if category.get("status") != "approved":
                errors.append(f"Asset category {category_id} is not approved")
            if not isinstance(items, list) or not items:
                errors.append(f"Asset category {category_id} has no designed assets")
                continue
            for index, item in enumerate(items):
                label = f"asset_registry.{category_id}[{index}]"
                aid = item.get("asset_id")
                if not isinstance(aid, str) or not aid.strip() or aid in asset_ids:
                    errors.append(f"{label}: asset_id must be non-empty and unique")
                else:
                    asset_ids.add(aid)
                if item.get("review_status") != "approved":
                    errors.append(f"{label}: review_status must be approved")
                existing_repo_file(item.get("asset_file"), label + ".asset_file", errors)
                existing_repo_file(item.get("review_evidence"), label + ".review_evidence", errors)
                if category_id == "characters":
                    character_count += 1
                    for field in ("model_sheet", "turntable", "model_blend", "rig_blend", "facial_test"):
                        existing_repo_file(item.get(field), label + "." + field, errors)
        if character_count < REQUIRED_CHARACTER_COUNT:
            errors.append(f"Character library has {character_count} approved character records; {REQUIRED_CHARACTER_COUNT} named characters are required")
        unresolved = sorted(linked_asset_ids - asset_ids)
        if unresolved:
            errors.append("Story scenes reference unknown asset IDs: " + ", ".join(unresolved[:30]))

    if approvals:
        approval_map = approvals.get("approvals", {})
        for key in manifest.get("approvals_required", []):
            record = approval_map.get(key, {})
            if record.get("approved") is not True:
                errors.append(f"Production approval missing: {key}")
            existing_repo_file(record.get("evidence_file"), f"approval.{key}.evidence_file", errors)

    for key, label in (("approved_master_blend", "approved Blender master scene"),
                       ("master_audio_mix", "approved full-length audio mix")):
        existing_repo_file(paths.get(key), label, errors)

    notes.append("All model sheets, rigs, environment packs and prop packs must be reviewed as actual visual assets; a filename alone is not a quality approval.")
    notes.append("The 240 one-minute segments equal 4 hours and 288,000 frames at 20 fps.")
    notes.append("Technical checks cannot guarantee studio-level artistry; human visual QC remains a hard gate.")
    return {
        "ready": not errors,
        "project": manifest.get("project"),
        "runtime_seconds": manifest.get("runtime_seconds"),
        "segment_count": manifest.get("segment_count"),
        "segment_duration_seconds": manifest.get("segment_duration_seconds"),
        "render": render,
        "approved_character_records": character_count,
        "story_scenes": len(story.get("scenes", [])) if story else 0,
        "approved_asset_ids": len(asset_ids),
        "errors": errors,
        "notes": notes,
    }

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, help="Write JSON readiness report to this path")
    parser.add_argument("--require-render-ready", action="store_true",
                        help="Exit non-zero unless every preproduction gate is satisfied")
    parser.add_argument("--print-ready", action="store_true",
                        help="Print only true or false, for workflow output")
    args = parser.parse_args()
    report = validate()
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if args.print_ready:
        print("true" if report["ready"] else "false")
    else:
        print(json.dumps(report, indent=2))
    if args.require_render_ready and not report["ready"]:
        return 2
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
