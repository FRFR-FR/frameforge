#!/usr/bin/env python3
"""Create lightweight contact-sheet, scene-preview and audio-waveform review files."""
from __future__ import annotations

import argparse
import html
import json
import math
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, capture_output=True, text=True, check=False)


def probe_media(path: str | Path, ffprobe: str = "ffprobe") -> dict[str, Any]:
    if not shutil.which(ffprobe):
        raise RuntimeError(f"Could not find {ffprobe!r} on PATH.")
    result = run([
        ffprobe, "-v", "error", "-show_entries",
        "format=duration,size,format_name:stream=codec_type,codec_name,width,height,avg_frame_rate,sample_rate,channels",
        "-of", "json", str(path),
    ])
    if result.returncode:
        raise RuntimeError("ffprobe failed: " + result.stderr[-2500:])
    return json.loads(result.stdout)


def create_review(
    video: str | Path,
    output_dir: str | Path,
    *,
    sample_interval: float = 2.5,
    scene_threshold: float = 0.32,
    max_scene_previews: int = 20,
    ffmpeg: str = "ffmpeg",
    ffprobe: str = "ffprobe",
) -> dict[str, Any]:
    source = Path(video)
    if not source.is_file():
        raise FileNotFoundError(f"Video does not exist: {source}")
    if sample_interval <= 0 or sample_interval > 300:
        raise ValueError("Sample interval must be greater than 0 and at most 300 seconds.")
    if not (0.05 <= scene_threshold <= 0.95):
        raise ValueError("Scene threshold must be between 0.05 and 0.95.")
    if not (0 <= max_scene_previews <= 100):
        raise ValueError("Maximum scene previews must be between 0 and 100.")
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    scenes_dir = destination / "scene-previews"
    scenes_dir.mkdir(exist_ok=True)
    metadata = probe_media(source, ffprobe)
    streams = metadata.get("streams", [])
    video_stream = next((stream for stream in streams if stream.get("codec_type") == "video"), None)
    audio_stream = next((stream for stream in streams if stream.get("codec_type") == "audio"), None)
    if not video_stream:
        raise RuntimeError("Input file contains no video stream.")
    try:
        duration = float(metadata.get("format", {}).get("duration") or video_stream.get("duration") or 0)
    except (TypeError, ValueError):
        duration = 0
    if duration <= 0:
        raise RuntimeError("Could not determine the video duration.")

    sample_count = max(1, min(40, int(math.ceil(duration / sample_interval))))
    columns = 4
    rows = max(1, math.ceil(sample_count / columns))
    contact = destination / "contact-sheet.jpg"
    filter_value = (
        f"fps=1/{sample_interval},"
        "scale=320:180:force_original_aspect_ratio=decrease:flags=lanczos,"
        "pad=320:180:(ow-iw)/2:(oh-ih)/2:color=black,"
        f"tile={columns}x{rows}:nb_frames={sample_count}:padding=8:margin=8:color=0x162334"
    )
    contact_result = run([
        ffmpeg, "-hide_banner", "-nostdin", "-y", "-i", str(source),
        "-vf", filter_value, "-frames:v", "1", "-q:v", "3", str(contact),
    ])
    if contact_result.returncode or not contact.is_file() or contact.stat().st_size == 0:
        raise RuntimeError("Could not create a contact sheet: " + contact_result.stderr[-2500:])

    waveform = None
    waveform_note = "No audio stream was found in this export."
    if audio_stream:
        waveform_path = destination / "audio-waveform.png"
        wave_result = run([
            ffmpeg, "-hide_banner", "-nostdin", "-y", "-i", str(source),
            "-filter_complex", "aformat=channel_layouts=stereo,showwavespic=s=1600x240:colors=0x55a7ff",
            "-frames:v", "1", str(waveform_path),
        ])
        if wave_result.returncode == 0 and waveform_path.is_file() and waveform_path.stat().st_size:
            waveform = waveform_path.name
            waveform_note = "Waveform rendered from the embedded audio stream."
        else:
            waveform_note = "Audio stream exists, but waveform rendering failed: " + wave_result.stderr[-800:]

    scene_files: list[str] = []
    if max_scene_previews:
        pattern = scenes_dir / "scene_%03d.jpg"
        scene_result = run([
            ffmpeg, "-hide_banner", "-nostdin", "-y", "-i", str(source),
            "-vf", f"select='gt(scene,{scene_threshold})',scale=640:-2:flags=lanczos",
            "-fps_mode", "vfr", "-frames:v", str(max_scene_previews), "-q:v", "3", str(pattern),
        ])
        if scene_result.returncode == 0:
            scene_files = [str(path.relative_to(destination)) for path in sorted(scenes_dir.glob("scene_*.jpg"))]

    fps = video_stream.get("avg_frame_rate") or video_stream.get("r_frame_rate")
    report = {
        "format": "frameforge-visual-audio-review",
        "version": 1,
        "source": str(source),
        "created_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        "media": {
            "duration_seconds": duration,
            "width": video_stream.get("width"),
            "height": video_stream.get("height"),
            "frame_rate": fps,
            "video_codec": video_stream.get("codec_name"),
            "audio_stream": bool(audio_stream),
            "audio_codec": audio_stream.get("codec_name") if audio_stream else None,
            "audio_sample_rate": audio_stream.get("sample_rate") if audio_stream else None,
        },
        "contact_sheet": contact.name,
        "sample_interval_seconds": sample_interval,
        "audio_waveform": waveform,
        "audio_waveform_note": waveform_note,
        "scene_preview_files": scene_files,
        "human_review_required": True,
        "review_notes": [],
    }
    (destination / "review.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    title = html.escape(source.name)
    waveform_html = (
        f'<h2>Audio waveform</h2><img src="{html.escape(waveform)}" alt="Audio waveform">'
        if waveform else f'<h2>Audio waveform</h2><p>{html.escape(waveform_note)}</p>'
    )
    scene_html = "".join(
        f'<figure><img src="{html.escape(path)}" alt="Scene preview"><figcaption>{html.escape(Path(path).name)}</figcaption></figure>'
        for path in scene_files
    ) or "<p>No high-confidence scene changes were extracted. Use the contact sheet to review the sequence.</p>"
    page = f"""<!doctype html>
<html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>FrameForge review · {title}</title>
<style>
body{{margin:0;padding:24px;background:#0b111a;color:#e8eef6;font:15px/1.5 system-ui,sans-serif}}
main{{max-width:1200px;margin:auto}}img{{max-width:100%;height:auto;background:#142031;border:1px solid #30445c;border-radius:8px}}
h1,h2{{color:#cfe2f7}}.facts{{display:flex;flex-wrap:wrap;gap:12px}}.facts span{{padding:7px 10px;background:#152336;border-radius:6px}}
.scenes{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px}}
figure{{margin:0;padding:8px;background:#121e2d;border-radius:8px}}figcaption{{font-size:12px;color:#9cb1c6}}
.notice{{padding:12px;border:1px solid #9c7a45;border-radius:8px;color:#f0d39b}}
</style><main>
<h1>FrameForge visual / audio review</h1><p>{title}</p>
<div class="facts"><span>{report['media']['width']} × {report['media']['height']}</span>
<span>{html.escape(str(fps))} fps</span><span>{duration:.2f} seconds</span>
<span>{html.escape(str(report['media']['video_codec']))}</span>
<span>Audio: {'present' if audio_stream else 'not present'}</span></div>
<h2>Contact sheet</h2><p>Sample interval: {sample_interval:.2f} seconds. Use this sheet to inspect overall visual continuity.</p>
<img src="{contact.name}" alt="Video contact sheet">
{waveform_html}
<h2>Detected scene previews</h2><div class="scenes">{scene_html}</div>
<p class="notice">Automated previews help locate issues; human visual and audio approval is still required before publication.</p>
</main></html>"""
    (destination / "review.html").write_text(page, encoding="utf-8")
    report["html_review"] = "review.html"
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Rendered MP4 or other FFmpeg-readable file.")
    parser.add_argument("--output-dir", required=True, help="Directory for contact sheet, waveform and HTML review.")
    parser.add_argument("--sample-interval", type=float, default=2.5)
    parser.add_argument("--scene-threshold", type=float, default=0.32)
    parser.add_argument("--max-scene-previews", type=int, default=20)
    args = parser.parse_args(argv)
    try:
        report = create_review(
            args.input, args.output_dir, sample_interval=args.sample_interval,
            scene_threshold=args.scene_threshold, max_scene_previews=args.max_scene_previews,
        )
    except Exception as error:
        print("ERROR: " + str(error), file=sys.stderr)
        return 1
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
