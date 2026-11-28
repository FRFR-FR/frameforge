#!/usr/bin/env python3
"""Rights-aware multi-provider B-roll acquisition for Frameforge documentaries."""
from pathlib import Path
from datetime import datetime, timezone, timedelta
from urllib.parse import quote
import argparse, csv, hashlib, html, json, os, re, subprocess, time
import requests
import acquire_pixabay_broll as pix

CACHE = Path.home() / ".cache" / "frameforge-footage"
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "FrameforgeDocumentaryBroll/1.0 (https://github.com/FRFR-FR/frameforge)"})
SHOT, MIN_W, MIN_H, MAX_BYTES = 7.0, 1280, 720, 500_000_000
COVERR_LIMIT = 10
AI_RE = re.compile(r"ai[- ]generated|synthetic footage|computer[- ]generated|\bcgi\b|animation|animated|artist.?s concept|visualization|rendered scene", re.I)
LICENCES = {
 "Pixabay": ("Pixabay Content License", "https://pixabay.com/service/license-summary/"),
 "Coverr": ("Coverr Stock Library License", "https://coverr.co/license"),
 "NASA": ("NASA media guidance; check third-party rights on the individual asset", "https://www.nasa.gov/nasa-brand-center/images-and-media/"),
 "Wikimedia Commons": ("Individual Creative Commons/Public Domain licence", "https://commons.wikimedia.org/wiki/Commons:Reusing_content_outside_Wikimedia"),
 "Internet Archive": ("Individual item licence as recorded in item metadata", "https://archive.org/about/terms.php"),
 "Pexels": ("Pexels License", "https://www.pexels.com/license/"),
 "DVIDS": ("U.S. DoD/Federal Agency public domain unless an item indicates otherwise; verify each item", "https://api.dvidshub.net/docs/copyright")
}

def clean(value):
    return re.sub(r"<[^>]+>", " ", html.unescape(str(value or ""))).strip()

def get_json(provider, query, url, params=None, headers=None, ttl=48):
    CACHE.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha256((provider + "|" + query).lower().encode()).hexdigest()[:24]
    path = CACHE / (key + ".json")
    if path.exists() and datetime.now(timezone.utc) - datetime.fromtimestamp(path.stat().st_mtime, timezone.utc) < timedelta(hours=ttl):
        return json.loads(path.read_text(encoding="utf-8"))
    response = SESSION.get(url, params=params, headers=headers, timeout=45)
    response.raise_for_status()
    data = response.json()
    path.write_text(json.dumps(data), encoding="utf-8")
    time.sleep(1)
    return data

def make(provider, aid, title, description, tags, duration, width, height, download_url, source_url, creator,
         licence=None, licence_url=None, creator_url="", **extra):
    if not aid or not download_url or not source_url or float(duration or 0) < SHOT:
        return None
    if width and int(width) < MIN_W or height and int(height) < MIN_H:
        return None
    text = " ".join(map(str, (title, description, tags)))
    if AI_RE.search(text):
        return None
    default_licence, default_url = LICENCES[provider]
    return {
      "asset_id": f"{provider.lower().replace(' ', '_')}:{aid}", "provider": provider,
      "title": clean(title) or "Untitled footage", "description": clean(description), "tags": clean(tags),
      "duration": float(duration or 0), "width": int(width or 0), "height": int(height or 0),
      "download_url": download_url, "source_url": source_url, "creator": clean(creator) or provider,
      "creator_url": creator_url, "license": licence or default_licence,
      "license_url": licence_url or default_url, "ai_generated_check": "PASS", **extra
    }

def search_pixabay(query, key):
    if not key:
        return []
    data = pix.search(query, key)
    result = []
    for hit in data.get("hits", []):
        if hit.get("type") not in (None, "film"):
            continue
        videos = hit.get("videos") or {}
        rendition = next((videos.get(k) for k in ("large", "medium")
                          if videos.get(k) and videos[k].get("url")
                          and int(videos[k].get("width", 0)) >= MIN_W
                          and int(videos[k].get("height", 0)) >= MIN_H), None)
        if not rendition:
            continue
        item = make("Pixabay", hit.get("id"), hit.get("tags"), hit.get("tags"), hit.get("tags"),
                    hit.get("duration"), rendition.get("width"), rendition.get("height"),
                    rendition.get("url"), hit.get("pageURL"), hit.get("user", "Pixabay contributor"))
        if item:
            result.append(item)
    return result

