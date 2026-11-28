#!/usr/bin/env python3
"""FrameForge imported-VFX portrait test: real alpha cut-out plus downloaded fire footage."""
from __future__ import annotations
import json, os, subprocess, urllib.error, urllib.parse, urllib.request
from pathlib import Path
import numpy as np
from PIL import Image
from rembg import new_session, remove

OUT = Path(os.environ.get("OUTPUT_DIR", "artifacts/vfx-test")).resolve()
IMPORTS = Path(os.environ.get("VFX_CACHE_DIR", OUT / "imported-vfx")).resolve()
PORTRAIT_URL = "https://upload.wikimedia.org/wikipedia/commons/a/a3/Vladimir_Putin_portrait_%282024-02-23%29.png"
PIXABAY_ID = 237888
PIXABAY_PAGE = "https://pixabay.com/videos/flame-fire-flaming-heat-burn-237888/"
PIXABAY_LICENSE = "https://pixabay.com/service/license-summary/"
DURATION, FPS, WIDTH, HEIGHT = 10, 24, 1280, 720

def run(args):
    return subprocess.run(args, check=True, text=True, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT).stdout

def download(url, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "FrameForge-VFX-Import/1.0"})
    with urllib.request.urlopen(req, timeout=120) as response, destination.open("wb") as target:
        while True:
            block = response.read(1024 * 1024)
            if not block: break
            target.write(block)
    if not destination.exists() or destination.stat().st_size < 10000:
        raise RuntimeError("Downloaded source file is missing or unexpectedly small.")

