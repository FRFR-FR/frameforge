#!/usr/bin/env python3
"""Cost-capped, manual-only GitHub Actions helpers for small FrameForge jobs."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
INPUT_ROOT = (ROOT / "render-input").resolve()
ARTIFACT_ROOT = (ROOT / "artifacts" / "manual-ops").resolve()
MAX_CHUNK_BYTES = 100 * 1024 * 1024
MAX_VIDEO_BYTES = 100 * 1024 * 1024
MAX_PACKAGE_SECONDS = 30
sys.path.insert(0, str(ROOT))


def repo_path(raw: str | Path, *, must_exist: bool = True) -> Path:
    candidate = Path(raw)
    candidate = candidate.resolve() if candidate.is_absolute() else (ROOT / candidate).resolve()
    if not candidate.is_relative_to(ROOT):
        raise ValueError("Path must stay inside the checked-out FrameForge repository.")
    if must_exist and not candidate.exists():
        raise FileNotFoundError(f"Repository path does not exist: {candidate.relative_to(ROOT)}")
    return candidate


def input_path(raw: str | Path, *, must_exist: bool = True) -> Path:
    candidate = repo_path(raw, must_exist=must_exist)
    if not candidate.is_relative_to(INPUT_ROOT):
        raise ValueError("Render inputs must be placed under render-input/; arbitrary repository and external paths are blocked.")
    return candidate


def validate_frame_budget(total_frames: int, max_frames: int) -> None:
    if not 1 <= max_frames <= 480:
        raise ValueError("Maximum frame budget must be between 1 and 480 frames.")
    if total_frames < 1 or total_frames > max_frames:
        raise ValueError(f"Render contains {total_frames} frames; configured safety limit is {max_frames}.")


def validate_input_size(paths: list[Path], limit: int = MAX_CHUNK_BYTES) -> int:
    total = sum(path.stat().st_size for path in paths if path.is_file())
    if total > limit:
        raise ValueError(f"Input files total {total / (1024 * 1024):.1f} MB; limit is {limit / (1024 * 1024):.0f} MB.")
    return total


def validate_assets(project_path: str, manifest_path: str) -> dict[str, Any]:
    project = repo_path(project_path)
    manifest = repo_path(manifest_path)
    commands = [
        [sys.executable, str(ROOT / "tools" / "validate_project.py"), str(project)],
        [sys.executable, str(ROOT / "tools" / "validate_media_manifest.py"), str(manifest)],
    ]
    for command in commands:
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
        if result.returncode:
            raise RuntimeError((result.stdout + "\n" + result.stderr).strip()[-5000:])
    return {"project": str(project.relative_to(ROOT)), "manifest": str(manifest.relative_to(ROOT)), "passed": True}


def merge_and_export(
    chunks_dir: str,
    output_dir: str,
    output: str,
    profile: str,
    fps: int,
    max_frames: int,
) -> dict[str, Any]:
    from tools.export_ffmpeg import PROFILES, encode_sequence
    from tools.merge_render_chunks import merge_chunks, read_chunk

    chunk_folder = input_path(chunks_dir)
    if not chunk_folder.is_dir():
        raise ValueError("Chunk input path must be a directory under render-input/.")
    chunks = sorted(chunk_folder.glob("*.zip"))
    if not chunks:
        raise FileNotFoundError("No render chunk ZIP files found in render-input/chunks/.")
    input_size = validate_input_size(chunks)
    manifests = [read_chunk(path)[0] for path in chunks]
    signatures = {(item["job_id"], item["project_id"], item["project_signature"], item["total_frames"], item["width"], item["height"], item["fps"]) for item in manifests}
    if len(signatures) != 1:
        raise ValueError("All chunks must belong to one render job and matching project signature/settings.")
    total_frames = int(manifests[0]["total_frames"])
    validate_frame_budget(total_frames, max_frames)
    if profile not in {"720p-horizontal", "720p-vertical"} or profile not in PROFILES:
        raise ValueError("Manual Actions export is limited to 720p horizontal or vertical.")
    if fps not in {24, 30}:
        raise ValueError("Manual Actions export supports only 24 or 30 FPS.")
    merged_to = repo_path(output_dir, must_exist=False)
    destination = repo_path(output, must_exist=False)
    if not merged_to.is_relative_to(ARTIFACT_ROOT) or not destination.is_relative_to(ARTIFACT_ROOT):
        raise ValueError("Merged frames and MP4 output must be saved inside artifacts/manual-ops/.")
    report = merge_chunks([str(path) for path in chunks], merged_to)
    if not report["complete"]:
        raise RuntimeError(f"Render chunk set is incomplete ({report['missing_frames']} frame(s) missing).")
    encoded = encode_sequence(merged_to / "frames", destination, profile=profile, fps=fps, crf=22, preset="veryfast", overwrite=True)
    return {"input_size_mb": round(input_size / (1024 * 1024), 2), "merge": report, "export": encoded}


def review_and_package(video_path: str, project_path: str, output_dir: str) -> dict[str, Any]:
    from tools.create_review import create_review
    from tools.export_ffmpeg import probe
    from tools.package_delivery import build_delivery_package
    from tools.qa_render import qa_video

    video = input_path(video_path)
    project = repo_path(project_path)
    if not video.is_file() or video.suffix.lower() not in {".mp4", ".mov", ".webm"}:
        raise ValueError("Video input must be an MP4, MOV or WebM file under render-input/.")
    if video.stat().st_size > MAX_VIDEO_BYTES:
        raise ValueError("Video exceeds the 100 MB manual Actions input limit.")
    probe_data = probe(video)
    duration = float(probe_data.get("format", {}).get("duration") or 0)
    if duration <= 0 or duration > MAX_PACKAGE_SECONDS:
        raise ValueError(f"Manual Actions QA/package is limited to videos from 0 to {MAX_PACKAGE_SECONDS} seconds.")
    videos = [stream for stream in probe_data.get("streams", []) if stream.get("codec_type") == "video"]
    if not videos or int(videos[0].get("width") or 0) > 1280 or int(videos[0].get("height") or 0) > 1280:
        raise ValueError("Manual Actions QA/package accepts video streams no larger than 1280 pixels per dimension.")
    destination = repo_path(output_dir, must_exist=False)
    if not destination.is_relative_to(ARTIFACT_ROOT):
        raise ValueError("QA, review and delivery outputs must be saved inside artifacts/manual-ops/.")
    destination.mkdir(parents=True, exist_ok=True)
    qa = qa_video(video)
    qa_path = destination / "qa-report.json"
    qa_path.write_text(json.dumps(qa, indent=2) + "\n", encoding="utf-8")
    if not qa["passed"]:
        raise RuntimeError("Technical QA failed; package was not created. See artifacts/manual-ops/qa-report.json.")
    review_dir = destination / "review"
    review = create_review(video, review_dir, sample_interval=1.5, max_scene_previews=8)
    package = build_delivery_package(
        video, project, destination / "delivery.zip",
        qa_report=qa_path, review_dir=review_dir, overwrite=True,
    )
    return {"qa": qa, "review": review, "delivery": package}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="operation", required=True)

    validate = sub.add_parser("validate", help="Validate a V2 project and asset rights manifest.")
    validate.add_argument("--project", required=True)
    validate.add_argument("--manifest", required=True)

    export = sub.add_parser("merge-export", help="Merge a small set of browser chunk ZIPs and encode a 720p MP4.")
    export.add_argument("--chunks-dir", default="render-input/chunks")
    export.add_argument("--output-dir", default="artifacts/manual-ops/merged")
    export.add_argument("--output", default="artifacts/manual-ops/final.mp4")
    export.add_argument("--profile", choices=("720p-horizontal", "720p-vertical"), default="720p-horizontal")
    export.add_argument("--fps", type=int, choices=(24, 30), default=24)
    export.add_argument("--max-frames", type=int, default=240)

    package = sub.add_parser("qa-review-package", help="Run QA/review and package a short final video.")
    package.add_argument("--video", default="render-input/final.mp4")
    package.add_argument("--project", required=True)
    package.add_argument("--output-dir", default="artifacts/manual-ops")

    args = parser.parse_args(argv)
    try:
        if args.operation == "validate":
            result = validate_assets(args.project, args.manifest)
        elif args.operation == "merge-export":
            result = merge_and_export(args.chunks_dir, args.output_dir, args.output, args.profile, args.fps, args.max_frames)
        else:
            result = review_and_package(args.video, args.project, args.output_dir)
        print(json.dumps(result, indent=2))
        return 0
    except Exception as error:
        print("ERROR: " + str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