def search_coverr(query, key):
    if not key:
        return []
    data = get_json("coverr", query, "https://api.coverr.co/videos",
        {"query": query, "page": 0, "page_size": 20, "urls": "true",
         "filter": "is_premium:false,is_ai_generated:false"}, {"x-api-key": key}, ttl=12)
    result = []
    for hit in data.get("hits", []):
        if hit.get("is_ai_generated") is not False or hit.get("is_premium") is True:
            continue
        creator = hit.get("creator") or hit.get("user") or hit.get("author") or {}
        if isinstance(creator, dict):
            creator_name = creator.get("name") or creator.get("username") or ""
            creator_url = creator.get("url") or creator.get("profile_url") or ""
        else:
            creator_name, creator_url = str(creator or ""), ""
        if not creator_name.strip() or not creator_url.strip():
            print(f"Coverr clip skipped {hit.get('id')}: API response lacks creator name/profile needed for Demo attribution.", flush=True)
            continue
        slug = hit.get("slug") or hit.get("id")
        page = f"https://coverr.co/videos/{slug}" if slug else "https://coverr.co/"
        urls = hit.get("urls") or {}
        item = make("Coverr", hit.get("id"), hit.get("title"), hit.get("description"), hit.get("tags", []),
                    hit.get("duration"), hit.get("max_width"), hit.get("max_height"),
                    urls.get("mp4_download") or urls.get("mp4"), page, creator_name,
                    creator_url=creator_url, coverr_id=hit.get("id"))
        if item:
            result.append(item)
    return result

def search_nasa(query):
    data = get_json("nasa", query, "https://images-api.nasa.gov/search",
                    {"q": query, "media_type": "video", "page_size": 18}, ttl=48)
    result = []
    for hit in data.get("collection", {}).get("items", []):
        meta = (hit.get("data") or [{}])[0]
        title, desc = meta.get("title", ""), meta.get("description", "")
        if re.search(r"copyright|courtesy of|third.party|not for distribution", desc, re.I):
            continue
        href, nasa_id = hit.get("href"), meta.get("nasa_id")
        if not href or not nasa_id:
            continue
        try:
            files = SESSION.get(href, timeout=45).json()
            mp4s = [u for u in files if str(u).lower().split("?", 1)[0].endswith(".mp4")]
            if not mp4s:
                continue
            url = next((u for u in mp4s if "~large" in u.lower()), None) or next((u for u in mp4s if "~medium" in u.lower()), None) or mp4s[-1]
            item = make("NASA", nasa_id, title, desc, meta.get("keywords", []), 999, 0, 0, url,
                        f"https://images.nasa.gov/details/{nasa_id}", meta.get("center", "NASA"))
            if item:
                result.append(item)
        except Exception as exc:
            print(f"NASA item skipped {nasa_id}: {exc}", flush=True)
    return result

def cc_ok(name, url):
    value = (str(name or "") + " " + str(url or "")).lower()
    if any(x in value for x in ("/by-nc", "/by-nd", "noncommercial", "non-commercial",
                                  "no derivatives", "all rights reserved", "fair use")):
        return False
    return any(x in value for x in ("public domain", "publicdomain", "cc0",
                                    "creativecommons.org/licenses/by/"))

