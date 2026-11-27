#!/usr/bin/env python3
"""EP002 footage-led 720p master plus 360p 24fps derivative. No captions or subtitle streams."""
from pathlib import Path
import csv, json, math, shutil, subprocess, sys

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output"
ASSETS = ROOT / "assets" / "broll"
FPS = 24
SHOT_SECONDS = 7.0
MAX_SOURCE_USES = 2
CUTS = {
    "section_04": "scene_04_tin_plasma",
    "section_05": "scene_05_mirror_optics",
    "section_06": "scene_06_reticle_projection",
    "section_07": "scene_07_wafer_stage",
    "section_08": "scene_08_layer_stack",
}

def run(cmd):
    subprocess.run(cmd, check=True)

def probe(path):
    return json.loads(subprocess.check_output([
        "ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)
    ], text=True))

def duration(path):
    return float(probe(path)["format"]["duration"])

def validate_clip(path):
    meta = probe(path)
    video = next((s for s in meta["streams"] if s.get("codec_type") == "video"), None)
    if not video or int(video.get("width", 0)) < 1280 or int(video.get("height", 0)) < 720:
        raise RuntimeError(f"Source B-roll must contain at least 1280x720 video: {path}")
    seconds = float(meta["format"]["duration"])
    if seconds < 7:
        raise RuntimeError(f"B-roll clip shorter than 7 seconds: {path}")
    return seconds

def encode(src, dest, seconds, seek):
    vf = "scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720,setsar=1,fps=24,format=yuv420p"
    run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", f"{seek:.3f}",
        "-stream_loop", "-1", "-i", str(src), "-t", f"{seconds:.3f}", "-vf", vf,
        "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
        "-profile:v", "high", "-pix_fmt", "yuv420p", "-r", "24", "-g", "48",
        "-movflags", "+faststart", str(dest)
    ])

def load_manifest():
    manifest_path = ROOT / "asset-manifest-broll.csv"
    if not manifest_path.is_file():
        raise RuntimeError("B-roll rights manifest missing.")
    by_filename = {}
    with manifest_path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if int(row.get("relevance_groups_matched", 0)) < int(row.get("relevance_groups_total", 2)):
                raise RuntimeError(f"Clip failed topic-match gate: {row.get('filename')}")
            if row.get("full_decode_check") != "PASS":
                raise RuntimeError(f"Clip failed decode validation: {row.get('filename')}")
            by_filename[row["filename"].replace("\\", "/")] = row
    return by_filename

