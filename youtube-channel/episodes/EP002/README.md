# Underneath Everything — EP002

**The Machine That Prints the World's Most Advanced Chips**

A research-led semiconductor engineering documentary about extreme ultraviolet lithography (EUV), tin-plasma light generation, reflective optics, wafer stages, alignment and the 2026 High-NA production milestone.

## Permanent export lock
- Final long-form master: 1280×720, 16:9, MP4, H.264 video and AAC audio.
- Never export 1080p or 4K masters. Other master resolutions are prohibited. A 360p low-data derivative is allowed only when explicitly requested; it is not a master.
- Master frame rate: 24–30 fps only when the runner can produce it reliably. Record the measured frame rate from ffprobe; never relabel it.
- Requested low-data derivative: 640×360, measured 12 fps, H.264 target 180 kb/s and mono AAC target 40 kb/s at 32 kHz.
- Runtime target: 8–12 minutes, only when narration naturally supports it. Do not stretch or loop footage to reach a quota.
- No captions, subtitles, SRT/VTT files, burned-in words, shot labels, lower thirds, logo bugs or subtitle streams.
- Narration: Kokoro-82M, American English Echo (am_echo), as the available natural local voice. Cartesia is not claimed unless its credential and generator are available in the runner.
- 70% minimum relevant real moving B-roll for a release candidate; 75–85% is the target.
- Original Blender cutaways are identified as conceptual reconstructions, never passed off as actual factory footage.
- No automatic YouTube publishing.

## Package files
brief.md; narration.md; research/source-ledger.csv; research/fact-check.md; storyboard/storyboard.csv; storyboard/shot-list.md; assets/broll_plan.json; assets/asset-manifest.csv; thumbnail-concept.md; shorts-concepts.md; render/render_config.json; render_episode.py; scripts/generate_3d_cutaways.py; scripts/create_thumbnail.py; output/production_report.md.

Large video and audio assets stay out of normal Git history. The 720p master, narration files, thumbnail and QC report are uploaded as a GitHub Actions artifact. EP001 remains the submarine-cable pilot and is not duplicated.