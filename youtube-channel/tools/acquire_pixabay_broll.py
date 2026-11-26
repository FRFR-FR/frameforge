#!/usr/bin/env python3
"""Download a small, topic-matched, rights-documented B-roll set from Pixabay."""
from pathlib import Path
from datetime import datetime, timezone, timedelta
from urllib.parse import quote
import argparse, csv, hashlib, json, os, re, time, subprocess
import requests

API = "https://pixabay.com/api/videos/"
LICENSE = "Pixabay Content License (combined creative audiovisual work; not for standalone redistribution)"
PLAN = [
 {"id":"section_01","title":"The invisible network","query":"ocean aerial ship city night","fallback":"smartphone city night aerial","count":4},
 {"id":"section_02","title":"A network under the sea","query":"container cargo ship ocean","fallback":"commercial ship at sea","count":4},
 {"id":"section_03","title":"How light carries information","query":"fiber optic cable close up","fallback":"optical fiber cable technology","count":4},
 {"id":"section_04","title":"Keeping the signal strong","query":"data center server racks","fallback":"server room computers","count":4},
 {"id":"section_05","title":"Why the cable is built in layers","query":"industrial cable manufacturing","fallback":"wire cable factory machinery","count":4},
 {"id":"section_06","title":"How a cable reaches the seabed","query":"cable laying ship ocean","fallback":"offshore marine vessel at sea","count":4},
 {"id":"section_07","title":"When a cable needs repair","query":"ship crane repair vessel sea","fallback":"marine research ship ocean","count":4},
 {"id":"section_08","title":"Why one break does not always mean disconnection","query":"global data center network","fallback":"city aerial night traffic","count":4},
 {"id":"section_09","title":"The world beneath the connection","query":"underwater ocean deep sea","fallback":"ocean aerial ship sunset","count":4}
]
STOP = {"the","and","at","in","a","an","of","to","with","by","on","under","from","how","why"}

def cache_file(query):
    key = hashlib.sha256(query.lower().encode("utf-8")).hexdigest()[:20]
    return Path.home() / ".cache" / "pixabay" / f"{key}.json"

def search(query, api_key):
    cache = cache_file(query)
    cache.parent.mkdir(parents=True, exist_ok=True)
    if cache.exists() and datetime.now(timezone.utc) - datetime.fromtimestamp(cache.stat().st_mtime, timezone.utc) < timedelta(hours=24):
        return json.loads(cache.read_text(encoding="utf-8"))
    params = {
        "key": api_key, "q": query, "video_type": "film", "safesearch": "true",
        "order": "popular", "per_page": 50, "min_width": 1280, "min_height": 720
    }
    response = requests.get(API, params=params, timeout=45)
    response.raise_for_status()
    data = response.json()
    cache.write_text(json.dumps(data), encoding="utf-8")
    time.sleep(1)
    return data

def token_set(text):
    return {t for t in re.findall(r"[a-z0-9]+", text.lower()) if t not in STOP and len(t) > 2}

