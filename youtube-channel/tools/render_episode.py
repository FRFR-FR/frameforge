#!/usr/bin/env python3
"""B-roll-first documentary assembly with strict relevance, no captions and a two-use source cap."""
from pathlib import Path
import argparse, csv, json, math, re, subprocess

ap = argparse.ArgumentParser()
ap.add_argument("--episode-dir", required=True)
args = ap.parse_args()
ROOT = Path(args.episode_dir).resolve()
OUT = ROOT / "output"
ASSETS = ROOT / "assets" / "broll"
FPS = 24
SHOT_SECONDS = 7.0
MAX_SOURCE_USES = 2

def run(cmd):
    subprocess.run(cmd, check=True)

def duration(path):
    return float(subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "csv=p=0", str(path)
    ], text=True).strip())

def read_manifest():
    path = ROOT / "asset-manifest-broll.csv"
    if not path.is_file():
        raise RuntimeError("B-roll rights manifest is missing.")
    rows = {}
    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if int(row.get("relevance_groups_matched", 0)) < int(row.get("relevance_groups_total", 2)):
                raise RuntimeError(f"Clip failed topic relevance: {row.get('filename')}")
            if row.get("full_decode_check") != "PASS":
                raise RuntimeError(f"Clip failed full-file decode test: {row.get('filename')}")
            rows[row["filename"].replace("\\", "/")] = row
    return rows

def make_shot(src, out_path, seconds, seek):
    # Natural source colour is retained. No captions, labels, lower thirds or logo overlays.
    vf = "scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720,setsar=1,fps=24,format=yuv420p"
    run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-stream_loop", "-1", "-i", str(src), "-ss", f"{seek:.3f}",
        "-t", f"{seconds:.3f}", "-vf", vf, "-an", "-c:v", "libx264",
        "-preset", "veryfast", "-crf", "22", "-pix_fmt", "yuv420p",
        "-r", str(FPS), "-movflags", "+faststart", str(out_path)
    ])

