#!/usr/bin/env python3
"""Download the authorized Shorts listed in video_sources/youtube_shorts.txt."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_FILE = REPO_ROOT / "video_sources" / "youtube_shorts.txt"


def load_urls() -> list[str]:
    if not SOURCE_FILE.is_file():
        raise FileNotFoundError(f"Source list not found: {SOURCE_FILE}")
    urls: list[str] = []
    for raw_line in SOURCE_FILE.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if not (line.startswith("https://www.youtube.com/") or line.startswith("https://youtube.com/")):
            raise ValueError(f"Unsupported URL in source list: {line}")
        urls.append(line)
    if not urls:
        raise ValueError("No video URLs were found in the source list.")
    return urls


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        default="downloads/youtube-shorts",
        help="Folder to save the downloaded MP4 files (default: downloads/youtube-shorts).",
    )
    args = parser.parse_args()

    if os.environ.get("FRAMEFORGE_VIDEO_RIGHTS_CONFIRMED", "").lower() != "yes":
        print(
            "Download stopped. Set FRAMEFORGE_VIDEO_RIGHTS_CONFIRMED=yes only after "
            "confirming you own or are authorized to download and reuse every listed video.",
            file=sys.stderr,
        )
        return 2

    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        urls = load_urls()
    except (OSError, ValueError) as exc:
        print(f"Cannot read source list: {exc}", file=sys.stderr)
        return 2

    failed: list[str] = []
    template = str(output_dir / "%(autonumber)02d-%(title).100B-%(id)s.%(ext)s")

    for index, url in enumerate(urls, start=1):
        print(f"\n[{index}/{len(urls)}] Downloading {url}", flush=True)
        command = [
            sys.executable,
            "-m",
            "yt_dlp",
            "--no-playlist",
            "--windows-filenames",
            "--format",
            "bv*+ba/b",
            "--merge-output-format",
            "mp4",
            "--output",
            template,
            "--",
            url,
        ]
        result = subprocess.run(command, check=False)
        if result.returncode != 0:
            failed.append(url)

    print(f"\nFinished: {len(urls) - len(failed)}/{len(urls)} downloaded.")
    if failed:
        print("Failed URLs:")
        for url in failed:
            print(f" - {url}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