def search_wikimedia(query):
    data = get_json("wikimedia", query, "https://commons.wikimedia.org/w/api.php", {
        "action": "query", "format": "json", "generator": "search",
        "gsrsearch": f"filetype:video {query}", "gsrnamespace": 6, "gsrlimit": 20,
        "prop": "imageinfo", "iiprop": "url|extmetadata|user|size|mime"
    }, ttl=48)
    result = []
    for page in ((data.get("query") or {}).get("pages") or {}).values():
        info = (page.get("imageinfo") or [{}])[0]
        meta = info.get("extmetadata") or {}
        lic = clean((meta.get("LicenseShortName") or {}).get("value"))
        lic_url = clean((meta.get("LicenseUrl") or {}).get("value"))
        if not info.get("mime", "").startswith("video/") or not cc_ok(lic, lic_url):
            continue
        artist_raw = (meta.get("Artist") or {}).get("value", "")
        artist = clean(artist_raw) or info.get("user", "Wikimedia contributor")
        match = re.search(r"href=['\"]([^'\"]+)", artist_raw)
        title = page.get("title", "").removeprefix("File:")
        page_url = "https://commons.wikimedia.org/wiki/" + quote(page.get("title", "").replace(" ", "_"))
        item = make("Wikimedia Commons", page.get("pageid"), title,
                    clean((meta.get("ImageDescription") or {}).get("value")), title, 999,
                    info.get("width", 0), info.get("height", 0), info.get("url"), page_url,
                    artist, lic, lic_url, match.group(1) if match else "")
        if item:
            result.append(item)
    return result

def search_archive(query):
    data = get_json("internet_archive", query, "https://archive.org/advancedsearch.php", {
        "q": f'mediatype:movies AND "{query}"',
        "fl[]": ["identifier", "title", "description", "creator", "licenseurl"],
        "rows": 18, "page": 1, "output": "json"
    }, ttl=72)
    result = []
    for doc in data.get("response", {}).get("docs", []):
        ident, lic_url = doc.get("identifier"), doc.get("licenseurl", "")
        if not ident or not cc_ok("", lic_url):
            continue
        try:
            meta = get_json("ia_metadata", ident, f"https://archive.org/metadata/{quote(ident)}", ttl=72)
            files = [f for f in meta.get("files", []) if str(f.get("name", "")).lower().endswith(".mp4")
                     and int(f.get("size", 0) or 0) <= MAX_BYTES]
            files = [f for f in files if int(f.get("width", 0) or 0) >= MIN_W
                     and int(f.get("height", 0) or 0) >= MIN_H]
            if not files:
                continue
            f = max(files, key=lambda x: int(x.get("size", 0) or 0))
            url = f"https://archive.org/download/{quote(ident)}/{quote(f['name'])}"
            item = make("Internet Archive", ident, doc.get("title"), doc.get("description"), doc.get("title"),
                        999, f.get("width"), f.get("height"), url, f"https://archive.org/details/{quote(ident)}",
                        doc.get("creator", "Internet Archive contributor"),
                        "Internet Archive item licence (see item metadata)", lic_url)
            if item:
                result.append(item)
        except Exception as exc:
            print(f"Internet Archive item skipped {ident}: {exc}", flush=True)
    return result

def search_pexels(query, key):
    if not key:
        return []
    data = get_json("pexels", query, "https://api.pexels.com/videos/search",
                    {"query": query, "per_page": 20, "orientation": "landscape"},
                    {"Authorization": key}, ttl=48)
    result = []
    for hit in data.get("videos", []):
        files = sorted(hit.get("video_files", []),
                       key=lambda f: (int(f.get("width", 0)), int(f.get("height", 0))), reverse=True)
        f = next((x for x in files if x.get("link") and int(x.get("width", 0)) >= MIN_W
                  and int(x.get("height", 0)) >= MIN_H), None)
        if not f:
            continue
        user = hit.get("user") or {}
        slug = str(hit.get("url", "")).rstrip("/").split("/")[-1]
        title = re.sub(r"-[0-9]+$", "", slug).replace("-", " ")
        item = make("Pexels", hit.get("id"), title, "", title, hit.get("duration"),
                    f.get("width"), f.get("height"), f.get("link"), hit.get("url"),
                    user.get("name", "Pexels contributor"), creator_url=user.get("url", ""))
        if item:
            result.append(item)
    return result

