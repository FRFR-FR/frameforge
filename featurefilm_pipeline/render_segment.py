#!/usr/bin/env python3
"""Render one approved 60-second BROWN segment from the approved Blender master.

Run inside Blender:
  blender --background production/assets/BROWN_featurefilm_master.blend \
    --python featurefilm_pipeline/render_segment.py -- \
    --segment 1 --work-dir output/segment-001
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
import bpy

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = json.loads((Path(__file__).resolve().parent / "featurefilm_manifest.json").read_text(encoding="utf-8"))

def arguments():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--segment", type=int, required=True)
    parser.add_argument("--work-dir", type=Path, required=True)
    return parser.parse_args(argv)

def main():
    args = arguments()
    count = int(MANIFEST["segment_count"])
    seconds = int(MANIFEST["segment_duration_seconds"])
    fps = int(MANIFEST["render"]["fps"])
    total_frames = int(MANIFEST["render"]["total_frames"])
    if args.segment < 1 or args.segment > count:
        raise ValueError(f"segment must be between 1 and {count}")

    first_frame = (args.segment - 1) * seconds * fps + 1
    last_frame = first_frame + seconds * fps - 1
    if last_frame > total_frames:
        raise RuntimeError("Segment range exceeds the approved film timeline")

    scene = bpy.context.scene
    if scene is None or scene.camera is None:
        raise RuntimeError("Approved master scene has no active camera")
    if scene.frame_end < last_frame:
        raise RuntimeError(f"Master scene ends at frame {scene.frame_end}; segment needs frame {last_frame}")

    target = MANIFEST["render"]
    scene.render.resolution_x = int(target["width"])
    scene.render.resolution_y = int(target["height"])
    scene.render.resolution_percentage = 100
    scene.render.fps = fps
    scene.render.fps_base = 1.0
    scene.frame_start = first_frame
    scene.frame_end = last_frame
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.image_settings.color_depth = "16"
    scene.render.use_file_extension = True

    work = args.work_dir.resolve()
    frames = work / "frames"
    frames.mkdir(parents=True, exist_ok=True)
    scene.render.filepath = str(frames / "frame_")
    scene.frame_set(first_frame)

    print(json.dumps({
        "segment": args.segment,
        "first_frame": first_frame,
        "last_frame": last_frame,
        "frame_count": last_frame - first_frame + 1,
        "resolution": [target["width"], target["height"]],
        "fps": fps,
        "frames_dir": str(frames),
    }))
    bpy.ops.render.render(animation=True)
    missing = [frame for frame in (first_frame, first_frame + 1, last_frame)
               if not (frames / f"frame_{frame:06d}.png").is_file()]
    if missing:
        raise RuntimeError("Missing rendered frame files: " + ", ".join(map(str, missing)))

if __name__ == "__main__":
    main()
