#!/usr/bin/env python3
"""Verify the complete local GAMEFORGE cutscene/game toolchain."""
from __future__ import annotations
import argparse
import os
import re
import subprocess
import sys
from pathlib import Path


def run_version(command: list[str]) -> str:
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    output = (result.stdout + "\n" + result.stderr).strip()
    if result.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(command)}\n{output}")
    return output


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--blender", default="blender")
    parser.add_argument("--godot", default="godot")
    parser.add_argument("--android-sdk")
    args = parser.parse_args()

    failures: list[str] = []
    checks: list[tuple[str, str]] = []

    def check(name: str, command: list[str], pattern: str | None = None) -> None:
        try:
            output = run_version(command)
            if pattern and not re.search(pattern, output, re.IGNORECASE):
                raise RuntimeError(f"Unexpected version output: {output[:300]}")
            checks.append((name, output.splitlines()[0] if output else "OK"))
        except Exception as exc:
            failures.append(f"{name}: {exc}")

    check("Python", [args.python, "--version"], r"Python 3\.(12|13)")
    check("Blender", [args.blender, "--version"], r"Blender 4\.5")
    check("Godot", [args.godot, "--headless", "--version"], r"4\.4\.1")
    check("FFmpeg", ["ffmpeg", "-hide_banner", "-version"], r"ffmpeg version")
    check("FFprobe", ["ffprobe", "-hide_banner", "-version"], r"ffprobe version")
    if args.android_sdk:
        check("Java", ["java", "-version"], r'version "17\.')

    try:
        filters = run_version(["ffmpeg", "-hide_banner", "-filters"])
        if not re.search(r"\bass\s", filters) or not re.search(r"\bsubtitles\s", filters):
            raise RuntimeError("FFmpeg is missing the ASS/libass subtitle filters.")
        checks.append(("FFmpeg libass", "ASS + subtitles filters available"))
    except Exception as exc:
        failures.append(f"FFmpeg libass: {exc}")

    for module in ("pocket_tts", "whisperx", "torch", "numpy", "scipy", "soundfile", "jsonschema"):
        try:
            result = subprocess.run(
                [args.python, "-c", f"import {module}; print('OK')"],
                capture_output=True, text=True, check=False
            )
            if result.returncode != 0:
                raise RuntimeError((result.stderr or result.stdout).strip()[:500])
            checks.append((f"Python package: {module}", "import OK"))
        except Exception as exc:
            failures.append(f"Python package: {module}: {exc}")

    try:
        result = subprocess.run(
            [args.python, "-c", "import torch; print(torch.cuda.is_available())"],
            capture_output=True, text=True, check=True
        )
        if result.stdout.strip().lower() != "false":
            raise RuntimeError("This cutscene setup expects the CPU-only PyTorch runtime.")
        checks.append(("PyTorch device", "CPU runtime"))
    except Exception as exc:
        failures.append(f"PyTorch device: {exc}")

    if args.android_sdk:
        candidates = [
            Path(args.android_sdk) / "cmdline-tools/latest/bin/sdkmanager",
            Path(args.android_sdk) / "cmdline-tools/latest/bin/sdkmanager.bat",
        ]
        sdkmanager = next((p for p in candidates if p.exists()), None)
        if not sdkmanager:
            failures.append(f"Android SDK: sdkmanager missing under {args.android_sdk}")
        else:
            try:
                sdk_command = [str(sdkmanager), f"--sdk_root={args.android_sdk}", "--list_installed"]
                if os.name == "nt" and sdkmanager.suffix.lower() == ".bat":
                    sdk_command = ["cmd.exe", "/c", *sdk_command]
                output = run_version(sdk_command)
                checks.append(("Android SDK", "sdkmanager available"))
                for token in ("platform-tools", "platforms;android-34", "build-tools;34.0.0", "ndk;23.2.8568313"):
                    if token not in output:
                        failures.append(f"Android SDK package missing: {token}")
            except Exception as exc:
                failures.append(f"Android SDK: {exc}")

    print("\nGAMEFORGE installation check")
    for name, detail in checks:
        print(f"[OK]   {name}: {detail}")
    for failure in failures:
        print(f"[FAIL] {failure}")
    print(f"\n{len(checks)} checks passed; {len(failures)} failures.")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
