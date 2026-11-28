#!/usr/bin/env python3
"""Build a FrameForge delivery ZIP with MP4, editable project and rights/QA notes."""
from __future__ import annotations

import argparse
import json
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from tools.export_ffmpeg import probe, parse_rate
except ImportError:  # Direct execution from the tools directory.
    from export_ffmpeg import probe, parse_rate


def asset_manifest(project: dict[str, Any]) -> dict[str, Any]:
    rows = []
    for asset in project.get("assets", []):
        provenance = asset.get("provenance") or {}
        rights = asset.get("rights") or {}
        rows.append({
            "id": asset.get("id"),
            "label": asset.get("label") or asset.get("id"),
            "uri": asset.get("uri"),
            "media_type": asset.get("media_type"),
            "metadata": asset.get("metadata") or {},
            "tags": asset.get("tags") or [],
            "provenance": {
                "source_type": provenance.get("source_type", "unknown"),
                "source_url": provenance.get("source_url"),
                "source_title": provenance.get("source_title"),
                "creator": provenance.get("creator"),
                "provider": provenance.get("provider"),
                "acquired_at": provenance.get("acquired_at"),
                "notes": provenance.get("notes"),
            },
            "rights": {
                "status": rights.get("status", "unknown"),
                "license_name": rights.get("license_name"),
                "license_url": rights.get("license_url"),
                "permission_reference": rights.get("permission_reference"),
                "attribution_required": rights.get("attribution_required", True),
                "attribution_text": rights.get("attribution_text"),
                "review_basis": rights.get("review_basis"),
                "reviewed_by": rights.get("reviewed_by"),
                "reviewed_at": rights.get("reviewed_at"),
                "intended_use": rights.get("intended_use"),
                "restrictions": rights.get("restrictions") or [],
            },
        })
    return {
        "format": "frameforge-delivery-asset-manifest",
        "version": 1,
        "project_id": (project.get("project") or {}).get("id"),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "asset_count": len(rows),
        "assets": rows,
        "note": "Project JSON and this manifest store metadata and references only. Imported media binaries are not embedded unless separately supplied.",
    }


def attribution_document(manifest: dict[str, Any]) -> tuple[str, list[str]]:
    approved: list[str] = []
    pending: list[str] = []
    warnings: list[str] = []
    for asset in manifest["assets"]:
        rights = asset["rights"]
        label = str(asset.get("label") or asset.get("id") or "Unnamed asset")
        status = rights.get("status", "unknown")
        required = rights.get("attribution_required", True)
        credit = str(rights.get("attribution_text") or "").strip()
        restrictions = rights.get("restrictions") or []
        if status not in {"approved"}:
            pending.append(f"- {label}: rights status is {status}; do not assume publication is cleared.")
            warnings.append(f"Asset {label!r} has no approved rights state.")
        elif required and not credit:
            pending.append(f"- {label}: attribution is required but no credit text is recorded.")
            warnings.append(f"Asset {label!r} requires attribution text that is missing.")
        elif credit:
            approved.append(f"- {credit}")
        if restrictions:
            approved.append(f"  Usage limits for {label}:")
            approved.extend(f"  - {restriction}" for restriction in restrictions)
        if status == "restricted":
            warnings.append(f"Asset {label!r} is restricted.")
        if status == "rejected":
            warnings.append(f"Asset {label!r} is rejected and should be removed from the edit.")

    lines = [
        "FRAMEFORGE ATTRIBUTION AND RIGHTS NOTES",
        "",
        "APPROVED / REVIEWED CREDITS",
        *(approved or ["- No approved third-party attribution credits were recorded."]),
        "",
        "PENDING / UNRESOLVED ITEMS",
        *(pending or ["- No pending rights items were recorded in the supplied project metadata."]),
        "",
        "IMPORTANT",
        "- These notes reproduce project metadata; they do not independently verify licences, ownership, permission or legal status.",
        "- Confirm the scope, territory, platform, monetisation and attribution placement for every imported asset.",
        "- Assets marked pending, restricted, rejected or unknown are not cleared for publication by inclusion in this ZIP.",
        "- Imported binary assets are not part of the V2 project JSON. Include those files separately when a recipient must reopen the project.",
    ]
    return "\n".join(lines) + "\n", warnings


