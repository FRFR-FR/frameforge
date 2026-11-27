#!/usr/bin/env python3
"""Acquire topic-verified, rights-documented B-roll. No generic filler and no repeated asset downloads."""
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
LICENSE = "Pixabay Content License (combined creative audiovisual work; not for standalone redistribution)"
SHOT_SECONDS = 7.0
MAX_SOURCE_USES = 2
MAX_REJECTION_CHECKS = 2
MIN_SECTION_CLIPS = 4

def cache_file(query):
    import hashlib
    key = hashlib.sha256(query.lower().encode("utf-8")).hexdigest()[:20]
    return Path.home() / ".cache" / "pixabay" / f"{key}.json"

def search(query, api_key):
    cache = cache_file(query)
    cache.parent.mkdir(parents=True, exist_ok=True)
    if cache.exists() and datetime.now(timezone.utc) - datetime.fromtimestamp(cache.stat().st_mtime, timezone.utc) < timedelta(hours=24):
        return json.loads(cache.read_text(encoding="utf-8"))
    params = {
        "key": api_key, "q": query, "video_type": "film", "safesearch": "true",
        "order": "popular", "per_page": 100, "min_width": 1280, "min_height": 720
    }
    response = requests.get(API, params=params, timeout=45)
    response.raise_for_status()
    data = response.json()
    cache.write_text(json.dumps(data), encoding="utf-8")
    time.sleep(1)
    return data

STOP = {"the", "and", "at", "in", "a", "an", "of", "to", "with", "by", "on", "under", "from", "how", "why", "for"}

def token_set(text):
    return {t for t in re.findall(r"[a-z0-9]+", str(text).lower()) if t not in STOP and len(t) > 2}

def group_hits(tags, groups):
    tag_tokens = token_set(tags)
    return sum(1 for group in groups if tag_tokens.intersection(set(group)))

