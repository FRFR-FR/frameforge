#!/usr/bin/env python3
"""End-to-end GAMEFORGE cutscene render: Kyutai TTS -> forced alignment -> Blender -> MP4."""
from __future__ import annotations
import argparse, json, shutil, subprocess, sys
from pathlib import Path
from contracts import validate_project, load_json, render_policy

ROOT = Path(__file__).resolve().parent
AUDIO = ROOT / "audio"
BLENDER_SCRIPT = ROOT / "blender" / "build_scene.py"


def run(command: list[str], cwd: Path | None = None) -> None:
    print("+", " ".join(str(x) for x in command), flush=True)
    subprocess.run([str(x) for x in command], cwd=str(cwd) if cwd else None, check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--blender", default="blender")
    parser.add_argument("--ffmpeg", default="ffmpeg")
    parser.add_argument("--ffprobe", default="ffprobe")
    parser.add_argument("--alignment-device", choices=("cpu",), default="cpu")
    args = parser.parse_args()

    project_path = args.project.resolve()
    output = args.out.resolve()
    project = validate_project(load_json(project_path))
    policy = render_policy(project)
    for exe in (args.blender, args.ffmpeg, args.ffprobe):
        if shutil.which(exe) is None:
            raise SystemExit(f"Required executable not found on PATH: {exe}")
    output.mkdir(parents=True, exist_ok=True)

    voice_manifest = output / "voice_manifest.json"
    alignment_manifest = output / "alignment_manifest.json"
    run([sys.executable, str(AUDIO / "generate_dialogue.py"), "--project", str(project_path), "--out", str(output)])
    run([sys.executable, str(AUDIO / "align_dialogue.py"), "--project", str(project_path),
         "--voice-manifest", str(voice_manifest), "--out", str(alignment_manifest),
         "--device", args.alignment_device])

    run([args.blender, "--background", "--python-exit-code", "1", "--python", str(BLENDER_SCRIPT),
         "--", "--mode", "render", "--project", str(project_path),
         "--sync", str(alignment_manifest), "--out", str(output)])

    run([sys.executable, str(AUDIO / "assemble_audio.py"), "--project", str(project_path),
         "--voice-manifest", str(voice_manifest), "--alignment", str(alignment_manifest),
         "--out", str(output)], cwd=ROOT)

    # Use relative paths from the output directory so the same command works on Windows/Linux.
    video_path = output / "GAMEFORGE_Cutscene.mp4"
    run([args.ffmpeg, "-y", "-framerate", str(policy["fps"]), "-start_number", "1",
         "-i", "frames/frame_%04d.png", "-i", "dialogue_mix.wav",
         "-vf", "ass=subtitles.ass", "-map", "0:v:0", "-map", "1:a:0",
         "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart",
         video_path.name], cwd=output)

    probe = subprocess.run([args.ffprobe, "-v", "error", "-show_entries",
        "stream=codec_type,width,height,r_frame_rate", "-show_entries", "format=duration,size",
        "-of", "json", video_path.name], cwd=str(output), capture_output=True, text=True, check=True)
    result = json.loads(probe.stdout)
    video_stream = next((s for s in result.get("streams", []) if s.get("codec_type") == "video"), None)
    if not video_stream:
        raise RuntimeError("FFprobe found no video stream.")
    if int(video_stream["width"]) > 1920 or int(video_stream["height"]) > 1080:
        raise RuntimeError("Render exceeded the GAMEFORGE 1080p output ceiling.")
    report = {
        "status": "rendered",
        "project": project["project"]["id"],
        "output": str(video_path),
        "resolution": f"{video_stream['width']}x{video_stream['height']}",
        "fps": video_stream["r_frame_rate"],
        "duration_seconds": float(result.get("format", {}).get("duration", 0)),
        "bytes": int(result.get("format", {}).get("size", 0)),
        "render_profile": policy,
        "tts_provider": "kyutai-pocket-tts",
        "alignment_provider": "whisperx-forced-character-alignment",
        "subtitle_style": "ASS outline-only with transparent background",
        "rigged_character_glb": str(output / "GAMEFORGE_Cutscene_Characters.glb"),
        "lip_sync_review_required": True,
    }
    (output / "render_report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
