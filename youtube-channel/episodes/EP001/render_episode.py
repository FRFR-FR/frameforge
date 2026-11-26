#!/usr/bin/env python3
"""Render EP001 from source; locked to 1280x720, 18 fps, H.264 + AAC."""
from pathlib import Path
import base64, gzip, importlib.util, subprocess, json
ROOT = Path(__file__).resolve().parent
BUILDER = ROOT / "source" / "build_episode.py"
ENCODED = ROOT / "source" / "build_episode.py.gz.b64"
if not BUILDER.exists() and ENCODED.exists():
    BUILDER.write_bytes(gzip.decompress(base64.b64decode(ENCODED.read_text(encoding="ascii"))))
spec = importlib.util.spec_from_file_location("episode_builder", BUILDER)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
OUT = ROOT / "output"
FR = ROOT / "frames"
AUD = ROOT / "audio"
for p in (OUT, FR, AUD):
    p.mkdir(parents=True, exist_ok=True)

def run(cmd):
    subprocess.run(cmd, check=True)

def probe(path):
    return json.loads(subprocess.check_output(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)], text=True))

def duration(path):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)], text=True).strip())

narration, pieces = mod.make_audio()
clips = []
for idx, (heading, body) in enumerate(mod.SECTIONS):
    frame = mod.draw_scene(mod.BASE.copy(), mod.SCENE_MAP[idx], t=11 + idx * 3, dur=90)
    frame = mod.overlay_text(frame, heading.replace("—", "-"), "UNDERNEATH EVERYTHING  /  EPISODE 001", t=8, total=90)
    png = FR / f"keyart_{idx+1:02d}.png"
    import cv2
    cv2.imwrite(str(png), cv2.cvtColor(frame, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_PNG_COMPRESSION, 3])
    audio = AUD / f"section_{idx+1:02d}.wav"
    sec = duration(audio)
    clip = FR / f"zoom_{idx+1:02d}.mp4"
    vf = "zoompan=z='min(1.0+0.000055*on,1.10)':x='iw/2-(iw/zoom/2)+3*sin(on/95)':y='ih/2-(ih/zoom/2)+2*cos(on/110)':d=1:s=1280x720:fps=18,format=yuv420p"
    run(["ffmpeg", "-y", "-loop", "1", "-framerate", "18", "-i", str(png), "-t", f"{sec:.3f}", "-vf", vf, "-an", "-c:v", "libx264", "-preset", "ultrafast", "-crf", "20", "-r", "18", "-movflags", "+faststart", str(clip)])
    clips.append(clip)
    print(f"Scene {idx+1}/{len(mod.SECTIONS)} ready ({sec:.1f}s)", flush=True)

concat = OUT / "concat_video.txt"
concat.write_text("\n".join(f"file '{p.as_posix()}'" for p in clips), encoding="utf-8")
video = OUT / "video_only.mp4"
run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat), "-c", "copy", str(video)])
final = OUT / "Underneath_Everything_EP001_720p.mp4"
run(["ffmpeg", "-y", "-i", str(video), "-i", str(narration), "-map", "0:v:0", "-map", "1:a:0", "-vf", "scale=1280:720:flags=lanczos,setsar=1,fps=18", "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2", "-shortest", "-movflags", "+faststart", str(final)])
mod.create_captions(pieces)
mod.make_thumbnail()
meta = probe(final)
v = next(s for s in meta["streams"] if s["codec_type"] == "video")
a = next(s for s in meta["streams"] if s["codec_type"] == "audio")
assert (v["width"], v["height"]) == (1280, 720), f"720p lock failed: {v['width']}x{v['height']}"
assert v["codec_name"] == "h264" and a["codec_name"] == "aac", "Expected H.264 + AAC"
report = {"file": final.name, "size_bytes": final.stat().st_size, "size_mb_decimal": round(final.stat().st_size / 1_000_000, 2), "duration_seconds": round(float(meta["format"]["duration"]), 2), "width": v["width"], "height": v["height"], "fps": v.get("avg_frame_rate"), "video_codec": v["codec_name"], "audio_codec": a["codec_name"], "audio_sample_rate": a.get("sample_rate"), "voice": "eSpeak English (local fallback; Cartesia is not configured in this renderer)", "visuals": "original procedural motion graphics; not live-action footage"}
(OUT / "render_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps(report, indent=2))