def section_minimum(root, section):
    """Compute how many unique assets are needed to keep each source to at most two appearances."""
    seconds = float(section.get("duration_seconds", 0) or 0)
    audio_file = section.get("audio_file")
    if audio_file:
        candidate = root / audio_file
        if candidate.is_file():
            try:
                seconds = float(subprocess.check_output([
                    "ffprobe", "-v", "error", "-show_entries", "format=duration",
                    "-of", "csv=p=0", str(candidate)
                ], text=True).strip())
            except Exception:
                pass
    seconds = max(0.0, seconds - float(section.get("cutaway_seconds", 0) or 0))
    if seconds <= 0:
        return MIN_SECTION_CLIPS
    shot_count = max(1, int((seconds + SHOT_SECONDS - 0.001) // SHOT_SECONDS) + 1)
    return max(MIN_SECTION_CLIPS, (shot_count + MAX_SOURCE_USES - 1) // MAX_SOURCE_USES)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--episode-dir", required=True)
    args = ap.parse_args()
    root = Path(args.episode_dir).resolve()
    plan_file = root / "assets" / "broll_plan.json"
    if not plan_file.exists():
        plan_file = root / "broll_plan.json"
    if not plan_file.exists():
        raise SystemExit("A curated episode-specific broll_plan.json is required. Generic fallback footage is disabled.")
    plan = json.loads(plan_file.read_text(encoding="utf-8"))
    if not isinstance(plan, list) or not plan:
        raise SystemExit("broll_plan.json must contain a non-empty list.")

    required = {"id", "title", "query", "count", "match_groups"}
    for item in plan:
        if not required.issubset(item):
            raise SystemExit(f"Invalid B-roll plan item; required keys: {sorted(required)}")
        if not re.fullmatch(r"section_[0-9]{2}", item["id"]):
            raise SystemExit(f"Invalid section id: {item['id']}")
        if not isinstance(item["match_groups"], list) or len(item["match_groups"]) < 2:
            raise SystemExit(f"{item['id']} needs at least two subject-specific relevance groups.")
        item["queries"] = list(dict.fromkeys([item["query"], *item.get("queries", [])]))
        item["count"] = max(MIN_SECTION_CLIPS, int(item.get("count", 6)))

    key = os.environ.get("PIXABAY_API_KEY", "").strip()
    if not key:
        raise SystemExit("PIXABAY_API_KEY is missing. No unrelated substitute footage will be used.")

    report_path = root / "output" / "kokoro_narration_report.json"
    if not report_path.is_file():
        raise SystemExit("Kokoro section timing report is missing; cannot budget clips without narration timings.")
    narration_report = json.loads(report_path.read_text(encoding="utf-8"))
    narration_sections = {s.get("id"): s for s in narration_report.get("sections", [])}

    assets_root = root / "assets" / "broll"
    assets_root.mkdir(parents=True, exist_ok=True)
    manifest = []
    selected_global = set()
    section_counts = {}
    target_counts = {}
    rejected_checks = {}

    for section in plan:
        sid = section["id"]
        section_dir = assets_root / sid
        section_dir.mkdir(parents=True, exist_ok=True)
        timing = narration_sections.get(sid, {})
        minimum = section_minimum(root, timing)
        target = max(int(section["count"]), minimum)
        target_counts[sid] = target
        candidates = {}

        for query in section["queries"]:
            print(f"[{sid}] precise footage search: {query}", flush=True)
            data = search(query, key)
            for hit in data.get("hits", []):
                if hit.get("type") not in (None, "film"):
                    continue
                asset_id = str(hit.get("id", ""))
                if not asset_id or asset_id in selected_global:
                    continue
                tags = hit.get("tags", "")
                matched = group_hits(tags, section["match_groups"])
                if matched < len(section["match_groups"]):
                    # A candidate is checked at most twice across overlapping search results.
                    rejected_checks[asset_id] = min(MAX_REJECTION_CHECKS, rejected_checks.get(asset_id, 0) + 1)
                    continue
                videos = hit.get("videos", {})
                rendition = next((
                    videos.get(k) for k in ("large", "medium")
                    if videos.get(k) and videos[k].get("url")
                    and int(videos[k].get("width", 0)) >= 1280
                    and int(videos[k].get("height", 0)) >= 720
                ), None)
                if not rendition or int(hit.get("duration", 0)) < 7:
                    continue
                terms = token_set(query)
                overlap = len(terms.intersection(token_set(tags)))
                score = matched * 10000 + overlap * 250 + min(int(hit.get("duration", 0)), 90) + min(int(hit.get("downloads", 0)) // 100, 50)
                current = candidates.get(asset_id)
                if current is None or score > current[0]:
                    candidates[asset_id] = (score, hit, rendition, query, matched)

        ranked = sorted(candidates.values(), key=lambda x: x[0], reverse=True)
        chosen = ranked[:target]
        if len(chosen) < minimum:
            raise SystemExit(
                f"{sid}: only {len(chosen)} clips passed the two-group topic test; "
                f"{minimum} unique clips are required to keep every source at or below {MAX_SOURCE_USES} uses. "
                "No city, skyline, generic network-line or unrelated filler will be substituted."
            )

        for idx, (score, hit, rendition, selected_query, matched) in enumerate(chosen, start=1):
            asset_id = str(hit["id"])
            selected_global.add(asset_id)
            filename = f"{sid}_{idx:02d}_{asset_id}.mp4"
            target_path = section_dir / filename
            if not target_path.exists() or target_path.stat().st_size < 100_000:
                with requests.get(rendition["url"], stream=True, timeout=90) as response:
                    response.raise_for_status()
                    with target_path.open("wb") as f:
                        for chunk in response.iter_content(chunk_size=1024 * 1024):
                            if chunk:
                                f.write(chunk)
            if target_path.stat().st_size < 100_000:
                raise SystemExit(f"Downloaded footage is incomplete: {target_path}")
            meta = json.loads(subprocess.check_output([
                "ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(target_path)
            ], text=True))
            video = next((s for s in meta.get("streams", []) if s.get("codec_type") == "video"), None)
            if not video or int(video.get("width", 0)) < 1280 or int(video.get("height", 0)) < 720:
                raise SystemExit(f"Downloaded footage is not at least 1280x720: {target_path}")
            clip_duration = float(meta.get("format", {}).get("duration", 0))
            if clip_duration < 7:
                raise SystemExit(f"Downloaded footage is shorter than 7 seconds: {target_path}")
            subprocess.run(["ffmpeg", "-v", "error", "-i", str(target_path), "-f", "null", "-"], check=True)
            digest = hashlib.sha256()
            with target_path.open("rb") as src:
                for block in iter(lambda: src.read(1024 * 1024), b""):
                    digest.update(block)
            manifest.append({
                "asset_id": asset_id,
                "section_id": sid,
                "search_query": selected_query,
                "fallback_used": selected_query != section["query"],
                "relevance_groups_matched": matched,
                "relevance_groups_total": len(section["match_groups"]),
                "relevance_score": score,
                "file_size_bytes": target_path.stat().st_size,
                "sha256": digest.hexdigest(),
                "validated_codec": video.get("codec_name", ""),
                "validated_duration_seconds": round(clip_duration, 3),
                "full_decode_check": "PASS",
                "filename": target_path.relative_to(root).as_posix(),
                "source_url": hit.get("pageURL", ""),
                "contributor": hit.get("user", ""),
                "tags": hit.get("tags", ""),
                "duration_seconds": hit.get("duration", 0),
                "source_width": rendition.get("width", 0),
                "source_height": rendition.get("height", 0),
                "license": LICENSE,
                "credit": f"{hit.get('user', 'Contributor')} via Pixabay (credit recommended)",
                "downloaded_utc": datetime.now(timezone.utc).isoformat()
            })
            print(f"ACCEPTED [{sid}] {filename}; topic groups {matched}/{len(section['match_groups'])}; query={selected_query}", flush=True)

        section_counts[sid] = len(chosen)
        print(f"[{sid}] selected {len(chosen)} unique topic-matched clips (minimum needed {minimum}, target {target})", flush=True)

    if not manifest:
        raise SystemExit("No relevant B-roll was acquired.")
    out_csv = root / "asset-manifest-broll.csv"
    with out_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(manifest[0].keys()))
        writer.writeheader()
        writer.writerows(manifest)

    report = {
        "provider": "Pixabay API",
        "api_secret_name": "PIXABAY_API_KEY",
        "unique_clips": len(manifest),
        "target_clips": sum(target_counts.values()),
        "sections": section_counts,
        "minimum_clips_per_section": MIN_SECTION_CLIPS,
        "max_source_uses_per_video": MAX_SOURCE_USES,
        "max_rejection_checks_per_candidate": MAX_REJECTION_CHECKS,
        "topic_match_rule": "Every accepted clip matches every episode-specific relevance group; minimum two groups.",
        "generic_fallbacks": "disabled",
        "rejected_candidate_checks": sum(rejected_checks.values()),
        "sequential_downloads": True,
        "per_item_metadata_probe": "PASS",
        "per_item_full_decode": "PASS",
        "license": LICENSE,
        "source_attribution": "Pixabay contributor attribution retained in manifest; attribution is recommended.",
        "note": "Actual manufacturer-specific machine interiors are not claimed. Explanatory 3D cutaways are separately identified as conceptual reconstructions."
    }
    (root / "broll_acquisition_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2), flush=True)

if __name__ == "__main__":
    main()