def search_dvids(query, key):
    """Search DVIDS public-media footage; require an API key and preserve producer credit."""
    if not key:
        return []
    data = get_json("dvids_search", query, "https://api.dvidshub.net/search", {
        "q": query, "type": "video", "hd": 1, "max_results": 30, "api_key": key
    }, ttl=36)
    result = []
    for hit in data.get("results", []):
        asset_id = hit.get("id", "")
        if not str(asset_id).startswith("video:"):
            continue
        try:
            detail_data = get_json("dvids_asset", asset_id,
                "https://api.dvidshub.net/asset", {"id": asset_id, "api_key": key}, ttl=36)
            detail = detail_data.get("results") or {}
            desc = detail.get("description") or hit.get("short_description") or ""
            title = detail.get("title") or hit.get("title") or ""
            rights_text = " ".join((title, desc, str(detail.get("copyright", "")), str(detail.get("rights", ""))))
            if re.search(r"all rights reserved|not for commercial use|permission required|third.party copyright", rights_text, re.I):
                continue
            files = [f for f in detail.get("files", [])
                     if f.get("type") == "video/mp4"
                     and int(f.get("width", 0) or 0) >= MIN_W
                     and int(f.get("height", 0) or 0) >= MIN_H
                     and int(f.get("size", 0) or 0) <= MAX_BYTES
                     and f.get("src")]
            if not files:
                continue
            chosen = min(files, key=lambda f: (int(f.get("size", 0) or 0), -int(f.get("width", 0) or 0)))
            credit_data = detail.get("credit") or []
            if isinstance(credit_data, list):
                creator = ", ".join(x.get("name", "") for x in credit_data if isinstance(x, dict) and x.get("name"))
            elif isinstance(credit_data, dict):
                creator = credit_data.get("name", "")
            else:
                creator = str(credit_data or "")
            item = make("DVIDS", asset_id, title, desc, detail.get("keywords", hit.get("keywords", "")),
                        detail.get("duration", hit.get("duration", 0)), chosen.get("width"), chosen.get("height"),
                        chosen.get("src"), detail.get("url") or hit.get("url"), creator or "DVIDS producer")
            if item:
                result.append(item)
        except Exception as exc:
            print(f"DVIDS item skipped {asset_id}: {exc}", flush=True)
    return result

def relevance(item, section, query):
    tokens = pix.token_set(" ".join((item["title"], item["description"], item["tags"])))
    subject = bool(tokens.intersection(set(section["match_groups"][0])))
    context = bool(tokens.intersection(set(section["match_groups"][1])))
    overlap = len(pix.token_set(query).intersection(tokens))
    if not subject and not (context and section.get("context_only_allowed", True) and overlap >= 1):
        return None
    return (int(subject) * 10000 + int(context) * 5000 + overlap * 250 + min(int(item["duration"]), 90),
            "subject-specific" if subject else "context-only", subject, context)

def download(item, target):
    tmp = target.with_suffix(".source")
    total = 0
    with SESSION.get(item["download_url"], stream=True, timeout=120) as response:
        response.raise_for_status()
        with tmp.open("wb") as stream:
            for chunk in response.iter_content(1024 * 1024):
                if chunk:
                    total += len(chunk)
                    if total > MAX_BYTES:
                        raise RuntimeError("asset exceeded 500 MB download limit")
                    stream.write(chunk)
    if tmp.stat().st_size < 100_000:
        raise RuntimeError("download is incomplete or too small")
    meta = json.loads(subprocess.check_output(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(tmp)], text=True))
    video = next((s for s in meta.get("streams", []) if s.get("codec_type") == "video"), None)
    if not video or int(video.get("width", 0)) < MIN_W or int(video.get("height", 0)) < MIN_H or float(meta["format"].get("duration", 0)) < SHOT:
        raise RuntimeError("source failed 720p or seven-second checks")
    ext = item["download_url"].split("?", 1)[0].lower()
    if video.get("codec_name") == "h264" and ext.endswith(".mp4"):
        tmp.replace(target)
    else:
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(tmp),
                        "-vf", "scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720,setsar=1,fps=24",
                        "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-pix_fmt", "yuv420p", str(target)], check=True)
        tmp.unlink(missing_ok=True)
    subprocess.run(["ffmpeg", "-v", "error", "-i", str(target), "-f", "null", "-"], check=True)
    digest = hashlib.sha256()
    with target.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    probe = json.loads(subprocess.check_output(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(target)], text=True))
    return probe, digest.hexdigest()