def encode_360p(source, destination):
    run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(source),
        "-map", "0:v:0", "-map", "0:a:0", "-sn",
        "-vf", "scale=640:360:force_original_aspect_ratio=increase,crop=640:360,setsar=1,fps=24,format=yuv420p",
        "-c:v", "libx264", "-preset", "slow", "-b:v", "450k", "-maxrate", "500k", "-bufsize", "900k",
        "-profile:v", "main", "-level", "3.1", "-pix_fmt", "yuv420p", "-r", "24", "-g", "48",
        "-c:a", "aac", "-b:a", "96k", "-ar", "48000", "-ac", "2",
        "-movflags", "+faststart", str(destination)
    ])

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    report_path = OUT / "kokoro_narration_report.json"
    if not report_path.exists():
        raise RuntimeError("Kokoro narration report missing. Do not substitute eSpeak.")
    audio_report = json.loads(report_path.read_text(encoding="utf-8"))
    if audio_report.get("provider") != "Kokoro-82M" or audio_report.get("voice_id") != "am_echo":
        raise RuntimeError("Release narration must use Kokoro Echo (am_echo).")
    sections = audio_report.get("sections", [])
    audio_file = OUT / audio_report["wav"]
    if not audio_file.is_file():
        raise RuntimeError("Kokoro narration WAV is missing.")
    manifest = read_manifest()
    shot_dir = OUT / "broll_shots"
    shot_dir.mkdir(exist_ok=True)
    shot_files, timeline = [], []
    timeline_cursor = 0.0
    source_uses = {}
    unique_count = 0

    for section in sections:
        scene_id = section["id"]
        audio_path = ROOT / section["audio_file"]
        section_seconds = duration(audio_path)
        clips = sorted((ASSETS / scene_id).glob("*.mp4"))
        shot_count = max(1, math.ceil(section_seconds / SHOT_SECONDS))
        minimum_unique = max(4, math.ceil(shot_count / MAX_SOURCE_USES))
        if len(clips) < minimum_unique:
            raise RuntimeError(
                f"{scene_id}: {len(clips)} topic-matched clips available; {minimum_unique} are required "
                f"to keep source reuse at or below {MAX_SOURCE_USES}."
            )
        section_uses = {p: 0 for p in clips}
        previous = None
        for shot_index in range(shot_count):
            shot_seconds = min(SHOT_SECONDS, section_seconds - shot_index * SHOT_SECONDS)
            available = [p for p in clips if section_uses[p] < MAX_SOURCE_USES]
            if not available:
                raise RuntimeError(f"{scene_id}: ran out of unique footage under the two-use cap.")
            available.sort(key=lambda p: (section_uses[p], p == previous, p.name))
            source = available[0]
            used_before = section_uses[source]
            section_uses[source] += 1
            rel = source.relative_to(ROOT).as_posix()
            source_uses[rel] = section_uses[source]
            if rel not in manifest:
                raise RuntimeError(f"Source clip not present in the rights manifest: {rel}")
            asset = manifest[rel]
            src_duration = duration(source)
            max_seek = max(0.0, src_duration - min(shot_seconds, src_duration - .05))
            seek = (used_before * 2.2) % max(.1, max_seek) if max_seek > .1 else 0.0
            output = shot_dir / f"shot_{len(shot_files) + 1:04d}.mp4"
            make_shot(source, output, shot_seconds, seek)
            shot_files.append(output)
            timeline.append({
                "start_seconds": round(timeline_cursor, 3),
                "duration_seconds": round(shot_seconds, 3),
                "section_id": scene_id,
                "source_file": rel,
                "visual_type": "topic-matched real-world moving footage",
                "source_tags": asset.get("tags", ""),
                "search_query": asset.get("search_query", ""),
                "relevance_groups_matched": asset.get("relevance_groups_matched")
            })
            timeline_cursor += shot_seconds
            previous = source
        unique_count += len(clips)
        if max(section_uses.values(), default=0) > MAX_SOURCE_USES:
            raise RuntimeError(f"{scene_id}: source-use cap exceeded.")

    max_uses = max(source_uses.values(), default=0)
    if max_uses > MAX_SOURCE_USES:
        raise RuntimeError(f"A source clip was used {max_uses} times; maximum is {MAX_SOURCE_USES}.")
    concat = OUT / "broll_concat.txt"
    concat.write_text("\n".join(f"file '{p.as_posix()}'" for p in shot_files), encoding="utf-8")
    video_only = OUT / "broll_video_only.mp4"
    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(concat), "-c", "copy", "-fflags", "+genpts", str(video_only)])

    thumbnail = OUT / "thumbnail_rwb.png"
    thumb_filter = (
        "scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720,"
        "drawbox=x=0:y=0:w=iw:h=8:color=0xD62839:t=fill,"
        "drawbox=x=0:y=0:w=700:h=170:color=0x102B52@0.86:t=fill,"
        "drawbox=x=0:y=0:w=12:h=170:color=0xD62839:t=fill,"
        "drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
        "text='THE HIDDEN NETWORK':fontcolor=white:fontsize=48:x=42:y=48,"
        "drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:"
        "text='UNDER THE OCEAN':fontcolor=white:fontsize=28:x=44:y=112,"
        "drawbox=x=0:y=ih-8:w=iw:h=8:color=0x1746A2:t=fill"
    )
    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", "8", "-i", str(video_only), "-frames:v", "1", "-vf", thumb_filter, str(thumbnail)])

    final = OUT / f"Underneath_Everything_{ROOT.name}_Kokoro_Broll_720p.mp4"
    run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(video_only), "-i", str(audio_file),
        "-map", "0:v:0", "-map", "1:a:0", "-sn",
        "-vf", "scale=1280:720:flags=lanczos,setsar=1,fps=24",
        "-c:v", "libx264", "-preset", "medium", "-crf", "21",
        "-pix_fmt", "yuv420p", "-r", "24", "-c:a", "aac", "-b:a", "192k",
        "-ar", "48000", "-ac", "2", "-shortest", "-movflags", "+faststart", str(final)
    ])
    meta = json.loads(subprocess.check_output(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(final)], text=True))
    video = next(s for s in meta["streams"] if s["codec_type"] == "video")
    audio = next(s for s in meta["streams"] if s["codec_type"] == "audio")
    assert not any(s["codec_type"] == "subtitle" for s in meta["streams"]), "Subtitle streams are forbidden"
    runtime = float(meta["format"]["duration"])
    assert (video["width"], video["height"]) == (1280, 720)
    assert video["codec_name"] == "h264" and video.get("avg_frame_rate") == "24/1"
    assert audio["codec_name"] == "aac" and audio.get("sample_rate") == "48000" and int(audio.get("channels", 0)) == 2
    run(["ffmpeg", "-v", "error", "-i", str(final), "-f", "null", "-"])

    broll_duration = sum(item["duration_seconds"] for item in timeline)
    broll_pct = round(100 * broll_duration / max(runtime, 0.001), 2)
    if broll_pct < 70:
        raise RuntimeError(f"Relevant moving B-roll share was only {broll_pct}%; release minimum is 70%.")

    derivative = OUT / f"Underneath_Everything_{ROOT.name}_Kokoro_Broll_360p_24fps_450k_nocaptions.mp4"
    encode_360p(final, derivative)
    low_meta = json.loads(subprocess.check_output(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(derivative)], text=True))
    low_video = next(s for s in low_meta["streams"] if s["codec_type"] == "video")
    low_audio = next(s for s in low_meta["streams"] if s["codec_type"] == "audio")
    if (low_video["width"], low_video["height"]) != (640, 360) or low_video.get("avg_frame_rate") != "24/1":
        raise RuntimeError("360p derivative must be 640x360 at measured 24fps.")
    if low_audio.get("sample_rate") != "48000" or int(low_audio.get("channels", 0)) != 2:
        raise RuntimeError("360p derivative must use stereo AAC at 48 kHz.")
    run(["ffmpeg", "-v", "error", "-i", str(derivative), "-f", "null", "-"])

    report = {
        "episode": ROOT.name,
        "title": (json.loads((ROOT / "episode_meta.json").read_text(encoding="utf-8")).get("title") if (ROOT / "episode_meta.json").exists() else ROOT.name),
        "file": final.name,
        "file_size_bytes": final.stat().st_size,
        "file_size_mb_decimal": round(final.stat().st_size / 1_000_000, 2),
        "low_data_derivative": {"file": derivative.name, "file_size_bytes": derivative.stat().st_size, "file_size_mb_decimal": round(derivative.stat().st_size / 1_000_000, 2), "resolution": "640x360", "fps_measured": low_video["avg_frame_rate"], "video_bitrate_target_bps": 450000, "audio_sample_rate": low_audio["sample_rate"], "audio_channels": low_audio["channels"]},
        "duration_seconds": round(runtime, 3),
        "resolution": "1280x720",
        "fps_measured": video["avg_frame_rate"],
        "video_codec": video["codec_name"],
        "audio_codec": audio["codec_name"],
        "audio_sample_rate": audio["sample_rate"],
        "narration_provider": "Kokoro-82M",
        "narration_voice_id": "am_echo",
        "narration_file_wav": audio_report["wav"],
        "narration_file_mp3": audio_report["mp3"],
        "unique_broll_clips": unique_count,
        "broll_assets": unique_count,
        "broll_runtime_seconds": round(broll_duration, 3),
        "broll_coverage_percent": broll_pct,
        "max_source_clip_uses": max_uses,
        "source_clip_uses": source_uses,
        "visuals": "Only episode-matched moving footage; no generic filler; no captions, subtitles, lower thirds or logo overlays.",
        "thumbnail": thumbnail.name,
        "captions": "none",
        "subtitle_streams": "none",
        "full_decode_check": "PASS",
        "public_release_status": "Awaiting human review of footage rights and full playback."
    }
    (OUT / "render_report_broll_echo.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (OUT / "broll_timeline.json").write_text(json.dumps(timeline, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2), flush=True)

if __name__ == "__main__":
    main()