def rank_hits(hits, query):
    terms = token_set(query)
    scored = []
    for h in hits:
        if h.get("type") != "film":
            continue
        tags = token_set(h.get("tags", ""))
        overlap = len(terms & tags)
        if overlap < 1:
            continue
        duration = int(h.get("duration", 0))
        video = next((h.get("videos", {}).get(k) for k in ("large", "medium") if h.get("videos", {}).get(k) and h["videos"][k].get("url") and h["videos"][k].get("width", 0) >= 1280 and h["videos"][k].get("height", 0) >= 720), None)
        if not video or not video.get("url") or video.get("width", 0) < 1280 or video.get("height", 0) < 720 or duration < 7:
            continue
        score = overlap * 100 + min(duration, 90) + min(int(h.get("downloads", 0)) // 100, 50)
        scored.append((score, h, video))
    return [x[1:] for x in sorted(scored, key=lambda x: x[0], reverse=True)]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--episode-dir", required=True)
    args = ap.parse_args()
    root = Path(args.episode_dir).resolve()
    plan_file = root / "assets" / "broll_plan.json"
    if not plan_file.exists():
        plan_file = root / "broll_plan.json"
    plan = PLAN
    if plan_file.exists():
        plan = json.loads(plan_file.read_text(encoding="utf-8"))
        if not isinstance(plan, list) or not plan:
            raise SystemExit("broll_plan.json must contain a non-empty list.")
        required = {"id", "title", "query", "fallback", "count"}
        for item in plan:
            if not required.issubset(item):
                raise SystemExit(f"Invalid B-roll plan item; required keys: {sorted(required)}")
            if not re.fullmatch(r"section_[0-9]{2}", item["id"]):
                raise SystemExit(f"Invalid section id: {item['id']}")
            item["count"] = min(4, max(3, int(item["count"])))
    key = os.environ.get("PIXABAY_API_KEY", "").strip()
    if not key:
        raise SystemExit("PIXABAY_API_KEY is missing. No footage can be acquired; refusing a slide-only render.")

    assets_root = root / "assets" / "broll"
    assets_root.mkdir(parents=True, exist_ok=True)
    manifest = []
    seen = set()

    for section in plan:
        section_dir = assets_root / section["id"]
        section_dir.mkdir(parents=True, exist_ok=True)
        chosen = []
        for query in (section["query"], section["fallback"]):
            if len(chosen) >= section["count"]:
                break
            print(f"Pixabay search: {query}", flush=True)
            data = search(query, key)
            for hit, rendition in rank_hits(data.get("hits", []), query):
                if hit["id"] in seen:
                    continue
                chosen.append((hit, rendition, query))
                seen.add(hit["id"])
                if len(chosen) >= section["count"]:
                    break
        if len(chosen) < 3:
            raise SystemExit(
                f"Only {len(chosen)} relevant clips found for {section['id']}; "
                "minimum is 3. Do not substitute PowerPoint slides or unrelated filler."
            )

        for idx, (hit, rendition, selected_query) in enumerate(chosen, start=1):
            filename = f"{section['id']}_{idx:02d}_{hit['id']}.mp4"
            target = section_dir / filename
            if not target.exists() or target.stat().st_size < 100_000:
                with requests.get(rendition["url"], stream=True, timeout=90) as response:
                    response.raise_for_status()
                    with target.open("wb") as f:
                        for chunk in response.iter_content(chunk_size=1024 * 1024):
                            if chunk:
                                f.write(chunk)
            if target.stat().st_size < 100_000:
                raise SystemExit(f"Downloaded footage is incomplete: {target}")
            meta = json.loads(subprocess.check_output(["ffprobe","-v","error","-show_streams","-show_format","-of","json",str(target)],text=True))
            video = next((s for s in meta.get("streams",[]) if s.get("codec_type")=="video"),None)
            if not video or int(video.get("width",0))<1280 or int(video.get("height",0))<720:
                raise SystemExit(f"Downloaded footage does not contain 1280x720 video: {target}")
            clip_duration = float(meta.get("format",{}).get("duration",0))
            if clip_duration < 7:
                raise SystemExit(f"Downloaded footage is shorter than 7 seconds: {target}")
            subprocess.run(["ffmpeg","-v","error","-i",str(target),"-f","null","-"],check=True)
            digest = hashlib.sha256()
            with target.open("rb") as source_file:
                for block in iter(lambda: source_file.read(1024*1024),b""):
                    digest.update(block)
            manifest.append({
                "asset_id": str(hit["id"]), "section_id": section["id"],
                "search_query": selected_query,
                "fallback_used": selected_query != section["query"],
                "file_size_bytes": target.stat().st_size,
                "sha256": digest.hexdigest(),
                "validated_codec": video.get("codec_name",""),
                "validated_duration_seconds": round(clip_duration,3),
                "full_decode_check": "PASS",
                "filename": str(target.relative_to(root)),
                "source_url": hit.get("pageURL", ""),
                "contributor": hit.get("user", ""),
                "tags": hit.get("tags", ""),
                "duration_seconds": hit.get("duration", 0),
                "source_width": rendition.get("width", 0),
                "source_height": rendition.get("height", 0),
                "license": LICENSE,
                "credit": f"{hit.get('user','Contributor')} via Pixabay (credit recommended)",
                "downloaded_utc": datetime.now(timezone.utc).isoformat()
            })
            print(f"Downloaded {filename} ({target.stat().st_size/1_000_000:.2f} MB)", flush=True)

    out_csv = root / "asset-manifest-broll.csv"
    fields = list(manifest[0].keys())
    with out_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(manifest)
    report = {
        "provider": "Pixabay API",
        "api_secret_name": "PIXABAY_API_KEY",
        "unique_clips": len(manifest),
        "sections": {s["id"]: sum(1 for m in manifest if m["section_id"] == s["id"]) for s in plan},
        "fallback_substitutions": [{"section_id":m["section_id"],"query_used":m["search_query"],"asset_id":m["asset_id"],"tags":m["tags"]} for m in manifest if m["fallback_used"]],
        "sequential_downloads": True,
        "per_item_metadata_probe": "PASS",
        "per_item_full_decode": "PASS",
        "license": LICENSE,
        "source_attribution": "Pixabay contributor attribution retained in manifest; attribution is not generally required by the Content License but is recommended.",
        "note": "Every clip was selected by query/tag relevance and downloaded sequentially. Confirm third-party marks, recognizable people and property rights before commercial publication."
    }
    (root / "broll_acquisition_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2), flush=True)

if __name__ == "__main__":
    main()
