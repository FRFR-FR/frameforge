#!/usr/bin/env python3
"""B-roll-first EP002 assembly: 720p H.264/AAC, Kokoro Echo, subtitles and strict QC."""
from pathlib import Path
import csv
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output"
ASSETS = ROOT / "assets" / "broll"
FPS = 24
SHOT_SECONDS = 7.0
CUTAWAY_SECONDS = 12.0
MAX_SOURCE_USES = 1
MIN_BROLL_PERCENT = 75.0
MAX_BROLL_PERCENT = 85.0
CUTS = {
    "section_01": "scene_01_tin_plasma",
    "section_02": "scene_02_layer_stack",
    "section_03": "scene_03_wavelength",
    "section_04": "scene_04_tin_plasma_detail",
    "section_05": "scene_05_mirror_optics",
    "section_06": "scene_06_reticle_projection",
    "section_07": "scene_07_wafer_stage",
    "section_08": "scene_08_process_cycle",
    "section_09": "scene_09_high_na",
    "section_10": "scene_10_supply_chain"
}
SECTION_LABELS = {
    "section_01": "THE FLASH",
    "section_02": "CHIP LAYERS",
    "section_03": "WHY EUV",
    "section_04": "TIN PLASMA",
    "section_05": "MIRRORS AND VACUUM",
    "section_06": "PATTERN TO SILICON",
    "section_07": "THE WAFER STAGE",
    "section_08": "REPEATED ALIGNMENT",
    "section_09": "HIGH-NA EUV",
    "section_10": "THE WHOLE FACTORY"
}


def run(command):
    subprocess.run(command, check=True)


def probe(path):
    return json.loads(subprocess.check_output([
        "ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)
    ], text=True))


def duration(path):
    return float(probe(path)["format"]["duration"])


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_manifest():
    manifest_path = ROOT / "asset-manifest-broll.csv"
    if not manifest_path.is_file():
        raise RuntimeError("B-roll rights manifest is missing.")
    by_filename = {}
    with manifest_path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            required = ("filename", "source_url", "creator", "license", "license_url", "search_query")
            if any(not row.get(field) for field in required):
                raise RuntimeError(f"Incomplete rights metadata for {row.get('filename', 'unknown asset')}")
            if int(row.get("relevance_groups_matched", 0)) < 1:
                raise RuntimeError(f"Clip failed topic/scene-context relevance: {row.get('filename')}")
            if row.get("relevance_level") not in ("subject-specific", "context-only"):
                raise RuntimeError(f"Clip has no relevance classification: {row.get('filename')}")
            if row.get("ai_generated_check") != "PASS":
                raise RuntimeError(f"Clip failed AI-generated-footage exclusion: {row.get('filename')}")
            if row.get("full_decode_check") != "PASS":
                raise RuntimeError(f"Clip failed full-file decode: {row.get('filename')}")
            review_status = row.get("visual_review_status", "PENDING").strip().upper()
            if review_status not in ("APPROVED", "REJECTED", "PENDING"):
                raise RuntimeError(f"Invalid visual-review status for {row.get('filename')}: {review_status}")
            row["visual_review_status"] = review_status
            if review_status == "APPROVED":
                if row.get("relevance_level") != "subject-specific":
                    raise RuntimeError(f"Only subject-specific footage can be visually approved: {row.get('filename')}")
                if not row.get("visual_review_note", "").strip() or not row.get("visual_reviewed_at", "").strip():
                    raise RuntimeError(f"Approved footage needs a reviewer note and review timestamp: {row.get('filename')}")
                if row.get("media_type", "video").lower() not in ("video", "video/mp4", "mp4"):
                    raise RuntimeError(f"Still images cannot be B-roll: {row.get('filename')}")
                if row.get("motion_verified", "PASS").upper() not in ("PASS", "TRUE"):
                    raise RuntimeError(f"Clip has not passed motion verification: {row.get('filename')}")
            filename = row["filename"].replace("\\", "/")
            if filename in by_filename:
                raise RuntimeError(f"Duplicate rights manifest row: {filename}")
            by_filename[filename] = row
    return by_filename


