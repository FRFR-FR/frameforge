"""Adaptive cutscene render settings and hard resource/output governors."""
from __future__ import annotations
import os
from contracts import PROFILES, MAX_WIDTH, MAX_HEIGHT, MAX_FPS, MAX_SECONDS


def choose_settings(width: int, height: int, fps: int, duration: float, profile: str, cpu_count: int | None = None) -> dict:
    if width > MAX_WIDTH or height > MAX_HEIGHT:
        raise ValueError("Cutscene render output is limited to 1920x1080.")
    if (width, height) not in {(1280, 720), (1920, 1080)}:
        raise ValueError("Only 1280x720 or 1920x1080 render presets are supported.")
    if fps > MAX_FPS or fps < 1:
        raise ValueError("Cutscene frame rate must be between 1 and 30 FPS.")
    if duration <= 0 or duration > MAX_SECONDS:
        raise ValueError("One cutscene may be at most 600 seconds.")
    if profile not in PROFILES:
        raise ValueError(f"Unknown render profile '{profile}'.")
    cpu = cpu_count or os.cpu_count() or 2
    policy = PROFILES[profile]
    return {
        "device": "CPU",
        "threads": max(1, min(cpu, policy["threads_cap"])),
        "samples": policy["samples"],
        "width": width,
        "height": height,
        "fps": fps,
        "duration": duration,
        "max_frames": 18000,
        "denoising": True,
        "texture_max_dimension": 2048 if profile == "low" else 4096,
        "lod": True,
        "shadow_quality": "low" if profile == "low" else ("medium" if profile == "balanced" else "high"),
        "volumetrics": profile == "high",
        "motion_blur": False,
        "profile": profile,
    }
