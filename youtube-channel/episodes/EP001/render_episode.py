#!/usr/bin/env python3
"""Render EP001 at strict 720p; generate 24 fps and report measured output."""
from pathlib import Path
import importlib.util, subprocess, json, os, shutil
ROOT = Path(__file__).resolve().parent
BUILDER = ROOT / "source" / "build_episode.py"
ENCODED = ROOT / "source" / "build_episode.py.gz.b64"
OUT = ROOT / "output"
FR = ROOT / "frames"
AUD = ROOT / "audio"
for p in (OUT, FR, AUD):
    p.mkdir(parents=True, exist_ok=True)

# GitHub installs eSpeak NG; provide the legacy binary name if the builder expects it.
if not shutil.which("espeak") and shutil.which("espeak-ng"):
    wrapper = ROOT / "espeak"
    wrapper.write_text("#!/bin/sh\nexec espeak-ng \"$@\"\n", encoding="utf-8")
    wrapper.chmod(0o755)
    os.environ["PATH"] = str(ROOT) + os.pathsep + os.environ.get("PATH", "")

if not BUILDER.exists() and ENCODED.exists():
    import base64, gzip
    BUILDER.write_bytes(gzip.decompress(base64.b64decode(ENCODED.read_text(encoding="ascii"))))
spec = importlib.util.spec_from_file_location("episode_builder", BUILDER)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

def run(cmd):
    subprocess.run(cmd, check=True)

def probe(path):
    return json.loads(subprocess.check_output([
        "ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)
    ], text=True))

def duration(path):
    return float(subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "csv=p=0", str(path)
    ], text=True).strip())

FPS = 24
narration, pieces = mod.make_audio()
clips = []
for idx, (heading, body) in enumerate(mod.SECTIONS):
    frame = mod.draw_scene(mod.BASE.copy(), mod.SCENE_MAP[idx], t=11 + idx * 3, dur=90)
    frame = mod.overlay_text(frame, heading.replace("—", "-"),
                             "UNDERNEATH EVERYTHING  /  EPISODE 001", t=8, total=90)
    png = FR / f"keyart_{idx+1:02d}.png"
    import cv2
    cv2.imwrite(str(png), cv2.cvtColor(frame, cv2.COLOR_RGB2BGR),
                [cv2.IMWRITE_PNG_COMPRESSION, 3])
    audio = AUD / f"section_{idx+1:02d}.wav"
    sec = duration(audio)
    clip = FR / f"zoom_{idx+1:02d}.mp4"
    vf = (
        "zoompan=z='min(1.0+0.000055*on,1.10)':"
        "x='iw/2-(iw/zoom/2)+3*sin(on/95)':"
        "y='ih/2-(ih/zoom/2)+2*cos(on/110)':"
        f"d=1:s=1280x720:fps={FPS},format=yuv420p"
    )
    run(["ffmpeg", "-y", "-loop", "1", "-framerate", str(FPS), "-i", str(png),
         "-t", f"{sec:.3f}", "-vf", vf, "-an", "-c:v", "libx264",
         "-preset", "ultrafast", "-crf", "20", "-r", str(FPS),
         "-movflags", "+faststart", str(clip)])
    clips.append(clip)
    print(f"Scene {idx+1}/{len(mod.SECTIONS)} ready ({sec:.1f}s)", flush=True)

concat = OUT / "concat_video.txt"
concat.write_text("\n".join(f"file '{p.as_posix()}'" for p in clips), encoding="utf-8")
video = OUT / "video_only.mp4"
run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat),
     "-c", "copy", "-fflags", "+genpts", str(video)])
final = OUT / "Underneath_Everything_EP001_720p.mp4"
run(["ffmpeg", "-y", "-i", str(video), "-i", str(narration),
     "-map", "0:v:0", "-map", "1:a:0",
     "-vf", "scale=1280:720:flags=lanczos,setsar=1,fps=24",
     "-c:v", "libx264", "-preset", "slow", "-crf", "18",
     "-pix_fmt", "yuv420p", "-r", "24",
     "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
     "-shortest", "-movflags", "+faststart", str(final)])

mod.create_captions(pieces)
mod.make_thumbnail()
meta = probe(final)
v = next(s for s in meta["streams"] if s["codec_type"] == "video")
a = next(s for s in meta["streams"] if s["codec_type"] == "audio")
seconds = float(meta["format"]["duration"])
size = final.stat().st_size
fps = v.get("avg_frame_rate", "0/1")
assert (v["width"], v["height"]) == (1280, 720), f"720p lock failed: {v.get('width')}x{v.get('height')}"
assert v["codec_name"] == "h264" and a["codec_name"] == "aac", "Expected H.264 + AAC"
assert a.get("sample_rate") == "48000" and a.get("channels") == 2, "Expected 48 kHz stereo audio"
assert 480 <= seconds <= 720, f"Unexpected runtime: {seconds:.2f}s"
assert fps == "24/1", f"Measured frame rate is {fps}; renderer target was 24 fps"
run(["ffmpeg", "-v", "error", "-i", str(final), "-f", "null", "-"])
report = {
    "episode": "EP001",
    "title": "The Secret Cables That Keep the Internet Alive",
    "file": final.name,
    "size_bytes": size,
    "size_mb_decimal": round(size / 1_000_000, 2),
    "duration_seconds": round(seconds, 3),
    "resolution": f"{v['width']}x{v['height']}",
    "fps_measured": fps,
    "video_codec": v["codec_name"],
    "audio_codec": a["codec_name"],
    "audio_sample_rate": a.get("sample_rate"),
    "audio_channels": a.get("channels"),
    "narration_provider": "eSpeak local fallback; Cartesia voice is not wired into this renderer",
    "visuals": "Original procedural vector/motion graphics; not live-action footage",
    "captions": "Phrase-level estimated timing; not word-level verified",
    "thumbnail": "thumbnail.png, 1280x720 concept artwork",
    "full_decode_check": "PASS",
    "rights_status": "No third-party footage, music or images included; generated graphics and local TTS only",
    "public_release_status": "NOT APPROVED — licensed live-action footage, professional narration and final visual review still required"
}
(OUT / "render_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps(report, indent=2))
