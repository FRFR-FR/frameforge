# EP001 — Production and quality report

**Run date:** 26 November 2026  
**Episode:** 001 — The Secret Cables That Keep the Internet Alive  
**Status:** Pilot file exists; package completed; not approved for public release.

## Export verification

| Check | Measured result | Status |
|---|---|---|
| File exists | `Underneath_Everything_EP001_720p.mp4` | PASS |
| Resolution | 1280×720 (16:9) | PASS |
| Video codec | H.264 | PASS |
| Audio codec | AAC | PASS |
| Audio sample rate | 48 kHz, stereo | PASS |
| Frame rate | 18/1 = 18 fps | PASS; actual measured rate, not relabelled |
| Duration | 534.666667 seconds (8:54.67) | PASS |
| File size | 66,761,480 bytes = 66.76148 MB decimal = 63.668709 MiB | PASS |
| Full decode | FFmpeg decoded entire MP4 without reported errors | PASS |
| Audio stream | Present; mean level -20.1 dB, peak -4.2 dB | PASS at stream/file level |
| Captions | 167 ordered SRT cues; final cue ends at 8:55.745, slightly beyond reported container duration | REVIEW: adjust final cue/end timing |
| Thumbnail | 1280×720 PNG, 41,073 bytes | PASS technically; visual upgrade recommended |

## Production disclosure

- Narration: local eSpeak English US fallback. Cartesia credentials were not available in the render environment; no Cartesia voice was used.
- Visuals: original procedural vector/motion-graphic scenes. No third-party documentary footage, photographs or music were used.
- Shorts: three concepts prepared; no Shorts video files rendered.
- YouTube: not uploaded or scheduled.

## Quality review

The pilot demonstrates a functioning 720p video/audio/caption assembly path. It is not a maximum-quality cinematic documentary yet. Representative frame review found simple vector scenes rather than live-action or detailed 3D. One sampled scene showed lower-third/title overlap and inconsistent spacing, so the graphic template needs a layout pass. The 18 fps frame rate is below the preferred 24–30 fps target. The current thumbnail is a clean vector graphic but lacks the visual authority of a real cable ship or technical macro photograph.

## Required upgrades before public release

1. Replace eSpeak narration with the configured Cartesia voice only after the runner can confirm the credential is present; otherwise use a licensed, natural local voice and disclose it.
2. Add verified, licensed real cable-ship, repair-vessel, landing-station and ocean footage; keep a rights manifest for every clip.
3. Replace repetitive vector-only scenes with subject-specific 3D cutaways and real footage; do not use generated illustrations as documentary evidence.
4. Rework the lower-third system to eliminate text overlap and improve typography and pacing.
5. Re-render at 24 or 30 fps only if the actual runner supports it cleanly; preserve the measured rate and never fake it.
6. Fact-check the opening “bank payment ... in less than a second” wording. It is too broad as a universal statement; use a qualified example or remove the speed claim.
7. Re-align the final SRT cue to the exact final audio/container duration.
8. Create two stronger thumbnail variants based on rights-cleared real imagery.
9. Full watch/listen review is still required before public release; file-level decode and representative-frame inspection are not a substitute for editorial review.

## Final decision

Keep EP001 as the pipeline pilot and technical proof. Do not label it a premium live-action documentary or publish it as the finished channel launch episode until the upgrades above are complete.