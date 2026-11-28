#!/usr/bin/env python3
"""Merge FrameForge browser-rendered PNG chunk ZIPs into a resumable frame folder.

Chunk ZIPs are exported by the V2 browser render queue. Re-running this command
is safe: identical frames are skipped, while conflicting duplicate frame data
is rejected instead of silently overwriting earlier work.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any

FRAME_RE = re.compile(r"^frames/frame_(\d{6,9})\.png$")
REQUIRED = ("job_id", "project_id", "project_signature", "chunk_index",
            "start_frame", "end_frame_exclusive", "total_frames",
            "width", "height", "fps", "frame_count")


def png_dimensions(data: bytes) -> tuple[int, int]:
    if len(data) < 24 or data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR":
        raise ValueError("Frame file is not a valid PNG header.")
    width = int.from_bytes(data[16:20], "big")
    height = int.from_bytes(data[20:24], "big")
    if width < 1 or height < 1:
        raise ValueError("PNG frame has invalid dimensions.")
    return width, height


def read_chunk(path: Path) -> tuple[dict[str, Any], dict[int, bytes], str]:
    if not path.is_file():
        raise FileNotFoundError(f"Chunk archive does not exist: {path}")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        if any(PurePosixPath(name).is_absolute() or ".." in PurePosixPath(name).parts for name in names):
            raise ValueError(f"Chunk contains an unsafe archive path: {path.name}")
        if names.count("chunk-manifest.json") != 1:
            raise ValueError(f"{path.name} must contain exactly one chunk-manifest.json.")
        manifest = json.loads(archive.read("chunk-manifest.json"))
        if manifest.get("format") != "frameforge-render-chunk" or manifest.get("version") != 1:
            raise ValueError(f"{path.name} is not a supported FrameForge render chunk.")
        missing = [key for key in REQUIRED if key not in manifest]
        if missing:
            raise ValueError(f"{path.name} manifest is missing: {', '.join(missing)}")
        start = int(manifest["start_frame"])
        end = int(manifest["end_frame_exclusive"])
        if start < 0 or end <= start or end > int(manifest["total_frames"]):
            raise ValueError(f"{path.name} has invalid frame bounds.")
        width, height = int(manifest["width"]), int(manifest["height"])
        if width < 1 or height < 1 or float(manifest["fps"]) <= 0:
            raise ValueError(f"{path.name} has invalid resolution or frame rate.")
        frames: dict[int, bytes] = {}
        for name in names:
            match = FRAME_RE.fullmatch(name)
            if not match:
                if name == "chunk-manifest.json":
                    continue
                raise ValueError(f"Unexpected file in {path.name}: {name}")
            frame = int(match.group(1))
            if frame in frames:
                raise ValueError(f"Duplicate frame {frame} inside {path.name}.")
            if frame < start or frame >= end:
                raise ValueError(f"Frame {frame} is outside its declared chunk range.")
            info = archive.getinfo(name)
            if info.file_size > 200 * 1024 * 1024:
                raise ValueError(f"Frame {frame} exceeds the 200 MB safety limit.")
            data = archive.read(name)
            if png_dimensions(data) != (width, height):
                raise ValueError(f"Frame {frame} dimensions disagree with its chunk manifest.")
            frames[frame] = data
        expected = end - start
        if len(frames) != expected or int(manifest["frame_count"]) != expected:
            raise ValueError(f"{path.name} is incomplete: expected {expected} PNG frames, found {len(frames)}.")
        if set(frames) != set(range(start, end)):
            raise ValueError(f"{path.name} contains a gap in its declared frame range.")
        return manifest, frames, digest


def merge_chunks(chunks: list[str | Path], output_dir: str | Path) -> dict[str, Any]:
    if not chunks:
        raise ValueError("Supply at least one chunk ZIP.")
    destination = Path(output_dir)
    frame_dir = destination / "frames"
    frame_dir.mkdir(parents=True, exist_ok=True)
    state_path = destination / "render-frames.json"
    state: dict[str, Any] = {
        "format": "frameforge-render-frames",
        "version": 1,
        "job_id": None,
        "project_id": None,
        "project_signature": None,
        "width": None,
        "height": None,
        "fps": None,
        "total_frames": None,
        "chunks": {},
    }
    if state_path.exists():
        state = json.loads(state_path.read_text(encoding="utf-8"))
        if state.get("format") != "frameforge-render-frames" or state.get("version") != 1:
            raise ValueError("Existing render-frames.json is not a supported merge state.")

    added = 0
    skipped = 0
    processed = []
    for raw_path in chunks:
        path = Path(raw_path)
        manifest, frames, archive_hash = read_chunk(path)
        for field in ("job_id", "project_id", "project_signature", "width", "height", "fps", "total_frames"):
            current = state.get(field)
            incoming = manifest[field]
            if current is not None and current != incoming:
                raise ValueError(f"Chunk {path.name} does not match existing render set field {field!r}.")
            state[field] = incoming
        chunk_key = str(int(manifest["chunk_index"]))
        prior_chunk = state["chunks"].get(chunk_key)
        if prior_chunk:
            if prior_chunk.get("archive_sha256") == archive_hash:
                skipped += len(frames)
                processed.append(path.name + " (already merged)")
                continue
            raise ValueError(f"Chunk index {chunk_key} conflicts with a previously merged archive.")

        for frame, data in frames.items():
            target = frame_dir / f"frame_{frame:06d}.png"
            if target.exists():
                existing_hash = hashlib.sha256(target.read_bytes()).hexdigest()
                incoming_hash = hashlib.sha256(data).hexdigest()
                if existing_hash != incoming_hash:
                    raise ValueError(f"Frame {frame} already exists with different content.")
                skipped += 1
                continue
            temporary = target.with_suffix(".png.tmp")
            temporary.write_bytes(data)
            os.replace(temporary, target)
            added += 1

        state["chunks"][chunk_key] = {
            "archive": path.name,
            "archive_sha256": archive_hash,
            "start_frame": int(manifest["start_frame"]),
            "end_frame_exclusive": int(manifest["end_frame_exclusive"]),
            "frame_count": len(frames),
        }
        processed.append(path.name)

    total = int(state["total_frames"] or 0)
    present = sorted(int(path.stem.split("_")[1]) for path in frame_dir.glob("frame_*.png"))
    missing = sorted(set(range(total)) - set(present))
    state.update({
        "merged_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        "frame_count": len(present),
        "missing_frames": missing,
        "complete": total > 0 and not missing,
    })
    state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")
    return {
        "output_dir": str(destination),
        "added_frames": added,
        "skipped_frames": skipped,
        "frame_count": len(present),
        "total_frames": total,
        "missing_frames": len(missing),
        "complete": state["complete"],
        "processed_chunks": processed,
        "manifest": str(state_path),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chunk", action="append", default=[], help="Chunk ZIP; may be supplied more than once.")
    parser.add_argument("--chunks-dir", help="Also merge all *.zip files in this directory.")
    parser.add_argument("--output-dir", required=True, help="Destination directory for numbered PNG frames.")
    args = parser.parse_args(argv)
    paths = [Path(item) for item in args.chunk]
    if args.chunks_dir:
        paths.extend(sorted(Path(args.chunks_dir).glob("*.zip")))
    try:
        report = merge_chunks(paths, args.output_dir)
    except Exception as error:
        print("ERROR: " + str(error), file=sys.stderr)
        return 1
    print(json.dumps(report, indent=2))
    return 0 if report["complete"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