def import_pixabay_vfx(destination):
    key = os.environ.get("PIXABAY_API_KEY", "").strip()
    if not key:
        raise RuntimeError("PIXABAY_API_KEY is missing from GitHub Actions secrets; the external VFX is not bundled in the repository.")
    query = urllib.parse.urlencode({"key": key, "id": str(PIXABAY_ID)})
    request = urllib.request.Request(
        "https://pixabay.com/api/videos/?" + query,
        headers={"User-Agent": "FrameForge-VFX-Import/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        details = error.read().decode("utf-8", errors="replace").strip()
        if key:
            details = details.replace(key, "[REDACTED]")
        raise RuntimeError(
            f"Pixabay API rejected the asset lookup (HTTP {error.code}): {details[:1200]}. "
            "Check that PIXABAY_API_KEY is a valid Pixabay API key."
        ) from error
    matches = [item for item in payload.get("hits", []) if int(item.get("id", -1)) == PIXABAY_ID]
    if len(matches) != 1:
        raise RuntimeError("Pixabay did not return the requested fire asset ID.")
    import urllib.parse as urlparse
    returned_page = urlparse.urlparse(matches[0].get("pageURL", ""))
    if returned_page.scheme != "https" or returned_page.hostname not in {"pixabay.com", "www.pixabay.com"} or str(PIXABAY_ID) not in returned_page.path:
        raise RuntimeError("Pixabay returned a source page that does not match the requested asset ID.")
    hit = matches[0]
    videos = hit.get("videos") or {}
    stream_name = "medium" if videos.get("medium", {}).get("url") else "large"
    stream = videos.get(stream_name) or videos.get("small")
    if not stream or not stream.get("url"):
        raise RuntimeError("Pixabay returned no downloadable MP4 rendition.")
    download(stream["url"], destination)
    metadata = {
        "asset_id": f"pixabay:{PIXABAY_ID}",
        "title": "Flame, fire, flaming",
        "creator": hit.get("user", "Luis_Humanoide"),
        "source_page": PIXABAY_PAGE,
        "license_name": "Pixabay Content License",
        "license_url": PIXABAY_LICENSE,
        "rendition": stream_name,
        "width": stream.get("width"),
        "height": stream.get("height"),
        "size_bytes": destination.stat().st_size,
        "source_description": "The item page describes this as a flame overlay and a fire simulation made in EmberGen.",
        "storage": "Downloaded at render time into the temporary artifact workspace; not committed to Git."
    }
    (IMPORTS / "pixabay-fire-source.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return metadata

def make_cutout(source, output):
    print("Running BiRefNet portrait background removal…", flush=True)
    session = new_session("birefnet-portrait")
    with Image.open(source) as image:
        result = remove(image.convert("RGB"), session=session).convert("RGBA")
    alpha = np.asarray(result.getchannel("A"), dtype=np.uint8)
    bbox = result.getchannel("A").getbbox()
    coverage = float(np.count_nonzero(alpha > 16)) / float(alpha.size)
    if bbox is None or not 0.08 <= coverage <= 0.98:
        raise RuntimeError(f"Background removal produced an implausible cut-out (coverage {coverage:.3f}).")
    result.save(output, optimize=True)
    return {
        "model": "BiRefNet portrait via rembg",
        "model_license": "MIT",
        "model_source": "https://github.com/ZhengPeng7/BiRefNet",
        "width": result.width, "height": result.height,
        "foreground_coverage": round(coverage, 4),
        "alpha_bounds": list(bbox),
        "transparent_background": True
    }

def make_red_cutout(source, output):
    with Image.open(source) as image:
        rgba = np.asarray(image.convert("RGBA"), dtype=np.float32)
    rgb = rgba[:, :, :3] / 255.0
    luma = 0.2126 * rgb[:, :, 0] + 0.7152 * rgb[:, :, 1] + 0.0722 * rgb[:, :, 2]
    red = np.clip(0.35 + 0.65 * luma, 0, 1)
    green = np.clip(0.02 + 0.18 * luma, 0, 1)
    blue = np.clip(0.015 + 0.14 * luma, 0, 1)
    graded = np.dstack((red, green, blue, rgba[:, :, 3] / 255.0))
    Image.fromarray(np.uint8(np.clip(graded * 255, 0, 255)), "RGBA").save(output, optimize=True)

def checker_preview(cutout, output):
    with Image.open(cutout) as image:
        foreground = image.convert("RGBA")
    w, h = foreground.size
    yy, xx = np.indices((h, w))
    pattern = ((xx // 36 + yy // 36) % 2).astype(bool)
    a = np.empty((h, w, 3), dtype=np.uint8)
    a[pattern] = (168, 168, 168)
    a[~pattern] = (224, 224, 224)
    background = Image.fromarray(a, "RGB").convert("RGBA")
    background.alpha_composite(foreground)
    background.convert("RGB").save(output, quality=92)

def compose(portrait, red_cutout, fire, output):
    regular = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    bold = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    graph = ";".join([
        "[0:v]scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720,boxblur=28:12,eq=brightness=-0.25:saturation=0.78[bg]",
        "[0:v]scale=520:720:force_original_aspect_ratio=decrease,setsar=1,format=rgba[portrait]",
        "[bg][portrait]overlay=(W-w)/2:(H-h)/2:shortest=1[scene]",
        "[2:v]fps=24,scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720,setsar=1,format=rgba[importedfire]",
        "[scene][importedfire]blend=all_mode=screen:all_opacity=0.68[scenevfx]",
        "[1:v]scale=520:720:force_original_aspect_ratio=decrease,setsar=1,format=rgba,fade=t=in:st=0.8:d=4.4:alpha=1[redsubject]",
        "[scenevfx][redsubject]overlay=(W-w)/2:(H-h)/2:shortest=1:format=auto,"
        f"drawtext=fontfile={bold}:text='FRAMEFORGE VFX TEST':fontcolor=white:fontsize=32:x=(w-text_w)/2:y=24:box=1:boxcolor=0x07111dcc:boxborderw=12,"
        f"drawtext=fontfile={regular}:text='SIMULATED EFFECTS - NOT REAL FOOTAGE':fontcolor=white:fontsize=16:x=(w-text_w)/2:y=h-52:box=1:boxcolor=0x07111dcc:boxborderw=8,"
        f"drawtext=fontfile={regular}:text='Kremlin.ru portrait - CC BY 4.0':fontcolor=0xe6edf5:fontsize=12:x=20:y=h-18:box=1:boxcolor=0x07111dcc:boxborderw=5,"
        f"drawtext=fontfile={regular}:text='Fire sim - Luis_Humanoide / Pixabay':fontcolor=0xe6edf5:fontsize=12:x=w-text_w-20:y=h-18:box=1:boxcolor=0x07111dcc:boxborderw=5[outv]"
    ])
    run([
        "ffmpeg", "-hide_banner", "-y",
        "-loop", "1", "-framerate", str(FPS), "-i", str(portrait),
        "-loop", "1", "-framerate", str(FPS), "-i", str(red_cutout),
        "-stream_loop", "-1", "-i", str(fire),
        "-filter_complex", graph, "-map", "[outv]", "-t", str(DURATION),
        "-r", str(FPS), "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-an",
        "-metadata", "title=FrameForge imported VFX portrait test", str(output)
    ])

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    IMPORTS.mkdir(parents=True, exist_ok=True)
    portrait = OUT / "putin-original.png"
    cutout = OUT / "putin-cutout-transparent.png"
    red = OUT / "putin-red-tinted-transparent.png"
    fire = IMPORTS / "pixabay-fire-simulation.mp4"
    video = OUT / "frameforge-vfx-russia-president-10s-imported.mp4"
    if not portrait.exists(): download(PORTRAIT_URL, portrait)
    vfx = import_pixabay_vfx(fire)
    cutout_info = make_cutout(portrait, cutout)
    make_red_cutout(cutout, red)
    checker_preview(cutout, OUT / "putin-cutout-checker-preview.jpg")
    compose(portrait, red, fire, video)
    probe = json.loads(run([
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=codec_name,width,height,r_frame_rate,nb_frames",
        "-show_entries", "format=duration,size", "-of", "json", str(video)
    ]))
    stream = probe["streams"][0]
    duration, size = float(probe["format"]["duration"]), int(probe["format"]["size"])
    assert stream["codec_name"] == "h264" and stream["width"] == WIDTH and stream["height"] == HEIGHT
    assert stream["r_frame_rate"] == "24/1" and abs(duration - DURATION) < 0.05
    credits = (
        "FRAMEFORGE V2 - IMPORTED VFX PORTRAIT TEST\n\n"
        "SUBJECT PHOTO\nVladimir Putin portrait, 23 February 2024. Source: Kremlin.ru via Wikimedia Commons.\n"
        f"File: {PORTRAIT_URL}\nLicence: Creative Commons Attribution 4.0 International (CC BY 4.0).\n"
        "Attribution: Kremlin.ru. Changes: background removed to create a transparent subject cut-out; red colour "
        "grade applied only to the isolated subject. The original photo background is not red-tinted.\n"
        "Licence: https://creativecommons.org/licenses/by/4.0/\n\n"
        "IMPORTED VFX\n"
        f"Title: {vfx['title']}\nCreator: {vfx['creator']}\nSource: {vfx['source_page']}\n"
        "Licence: Pixabay Content License. Free to use and adapt, subject to prohibited-use terms and any "
        "additional third-party rights. The item page describes the clip as an EmberGen fire-simulation overlay.\n"
        f"Licence summary: {vfx['license_url']}\n"
        "Downloaded at render time. The VFX video binary is not stored in the FrameForge repository.\n\n"
        "CUT-OUT SOFTWARE\nrembg 2.0.88; BiRefNet portrait model, MIT licence.\n"
        "https://github.com/danielgatis/rembg\nhttps://github.com/ZhengPeng7/BiRefNet\n\n"
        "Clearly labelled simulated visual-effects demonstration; not documentary footage and not evidence of a real event.\n"
    )
    (OUT / "CREDITS.txt").write_text(credits, encoding="utf-8")
    report = {
        "render": {"file": video.name, "duration_seconds": duration, "width": stream["width"],
                   "height": stream["height"], "fps": stream["r_frame_rate"],
                   "frames": int(stream["nb_frames"]), "codec": stream["codec_name"],
                   "size_bytes": size, "size_mb": round(size / 1048576, 3), "audio": False},
        "subject_cutout": cutout_info,
        "imported_vfx": vfx,
        "processing": {"red_tint_target": "isolated transparent subject PNG only",
                       "original_photo_background_tinted": False,
                       "fire_vfx_source": "downloaded external EmberGen video; screen-blended",
                       "repository_generated_fire_or_particles": False}
    }
    (OUT / "technical-report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"PASS: {duration:.3f}s, 1280x720, 24 FPS, H.264, {size / 1048576:.2f} MB")
    print(f"Transparent cut-out: {cutout}")
    print(f"Imported VFX footage: {fire}")

if __name__ == "__main__":
    main()
