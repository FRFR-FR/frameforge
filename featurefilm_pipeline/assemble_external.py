#!/usr/bin/env python3
"""Verify 240 remote-mounted segments and stream-copy them into external storage.

The output is fragmented MP4 sent directly to rclone rcat. The four-hour file
never has to be staged on the GitHub runner's local disk.
"""
from __future__ import annotations
import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

COUNT = 240
FPS = 24
WIDTH = 1280
HEIGHT = 720
FRAMES_PER_SEGMENT = 1440
EXPECTED_FRAMES = COUNT * FRAMES_PER_SEGMENT
EXPECTED_SECONDS = COUNT * 60

def run(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(args, check=True, capture_output=True, text=True)

def probe(path: Path, count_frames: bool = False) -> dict:
    args = ["ffprobe", "-v", "error"]
    if count_frames:
        args.append("-count_frames")
    args += ["-show_streams", "-show_format", "-of", "json", str(path)]
    return json.loads(run(args).stdout)

def validate_segment(path: Path, number: int) -> None:
    if not path.is_file() or path.stat().st_size <= 0:
        raise RuntimeError(f"Missing/empty remote segment {number:03d}: {path}")
    data = probe(path, count_frames=True)
    videos = [x for x in data.get("streams", []) if x.get("codec_type") == "video"]
    audios = [x for x in data.get("streams", []) if x.get("codec_type") == "audio"]
    if len(videos) != 1 or len(audios) < 1:
        raise RuntimeError(f"Segment {number:03d}: expected one video stream and at least one audio stream")
    v, a = videos[0], audios[0]
    if (v.get("codec_name"), v.get("width"), v.get("height"),
        v.get("r_frame_rate"), str(v.get("nb_read_frames"))) != (
            "h264", WIDTH, HEIGHT, f"{FPS}/1", str(FRAMES_PER_SEGMENT)):
        raise RuntimeError(f"Segment {number:03d}: video QC failed: {v}")
    if a.get("codec_name") != "aac":
        raise RuntimeError(f"Segment {number:03d}: audio is not AAC")
    duration = float(data.get("format", {}).get("duration", 0))
    if not 59.9 <= duration <= 60.1:
        raise RuntimeError(f"Segment {number:03d}: duration {duration:.3f}s is not 60s")

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, required=True,
                        help="rclone-mounted remote root/segments")
    parser.add_argument("--remote-root", required=True,
                        help="Configured rclone root, e.g. remote:root/project")
    parser.add_argument("--output-relative", default="final/BROWN_Book_One_Complete_4h_720p24.mp4",
                        help="Output path relative to the configured remote root")
    parser.add_argument("--rclone-config", type=Path, required=True)
    parser.add_argument("--work-dir", type=Path, required=True)
    args = parser.parse_args()

    source = args.input_dir.resolve()
    work = args.work_dir.resolve()
    work.mkdir(parents=True, exist_ok=True)
    concat = work / "featurefilm_concat.txt"

    ordered = []
    for number in range(1, COUNT + 1):
        path = source / f"segment-{number:03d}.mp4"
        validate_segment(path, number)
        ordered.append(path)
        print(f"Validated external segment {number:03d}/{COUNT}", flush=True)

    def quote_concat(path: Path) -> str:
        return str(path).replace("'", "'\\''")

    concat.write_text("".join(f"file '{quote_concat(p)}'\n" for p in ordered),
                      encoding="utf-8")

    remote_output = args.remote_root.rstrip("/") + "/" + args.output_relative.lstrip("/")
    ffmpeg_cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "warning",
        "-f", "concat", "-safe", "0", "-i", str(concat),
        "-map", "0", "-c", "copy",
        "-movflags", "+frag_keyframe+empty_moov+default_base_moof",
        "-f", "mp4", "pipe:1"
    ]
    rclone_cmd = [
        "rclone", "rcat", "--config", str(args.rclone_config), remote_output
    ]
    log = (work / "final-assembly-ffmpeg.log").open("w", encoding="utf-8")
    uploader = subprocess.Popen(rclone_cmd, stdin=subprocess.PIPE,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    assert uploader.stdin is not None
    ffmpeg = subprocess.Popen(ffmpeg_cmd, stdout=uploader.stdin,
                               stderr=log)
    uploader.stdin.close()
    ffmpeg_rc = ffmpeg.wait()
    upload_stdout, upload_stderr = uploader.communicate()
    log.close()
    if ffmpeg_rc != 0:
        raise RuntimeError(f"FFmpeg assembly failed (exit {ffmpeg_rc}); inspect {log.name}")
    if uploader.returncode != 0:
        raise RuntimeError("External upload failed: " + upload_stderr.decode("utf-8", "replace")[-4000:])

    # Verify the uploaded object through the mounted remote. The fragmented MP4
    # stores stream metadata and duration up front, so this probe need not scan
    # all 4 hours of encoded packets again.
    # The supplied mount root represents exactly the configured remote root.
    mount_root = source.parent
    final_path = mount_root / args.output_relative
    for _ in range(30):
        if final_path.is_file() and final_path.stat().st_size > 0:
            break
        time.sleep(2)
    if not final_path.is_file() or final_path.stat().st_size <= 0:
        raise RuntimeError("Final object is not visible in the external storage mount after upload")

    final = probe(final_path, count_frames=False)
    videos = [x for x in final.get("streams", []) if x.get("codec_type") == "video"]
    audios = [x for x in final.get("streams", []) if x.get("codec_type") == "audio"]
    if len(videos) != 1 or len(audios) < 1:
        raise RuntimeError(f"Final remote file has invalid streams: {final.get('streams')}")
    v, a = videos[0], audios[0]
    if (v.get("codec_name"), v.get("width"), v.get("height"),
        v.get("r_frame_rate")) != ("h264", WIDTH, HEIGHT, f"{FPS}/1"):
        raise RuntimeError(f"Final video metadata failed: {v}")
    duration = float(final.get("format", {}).get("duration", 0))
    if not EXPECTED_SECONDS - 1 <= duration <= EXPECTED_SECONDS + 1:
        raise RuntimeError(f"Final duration {duration:.2f}s does not equal four hours")
    if a.get("codec_name") != "aac":
        raise RuntimeError(f"Final audio metadata failed: {a}")
    if (COUNT, EXPECTED_FRAMES) != (240, 345600):
        raise RuntimeError("Internal expected runtime/frame count inconsistency")

    print(json.dumps({
        "status": "VERIFIED_REMOTE",
        "segments": COUNT,
        "frames_expected": EXPECTED_FRAMES,
        "runtime_seconds": duration,
        "resolution": "1280x720",
        "fps": "24/1",
        "video_codec": v.get("codec_name"),
        "audio_codec": a.get("codec_name"),
        "remote_output": remote_output,
        "remote_bytes": final_path.stat().st_size
    }, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