def validate_clip(path):
    metadata = probe(path)
    video = next((stream for stream in metadata["streams"] if stream.get("codec_type") == "video"), None)
    if not video:
        raise RuntimeError(f"No video stream in {path}")
    if int(video.get("width", 0)) < 1280 or int(video.get("height", 0)) < 720:
        raise RuntimeError(f"Source B-roll is below 720p and cannot be upscaled: {path}")
    seconds = float(metadata["format"]["duration"])
    if seconds < SHOT_SECONDS:
        raise RuntimeError(f"B-roll clip is shorter than seven seconds: {path}")
    run(["ffmpeg", "-v", "error", "-i", str(path), "-f", "null", "-"])
    return seconds


def make_shot(source, destination, seconds, seek):
    filters = "scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720,setsar=1,fps=24,format=yuv420p"
    run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-ss", f"{seek:.3f}", "-i", str(source), "-t", f"{seconds:.3f}",
        "-vf", filters, "-an", "-c:v", "libx264", "-preset", "veryfast",
        "-crf", "20", "-profile:v", "high", "-pix_fmt", "yuv420p",
        "-r", "24", "-g", "48", "-movflags", "+faststart", str(destination)
    ])


def make_3d_clips(frames_dir):
    node = shutil.which("node")
    if not node:
        raise RuntimeError("Node.js is missing; the upgraded Three.js cutaway renderer cannot run.")
    renderer_script = ROOT / "scripts" / "render_threejs_cutaways.mjs"
    scene_file = ROOT / "threejs" / "ep002_threejs_master.mjs"
    html_file = ROOT / "threejs" / "render_frame.html"
    if not renderer_script.is_file() or not scene_file.is_file() or not html_file.is_file():
        raise RuntimeError("The Three.js scene module, render page or headless renderer is missing.")

    scene_names = sorted(CUTS.values())
    direct_files = {name: frames_dir / f"{name}.mp4" for name in scene_names}
    def direct_valid(name):
        candidate = direct_files[name]
        if not candidate.is_file() or candidate.stat().st_size < 1000:
            return False
        try:
            metadata = probe(candidate)
            video = next(stream for stream in metadata["streams"] if stream.get("codec_type") == "video")
            return (
                abs(float(metadata["format"]["duration"]) - CUTAWAY_SECONDS) <= 0.06
                and (video.get("width"), video.get("height")) == (1280, 720)
                and video.get("avg_frame_rate") == "24/1"
                and video.get("codec_name") == "h264"
            )
        except Exception:
            return False

    direct_complete = all(direct_valid(name) for name in scene_names)
    frames_complete = all(
        (frames_dir / name).is_dir()
        and len(list((frames_dir / name).glob("frame_*.png"))) == 288
        for name in scene_names
    )
    if not direct_complete and not frames_complete:
        run([node, str(renderer_script), "--output-dir", str(frames_dir)])
    elif direct_complete:
        print("Reusing the ten directly encoded H.264 Three.js clips.", flush=True)
    else:
        print("Reusing the complete 2,880-frame Three.js PNG render.", flush=True)

    output = {}
    contact_dir = OUT / "threejs_qc_frames"
    contact_dir.mkdir(parents=True, exist_ok=True)
    contact_frames = []
    for index, scene_name in enumerate(scene_names):
        clip_path = OUT / "3d_clips" / f"{scene_name}.mp4"
        clip_path.parent.mkdir(parents=True, exist_ok=True)
        if direct_valid(scene_name):
            shutil.copy2(direct_files[scene_name], clip_path)
        else:
            folder = frames_dir / scene_name
            pngs = sorted(folder.glob("frame_*.png"))
            if len(pngs) != 288:
                raise RuntimeError(f"{scene_name} produced {len(pngs)} frames; exactly 288 are required.")
            run([
                "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                "-framerate", "24", "-start_number", "1",
                "-i", str(folder / "frame_%04d.png"), "-frames:v", "288",
                "-vf", "setsar=1,fps=24,format=yuv420p",
                "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "19",
                "-profile:v", "high", "-pix_fmt", "yuv420p", "-r", "24", "-g", "48",
                str(clip_path)
            ])
        if abs(duration(clip_path) - CUTAWAY_SECONDS) > 0.06:
            raise RuntimeError(f"{scene_name} is not a measured 12-second cutaway.")
        metadata = probe(clip_path)
        video = next(stream for stream in metadata["streams"] if stream.get("codec_type") == "video")
        if (video.get("width"), video.get("height")) != (1280, 720) or video.get("avg_frame_rate") != "24/1":
            raise RuntimeError(f"{scene_name} is not a native 1280x720 24fps render.")
        run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(clip_path), "-f", "null", "-"])

        still = contact_dir / f"{index:02d}_{scene_name}.jpg"
        run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
             "-ss", "6.0", "-i", str(clip_path), "-frames:v", "1",
             "-vf", "scale=320:180:flags=lanczos", "-q:v", "3", str(still)])
        contact_frames.append((scene_name, still))
        output[scene_name] = clip_path

    columns, cell_w, cell_h, label_h = 4, 320, 180, 28
    rows = math.ceil(len(contact_frames) / columns)
    sheet = Image.new("RGB", (columns * cell_w, rows * (cell_h + label_h)), (16, 32, 50))
    draw = ImageDraw.Draw(sheet)
    for index, (name, image_path) in enumerate(contact_frames):
        x = (index % columns) * cell_w
        y = (index // columns) * (cell_h + label_h)
        with Image.open(image_path) as frame:
            sheet.paste(frame.convert("RGB"), (x, y + label_h))
        draw.rectangle((x, y, x + cell_w, y + label_h), fill=(23, 70, 162))
        draw.text((x + 8, y + 7), name, fill=(255, 255, 255))
    contact_sheet = OUT / "threejs_contact_sheet.jpg"
    sheet.save(contact_sheet, quality=92, optimize=True)

    collision_path = frames_dir / "collision_report.json"
    if not collision_path.is_file():
        raise RuntimeError("Three.js collision report is missing.")
    collision_report = json.loads(collision_path.read_text(encoding="utf-8"))
    if len(collision_report.get("collision", [])) != 10:
        raise RuntimeError("Three.js collision report does not contain all ten scene sections.")
    render_mode_path = frames_dir / "render_mode.json"
    render_mode = json.loads(render_mode_path.read_text(encoding="utf-8")) if render_mode_path.is_file() else {}
    render_report = {
        "renderer": "Three.js r175 / Playwright Chromium / SwiftShader",
        "encoding": render_mode.get("encoding", "PNG frames + FFmpeg"),
        "resolution": "1280x720",
        "fps": 24,
        "scenes": [{"name": name, "duration_seconds": duration(path)} for name, path in output.items()],
        "frame_count": 2880,
        "collision_report": "3d_frames/collision_report.json",
        "contact_sheet": contact_sheet.name,
        "status": "FRAME_RENDER_AND_TECHNICAL_CHECKS_PASSED; visual approval remains separate"
    }
    (OUT / "threejs_render_report.json").write_text(json.dumps(render_report, indent=2), encoding="utf-8")
    return output

def make_subtitle_filter(srt_path):
    escaped_path = str(srt_path).replace("\\", "/").replace(":", "\\:")
    style = (
        "FontName=DejaVu Sans,FontSize=24,PrimaryColour=&H00FFFFFF,"
        "OutlineColour=&H00A24617,BackColour=&H66522B10,BorderStyle=3,"
        "Outline=1,Shadow=0,Alignment=2,MarginV=42,MarginL=48,MarginR=48"
    )
    return f"subtitles=filename='{escaped_path}':force_style='{style}'"


def overlay_filters(chapters):
    bold_font = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    filters = [
        "drawbox=x=0:y=0:w=iw:h=6:color=0xD62839:t=fill",
        "drawbox=x=iw-342:y=18:w=320:h=40:color=0x102B52@0.86:t=fill",
        "drawbox=x=iw-342:y=18:w=5:h=40:color=0x1746A2:t=fill",
        f"drawtext=fontfile={bold_font}:text='UNDERNEATH EVERYTHING':fontcolor=white:fontsize=16:x=w-328:y=30"
    ]
    for chapter in chapters:
        start = float(chapter["start_seconds"])
        end = start + 3.2
        enable = f"between(t,{start:.3f},{end:.3f})"
        label = chapter["label"].replace("'", "")
        filters.extend([
            f"drawbox=x=48:y=70:w=500:h=48:color=0x102B52@0.82:t=fill:enable='{enable}'",
            f"drawbox=x=48:y=70:w=6:h=48:color=0xD62839:t=fill:enable='{enable}'",
            f"drawtext=fontfile={bold_font}:text='{label}':fontcolor=white:fontsize=21:x=68:y=83:enable='{enable}'"
        ])
    return filters


def make_qc_contact_sheet(video_path, runtime):
    contact_dir = OUT / "qc_frames"
    contact_dir.mkdir(parents=True, exist_ok=True)
    timestamps = list(range(0, max(1, int(runtime)), 30))
    if not timestamps or timestamps[-1] < runtime - 5:
        timestamps.append(max(0, runtime - 1))
    frames = []
    for index, timestamp in enumerate(timestamps):
        frame_path = contact_dir / f"frame_{index:03d}.jpg"
        run([
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-ss", f"{timestamp:.3f}", "-i", str(video_path), "-frames:v", "1",
            "-vf", "scale=320:180:flags=lanczos", "-q:v", "3", str(frame_path)
        ])
        frames.append((timestamp, frame_path))

    columns = 4
    cell_w, cell_h, label_h = 320, 180, 28
    rows = math.ceil(len(frames) / columns)
    sheet = Image.new("RGB", (columns * cell_w, rows * (cell_h + label_h)), (16, 43, 82))
    draw = ImageDraw.Draw(sheet)
    for index, (timestamp, frame_path) in enumerate(frames):
        row, column = divmod(index, columns)
        x, y = column * cell_w, row * (cell_h + label_h)
        image = Image.open(frame_path).convert("RGB")
        sheet.paste(image, (x, y + label_h))
        draw.rectangle((x, y, x + cell_w, y + label_h), fill=(23, 70, 162))
        draw.text((x + 8, y + 6), f"{timestamp:05.1f}s", fill=(255, 255, 255))
    destination = OUT / "qc_contact_sheet.jpg"
    sheet.save(destination, quality=90, optimize=True)
    return destination


def run_freeze_detection(video_path):
    result = subprocess.run([
        "ffmpeg", "-hide_banner", "-i", str(video_path),
        "-vf", "freezedetect=n=-50dB:d=2.5",
        "-an", "-f", "null", "-"
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError("FFmpeg frozen-frame detection could not complete.")
    durations = [float(value) for value in re.findall(r"freeze_duration:\s*([0-9.]+)", result.stderr)]
    longest = max(durations, default=0.0)
    if longest > 4.0:
        raise RuntimeError(f"Frozen-frame detection found a {longest:.2f}s freeze; manual correction required.")
    return {
        "status": "PASS" if not durations else "PASS_WITH_REVIEW_FLAGS",
        "freeze_events_over_2_5_seconds": len(durations),
        "longest_freeze_seconds": round(longest, 3),
        "threshold": "n=-50dB, d=2.5s; any event over 4.0s fails"
    }



def audio_level_check(audio_path):
    result = subprocess.run([
        "ffmpeg", "-hide_banner", "-i", str(audio_path),
        "-af", "volumedetect", "-f", "null", "-"
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError("FFmpeg audio-level check could not complete.")
    mean_match = re.search(r"mean_volume:\s*(-?[0-9.]+)\s*dB", result.stderr)
    max_match = re.search(r"max_volume:\s*(-?[0-9.]+)\s*dB", result.stderr)
    if not mean_match or not max_match:
        raise RuntimeError("FFmpeg did not report narration mean and peak levels.")
    mean_db = float(mean_match.group(1))
    peak_db = float(max_match.group(1))
    if mean_db <= -60:
        raise RuntimeError("Narration WAV is effectively silent.")
    if peak_db > 0.5:
        raise RuntimeError(f"Narration peak is unexpectedly high at {peak_db:.2f} dB.")
    return {
        "mean_volume_db": round(mean_db, 2),
        "max_volume_db": round(peak_db, 2),
        "status": "PASS"
    }


def markdown_report(report):
    return f"""# EP002 production report

- Episode: EP002 — The Machine That Prints the World's Most Advanced Chips
- Provider / voice: {report['narration_provider']} / {report['narration_voice_id']} (American English Echo)
- Narration WAV: {report['narration_wav']} ({report['narration_wav_mb']} MB)
- Narration MP3: {report['narration_mp3']} ({report['narration_mp3_mb']} MB)
- Final master: {report['file']} ({report['file_size_mb']} MB)
- Runtime: {report['runtime_seconds']} seconds
- Measured frame rate: {report['fps_measured']}
- Video/audio: {report['video_codec']} / {report['audio_codec']}
- Resolution: {report['resolution']}
- Relevant moving real-world B-roll: {report['broll_coverage_percent']}% ({report['broll_seconds']} seconds; {report['unique_broll_clips']} unique clips used)
- Subject-specific / context-only B-roll: {report['subject_specific_clips']} / {report['context_only_clips']} unique clips
- Original conceptual 3D motion graphics: {report['graphics_percent']}% ({report['graphics_seconds']} seconds; ten 12-second scenes)
- Source reuse: maximum {report['max_source_clip_uses']} uses per source asset (global URL + SHA-256 gate)
- Captions/subtitles: burned into picture; separate SRT retained
- Chapter labels / channel bug: included over moving footage
- Thumbnail: {report['thumbnail']} ({report['thumbnail_size_mb']} MB)
- QC contact sheet: {report['qc_contact_sheet']}
- Audio level check: mean {report['audio_level_check']['mean_volume_db']} dB, peak {report['audio_level_check']['max_volume_db']} dB
- Full decode: {report['full_decode_check']}
- Freeze detection: {report['freeze_detection']['status']}
- Rights manifest: {report['rights_manifest']} ({report['rights_records_count']} records); third-party rights review still requires human confirmation
- B-roll visual-review contact sheets: {report['broll_contact_sheets_count']} sections
- Shorts: concepts only; no Shorts export
- Git commit: {report['git_commit_sha']}
- Auto-publish: disabled

## Approval state

Automated technical QC has passed. This is not public-release approval. Watch the complete episode, review every B-roll contact sheet and rights record, listen to the full narration mix, and approve the thumbnail before publication.
"""


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Render EP002 or only its original Three.js cutaways.")
    parser.add_argument("--cutaways-only", action="store_true",
                        help="Render the ten native 720p Three.js engineering scenes without starting the full documentary assembly.")
    args = parser.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    if args.cutaways_only:
        clips = make_3d_clips(OUT / "3d_frames")
        print(json.dumps({
            "status": "THREEJS_CUTAWAYS_RENDERED",
            "scene_count": len(clips),
            "clip_files": [path.name for path in clips.values()],
            "contact_sheet": "threejs_contact_sheet.jpg",
            "collision_report": "3d_frames/collision_report.json"
        }, indent=2), flush=True)
        return

    narration_report_path = OUT / "kokoro_narration_report.json"
    if not narration_report_path.is_file():
        raise RuntimeError("Kokoro narration report missing; no silent voice substitution is permitted.")
    narration = json.loads(narration_report_path.read_text(encoding="utf-8"))
    if narration.get("provider") != "Kokoro-82M" or narration.get("voice_id") != "am_echo":
        raise RuntimeError("Release narration must use Kokoro-82M Echo (am_echo).")

    wav = OUT / narration["wav"]
    mp3 = OUT / narration["mp3"]
    for required in (wav, mp3):
        if not required.is_file() or required.stat().st_size < 1000:
            raise RuntimeError(f"Required Kokoro narration deliverable is missing: {required.name}")

    audio_seconds = duration(wav)
    if not 480 <= audio_seconds <= 720:
        raise RuntimeError(f"Kokoro narration is {audio_seconds:.1f}s; expected natural 8–12 minutes. Do not pad.")
    sections = narration.get("sections", [])
    if len(sections) != 10:
        raise RuntimeError(f"Expected ten timed narration sections, found {len(sections)}.")

    manifest = load_manifest()
    clipmap = {}
    clip_durations = {}
    clip_hashes = {}
    for section in sections:
        section_id = section["id"]
        discovered = sorted((ASSETS / section_id).glob("*.mp4"))
        clips = []
        for clip in discovered:
            relative = clip.relative_to(ROOT).as_posix()
            if relative not in manifest:
                raise RuntimeError(f"Clip is absent from the rights/relevance manifest: {relative}")
            record = manifest[relative]
            if record.get("visual_review_status") != "APPROVED":
                continue
            if record.get("relevance_level") != "subject-specific":
                continue
            clips.append(clip)

        section_audio = ROOT / section["audio_file"]
        section_seconds = duration(section_audio)
        remaining = section_seconds - CUTAWAY_SECONDS
        shots_needed = max(1, math.ceil(remaining / SHOT_SECONDS))
        minimum_unique = max(4, math.ceil(shots_needed / MAX_SOURCE_USES))
        if len(clips) < minimum_unique:
            raise RuntimeError(
                f"{section_id}: only {len(clips)} visually approved, subject-specific clips are eligible; "
                f"{minimum_unique} globally unique assets are required under the one-use rule. "
                "Do not use generic or context-only footage. Render the matching Three.js scene from "
                "threejs/ep002_threejs_master.mjs and keep this episode blocked until the approved footage "
                "and diagram timeline are integrated."
            )
        for clip in clips:
            clip_durations[clip] = validate_clip(clip)
            clip_hashes[clip] = sha256_file(clip)
        clipmap[section_id] = clips

    frames_dir = OUT / "3d_frames"
    frames_dir.mkdir(exist_ok=True)
    cutclips = make_3d_clips(frames_dir)
    if not all(name in cutclips for name in CUTS.values()):
        raise RuntimeError("One or more original explanatory 3D cutaways are missing.")

    shot_dir = OUT / "broll_shots"
    shot_dir.mkdir(exist_ok=True)
    concat_files = []
    timeline = []
    chapter_rows = []
    cursor = 0.0
    broll_seconds = 0.0
    source_uses = {}
    unique_sources = set()
    used_source_urls = set()
    used_source_hashes = set()
    shot_index = 0

    for section in sections:
        section_id = section["id"]
        chapter_rows.append({
            "start_seconds": round(cursor, 3),
            "label": SECTION_LABELS[section_id]
        })
        section_seconds = duration(ROOT / section["audio_file"])
        remaining = section_seconds - CUTAWAY_SECONDS
        clips = clipmap[section_id]
        uses = {clip: 0 for clip in clips}
        previous = None

        cut = cutclips[CUTS[section_id]]
        cut_duration = duration(cut)
        if abs(cut_duration - CUTAWAY_SECONDS) > 0.06:
            raise RuntimeError(f"{section_id}: Three.js cutaway duration is {cut_duration:.3f}s, not {CUTAWAY_SECONDS:.3f}s.")
        concat_files.append(cut)
        timeline.append({
            "start_seconds": round(cursor, 3),
            "duration_seconds": round(cut_duration, 3),
            "section_id": section_id,
            "visual_type": "original rigged Three.js engineering reconstruction; not proprietary factory footage",
            "source_file": str(cut.relative_to(ROOT))
        })
        cursor += cut_duration

        while remaining > 0.01:
            shot_seconds = min(SHOT_SECONDS, remaining)
            available = [
                clip for clip in clips
                if uses[clip] < MAX_SOURCE_USES
                and manifest[clip.relative_to(ROOT).as_posix()]["source_url"] not in used_source_urls
                and clip_hashes[clip] not in used_source_hashes
            ]
            if not available:
                raise RuntimeError(
                    f"{section_id}: no globally unique, visually approved source remains. "
                    "Do not repeat a stock asset; use the corresponding Three.js scene instead."
                )
            available.sort(key=lambda clip: (uses[clip], clip == previous, clip.name))
            source = available[0]
            used_before = uses[source]
            uses[source] += 1
            relative = source.relative_to(ROOT).as_posix()
            record = manifest[relative]
            unique_sources.add(relative)
            used_source_urls.add(record["source_url"])
            used_source_hashes.add(clip_hashes[source])
            source_uses[relative] = uses[source]

            source_duration = clip_durations[source]
            max_seek = max(0.0, source_duration - min(shot_seconds, source_duration - 0.05))
            seek = min(used_before * 2.13, max_seek) if max_seek > 0 else 0.0
            destination = shot_dir / f"shot_{shot_index:05d}.mp4"
            shot_index += 1
            make_shot(source, destination, shot_seconds, seek)
            actual = duration(destination)
            concat_files.append(destination)
            timeline.append({
                "start_seconds": round(cursor, 3),
                "duration_seconds": round(actual, 3),
                "section_id": section_id,
                "visual_type": "relevant real-world moving B-roll",
                "source_file": relative,
                "source_url": record["source_url"],
                "creator": record["creator"],
                "license": record["license"],
                "search_query": record["search_query"],
                "fallback_used": record.get("fallback_used", "False"),
                "relevance_groups_matched": record.get("relevance_groups_matched"),
                "relevance_level": record.get("relevance_level"),
                "ai_generated_check": record.get("ai_generated_check")
            })
            cursor += actual
            broll_seconds += actual
            remaining -= actual
            previous = source

        if max(uses.values(), default=0) > MAX_SOURCE_USES:
            raise RuntimeError(f"{section_id}: source clip reuse exceeded {MAX_SOURCE_USES}.")

    max_uses = max(source_uses.values(), default=0)
    if max_uses > MAX_SOURCE_USES:
        raise RuntimeError(f"A B-roll source was used {max_uses} times; maximum is {MAX_SOURCE_USES}.")
    subject_specific_sources = {
        filename for filename in unique_sources
        if manifest[filename].get("relevance_level") == "subject-specific"
    }
    context_only_sources = unique_sources - subject_specific_sources
    subject_specific_sections = {
        item["section_id"] for item in timeline
        if item.get("visual_type") == "relevant real-world moving B-roll"
        and item.get("relevance_level") == "subject-specific"
    }
    if len(subject_specific_sections) < 8:
        raise RuntimeError(
            f"Only {len(subject_specific_sections)} sections have subject-specific footage; at least 8 are required."
        )
    if len(unique_sources) < 40:
        raise RuntimeError(f"Only {len(unique_sources)} unique B-roll clips were used; minimum is 40.")

    concat_file = OUT / "concat_timeline.txt"
    concat_file.write_text(
        "\n".join(f"file '{path.as_posix()}'" for path in concat_files) + "\n",
        encoding="utf-8"
    )
    silent = OUT / "temporary_720p_video.mp4"
    run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-f", "concat", "-safe", "0", "-i", str(concat_file),
        "-fflags", "+genpts", "-c:v", "libx264", "-preset", "veryfast",
        "-crf", "20", "-profile:v", "high", "-pix_fmt", "yuv420p",
        "-r", "24", "-g", "48", "-an", str(silent)
    ])
    if abs(duration(silent) - audio_seconds) > 0.35:
        raise RuntimeError(
            f"Video timeline ({duration(silent):.3f}s) and narration ({audio_seconds:.3f}s) differ by over 0.35s."
        )

    thumbnail = OUT / "thumbnail_rwb.png"
    run([sys.executable, str(ROOT / "scripts" / "create_thumbnail.py")])
    if not thumbnail.is_file():
        raise RuntimeError("Original vector thumbnail was not created.")

    final = OUT / "Underneath_Everything_EP002_Kokoro_Broll_720p.mp4"
    srt = OUT / "narration_echo_kokoro.srt"
    if not srt.is_file() or srt.stat().st_size < 100:
        raise RuntimeError("Kokoro SRT is missing or empty; subtitles cannot be approved.")
    filters = overlay_filters(chapter_rows)
    filters.append(make_subtitle_filter(srt))
    filter_graph = ",".join(filters)
    run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-i", str(silent), "-i", str(wav),
        "-map", "0:v:0", "-map", "1:a:0",
        "-vf", filter_graph,
        "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-profile:v", "high", "-pix_fmt", "yuv420p", "-r", "24", "-g", "48",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
        "-shortest", "-movflags", "+faststart", str(final)
    ])

    metadata = probe(final)
    video = next(stream for stream in metadata["streams"] if stream["codec_type"] == "video")
    audio = next(stream for stream in metadata["streams"] if stream["codec_type"] == "audio")
    if (video["width"], video["height"]) != (1280, 720):
        raise RuntimeError(f"Final resolution is {video['width']}x{video['height']}; exactly 1280x720 is required.")
    if video["codec_name"] != "h264" or audio["codec_name"] != "aac":
        raise RuntimeError("Final codec must be H.264 video and AAC audio.")
    if video.get("avg_frame_rate") != "24/1":
        raise RuntimeError(f"Measured frame rate is {video.get('avg_frame_rate')}; expected 24/1.")
    if audio.get("sample_rate") != "48000" or int(audio.get("channels", 0)) != 2:
        raise RuntimeError("Final audio must be stereo AAC at 48 kHz.")
    if any(stream.get("codec_type") == "subtitle" for stream in metadata["streams"]):
        raise RuntimeError("Subtitles must be burned into picture; no separate subtitle stream is expected.")

    runtime = float(metadata["format"]["duration"])
    if not 480 <= runtime <= 720:
        raise RuntimeError(f"Final runtime is {runtime:.1f}s; expected 8–12 minutes without padding.")
    run(["ffmpeg", "-v", "error", "-i", str(final), "-f", "null", "-"])

    broll_percent = round(100 * broll_seconds / max(runtime, 0.001), 2)
    graphics_seconds = max(0.0, runtime - broll_seconds)
    graphics_percent = round(100 * graphics_seconds / max(runtime, 0.001), 2)
    if not MIN_BROLL_PERCENT <= broll_percent <= MAX_BROLL_PERCENT:
        raise RuntimeError(
            f"Measured real B-roll is {broll_percent}%; target is 75–85% and hard minimum is 70%."
        )
    if not 15.0 <= graphics_percent <= 25.0:
        raise RuntimeError(f"Explanatory motion graphics are {graphics_percent}%; target is 15–25%.")

    freeze_report = run_freeze_detection(final)
    audio_levels = audio_level_check(wav)
    contact_sheet = make_qc_contact_sheet(final, runtime)
    try:
        with Image.open(thumbnail) as thumbnail_image:
            thumbnail_size = thumbnail_image.size
    except Exception as error:
        raise RuntimeError(f"Thumbnail could not be inspected: {error}")

    report = {
        "episode": "EP002",
        "title": "The Machine That Prints the World's Most Advanced Chips",
        "file": final.name,
        "file_size_bytes": final.stat().st_size,
        "file_size_mb": round(final.stat().st_size / 1_000_000, 2),
        "runtime_seconds": round(runtime, 3),
        "resolution": "1280x720",
        "aspect_ratio": "16:9",
        "fps_measured": video["avg_frame_rate"],
        "video_codec": video["codec_name"],
        "audio_codec": audio["codec_name"],
        "audio_sample_rate": audio["sample_rate"],
        "audio_channels": audio["channels"],
        "narration_provider": "Kokoro-82M",
        "narration_voice_id": "am_echo",
        "narration_wav": wav.name,
        "narration_wav_mb": round(wav.stat().st_size / 1_000_000, 2),
        "narration_mp3": mp3.name,
        "narration_mp3_mb": round(mp3.stat().st_size / 1_000_000, 2),
        "narration_seconds": round(audio_seconds, 3),
        "unique_broll_clips": len(unique_sources),
        "subject_specific_clips": len(subject_specific_sources),
        "context_only_clips": len(context_only_sources),
        "subject_specific_sections": len(subject_specific_sections),
        "broll_seconds": round(broll_seconds, 3),
        "broll_coverage_percent": broll_percent,
        "graphics_seconds": round(graphics_seconds, 3),
        "graphics_percent": graphics_percent,
        "max_source_clip_uses": max_uses,
        "source_asset_unique_key": "source_url + SHA-256",
        "source_asset_uses": len(used_source_urls),
        "source_clip_uses": source_uses,
        "original_3d_cutaways": list(CUTS.values()),
        "original_3d_cutaway_count": len(CUTS),
        "original_3d_cutaway_seconds_each": CUTAWAY_SECONDS,
        "rights_manifest": "asset-manifest-broll.csv",
        "rights_records_count": len(manifest),
        "broll_contact_sheets_count": len(list((OUT / "broll_review").glob("*_contact_sheet.jpg"))),
        "captions": "burned-in",
        "chapter_labels": True,
        "channel_bug": True,
        "subtitle_streams": "none",
        "thumbnail": thumbnail.name,
        "thumbnail_size_mb": round(thumbnail.stat().st_size / 1_000_000, 3),
        "thumbnail_dimensions": f"{thumbnail_size[0]}x{thumbnail_size[1]}",
        "qc_contact_sheet": contact_sheet.name,
        "qc_contact_sheet_size_mb": round(contact_sheet.stat().st_size / 1_000_000, 2),
        "freeze_detection": freeze_report,
        "audio_level_check": audio_levels,
        "temporary_silent_video_mb": round(silent.stat().st_size / 1_000_000, 2),
        "intermediate_3d_files": [
            {"file": path.name, "size_mb": round(path.stat().st_size / 1_000_000, 2), "duration_seconds": round(duration(path), 3)}
            for path in cutclips.values()
        ],
        "full_decode_check": "PASS",
        "git_commit_sha": os.environ.get("GITHUB_SHA", "local-run"),
        "shorts_status": "Concepts only; no vertical Shorts exported.",
        "public_release_status": "NOT APPROVED; full human playback and rights review are pending.",
        "rights_review_status": "Multi-source provider metadata and licence records captured; human review of every clip remains required.",
        "auto_publish": False
    }

    (OUT / "render_report_broll_echo.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (OUT / "broll_timeline.json").write_text(json.dumps(timeline, indent=2), encoding="utf-8")
    (OUT / "production_report.md").write_text(markdown_report(report), encoding="utf-8")
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    main()