"""Render diagnostic stills plus a one-second moving smoke-test preview."""
import json
import os
import sys

import bpy

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
blend_path = argv[0] if argv else "output/game_cinematic/FrameForge_Game_Cinematic.blend"
out_dir = argv[1] if len(argv) > 1 else "output/game_cinematic/smoke_samples"
video_dir = os.path.join(out_dir, "video_frames")
os.makedirs(out_dir, exist_ok=True)
os.makedirs(video_dir, exist_ok=True)

bpy.ops.wm.open_mainfile(filepath=blend_path)
scene = bpy.context.scene
assert scene.camera is not None, "Camera is missing"
assert scene.render.engine == "CYCLES", "Expected Cycles render engine"
assert scene.frame_end >= 3, "Timeline is too short"

original_x = scene.render.resolution_x
original_y = scene.render.resolution_y
original_pct = scene.render.resolution_percentage
original_samples = scene.cycles.samples
scene.cycles.use_denoising = True
scene.render.image_settings.file_format = "PNG"

# Three diagnostic stills: opening, midpoint, ending.
scene.render.resolution_x = 640
scene.render.resolution_y = 360
scene.render.resolution_percentage = 100
scene.cycles.samples = 8
frames = sorted(set([scene.frame_start, (scene.frame_start + scene.frame_end) // 2, scene.frame_end]))
results = []
for frame in frames:
    scene.frame_set(frame)
    path = os.path.abspath(os.path.join(out_dir, "frame_%04d.png" % frame))
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    image = bpy.data.images.load(path, check_existing=False)
    pixels = image.pixels
    pixel_count = len(pixels) // 4
    if pixel_count < 1000:
        raise RuntimeError("Frame %d has no readable pixel buffer" % frame)
    stride = max(1, pixel_count // 12000)
    sample = []
    for p in range(0, pixel_count, stride):
        i = p * 4
        sample.append((float(pixels[i]) + float(pixels[i + 1]) + float(pixels[i + 2])) / 3.0)
    low, high = min(sample), max(sample)
    mean = sum(sample) / len(sample)
    variance = sum((v - mean) ** 2 for v in sample) / len(sample)
    if high - low < 0.015 or variance < 0.000005:
        raise RuntimeError("Frame %d appears blank or nearly uniform" % frame)
    if not os.path.exists(path) or os.path.getsize(path) < 10000:
        raise RuntimeError("Frame %d output missing or suspiciously small" % frame)
    results.append({"frame": frame, "file": os.path.basename(path), "bytes": os.path.getsize(path),
                    "width": int(image.size[0]), "height": int(image.size[1]),
                    "pixel_range": round(high-low, 5), "sample_variance": round(variance, 8),
                    "status": "passed"})
    bpy.data.images.remove(image)

# One second of consecutive frames demonstrates real camera/character motion.
scene.render.resolution_x = 320
scene.render.resolution_y = 180
scene.render.resolution_percentage = 100
scene.cycles.samples = 4
video_start = scene.frame_start
video_end = min(scene.frame_end, video_start + scene.render.fps - 1)
for frame in range(video_start, video_end + 1):
    scene.frame_set(frame)
    scene.render.filepath = os.path.abspath(os.path.join(video_dir, "smoke_%04d.png" % (frame-video_start)))
    bpy.ops.render.render(write_still=True)

scene.render.resolution_x = original_x
scene.render.resolution_y = original_y
scene.render.resolution_percentage = original_pct
scene.cycles.samples = original_samples
report = {
    "status": "passed",
    "test": "three diagnostic stills plus moving smoke-test preview",
    "render_engine": scene.render.engine,
    "still_preview_resolution": "640x360",
    "still_preview_samples": 8,
    "motion_preview_resolution": "320x180",
    "motion_preview_samples": 4,
    "motion_preview_fps": scene.render.fps,
    "motion_preview_frames": video_end-video_start+1,
    "frames": results
}
with open(os.path.join(out_dir, "smoke_test_report.json"), "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2)
print(json.dumps(report, indent=2))
