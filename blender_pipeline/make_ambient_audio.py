#!/usr/bin/env python3
"""Create original, royalty-free ambient soundtracks for the FrameForge videos.

ASMR: flowing-water noise, fine leaf rustle, tiny water drops and very soft taps.
Study: original felt-piano arpeggios and warm sustained chords; no sound effects.
"""
import argparse
import math
import random
import wave
from pathlib import Path

import numpy as np

SR_DEFAULT = 44100


def write_stereo_wav(path, left, right, sr):
    peak = max(float(np.max(np.abs(left))), float(np.max(np.abs(right))), 1e-6)
    gain = min(0.72 / peak, 1.0)
    l = np.tanh(left * gain * 1.18) / np.tanh(1.18)
    r = np.tanh(right * gain * 1.18) / np.tanh(1.18)
    interleaved = np.empty((len(l), 2), dtype=np.int16)
    interleaved[:, 0] = (np.clip(l, -1, 1) * 32767).astype(np.int16)
    interleaved[:, 1] = (np.clip(r, -1, 1) * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(interleaved.tobytes())


def loop_crossfade(left, right, sr, seconds=4.0):
    n = min(int(sr * seconds), len(left) // 5)
    if n <= 0:
        return left, right
    w = np.linspace(0.0, 1.0, n, dtype=np.float32)
    left[-n:] = left[-n:] * (1.0 - w) + left[:n] * w
    right[-n:] = right[-n:] * (1.0 - w) + right[:n] * w
    return left, right


def filtered_noise(rng, n, low_hz, high_hz, sr, tilt=0.35):
    raw = rng.standard_normal(n).astype(np.float32)
    spectrum = np.fft.rfft(raw)
    freqs = np.fft.rfftfreq(n, 1.0 / sr)
    lo, hi = max(1.0, low_hz), min(sr * 0.49, high_hz)
    band = np.clip((freqs - lo) / (lo * 0.45), 0.0, 1.0)
    band *= np.clip((hi - freqs) / (hi * 0.2), 0.0, 1.0)
    weight = np.maximum(freqs, lo) ** (-tilt)
    weight[0] = 0.0
    result = np.fft.irfft(spectrum * weight * band, n=n).astype(np.float32)
    result /= max(float(np.std(result)), 1e-6)
    return result


def make_asmr(path, seconds, sr):
    rng = np.random.default_rng(20261113)
    n = seconds * sr
    low = filtered_noise(rng, n, 90, 1200, sr, 0.65)
    flow = filtered_noise(rng, n, 280, 7800, sr, 0.20)
    leaf = filtered_noise(rng, n, 1500, 10000, sr, 0.12)
    t = np.arange(n, dtype=np.float32) / sr
    slow = 0.72 + 0.12 * np.sin(2 * math.pi * 0.071 * t) + 0.07 * np.sin(2 * math.pi * 0.113 * t + 1.7)
    ripple = 0.86 + 0.12 * np.sin(2 * math.pi * 0.42 * t + 0.4)
    base = 0.12 * low + 0.23 * flow * slow * ripple + 0.055 * leaf
    left = base.astype(np.float32)
    right = (0.12 * low + 0.22 * flow * slow * np.roll(ripple, int(sr * 0.012)) +
             0.058 * np.roll(leaf, int(sr * 0.018))).astype(np.float32)

    drop_rng = random.Random(77129)
    position = 1.0
    while position < seconds - 1:
        position += drop_rng.uniform(0.38, 1.65)
        start = int(position * sr)
        duration = drop_rng.uniform(0.10, 0.42)
        count = min(int(duration * sr), n - start)
        if count <= 0:
            continue
        tt = np.arange(count, dtype=np.float32) / sr
        f0 = drop_rng.uniform(580, 1480)
        f1 = f0 * drop_rng.uniform(0.52, 0.84)
        phase = 2 * math.pi * (f0 * tt + (f1 - f0) * tt * tt / (2 * duration))
        env = np.exp(-tt * drop_rng.uniform(9.0, 17.0)) * np.sin(np.minimum(1.0, tt * 45) * math.pi / 2)
        plink = (np.sin(phase) + 0.22 * np.sin(phase * 2.03 + 0.2)) * env * drop_rng.uniform(0.018, 0.045)
        left[start:start + count] += plink
        offset = int(sr * drop_rng.uniform(0.008, 0.025))
        rs, re = min(n, start + offset), min(n, start + offset + count)
        if re > rs:
            right[rs:re] += plink[:re - rs] * 0.82

    position = 7.0
    while position < seconds - 1:
        position += drop_rng.uniform(8.0, 17.0)
        start = int(position * sr)
        count = min(int(0.085 * sr), n - start)
        if count <= 0:
            continue
        tt = np.arange(count, dtype=np.float32) / sr
        click = np.sin(2 * math.pi * drop_rng.uniform(180, 340) * tt) * np.exp(-tt * 42) * drop_rng.uniform(0.015, 0.028)
        left[start:start + count] += click
        right[start:start + count] += np.roll(click, int(sr * 0.004))

    left, right = loop_crossfade(left, right, sr, 4.5)
    write_stereo_wav(path, left * 0.64, right * 0.64, sr)


def midi_hz(note):
    return 440.0 * (2.0 ** ((note - 69) / 12.0))


def add_note(left, right, start_s, duration_s, note, amplitude, sr,
             instrument="piano", pan=0.0):
    start = max(0, int(start_s * sr))
    length = min(int(duration_s * sr), len(left) - start)
    if length <= 0:
        return
    t = np.arange(length, dtype=np.float32) / sr
    freq = midi_hz(note)
    if instrument == "pad":
        attack = np.minimum(1.0, t / 0.95)
        release = np.minimum(1.0, np.maximum(0.0, duration_s - t) / 1.25)
        env = np.sin(attack * math.pi / 2) ** 1.5 * release
        signal = (np.sin(2 * math.pi * freq * t) +
                  0.24 * np.sin(2 * math.pi * freq * 2.003 * t + 0.3) +
                  0.10 * np.sin(2 * math.pi * freq * 3.01 * t + 0.7))
        signal *= env * amplitude
    else:
        decay = 1.25 + max(0, 60 - note) * 0.027
        env = np.exp(-t / decay) * (1.0 - np.exp(-t / 0.009))
        signal = (np.sin(2 * math.pi * freq * t) +
                  0.42 * np.sin(2 * math.pi * freq * 2.01 * t + 0.12) +
                  0.19 * np.sin(2 * math.pi * freq * 3.98 * t + 0.35) +
                  0.075 * np.sin(2 * math.pi * freq * 6.02 * t + 0.5))
        signal *= env * amplitude
    signal = signal.astype(np.float32)
    left[start:start + length] += signal * (0.72 - 0.24 * pan)
    right[start:start + length] += signal * (0.72 + 0.24 * pan)


def make_study(path, seconds, sr):
    n = seconds * sr
    left, right = np.zeros(n, np.float32), np.zeros(n, np.float32)
    bpm, beat = 72.0, 60.0 / 72.0
    bar = beat * 4.0
    chords = [
        [50, 54, 57, 61, 64], [45, 49, 52, 59, 64],
        [47, 50, 54, 57, 61], [43, 47, 50, 54, 57],
        [42, 50, 54, 57, 61], [40, 47, 52, 55, 59],
        [43, 47, 50, 54, 59], [45, 52, 57, 59, 62],
    ]
    arpeggio = [0, 2, 4, 3, 1, 3, 4, 2]
    melody_scale = [62, 64, 66, 69, 71, 74, 76]
    bar_index = 0
    while bar_index * bar < seconds:
        chord = chords[(bar_index // 2) % len(chords)]
        t0 = bar_index * bar
        if bar_index % 2 == 0:
            for i, note in enumerate(chord):
                add_note(left, right, t0, min(bar * 2.08, seconds - t0),
                         note - 12, 0.0085 if i else 0.011, sr, "pad", (i - 2) * 0.18)
            add_note(left, right, t0, min(3.0, seconds - t0), chord[0] - 24,
                     0.022, sr, "pad", -0.12)
        for b in range(4):
            idx = arpeggio[(bar_index + b) % len(arpeggio)]
            note = chord[idx] + 12
            start = t0 + b * beat
            add_note(left, right, start, 2.2, note, 0.028 + 0.004 * ((bar_index + b) % 3),
                     sr, "piano", -0.35 + 0.22 * b)
            if b in (1, 3) and (bar_index + b) % 3 != 0:
                add_note(left, right, start + beat * 0.47, 1.6,
                         chord[(idx + 2) % len(chord)] + 24, 0.010,
                         sr, "piano", 0.28)
        if bar_index % 2 == 1:
            note = melody_scale[(bar_index * 3 + (bar_index // 8)) % len(melody_scale)]
            add_note(left, right, t0 + beat * 1.55, 3.2, note + 12, 0.018,
                     sr, "piano", 0.16)
        bar_index += 1

    dry_l, dry_r = left.copy(), right.copy()
    for delay_s, gain in ((0.073, 0.16), (0.137, 0.10), (0.229, 0.055), (0.347, 0.025)):
        d = int(delay_s * sr)
        left[d:] += dry_l[:-d] * gain
        right[d:] += dry_r[:-d] * gain
    left, right = loop_crossfade(left, right, sr, 5.0)
    write_stereo_wav(path, left * 0.76, right * 0.76, sr)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", choices=("asmr", "study"), required=True)
    parser.add_argument("--output-dir", default="output/ambient")
    parser.add_argument("--seconds", type=int, default=300)
    parser.add_argument("--sample-rate", type=int, default=SR_DEFAULT)
    args = parser.parse_args()
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / ("asmr_nature_soundscape.wav" if args.project == "asmr" else "peaceful_study_music.wav")
    if args.project == "asmr":
        make_asmr(path, args.seconds, args.sample_rate)
        description = "Flowing creek, fine leaves, tiny water droplets and rare soft tactile clicks. No music."
    else:
        make_study(path, args.seconds, args.sample_rate)
        description = "Original felt-piano arpeggios and warm sustained D-major / B-minor ambient chords. No ASMR or SFX."
    report = {"project": args.project, "file": path.name, "duration_seconds": args.seconds,
              "sample_rate": args.sample_rate, "channels": 2, "format": "16-bit PCM WAV",
              "original_composition": True, "sound_design": description,
              "loop": "End-to-start crossfade is baked into the 5-minute audio bed."}
    with open(out / "audio_report.json", "w", encoding="utf-8") as f:
        import json
        json.dump(report, f, indent=2)
    print("FRAMEFORGE_AUDIO_OK", report)


if __name__ == "__main__":
    main()
