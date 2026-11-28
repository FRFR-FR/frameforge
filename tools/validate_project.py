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
    if not isinstance(items, list):
        return seen
    for item in items:
        if not isinstance(item, dict):
            continue
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
    raw_assets = data.get("assets", [])
    raw_sequences = data.get("sequences", [])
    assets = raw_assets if isinstance(raw_assets, list) else []
    sequences = raw_sequences if isinstance(raw_sequences, list) else []
    asset_ids = _unique_ids(assets, "asset", errors)
    sequence_ids = _unique_ids(sequences, "sequence", errors)

    all_clip_ids: set[str] = set()
    for sequence in sequences:
        if not isinstance(sequence, dict):
            continue
        sequence_id = sequence.get("id", "(unknown sequence)")
        duration = sequence.get("duration_frames", 0)
        raw_tracks = sequence.get("tracks", [])
        tracks = raw_tracks if isinstance(raw_tracks, list) else []
        _unique_ids(tracks, "track in " + str(sequence_id), errors)
        for track in tracks:
            if not isinstance(track, dict):
                continue
            raw_clips = track.get("clips", [])
            clips = raw_clips if isinstance(raw_clips, list) else []
            _unique_ids(clips, "clip in " + str(sequence_id) + "/" + str(track.get("id", "?")), errors)
            for clip in clips:
                if not isinstance(clip, dict):
                    continue
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

    raw_research = data.get("research", {})
    research = raw_research if isinstance(raw_research, dict) else {}
    source_ids = _unique_ids(research.get("sources", []), "research source", errors)
    claim_ids = _unique_ids(research.get("claims", []), "research claim", errors)
    raw_claims = research.get("claims", [])
    claims = raw_claims if isinstance(raw_claims, list) else []
    source_lookup = {
        item.get("id"): item for item in research.get("sources", [])
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    for claim in claims:
        if not isinstance(claim, dict):
            continue
        raw_source_ids = claim.get("source_ids", [])
        cited_source_ids = raw_source_ids if isinstance(raw_source_ids, list) else []
        for source_id in cited_source_ids:
            if source_id not in source_ids:
                errors.append(
                    "Research claim " + str(claim.get("id")) +
                    " references missing research source: " + str(source_id)
                )
        locations = claim.get("evidence_locations", [])
        for location in locations if isinstance(locations, list) else []:
            if not isinstance(location, dict):
                errors.append("Research claim " + str(claim.get("id")) + " has an invalid evidence location.")
                continue
            source_id = location.get("source_id")
            if source_id not in source_ids:
                errors.append(
                    "Research claim " + str(claim.get("id")) +
                    " evidence location references missing source: " + str(source_id)
                )
            if source_id not in cited_source_ids:
                errors.append(
                    "Research claim " + str(claim.get("id")) +
                    " evidence location source is not linked to the claim: " + str(source_id)
                )
            if not isinstance(location.get("locator"), str) or not location.get("locator", "").strip():
                errors.append("Research claim " + str(claim.get("id")) + " evidence location is missing its page/section/timecode locator.")
            start = location.get("start_time_seconds")
            end = location.get("end_time_seconds")
            if start is not None and (not isinstance(start, (int, float)) or start < 0):
                errors.append("Research claim " + str(claim.get("id")) + " has an invalid evidence start timestamp.")
            if end is not None and (not isinstance(end, (int, float)) or end < 0):
                errors.append("Research claim " + str(claim.get("id")) + " has an invalid evidence end timestamp.")
            if isinstance(start, (int, float)) and isinstance(end, (int, float)) and end < start:
                errors.append("Research claim " + str(claim.get("id")) + " evidence end timestamp precedes its start timestamp.")
    for sequence in sequences:
        if not isinstance(sequence, dict):
            continue
        raw_tracks = sequence.get("tracks", [])
        for track in raw_tracks if isinstance(raw_tracks, list) else []:
            if not isinstance(track, dict):
                continue
            raw_clips = track.get("clips", [])
            for clip in raw_clips if isinstance(raw_clips, list) else []:
                if not isinstance(clip, dict):
                    continue
                raw_evidence_ids = clip.get("evidence_claim_ids", [])
                for claim_id in raw_evidence_ids if isinstance(raw_evidence_ids, list) else []:
                    if claim_id not in claim_ids:
                        errors.append(
                            "Clip " + str(clip.get("id")) +
                            " references missing evidence claim: " + str(claim_id)
                        )

    reference_ids = _unique_ids(research.get("reference_videos", []), "reference video", errors)
    raw_references = research.get("reference_videos", [])
    for reference in raw_references if isinstance(raw_references, list) else []:
        if isinstance(reference, dict) and reference.get("reference_only") is not True:
            errors.append("Reference video must be marked reference_only: " + str(reference.get("id")))

    raw_plan = data.get("shot_plan")
    if raw_plan is not None:
        if not isinstance(raw_plan, dict) or not isinstance(raw_plan.get("beats"), list):
            errors.append("Shot plan must contain a beats array.")
        else:
            beat_ids = _unique_ids(raw_plan["beats"], "shot beat", errors)
            for beat in raw_plan["beats"]:
                if not isinstance(beat, dict):
                    continue
                start = beat.get("start_frame")
                end = beat.get("end_frame")
                if not isinstance(start, int) or not isinstance(end, int) or start < 0 or end <= start:
                    errors.append("Shot beat has invalid frame timing: " + str(beat.get("id")))
                raw_linked_claims = beat.get("evidence_claim_ids", [])
                linked_claims = raw_linked_claims if isinstance(raw_linked_claims, list) else []
                proof_role = beat.get("visual_role") in {"factual_evidence", "comparative_evidence"}
                if proof_role and not linked_claims:
                    errors.append("Evidence shot beat must reference at least one claim: " + str(beat.get("id")))
                for asset_id in beat.get("asset_ids", []) if isinstance(beat.get("asset_ids", []), list) else []:
                    if asset_id not in asset_ids:
                        errors.append(
                            "Shot beat " + str(beat.get("id")) +
                            " references missing asset: " + str(asset_id)
                        )
                for claim_id in linked_claims:
                    if claim_id not in claim_ids:
                        errors.append(
                            "Shot beat " + str(beat.get("id")) +
                            " references missing research claim: " + str(claim_id)
                        )
                        continue
                    claim = next((item for item in claims if isinstance(item, dict) and item.get("id") == claim_id), None)
                    if proof_role and claim and (
                        claim.get("verification_status") != "verified" or
                        not claim.get("source_ids") or
                        claim.get("classification") not in {"factual", "comparative"}
                    ):
                        errors.append(
                            "Shot beat " + str(beat.get("id")) +
                            " cannot present an unverified or unsourced claim as evidence: " + str(claim_id)
                        )
                    if proof_role and claim:
                        for source_id in claim.get("source_ids", []):
                            source = source_lookup.get(source_id, {})
                            if source.get("access_status") != "public":
                                errors.append(
                                    "Evidence claim " + str(claim_id) +
                                    " relies on a source not marked publicly accessible: " + str(source_id)
                                )

                requirement = beat.get("evidence_requirement", "none")
                media_mix = beat.get("media_mix", [])
                linked_assets = [
                    next((asset for asset in assets if isinstance(asset, dict) and asset.get("id") == asset_id), None)
                    for asset_id in beat.get("asset_ids", [])
                ]
                if requirement == "actual_footage":
                    if "source_footage" not in media_mix:
                        errors.append("Shot beat " + str(beat.get("id")) + " requires source_footage media.")
                    if not any(asset and asset.get("media_type") == "video" for asset in linked_assets):
                        errors.append("Shot beat " + str(beat.get("id")) + " requires a linked video asset for actual footage.")
                if requirement == "official_screenshot":
                    if "screenshots" not in media_mix:
                        errors.append("Shot beat " + str(beat.get("id")) + " requires screenshots media.")
                    if not any(asset and asset.get("media_type") == "image" for asset in linked_assets):
                        errors.append("Shot beat " + str(beat.get("id")) + " requires a linked image asset for an official screenshot.")

    raw_rights_review = data.get("rights_review")
    if isinstance(raw_rights_review, dict):
        reviews = raw_rights_review.get("asset_reviews", [])
        review_ids: set[str] = set()
        for review in reviews if isinstance(reviews, list) else []:
            if not isinstance(review, dict):
                continue
            asset_id = review.get("asset_id")
            if isinstance(asset_id, str) and asset_id in review_ids:
                errors.append("Duplicate asset rights review: " + asset_id)
            if isinstance(asset_id, str):
                review_ids.add(asset_id)
            if asset_id not in asset_ids:
                errors.append("Rights review references missing asset: " + str(asset_id))
            if review.get("decision") in {"approved", "approved_with_limits"} and (
                len(str(review.get("basis", "")).strip()) < 10 or
                not str(review.get("reviewer", "")).strip() or
                not review.get("reviewed_at")
            ):
                errors.append("Approved rights review needs a basis, reviewer and review date: " + str(asset_id))
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
