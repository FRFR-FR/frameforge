#!/usr/bin/env python3
"""Sequential, topic-specific Pixabay B-roll acquisition with per-asset rights records."""
from pathlib import Path
from datetime import datetime, timezone, timedelta
import argparse
import csv
import hashlib
import json
import os
import re
import subprocess
import time

import requests

API = "https://pixabay.com/api/videos/"
LICENSE = "Pixabay Content License; used only as part of a new edited documentary, never standalone."
LICENSE_URL = "https://pixabay.com/service/license-summary/"
TERMS_URL = "https://pixabay.com/service/terms/"
API_DOCS_URL = "https://pixabay.com/api/docs/"
SHOT_SECONDS = 7.0
MAX_SOURCE_USES = 2
MAX_REJECTION_CHECKS = 2
MIN_SECTION_CLIPS = 4
REQUEST_SPACING_SECONDS = 1.0


def cache_file(query):
    import hashlib
    key = hashlib.sha256(query.lower().encode("utf-8")).hexdigest()[:20]
    return Path.home() / ".cache" / "pixabay" / f"{key}.json"


def search(query, api_key):
    cache = cache_file(query)
    cache.parent.mkdir(parents=True, exist_ok=True)
    if cache.exists():
        age = datetime.now(timezone.utc) - datetime.fromtimestamp(cache.stat().st_mtime, timezone.utc)
        if age < timedelta(hours=24):
            return json.loads(cache.read_text(encoding="utf-8"))

    params = {
        "key": api_key,
        "q": query,
        "video_type": "film",
        "safesearch": "true",
        "order": "popular",
        "per_page": 30,
        "min_width": 1280,
        "min_height": 720
    }
    response = requests.get(API, params=params, timeout=45)
    response.raise_for_status()
    data = response.json()
    cache.write_text(json.dumps(data), encoding="utf-8")
    time.sleep(REQUEST_SPACING_SECONDS)
    return data


STOP = {"the", "and", "at", "in", "a", "an", "of", "to", "with", "by", "on", "under", "from", "how", "why", "for"}


def token_set(text):
    return {
        token for token in re.findall(r"[a-z0-9]+", str(text).lower())
        if token not in STOP and len(token) > 2
    }


def group_hits(tags, groups):
    tag_tokens = token_set(tags)
    return sum(1 for group in groups if tag_tokens.intersection(set(group)))


