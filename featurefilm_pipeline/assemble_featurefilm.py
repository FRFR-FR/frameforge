#!/usr/bin/env python3
"""Verify and concatenate all 240 unique segments in strict numeric order."""
from __future__ import annotations
import argparse
import json
import subprocess
from pathlib import Path

SEGMENT_COUNT = 240

def run(command):
    return subprocess.run(command, check=True, capture_output=True, text=True)

def probe(path: Path) -> dict:
    return json.loads(run([
        "ffprobe", "-v", "error", "-count_frames", "-show_streams",
        "-show_format", "-of", "json", str(path)
    ]).stdout)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source = args.input_dir.resolve()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    concat_file = args.output.parent / "featurefilm_concat.txt"
    ordered = []
    for number in range(1, SEGMENT_COUNT + 1):
        path = source / f"segment-{number:03d}.mp4"
        if not path.is_file() or path.stat().st_size == 0:
            raise SystemExit(f"Missing segment {number:03d}: {path}")
        data = probe(path)
        videos = [s for s in data.get("streams", []) if s.get("codec_type") == "video"]
        audios = [s for s in data.get("streams", []) if s.get("codec_type") == "audio"]
        if len(videos) != 1 or not audios:
            raise SystemExit(f"Segment {number:03d} has missing or ambiguous streams")
        v = videos[0]
        f = data.get("format", {})
        if (v.get("width"), v.get("height"), v.get("r_frame_rate"),
            str(v.get("nb_read_frames"))) != (1280, 720, "24/1", "1440"):
            raise SystemExit(f"Segment {number:03d} failed video frame/size/fps QC: {v}")
        if not 59.9 <= float(f.get("duration", 0)) <= 60.1:
            raise SystemExit(f"Segment {number:03d} duration is not 60 seconds")
        if v.get("codec_name") != "h264" or audios[0].get("codec_name") != "aac":
            raise SystemExit(f"Segment {number:03d} codecs do not match the assembly profile")
        ordered.append(path)

    lines = []
    for path in ordered:
        escaped = str(path).replace("'", "'\\''")
        lines.append(f"file '{escaped}'")
    concat_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "warning",
         "-f", "concat", "-safe", "0", "-i", str(concat_file),
         "-c", "copy", "-movflags", "+faststart", str(args.output)])

    final = probe(args.output)
    videos = [s for s in final.get("streams", []) if s.get("codec_type") == "video"]
    audios = [s for s in final.get("streams", []) if s.get("codec_type") == "audio"]
    if len(videos) != 1 or not audios:
        raise SystemExit("Final file does not contain exactly one video and at least one audio stream")
    v = videos[0]
    duration = float(final.get("format", {}).get("duration", 0))
    if (v.get("width"), v.get("height"), v.get("r_frame_rate"),
        str(v.get("nb_read_frames"))) != (1280, 720, "24/1", "345600"):
        raise SystemExit(f"Final frame/resolution/fps QC failed: {v}")
    if not 14399 <= duration <= 14401:
        raise SystemExit(f"Final duration is {duration:.2f}s; expected 14,400s")
    print(json.dumps({
        "status": "VERIFIED",
        "segments": SEGMENT_COUNT,
        "runtime_seconds": duration,
        "runtime_hours": duration / 3600,
        "frames": int(v["nb_read_frames"]),
        "resolution": "1280x720",
        "fps": "24/1",
        "output": str(args.output),
        "bytes": args.output.stat().st_size
    }, indent=2))

if __name__ == "__main__":
    main()