def main():
    OUT.mkdir(exist_ok=True, parents=True)
    narration_report_path = OUT / "kokoro_narration_report.json"
    if not narration_report_path.is_file():
        raise RuntimeError("Kokoro narration report missing; no silent voice substitution.")
    narration_report = json.loads(narration_report_path.read_text(encoding="utf-8"))
    if narration_report.get("provider") != "Kokoro-82M" or narration_report.get("voice_id") != "am_echo":
        raise RuntimeError("The release voice must be Kokoro Echo (am_echo).")
    wav = OUT / narration_report["wav"]
    if not wav.is_file() or wav.stat().st_size < 10000:
        raise RuntimeError("Kokoro WAV is missing or empty.")
    audio_seconds = duration(wav)
    if not 480 <= audio_seconds <= 720:
        raise RuntimeError("Narration length outside 8-12 minutes; revise naturally, do not pad.")
    sections = narration_report.get("sections", [])
    if len(sections) != 10:
        raise RuntimeError(f"Expected ten narration sections, found {len(sections)}.")

    manifest = load_manifest()
    clipmap = {}
    clip_durations = {}
    count = 0
    for sec in sections:
        sid = sec["id"]
        clips = sorted((ASSETS / sid).glob("*.mp4"))
        cut_seconds = 5 if sid in CUTS else 0
        section_audio = ROOT / sec["audio_file"]
        section_seconds = duration(section_audio)
        shots_needed = max(1, math.ceil(max(0.1, section_seconds - cut_seconds) / SHOT_SECONDS))
        minimum_unique = max(4, math.ceil(shots_needed / MAX_SOURCE_USES))
        if len(clips) < minimum_unique:
            raise RuntimeError(
                f"{sid}: {len(clips)} relevant clips available; {minimum_unique} are required "
                f"to keep every source to at most {MAX_SOURCE_USES} uses."
            )
        for clip in clips:
            rel = clip.relative_to(ROOT).as_posix()
            if rel not in manifest:
                raise RuntimeError(f"Clip is absent from the rights/relevance manifest: {rel}")
            clip_durations[clip] = validate_clip(clip)
        clipmap[sid] = clips
        count += len(clips)

    if count < 40:
        raise RuntimeError(f"Only {count} relevant unique clips found; 40 are required for this 10-section episode.")

    blender = shutil.which("blender")
    if not blender:
        raise RuntimeError("Blender executable missing; original 3D cutaways cannot be rendered.")
    frames = OUT / "3d_frames"
    frames.mkdir(exist_ok=True)
    run([
        blender, "--background", "--factory-startup",
        "--python", str(ROOT / "scripts" / "generate_3d_cutaways.py"),
        "--", "--output-dir", str(frames)
    ])
    cutclips = {}
    for folder in sorted(frames.glob("scene_*")):
        pngs = sorted(folder.glob("frame_*.png"))
        if len(pngs) != 120:
            raise RuntimeError(f"{folder.name} did not produce 120 frames (produced {len(pngs)}).")
        dest = OUT / "3d_clips" / f"{folder.name}.mp4"
        dest.parent.mkdir(exist_ok=True)
        run([
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-framerate", "24", "-start_number", "1",
            "-i", str(folder / "frame_%04d.png"), "-frames:v", "120",
            "-vf", "scale=1280:720:flags=lanczos,setsar=1,fps=24,format=yuv420p",
            "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
            "-profile:v", "high", "-pix_fmt", "yuv420p", "-r", "24", "-g", "48", str(dest)
        ])
        cutclips[folder.name] = dest
    if not all(name in cutclips for name in CUTS.values()):
        raise RuntimeError("A conceptual 3D cutaway did not render.")

    shotdir = OUT / "broll_shots"
    shotdir.mkdir(exist_ok=True)
    concat, timeline = [], []
    cursor = 0.0
    broll_time = 0.0
    index = 0
    source_uses = {}

    for sec in sections:
        sid = sec["id"]
        total = float(duration(ROOT / sec["audio_file"]))
        cutname = CUTS.get(sid)
        cutsecs = 5 if cutname else 0
        left = total - cutsecs
        clips = clipmap[sid]
        section_uses = {p: 0 for p in clips}
        previous = None
        shot_number = 0
        while left > 0.01:
            length = min(SHOT_SECONDS, left)
            available = [p for p in clips if section_uses[p] < MAX_SOURCE_USES]
            if not available:
                raise RuntimeError(f"{sid}: clip-use limit reached before the narration section was covered.")
            available.sort(key=lambda p: (section_uses[p], p == previous, p.name))
            src = available[0]
            used_before = section_uses[src]
            section_uses[src] += 1
            source_uses[src.relative_to(ROOT).as_posix()] = section_uses[src]
            sd = clip_durations[src]
            max_seek = max(0.0, sd - min(length, sd - 0.05))
            seek = (used_before * 2.13) % max(0.1, max_seek)
            dst = shotdir / f"shot_{index:05d}.mp4"
            index += 1
            encode(src, dst, length, seek)
            actual = duration(dst)
            concat.append(dst)
            rel = src.relative_to(ROOT).as_posix()
            asset = manifest[rel]
            timeline.append({
                "start_seconds": round(cursor, 3),
                "duration_seconds": round(actual, 3),
                "section_id": sid,
                "visual_type": "topic-matched real-world moving footage",
                "source": rel,
                "source_tags": asset.get("tags", ""),
                "search_query": asset.get("search_query", ""),
                "relevance_groups_matched": asset.get("relevance_groups_matched")
            })
            cursor += actual
            broll_time += actual
            left -= length
            previous = src
            shot_number += 1

        if max(section_uses.values(), default=0) > MAX_SOURCE_USES:
            raise RuntimeError(f"{sid}: a source clip exceeded the {MAX_SOURCE_USES}-use limit.")
        if cutname:
            cut = cutclips[cutname]
            actual = duration(cut)
            concat.append(cut)
            timeline.append({
                "start_seconds": round(cursor, 3),
                "duration_seconds": round(actual, 3),
                "section_id": sid,
                "visual_type": "original conceptual 3D reconstruction, not proprietary machine footage"
            })
            cursor += actual

    max_uses = max(source_uses.values(), default=0)
    if max_uses > MAX_SOURCE_USES:
        raise RuntimeError(f"A source clip was used {max_uses} times; limit is {MAX_SOURCE_USES}.")

    concatfile = OUT / "concat_timeline.txt"
    concatfile.write_text("\n".join("file '" + p.as_posix() + "'" for p in concat) + "\n", encoding="utf-8")
    silent = OUT / "temporary_720p_video.mp4"
    run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "concat",
        "-safe", "0", "-i", str(concatfile), "-fflags", "+genpts",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-profile:v", "high",
        "-pix_fmt", "yuv420p", "-r", "24", "-g", "48", "-an", str(silent)
    ])
    if abs(duration(silent) - audio_seconds) > 0.35:
        raise RuntimeError("Video timeline and narration duration differ by more than 0.35 seconds.")

    final = OUT / "Underneath_Everything_EP002_Kokoro_Broll_720p.mp4"
    run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(silent), "-i", str(wav),
        "-map", "0:v:0", "-map", "1:a:0", "-sn", "-c:v", "copy",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
        "-shortest", "-movflags", "+faststart", str(final)
    ])
    meta = probe(final)
    video = next(s for s in meta["streams"] if s["codec_type"] == "video")
    audio = next(s for s in meta["streams"] if s["codec_type"] == "audio")
    if (video["width"], video["height"]) != (1280, 720) or video["codec_name"] != "h264" or audio["codec_name"] != "aac":
        raise RuntimeError("Strict 720p H.264/AAC validation failed.")
    if video.get("avg_frame_rate") != "24/1":
        raise RuntimeError(f"Measured master frame rate is {video.get('avg_frame_rate')}, expected 24fps.")
    if audio.get("sample_rate") != "48000" or int(audio.get("channels", 0)) != 2:
        raise RuntimeError("Master audio must be stereo AAC at 48 kHz.")
    if any(s.get("codec_type") == "subtitle" for s in meta["streams"]):
        raise RuntimeError("Subtitle track is forbidden.")
    runtime = float(meta["format"]["duration"])
    if not 480 <= runtime <= 720:
        raise RuntimeError("Final runtime outside 8-12 minutes; no padding.")
    run(["ffmpeg", "-v", "error", "-i", str(final), "-f", "null", "-"])

    derivative = OUT / "Underneath_Everything_EP002_Kokoro_Broll_360p_24fps_450k_nocaptions.mp4"
    run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(final),
        "-map", "0:v:0", "-map", "0:a:0", "-sn",
        "-vf", "scale=640:360:force_original_aspect_ratio=increase,crop=640:360,setsar=1,fps=24,format=yuv420p",
        "-c:v", "libx264", "-preset", "slow", "-b:v", "450k", "-maxrate", "500k", "-bufsize", "900k",
        "-profile:v", "main", "-level", "3.1", "-pix_fmt", "yuv420p", "-r", "24", "-g", "48",
        "-c:a", "aac", "-b:a", "96k", "-ar", "48000", "-ac", "2", "-movflags", "+faststart", str(derivative)
    ])
    low_meta = probe(derivative)
    low_video = next(s for s in low_meta["streams"] if s["codec_type"] == "video")
    low_audio = next(s for s in low_meta["streams"] if s["codec_type"] == "audio")
    if (low_video["width"], low_video["height"]) != (640, 360) or low_video["codec_name"] != "h264" or low_video.get("avg_frame_rate") != "24/1":
        raise RuntimeError("360p derivative must be H.264 at 640x360 and measured 24fps.")
    if low_audio["codec_name"] != "aac" or low_audio.get("sample_rate") != "48000" or int(low_audio.get("channels", 0)) != 2:
        raise RuntimeError("360p derivative audio must be stereo AAC at 48 kHz.")
    if abs(duration(derivative) - runtime) > 0.5:
        raise RuntimeError("360p derivative duration differs from the 720p master.")
    run(["ffmpeg", "-v", "error", "-i", str(derivative), "-f", "null", "-"])

    coverage = round(100 * broll_time / max(runtime, 0.001), 2)
    if coverage < 70:
        raise RuntimeError(f"Relevant real B-roll coverage is {coverage}%; minimum is 70%.")
    run([sys.executable, str(ROOT / "scripts" / "create_thumbnail.py")])

    derivative_report = {
        "file": derivative.name,
        "file_size_bytes": derivative.stat().st_size,
        "file_size_mb_decimal": round(derivative.stat().st_size / 1_000_000, 2),
        "resolution": "640x360",
        "fps_measured": low_video.get("avg_frame_rate"),
        "video_bitrate_target_bps": 450000,
        "audio_codec": low_audio["codec_name"],
        "audio_sample_rate": low_audio["sample_rate"],
        "audio_channels": low_audio["channels"],
        "profile": "H.264 450 kb/s target + stereo AAC 96 kb/s at 48 kHz"
    }
    report = {
        "episode": "EP002",
        "title": "The Machine That Prints the World's Most Advanced Chips",
        "file": final.name,
        "file_size_bytes": final.stat().st_size,
        "file_size_mb_decimal": round(final.stat().st_size / 1_000_000, 2),
        "low_data_derivative": derivative_report,
        "duration_seconds": round(runtime, 3),
        "resolution": "1280x720",
        "fps_measured": video["avg_frame_rate"],
        "video_codec": video["codec_name"],
        "audio_codec": audio["codec_name"],
        "audio_sample_rate": audio["sample_rate"],
        "audio_channels": audio["channels"],
        "narration_provider": "Kokoro-82M",
        "narration_voice_id": "am_echo",
        "narration_seconds": round(audio_seconds, 3),
        "broll_assets": count,
        "unique_broll_clips": count,
        "broll_seconds": round(broll_time, 3),
        "broll_coverage_percent": coverage,
        "max_source_clip_uses": max_uses,
        "source_clip_uses": source_uses,
        "original_3d_cutaways": sorted(CUTS.values()),
        "captions": "none",
        "subtitle_streams": "none",
        "visual_text_overlays": "none",
        "thumbnail": "thumbnail_rwb.png",
        "full_decode_check": "PASS",
        "auto_publish": False,
        "rights_status": "Awaiting human review of every selected asset and full playback."
    }
    (OUT / "render_report_broll_echo.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (OUT / "broll_timeline.json").write_text(json.dumps(timeline, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2), flush=True)

if __name__ == "__main__":
    main()