def section_minimum(root, section):
    seconds = float(section.get("duration_seconds", 0) or 0)
    audio_file = section.get("audio_file")
    if audio_file:
        candidate = root / audio_file
        if candidate.is_file():
            seconds = float(subprocess.check_output([
                "ffprobe", "-v", "error", "-show_entries", "format=duration",
                "-of", "csv=p=0", str(candidate)
            ], text=True).strip())
    seconds = max(0.0, seconds - 12.0)
    shots = max(1, int((seconds + SHOT_SECONDS - 0.001) // SHOT_SECONDS) + 1)
    return max(MIN_SECTION_CLIPS, (shots + MAX_SOURCE_USES - 1) // MAX_SOURCE_USES)


def reject_once_or_twice(rejected, asset_id):
    current = rejected.get(asset_id, 0)
    if current >= MAX_REJECTION_CHECKS:
        return False
    rejected[asset_id] = current + 1
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--episode-dir", required=True)
    args = parser.parse_args()
    root = Path(args.episode_dir).resolve()

    plan_file = root / "assets" / "broll_plan.json"
    if not plan_file.is_file():
        raise SystemExit("A curated episode-specific broll_plan.json is required. Generic fallback footage is disabled.")
    plan = json.loads(plan_file.read_text(encoding="utf-8"))
    if not isinstance(plan, list) or len(plan) != 10:
        raise SystemExit("The episode-specific B-roll plan must contain ten section entries.")

    for item in plan:
        required = {"id", "title", "query", "count", "match_groups"}
        if not required.issubset(item):
            raise SystemExit(f"Invalid B-roll plan item; required keys: {sorted(required)}")
        if not re.fullmatch(r"section_[0-9]{2}", item["id"]):
            raise SystemExit(f"Invalid section id: {item['id']}")
        if not isinstance(item["match_groups"], list) or len(item["match_groups"]) < 2:
            raise SystemExit(f"{item['id']} needs at least two subject-specific relevance groups.")
        item["queries"] = list(dict.fromkeys([item["query"], *item.get("queries", [])]))
        item["count"] = max(MIN_SECTION_CLIPS, int(item.get("count", MIN_SECTION_CLIPS)))

    key = os.environ.get("PIXABAY_API_KEY", "").strip()
    if not key:
        raise SystemExit("PIXABAY_API_KEY is missing. No unrelated substitute footage will be used.")

    report_path = root / "output" / "kokoro_narration_report.json"
    if not report_path.is_file():
        raise SystemExit("Kokoro section timing report is missing; clip counts cannot be budgeted.")
    narration_report = json.loads(report_path.read_text(encoding="utf-8"))
    narration_sections = {section.get("id"): section for section in narration_report.get("sections", [])}

    assets_root = root / "assets" / "broll"
    assets_root.mkdir(parents=True, exist_ok=True)
    manifest = []
    selected_global = set()
    section_counts = {}
    target_counts = {}
    rejected_checks = {}
    queries_used = []

    for section in plan:
        section_id = section["id"]
        section_dir = assets_root / section_id
        section_dir.mkdir(parents=True, exist_ok=True)
        timing = narration_sections.get(section_id, {})
        minimum = section_minimum(root, timing)
        target = max(int(section["count"]), minimum)
        target_counts[section_id] = target
        candidates = {}

        for query in section["queries"]:
            print(f"[{section_id}] precise search: {query}", flush=True)
            data = search(query, key)
            queries_used.append({"section_id": section_id, "query": query})
            for hit in data.get("hits", []):
                if hit.get("type") not in (None, "film"):
                    continue
                asset_id = str(hit.get("id", ""))
                if not asset_id or asset_id in selected_global:
                    continue
                if rejected_checks.get(asset_id, 0) >= MAX_REJECTION_CHECKS:
                    continue

                tags = hit.get("tags", "")
                if re.search(r"generated by ai|ai[- ]generated|synthetic footage|cgi animation", tags, re.I):
                    reject_once_or_twice(rejected_checks, asset_id)
                    print(f"REJECTED [{section_id}] {asset_id}: AI-generated/animated tag", flush=True)
                    continue

                subject_match = group_hits(tags, [section["match_groups"][0]]) > 0
                context_match = group_hits(tags, [section["match_groups"][1]]) > 0
                overlap = len(token_set(query).intersection(token_set(tags)))
                context_only_allowed = bool(section.get("context_only_allowed", True))
                if not subject_match and not (context_match and context_only_allowed and overlap >= 1):
                    reject_once_or_twice(rejected_checks, asset_id)
                    print(
                        f"REJECTED [{section_id}] {asset_id}: scene relevance check "
                        f"{rejected_checks.get(asset_id, 0)}/{MAX_REJECTION_CHECKS}",
                        flush=True
                    )
                    continue

                matched = int(subject_match) + int(context_match)
                relevance_level = "subject-specific" if subject_match else "context-only"

                videos = hit.get("videos", {})
                rendition = next((
                    videos.get(key_name) for key_name in ("large", "medium")
                    if videos.get(key_name)
                    and videos[key_name].get("url")
                    and int(videos[key_name].get("width", 0)) >= 1280
                    and int(videos[key_name].get("height", 0)) >= 720
                ), None)
                if not rendition or int(hit.get("duration", 0)) < 7:
                    reject_once_or_twice(rejected_checks, asset_id)
                    continue

                score = (
                    int(subject_match) * 10000
                    + int(context_match) * 5000
                    + overlap * 250
                    + min(int(hit.get("duration", 0)), 90)
                    + min(int(hit.get("downloads", 0)) // 100, 50)
                )
                previous = candidates.get(asset_id)
                if previous is None or score > previous[0]:
                    candidates[asset_id] = (
                        score, hit, rendition, query, matched,
                        relevance_level, subject_match, context_match
                    )

            # Only try a fallback if the current and earlier searches did not find enough.
            if len(candidates) >= target:
                break

        ranked = sorted(candidates.values(), key=lambda item: item[0], reverse=True)
        chosen = ranked[:target]
        if len(chosen) < minimum:
            raise SystemExit(
                f"{section_id}: only {len(chosen)} clips matched a subject-specific or explicitly allowed scene-context group; "
                f"{minimum} are required for the two-use cap. Relevant fallback searches were exhausted. "
                "No city, skyline, generic network-line or unrelated filler will be substituted."
            )

        for index, (score, hit, rendition, selected_query, matched, relevance_level, subject_match, context_match) in enumerate(chosen, start=1):
            asset_id = str(hit["id"])
            selected_global.add(asset_id)
            filename = f"{section_id}_{index:02d}_{asset_id}.mp4"
            target_path = section_dir / filename

            if not target_path.exists() or target_path.stat().st_size < 100_000:
                with requests.get(rendition["url"], stream=True, timeout=90) as response:
                    response.raise_for_status()
                    with target_path.open("wb") as handle:
                        for chunk in response.iter_content(chunk_size=1024 * 1024):
                            if chunk:
                                handle.write(chunk)

            if target_path.stat().st_size < 100_000:
                raise SystemExit(f"Downloaded footage is incomplete: {target_path}")

            metadata = json.loads(subprocess.check_output([
                "ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(target_path)
            ], text=True))
            video = next((stream for stream in metadata.get("streams", []) if stream.get("codec_type") == "video"), None)
            if not video or int(video.get("width", 0)) < 1280 or int(video.get("height", 0)) < 720:
                raise SystemExit(f"Downloaded footage is not at least 1280x720: {target_path}")
            clip_seconds = float(metadata.get("format", {}).get("duration", 0))
            if clip_seconds < 7:
                raise SystemExit(f"Downloaded footage is shorter than seven seconds: {target_path}")
            subprocess.run(["ffmpeg", "-v", "error", "-i", str(target_path), "-f", "null", "-"], check=True)

            digest = hashlib.sha256()
            with target_path.open("rb") as source:
                for block in iter(lambda: source.read(1024 * 1024), b""):
                    digest.update(block)

            creator = hit.get("user", "Pixabay contributor")
            page_url = hit.get("pageURL", "")
            manifest.append({
                "asset_id": asset_id,
                "section_id": section_id,
                "intended_use": section["title"],
                "filename": target_path.relative_to(root).as_posix(),
                "source_url": page_url,
                "creator": creator,
                "credit": f"{creator} via Pixabay (credit recommended)",
                "license": LICENSE,
                "license_url": LICENSE_URL,
                "terms_url": TERMS_URL,
                "api_docs_url": API_DOCS_URL,
                "license_checked_date": datetime.now(timezone.utc).date().isoformat(),
                "third_party_rights_review": "PENDING human review; check logos, trademarks, people and property",
                "search_query": selected_query,
                "fallback_used": selected_query != section["query"],
                "tags": hit.get("tags", ""),
                "relevance_groups_matched": matched,
                "relevance_groups_total": len(section["match_groups"]),
                "relevance_level": relevance_level,
                "subject_specific_match": bool(subject_match),
                "context_match": bool(context_match),
                "ai_generated_check": "PASS",
                "relevance_score": score,
                "source_width": rendition.get("width", 0),
                "source_height": rendition.get("height", 0),
                "duration_seconds": round(clip_seconds, 3),
                "validated_codec": video.get("codec_name", ""),
                "full_decode_check": "PASS",
                "file_size_bytes": target_path.stat().st_size,
                "file_size_mb_decimal": round(target_path.stat().st_size / 1_000_000, 2),
                "sha256": digest.hexdigest(),
                "downloaded_utc": datetime.now(timezone.utc).isoformat()
            })
            print(
                f"ACCEPTED [{section_id}] {filename}; groups={matched}/{len(section['match_groups'])}; "
                f"query={selected_query}",
                flush=True
            )

        section_counts[section_id] = len(chosen)
        print(
            f"[{section_id}] selected {len(chosen)} unique clips; minimum={minimum}; target={target}",
            flush=True
        )

    if not manifest:
        raise SystemExit("No relevant B-roll was acquired.")

    output_csv = root / "asset-manifest-broll.csv"
    with output_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(manifest[0].keys()))
        writer.writeheader()
        writer.writerows(manifest)

    report = {
        "provider": "Pixabay API",
        "api_secret_name": "PIXABAY_API_KEY",
        "unique_clips": len(manifest),
        "subject_specific_clips": sum(1 for row in manifest if row["relevance_level"] == "subject-specific"),
        "context_only_clips": sum(1 for row in manifest if row["relevance_level"] == "context-only"),
        "target_clips": sum(target_counts.values()),
        "sections": section_counts,
        "queries_used": queries_used,
        "minimum_clips_per_section": MIN_SECTION_CLIPS,
        "max_source_uses_per_video": MAX_SOURCE_USES,
        "max_rejection_checks_per_candidate": MAX_REJECTION_CHECKS,
        "topic_match_rule": "Every accepted clip matches the episode's subject group or an explicitly allowed scene-context group from a topic-specific search; subject-specific clips are ranked first and context-only clips are labelled.",
        "context_only_policy": "Context-only footage may illustrate a generic cleanroom, optics, robotics or manufacturing environment, never a named factory or proprietary process.",
        "ai_generated_footage": "Rejected when Pixabay tags identify AI-generated, synthetic or animated footage.",
        "generic_fallbacks": "disabled",
        "sequential_downloads": True,
        "request_spacing_seconds": REQUEST_SPACING_SECONDS,
        "cache_hours": 24,
        "api_rate_limit_documented_per_60_seconds": 100,
        "systematic_bulk_downloads": False,
        "per_item_metadata_probe": "PASS",
        "per_item_full_decode": "PASS",
        "license": LICENSE,
        "license_url": LICENSE_URL,
        "terms_url": TERMS_URL,
        "api_docs_url": API_DOCS_URL,
        "third_party_rights_review": "PENDING human review; no proprietary ASML/ZEISS/Intel footage is claimed.",
        "rejected_candidate_checks": sum(rejected_checks.values()),
        "note": "Generic industrial footage is context only. All invisible EUV mechanisms are separately identified original 3D reconstructions."
    }
    (root / "broll_acquisition_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    main()
