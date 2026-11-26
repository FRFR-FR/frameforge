#!/usr/bin/env python3
"""B-roll-first documentary assembly. Strict landscape export: 1280x720."""
from pathlib import Path
import argparse, json, math, re, subprocess

ap = argparse.ArgumentParser()
ap.add_argument("--episode-dir", required=True)
args = ap.parse_args()
ROOT = Path(args.episode_dir).resolve()
OUT = ROOT / "output"
ASSETS = ROOT / "assets" / "broll"
FPS = 24
SHOT_SECONDS = 7.0

def run(cmd):
    subprocess.run(cmd, check=True)

def duration(path):
    return float(subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "csv=p=0", str(path)
    ], text=True).strip())

def list_scene_clips(scene_id):
    folder = ASSETS / scene_id
    files = sorted(folder.glob("*.mp4"))
    if len(files) < 3:
        raise RuntimeError(f"{scene_id}: at least 3 topic-matched moving B-roll clips are required; found {len(files)}")
    return files

def make_shot(src, out_path, seconds, seek, section_title, show_lower_third):
    # The footage remains naturally coloured. Red, white and blue are used only
    # for a restrained broadcast-style identity, never as a full-frame tint.
    title = re.sub(r"[^A-Za-z0-9 &-]", "", section_title).strip()[:42]
    font = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    vf_parts = [
        "scale=1280:720:force_original_aspect_ratio=increase",
        "crop=1280:720",
        "setsar=1",
        "fps=24",
        "format=yuv420p",
        # Thin red top rule and blue bottom rule.
        "drawbox=x=0:y=0:w=iw:h=6:color=0xD62839:t=fill",
        "drawbox=x=0:y=ih-6:w=iw:h=6:color=0x1746A2:t=fill",
        # Small, consistent channel bug on the footage.
        "drawbox=x=32:y=24:w=360:h=40:color=0x102B52@0.78:t=fill",
        "drawbox=x=32:y=24:w=7:h=40:color=0xD62839:t=fill",
        f"drawtext=fontfile={font}:text='UNDERNEATH EVERYTHING':fontcolor=white:fontsize=17:x=52:y=35"
    ]
    if show_lower_third:
        vf_parts.extend([
            "drawbox=x=32:y=ih-100:w=690:h=62:color=0x102B52@0.88:t=fill:enable='lt(t,4)'",
            "drawbox=x=32:y=ih-100:w=8:h=62:color=0xD62839:t=fill:enable='lt(t,4)'",
            f"drawtext=fontfile={font}:text='{title}':fontcolor=white:fontsize=22:x=56:y=main_h-78:enable='lt(t,4)'"
        ])
    vf = ",".join(vf_parts)
    run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-stream_loop", "-1", "-i", str(src),
        "-ss", f"{seek:.3f}", "-t", f"{seconds:.3f}",
        "-vf", vf, "-an", "-c:v", "libx264", "-preset", "veryfast",
        "-crf", "22", "-pix_fmt", "yuv420p", "-r", str(FPS),
        "-movflags", "+faststart", str(out_path)
    ])

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    audio_report_path = OUT / "kokoro_narration_report.json"
    if not audio_report_path.exists():
        raise RuntimeError("Kokoro narration report is missing. Do not use eSpeak as the release master.")
    audio_report = json.loads(audio_report_path.read_text(encoding="utf-8"))
    sections = audio_report["sections"]
    audio_file = OUT / audio_report["wav"]
    if not audio_file.exists():
        raise RuntimeError("Kokoro narration WAV is missing.")
    manifest_path = ROOT / "asset-manifest-broll.csv"
    if not manifest_path.exists():
        raise RuntimeError("B-roll rights manifest is missing; refusing to render.")
    clip_count = sum(1 for _ in ASSETS.glob("section_*/*.mp4"))
    if clip_count < 27:
        raise RuntimeError(f"Only {clip_count} moving B-roll clips found; 27 relevant clips are the minimum.")

    shot_dir = OUT / "broll_shots"
    shot_dir.mkdir(exist_ok=True)
    shot_files, timeline = [], []
    timeline_cursor = 0.0

    for sec in sections:
        scene_id = sec["id"]
        audio_path = ROOT / sec["audio_file"]
        section_seconds = duration(audio_path)
        clips = list_scene_clips(scene_id)
        shot_count = max(1, math.ceil(section_seconds / SHOT_SECONDS))
        for shot_index in range(shot_count):
            shot_seconds = min(SHOT_SECONDS, section_seconds - shot_index * SHOT_SECONDS)
            src = clips[shot_index % len(clips)]
            src_duration = duration(src)
            cycle = shot_index // len(clips)
            max_seek = max(0.0, src_duration - min(shot_seconds, SHOT_SECONDS))
            seek = (cycle * 2.9) % max_seek if max_seek > 0.1 else 0.0
            out_path = shot_dir / f"shot_{len(shot_files)+1:04d}.mp4"
            make_shot(src, out_path, shot_seconds, seek, sec.get('title', scene_id), shot_index == 0)
            shot_files.append(out_path)
            timeline.append({
                "start_seconds": round(timeline_cursor, 3),
                "duration_seconds": round(shot_seconds, 3),
                "section_id": scene_id,
                "source_file": str(src.relative_to(ROOT)),
                "visual_type": "moving real-world B-roll"
            })
            timeline_cursor += shot_seconds

    concat = OUT / "broll_concat.txt"
    concat.write_text("\n".join(f"file '{p.as_posix()}'" for p in shot_files), encoding="utf-8")
    video_only = OUT / "broll_video_only.mp4"
    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
         "-f", "concat", "-safe", "0", "-i", str(concat),
         "-c", "copy", "-fflags", "+genpts", str(video_only)])

    # Use an actual B-roll frame for the thumbnail, with the same R/W/B brand language.
    thumbnail = OUT / "thumbnail_rwb.png"
    thumb_vf = (
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
    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
         "-ss", "8", "-i", str(video_only), "-frames:v", "1",
         "-vf", thumb_vf, str(thumbnail)])

    final = OUT / f"Underneath_Everything_{ROOT.name}_Kokoro_Broll_720p.mp4"
    # No subtitles or closed-caption overlays are ever burned into channel videos.
    # Explicitly disable subtitle-stream mapping on the finished MP4.
    run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-i", str(video_only), "-i", str(audio_file),
        "-map", "0:v:0", "-map", "1:a:0", "-sn",
        "-vf", "scale=1280:720:flags=lanczos,setsar=1,fps=24",
        "-c:v", "libx264", "-preset", "medium", "-crf", "21",
        "-pix_fmt", "yuv420p", "-r", "24",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
        "-shortest", "-movflags", "+faststart", str(final)
    ])

    meta = json.loads(subprocess.check_output([
        "ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(final)
    ], text=True))
    v = next(s for s in meta["streams"] if s["codec_type"] == "video")
    a = next(s for s in meta["streams"] if s["codec_type"] == "audio")
    assert not any(s["codec_type"] == "subtitle" for s in meta["streams"]), "Subtitle streams are forbidden"
    runtime = float(meta["format"]["duration"])
    size = final.stat().st_size
    assert (v["width"], v["height"]) == (1280, 720), f"720p lock failed: {v.get('width')}x{v.get('height')}"
    assert v["codec_name"] == "h264" and a["codec_name"] == "aac", "Expected H.264 + AAC"
    assert a.get("sample_rate") == "48000", "Expected 48 kHz audio"
    assert v.get("avg_frame_rate") == "24/1", f"Measured frame rate is {v.get('avg_frame_rate')}"
    run(["ffmpeg", "-v", "error", "-i", str(final), "-f", "null", "-"])

    broll_duration = sum(x["duration_seconds"] for x in timeline)
    broll_pct = round(100 * broll_duration / max(runtime, 0.001), 2)
    if broll_pct < 70:
        raise RuntimeError(f"B-roll coverage was only {broll_pct}%; release minimum is 70%.")

    report = {
        "episode": ROOT.name,
        "title": (json.loads((ROOT / "episode_meta.json").read_text(encoding="utf-8")).get("title") if (ROOT / "episode_meta.json").exists() else ROOT.name),
        "file": final.name,
        "file_size_bytes": size,
        "file_size_mb_decimal": round(size / 1_000_000, 2),
        "duration_seconds": round(runtime, 3),
        "resolution": "1280x720",
        "fps_measured": v["avg_frame_rate"],
        "video_codec": v["codec_name"],
        "audio_codec": a["codec_name"],
        "audio_sample_rate": a.get("sample_rate"),
        "narration_provider": "Kokoro-82M",
        "narration_voice_id": "am_echo",
        "narration_file_wav": audio_report["wav"],
        "narration_file_mp3": audio_report["mp3"],
        "visuals": "Relevant moving real-world B-roll; restrained red/white/blue broadcast overlays and lower thirds; natural footage colour preserved; no PowerPoint slides or still-image zooms.",
        "brand_palette": {"red": "#D62839", "white": "#FFFFFF", "blue": "#1746A2", "navy": "#102B52"},
        "thumbnail": thumbnail.name,
        "broll_assets": clip_count,
        "broll_runtime_seconds": round(broll_duration, 3),
        "broll_coverage_percent": broll_pct,
        "music": "none",
        "captions": "none",
        "subtitle_streams": "none",
        "asset_manifest": str(manifest_path.name),
        "full_decode_check": "PASS",
        "public_release_status": "Awaiting human review of footage rights and full playback."
    }
    (OUT / "render_report_broll_echo.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (OUT / "broll_timeline.json").write_text(json.dumps(timeline, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2), flush=True)

if __name__ == "__main__":
    main()