def coverr_track(item, key):
    if item["provider"] != "Coverr":
        return
    response = SESSION.patch(f"https://api.coverr.co/videos/{quote(str(item['coverr_id']))}/stats/downloads",
                              headers={"x-api-key": key}, timeout=30)
    response.raise_for_status()

def credit(item):
    provider = item["provider"]
    title, source, creator = item["title"], item["source_url"], item["creator"]
    if provider == "Coverr":
        profile = f" | Creator profile: {item['creator_url']}"
        return f"- Video by {creator} on Coverr: {title}. Source: {source}{profile} | https://coverr.co"
    if provider == "NASA":
        return f"- {title} — NASA. Source: {source} | NASA Media Usage Guidelines: {LICENCES['NASA'][1]}"
    if provider == "DVIDS":
        return f"- {title} — Producer: {creator}. DVIDS public media; no DoD endorsement implied. Source: {source} | Copyright guidance: {LICENCES['DVIDS'][1]}"
    if provider == "Wikimedia Commons":
        return f"- {title} — {creator}. Licence: {item['license']} ({item['license_url']}). Source: {source}"
    if provider == "Internet Archive":
        return f"- {title} — {creator}. Item licence: {item['license_url']}. Source: {source}"
    if provider == "Pexels":
        return f"- Video by {creator} from Pexels: {source}"
    return f"- {title} — {creator} via Pixabay: {source}"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--episode-dir", required=True)
    root = Path(parser.parse_args().episode_dir).resolve()
    plan_path = root / "assets" / "broll_plan.json"
    if not plan_path.is_file():
        raise SystemExit("Curated episode B-roll plan missing; generic filler is disabled.")
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    if not isinstance(plan, list) or len(plan) != 10:
        raise SystemExit("Expected ten curated B-roll sections.")
    for section in plan:
        if not {"id", "title", "query", "count", "match_groups"}.issubset(section) or len(section["match_groups"]) < 2:
            raise SystemExit(f"Invalid topic-specific B-roll section: {section.get('id')}")
        section["queries"] = list(dict.fromkeys([section["query"], *section.get("queries", [])]))
    keys = {name: os.environ.get(name, "").strip()
            for name in ("PIXABAY_API_KEY", "COVERR_API_KEY", "PEXELS_API_KEY", "DVIDS_API_KEY")}
    searchers = [
      ("Pixabay", lambda q: search_pixabay(q, keys["PIXABAY_API_KEY"])),
      ("Coverr", lambda q: search_coverr(q, keys["COVERR_API_KEY"])),
      ("DVIDS", lambda q: search_dvids(q, keys["DVIDS_API_KEY"])),
      ("NASA", search_nasa), ("Wikimedia Commons", search_wikimedia),
      ("Internet Archive", search_archive),
      ("Pexels", lambda q: search_pexels(q, keys["PEXELS_API_KEY"]))
    ]
    enabled = [name for name, _ in searchers
               if name in ("NASA", "Wikimedia Commons", "Internet Archive")
               or (name == "Pixabay" and keys["PIXABAY_API_KEY"])
               or (name == "Coverr" and keys["COVERR_API_KEY"])
               or (name == "Pexels" and keys["PEXELS_API_KEY"])
               or (name == "DVIDS" and keys["DVIDS_API_KEY"])]
    print("Enabled footage sources: " + ", ".join(enabled), flush=True)
    timing_path = root / "output" / "kokoro_narration_report.json"
    if not timing_path.is_file():
        raise SystemExit("Kokoro section timing report missing.")
    timings = {x.get("id"): x for x in json.loads(timing_path.read_text()).get("sections", [])}
    assets = root / "assets" / "broll"
    assets.mkdir(parents=True, exist_ok=True)
    manifest, selected, rejected, section_counts, targets = [], set(), {}, {}, {}
    errors, queries_used, coverr_count = [], [], 0
    provider_order = [name for name, _ in searchers]
    # Reserve globally scarce semiconductor footage for constrained sections first.
    priority = {sid: rank for rank, sid in enumerate((
        "section_06", "section_07", "section_08", "section_03", "section_02",
        "section_09", "section_10", "section_01", "section_04", "section_05"
    ))}
    acquisition_plan = sorted(plan, key=lambda item: priority.get(item["id"], 999))
    for section in acquisition_plan:
        sid = section["id"]
        section_dir = assets / sid
        section_dir.mkdir(parents=True, exist_ok=True)
        timing = timings.get(sid, {})
        seconds = float(timing.get("duration_seconds", 0) or 0)
        audio_file = timing.get("audio_file")
        if audio_file and (root / audio_file).is_file():
            seconds = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                "-of", "csv=p=0", str(root / audio_file)], text=True).strip())
        shots = max(1, int((max(0, seconds - 12) + SHOT - .001) // SHOT) + 1)
        minimum = max(6, (shots + 1) // 2)
        target = max(int(section["count"]), minimum)
        targets[sid] = target
        candidates = {}
        for query in section["queries"]:
            queries_used.append({"section_id": sid, "query": query})
            for provider, searcher in searchers:
                if provider == "Coverr" and query != section["query"]:
                    continue
                try:
                    hits = searcher(query)
                except Exception as exc:
                    errors.append({"provider": provider, "query": query, "error": str(exc)[:250]})
                    print(f"SOURCE ERROR [{provider}] {query}: {exc}", flush=True)
                    continue
                for item in hits:
                    aid = item["asset_id"]
                    if aid in selected or rejected.get(aid, 0) >= pix.MAX_REJECTION_CHECKS:
                        continue
                    fit = relevance(item, section, query)
                    if not fit:
                        pix.reject_once_or_twice(rejected, aid)
                        continue
                    item.update({"score": fit[0], "relevance_level": fit[1], "subject_match": fit[2],
                                 "context_match": fit[3], "search_query": query,
                                 "relevance_groups_matched": int(fit[2]) + int(fit[3]),
                                 "relevance_groups_total": len(section["match_groups"])})
                    if aid not in candidates or item["score"] > candidates[aid]["score"]:
                        candidates[aid] = item
        groups = {}
        for item in candidates.values():
            groups.setdefault(item["provider"], []).append(item)
        for group in groups.values():
            group.sort(key=lambda item: item["score"], reverse=True)
        ranked = []
        while any(groups.values()):
            for provider in provider_order:
                if groups.get(provider):
                    ranked.append(groups[provider].pop(0))
        accepted = 0
        for item in ranked:
            if accepted >= target:
                break
            if item["provider"] == "Coverr" and coverr_count >= COVERR_LIMIT:
                continue
            aid = item["asset_id"]
            slug = re.sub(r"[^a-z0-9]+", "_", item["provider"].lower()).strip("_")
            short = hashlib.sha256(aid.encode()).hexdigest()[:12]
            dest = section_dir / f"{sid}_{accepted + 1:02d}_{slug}_{short}.mp4"
            try:
                probe, digest = download(item, dest)
                coverr_track(item, keys["COVERR_API_KEY"])
            except Exception as exc:
                dest.unlink(missing_ok=True)
                pix.reject_once_or_twice(rejected, aid)
                print(f"DOWNLOAD REJECTED [{sid}] {aid}: {exc}", flush=True)
                continue
            video = next(s for s in probe["streams"] if s.get("codec_type") == "video")
            row = {
              "asset_id": aid, "provider": item["provider"], "section_id": sid, "intended_use": section["title"],
              "filename": dest.relative_to(root).as_posix(), "source_url": item["source_url"],
              "title": item.get("title", "Untitled footage"), "description": item.get("description", ""),
              "creator": item["creator"], "creator_url": item.get("creator_url", ""), "credit": credit(item),
              "license": item["license"], "license_url": item["license_url"], "terms_url": item["license_url"],
              "license_checked_date": datetime.now(timezone.utc).date().isoformat(),
              "third_party_rights_review": "PENDING human review of people, trademarks, property and exact licence scope",
              "search_query": item["search_query"], "fallback_used": item["search_query"] != section["query"],
              "tags": item["tags"], "relevance_groups_matched": item["relevance_groups_matched"],
              "relevance_groups_total": item["relevance_groups_total"], "relevance_level": item["relevance_level"],
              "subject_specific_match": item["subject_match"], "context_match": item["context_match"],
              "ai_generated_check": "PASS", "relevance_score": item["score"],
              "source_width": video.get("width", 0), "source_height": video.get("height", 0),
              "duration_seconds": round(float(probe["format"]["duration"]), 3), "validated_codec": video.get("codec_name", ""),
              "full_decode_check": "PASS", "file_size_bytes": dest.stat().st_size,
              "file_size_mb_decimal": round(dest.stat().st_size / 1_000_000, 2), "sha256": digest,
              "downloaded_utc": datetime.now(timezone.utc).isoformat()
            }
            manifest.append(row)
            selected.add(aid)
            accepted += 1
            if item["provider"] == "Coverr":
                coverr_count += 1
            print(f"ACCEPTED [{sid}] {dest.name} from {item['provider']} ({item['relevance_level']})", flush=True)
        section_counts[sid] = accepted
        if accepted < minimum:
            raise SystemExit(f"{sid}: only {accepted} relevant clips found across all enabled sources; {minimum} required. No generic filler substituted.")
        print(f"[{sid}] selected {accepted}/{target} relevant clips", flush=True)
    if not manifest:
        raise SystemExit("No relevant B-roll acquired.")
    with (root / "asset-manifest-broll.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(manifest[0].keys()))
        writer.writeheader()
        writer.writerows(manifest)
    credits = ["FOOTAGE CREDITS — append this block to the YouTube video description", ""]
    credits += list(dict.fromkeys(credit(item) for item in manifest))
    credits += ["", "Footage is incorporated into an edited educational documentary. Each asset remains subject to its listed licence."]
    (root / "output" / "footage_attribution_description.txt").write_text("\n".join(credits) + "\n", encoding="utf-8")
    used = {}
    for row in manifest:
        used[row["provider"]] = used.get(row["provider"], 0) + 1
    report = {
      "provider": "Multi-source footage acquisition", "enabled_sources": enabled, "providers_used": used,
      "unique_clips": len(manifest), "subject_specific_clips": sum(x["relevance_level"] == "subject-specific" for x in manifest),
      "context_only_clips": sum(x["relevance_level"] == "context-only" for x in manifest),
      "target_clips": sum(targets.values()), "sections": section_counts, "queries_used": queries_used,
      "source_errors": errors, "minimum_clips_per_section": 6,
      "max_source_uses_per_video": pix.MAX_SOURCE_USES, "max_rejection_checks_per_candidate": pix.MAX_REJECTION_CHECKS,
      "generic_fallbacks": "disabled", "ai_generated_footage": "Metadata/text filtering applied; human visual review remains required",
      "download_limits": {"max_bytes": MAX_BYTES, "minimum_resolution": "1280x720", "minimum_duration_seconds": SHOT},
      "coverr_demo_api_budget": {"search_calls_max": 10, "download_tracking_calls_max": COVERR_LIMIT},
      "attribution_file": "output/footage_attribution_description.txt",
      "third_party_rights_review": "PENDING human review before publication",
      "rejected_candidate_checks": sum(rejected.values()),
      "excluded_sources": {
        "Mixkit": "Not automated: current terms require users to be 18+ and prohibit bot/script mass downloading.",
        "Videezy": "Not automated: terms prohibit bot/script access; direct guardian supervision is required for minors."
      }
    }
    (root / "broll_acquisition_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2), flush=True)

if __name__ == "__main__":
    main()
