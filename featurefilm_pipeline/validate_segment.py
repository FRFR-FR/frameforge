#!/usr/bin/env python3
"""Validate one encoded segment before it can be uploaded or assembled."""
from __future__ import annotations
import argparse
import json
import subprocess
import sys
from pathlib import Path

def probe(path: Path) -> dict:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-count_frames", "-show_streams",
         "-show_format", "-of", "json", str(path)],
        check=True, capture_output=True, text=True
    )
    return json.loads(result.stdout)

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--segment", type=int, required=True)
    args = parser.parse_args()
    if not args.video.is_file() or args.video.stat().st_size == 0:
        raise SystemExit(f"Missing or empty segment: {args.video}")
    data = probe(args.video)
    videos = [s for s in data.get("streams", []) if s.get("codec_type") == "video"]
    audios = [s for s in data.get("streams", []) if s.get("codec_type") == "audio"]
    if len(videos) != 1 or len(audios) < 1:
        raise SystemExit(f"Segment {args.segment}: expected one video and at least one audio stream")
    stream = videos[0]
    fmt = data.get("format", {})
    expected = {
        "width": 1280, "height": 720, "r_frame_rate": "24/1",
        "nb_read_frames": "1440"
    }
    for key, value in expected.items():
        actual = stream.get(key)
        if str(actual) != value:
            raise SystemExit(f"Segment {args.segment}: {key}={actual!r}, expected {value!r}")
    duration = float(fmt.get("duration", 0))
    if not 59.9 <= duration <= 60.1:
        raise SystemExit(f"Segment {args.segment}: duration={duration:.3f}s, expected 60s")
    if stream.get("codec_name") != "h264":
        raise SystemExit(f"Segment {args.segment}: video codec is not H.264")
    if audios[0].get("codec_name") != "aac":
        raise SystemExit(f"Segment {args.segment}: audio codec is not AAC")
    print(json.dumps({"segment": args.segment, "valid": True,
                      "duration": duration, "frames": 1440,
                      "resolution": "1280x720", "fps": "24/1",
                      "audio": audios[0].get("codec_name")}))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
