"""Fast visual smoke test: render start, midpoint and end frames from the saved scene."""
import json
import os
import sys

import bpy

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
blend_path = argv[0] if argv else "output/game_cinematic/FrameForge_Game_Cinematic.blend"
out_dir = argv[1] if len(argv) > 1 else "output/game_cinematic/smoke_samples"
os.makedirs(out_dir, exist_ok=True)

bpy.ops.wm.open_mainfile(filepath=blend_path)
scene = bpy.context.scene
assert scene.camera is not None, "Camera is missing"
assert scene.render.engine == "CYCLES", "Expected Cycles render engine"
assert scene.frame_end >= 3, "Timeline is too short"

original_x = scene.render.resolution_x
original_y = scene.render.resolution_y
original_pct = scene.render.resolution_percentage
original_samples = scene.cycles.samples
scene.render.resolution_x = 640
scene.render.resolution_y = 360
scene.render.resolution_percentage = 100
scene.cycles.samples = 8
scene.cycles.use_denoising = True
scene.render.image_settings.file_format = "PNG"

frames = sorted(set([scene.frame_start, (scene.frame_start + scene.frame_end) // 2, scene.frame_end]))
results = []
for frame in frames:
    scene.frame_set(frame)
    path = os.path.abspath(os.path.join(out_dir, "frame_%04d.png" % frame))
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)

    # Re-open the written PNG: Render Result may not expose a stable pixel buffer
    # across background-mode Blender versions.
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
    low = min(sample)
    high = max(sample)
    mean = sum(sample) / len(sample)
    variance = sum((v - mean) ** 2 for v in sample) / len(sample)
    if high - low < 0.015 or variance < 0.000005:
        raise RuntimeError("Frame %d appears blank or nearly uniform (range %.5f, variance %.8f)" % (frame, high-low, variance))
    if not os.path.exists(path) or os.path.getsize(path) < 10000:
        raise RuntimeError("Frame %d output missing or suspiciously small" % frame)
    results.append({
        "frame": frame,
        "file": os.path.basename(path),
        "bytes": os.path.getsize(path),
        "width": int(image.size[0]),
        "height": int(image.size[1]),
        "pixel_range": round(high-low, 5),
        "sample_variance": round(variance, 8),
        "status": "passed"
    })
    bpy.data.images.remove(image)

scene.render.resolution_x = original_x
scene.render.resolution_y = original_y
scene.render.resolution_percentage = original_pct
scene.cycles.samples = original_samples
report = {
    "status": "passed",
    "test": "three-frame Blender visual smoke test",
    "render_engine": scene.render.engine,
    "preview_resolution": "640x360",
    "preview_samples": 8,
    "frames": results
}
with open(os.path.join(out_dir, "smoke_test_report.json"), "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2)
print(json.dumps(report, indent=2))