def build_delivery_package(
    video: str | Path,
    project_path: str | Path,
    output: str | Path,
    *,
    qa_report: str | Path | None = None,
    review_dir: str | Path | None = None,
    extra_files: list[str | Path] | None = None,
    overwrite: bool = False,
) -> dict[str, Any]:
    video_path = Path(video)
    project_file = Path(project_path)
    output_path = Path(output)
    for path in (video_path, project_file):
        if not path.is_file():
            raise FileNotFoundError(f"Required delivery input does not exist: {path}")
    if output_path.resolve() in {video_path.resolve(), project_file.resolve()}:
        raise ValueError("Delivery ZIP cannot overwrite the MP4 or project JSON input.")
    if output_path.exists() and not overwrite:
        raise FileExistsError(f"Delivery ZIP already exists: {output_path}. Use --overwrite to replace it.")
    project = json.loads(project_file.read_text(encoding="utf-8"))
    if project.get("format") != "frameforge-project" or project.get("schema_version") != 2:
        raise ValueError("Project file is not a FrameForge V2 project JSON.")
    metadata = probe(video_path)
    video_streams = [stream for stream in metadata.get("streams", []) if stream.get("codec_type") == "video"]
    audio_streams = [stream for stream in metadata.get("streams", []) if stream.get("codec_type") == "audio"]
    if not video_streams:
        raise RuntimeError("Final media contains no video stream.")
    video_stream = video_streams[0]
    duration = float(metadata.get("format", {}).get("duration") or 0)
    manifest = asset_manifest(project)
    attribution, rights_warnings = attribution_document(manifest)
    fps = parse_rate(video_stream.get("avg_frame_rate")) or parse_rate(video_stream.get("r_frame_rate"))
    file_info = {
        "path": video_path.name,
        "format": "MP4",
        "size_bytes": video_path.stat().st_size,
        "size_mb": round(video_path.stat().st_size / (1024 * 1024), 2),
        "width": int(video_stream.get("width") or 0),
        "height": int(video_stream.get("height") or 0),
        "resolution": f"{video_stream.get('width')}x{video_stream.get('height')}",
        "fps": fps,
        "duration_seconds": duration,
        "video_codec": video_stream.get("codec_name"),
        "audio_stream": bool(audio_streams),
        "audio_codec": audio_streams[0].get("codec_name") if audio_streams else None,
        "audio_sample_rate": audio_streams[0].get("sample_rate") if audio_streams else None,
        "audio_channels": audio_streams[0].get("channels") if audio_streams else None,
    }
    warnings = list(rights_warnings)
    qa_data = None
    if qa_report:
        qa_path = Path(qa_report)
        if not qa_path.is_file():
            raise FileNotFoundError(f"QA report does not exist: {qa_path}")
        qa_data = json.loads(qa_path.read_text(encoding="utf-8"))
        if qa_data.get("passed") is not True:
            warnings.append("The supplied technical QA report did not pass.")
    else:
        warnings.append("No automated technical QA report was supplied.")
    render_report = {
        "format": "frameforge-delivery-report",
        "version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "project": project.get("project", {}),
        "final_media": file_info,
        "asset_count": manifest["asset_count"],
        "rights_warnings": rights_warnings,
        "qa_passed": qa_data.get("passed") if qa_data else None,
        "qa_report_included": bool(qa_data),
        "review_directory_included": bool(review_dir),
        "warnings": warnings,
    }
    readme = [
        "FRAMEFORGE DELIVERY PACKAGE",
        "",
        f"Final media: {file_info['path']}",
        f"Format: MP4 · {file_info['resolution']} · {file_info['fps'] or 'unknown'} FPS",
        f"Duration: {file_info['duration_seconds']:.3f} seconds",
        f"Size: {file_info['size_mb']:.2f} MB ({file_info['size_bytes']} bytes)",
        f"Video codec: {file_info['video_codec']}",
        f"Audio stream: {'yes' if file_info['audio_stream'] else 'no'}",
        "",
        "Included: final MP4, editable project JSON, generated asset rights/provenance manifest, attribution notes and delivery report.",
        "The review folder and technical QA report are included when supplied.",
        "The V2 project JSON does not embed imported binary assets from the originating browser's IndexedDB.",
        "See attribution.txt before publishing. Metadata is not independent legal or licence verification.",
    ]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        archive.write(video_path, "delivery/" + video_path.name)
        archive.write(project_file, "project/project.json")
        archive.writestr("project/asset_manifest.json", json.dumps(manifest, indent=2))
        archive.writestr("attribution.txt", attribution)
        archive.writestr("render_report.json", json.dumps(render_report, indent=2))
        archive.writestr("README.txt", "\n".join(readme) + "\n")
        if qa_report:
            archive.write(Path(qa_report), "qa/qa_report.json")
        if review_dir:
            directory = Path(review_dir)
            if not directory.is_dir():
                raise FileNotFoundError(f"Review directory does not exist: {directory}")
            for file in sorted(directory.rglob("*")):
                if file.is_file():
                    archive.write(file, "review/" + str(file.relative_to(directory)).replace("\\", "/"))
        for raw in extra_files or []:
            path = Path(raw)
            if not path.is_file():
                raise FileNotFoundError(f"Extra delivery file does not exist: {path}")
            archive.write(path, "additional/" + path.name)
    with zipfile.ZipFile(output_path, "r") as archive:
        bad_member = archive.testzip()
        if bad_member:
            raise RuntimeError(f"Delivery ZIP failed CRC verification at {bad_member}.")
    return {
        "output": str(output_path),
        "delivery_zip_size_bytes": output_path.stat().st_size,
        "delivery_zip_size_mb": round(output_path.stat().st_size / (1024 * 1024), 2),
        "final_media": file_info,
        "project_file_size_mb": round(project_file.stat().st_size / (1024 * 1024), 2),
        "asset_count": manifest["asset_count"],
        "qa_passed": qa_data.get("passed") if qa_data else None,
        "rights_warnings": len(rights_warnings),
        "warnings": warnings,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", required=True, help="Final MP4.")
    parser.add_argument("--project", required=True, help="FrameForge V2 project JSON.")
    parser.add_argument("--output", required=True, help="Delivery ZIP path.")
    parser.add_argument("--qa-report", help="Optional QA JSON produced by tools/qa_render.py.")
    parser.add_argument("--review-dir", help="Optional review directory produced by tools/create_review.py.")
    parser.add_argument("--extra", action="append", default=[], help="Additional file to include; can be repeated.")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = build_delivery_package(
            args.video, args.project, args.output,
            qa_report=args.qa_report, review_dir=args.review_dir,
            extra_files=args.extra, overwrite=args.overwrite,
        )
    except Exception as error:
        print("ERROR: " + str(error), file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
