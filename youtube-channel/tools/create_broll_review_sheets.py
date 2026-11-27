#!/usr/bin/env python3
"""Create human-review contact sheets from three frames of every acquired B-roll clip."""
from pathlib import Path
import argparse
import csv
import json
import math
import subprocess

from PIL import Image, ImageDraw, ImageFont

CELL_W = 320
CELL_H = 180
ROW_H = 222
BG = (16, 43, 82)
WHITE = (255, 255, 255)
RED = (214, 40, 57)
BLUE = (23, 70, 162)


def probe_duration(path):
    return float(subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "csv=p=0", str(path)
    ], text=True).strip())


def extract_frame(path, seconds, output):
    subprocess.run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-ss", f"{seconds:.3f}", "-i", str(path), "-frames:v", "1",
        "-vf", f"scale={CELL_W}:{CELL_H}:force_original_aspect_ratio=decrease,"
              f"pad={CELL_W}:{CELL_H}:(ow-iw)/2:(oh-ih)/2",
        "-q:v", "3", str(output)
    ], check=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--episode-dir", required=True)
    args = parser.parse_args()
    root = Path(args.episode_dir).resolve()
    manifest_path = root / "asset-manifest-broll.csv"
    assets_root = root / "assets" / "broll"
    output_dir = root / "output" / "broll_review"
    temp_dir = output_dir / "frames"
    output_dir.mkdir(parents=True, exist_ok=True)
    temp_dir.mkdir(parents=True, exist_ok=True)

    with manifest_path.open(newline="", encoding="utf-8") as handle:
        manifest = list(csv.DictReader(handle))
    by_file = {row["filename"].replace("\\", "/"): row for row in manifest}

    try:
        font_bold = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 15)
        font_regular = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
    except OSError:
        font_bold = ImageFont.load_default()
        font_regular = ImageFont.load_default()

    index = []
    section_dirs = sorted(path for path in assets_root.glob("section_*") if path.is_dir())
    for section_dir in section_dirs:
        clips = sorted(section_dir.glob("*.mp4"))
        if not clips:
            continue
        sheet = Image.new("RGB", (CELL_W * 3, ROW_H * len(clips)), BG)
        draw = ImageDraw.Draw(sheet)
        for row_index, clip in enumerate(clips):
            relative = clip.relative_to(root).as_posix()
            record = by_file.get(relative)
            if not record:
                raise RuntimeError(f"Missing manifest row for {relative}")
            duration = probe_duration(clip)
            sample_times = [max(0.05, duration * fraction) for fraction in (0.2, 0.5, 0.8)]
            title = f"{clip.name} | {record.get('creator', '')}"
            draw.rectangle((0, row_index * ROW_H, CELL_W * 3, row_index * ROW_H + 26), fill=BLUE)
            draw.text((8, row_index * ROW_H + 5), title[:130], font=font_bold, fill=WHITE)

            for column, seconds in enumerate(sample_times):
                frame_path = temp_dir / f"{section_dir.name}_{clip.stem}_{column}.jpg"
                extract_frame(clip, seconds, frame_path)
                frame = Image.open(frame_path).convert("RGB")
                sheet.paste(frame, (column * CELL_W, row_index * ROW_H + 30))
                draw.text(
                    (column * CELL_W + 8, row_index * ROW_H + 190),
                    f"{seconds:.1f}s",
                    font=font_regular,
                    fill=WHITE
                )

            index.append({
                "section_id": section_dir.name,
                "filename": relative,
                "source_url": record.get("source_url", ""),
                "creator": record.get("creator", ""),
                "search_query": record.get("search_query", ""),
                "license": record.get("license", ""),
                "review_status": "PENDING visual review"
            })

        sheet_path = output_dir / f"{section_dir.name}_contact_sheet.jpg"
        sheet.save(sheet_path, quality=90, optimize=True)

    (output_dir / "review_index.json").write_text(json.dumps(index, indent=2), encoding="utf-8")
    print(json.dumps({
        "contact_sheets": len(list(output_dir.glob("section_*_contact_sheet.jpg"))),
        "clips_reviewed": len(index),
        "status": "CONTACT SHEETS CREATED; human visual verification remains required",
        "output": str(output_dir)
    }, indent=2), flush=True)


if __name__ == "__main__":
    main()
