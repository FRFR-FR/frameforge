# FrameForge — Painterly 3D Ambient Films

This project creates two separate, one-hour, 720p landscape videos using native Blender 3D scenes. It does not use stock footage, flat image cards or AI-generated footage.

## Deliverables

1. **ASMR — Enchanted Water Garden**  
   A fully modelled koi pond, sculpted river stones, layered willow canopy, a flowing waterfall, lotus blooms, water lilies, ferns and slow-moving koi. The original audio bed contains flowing-water texture, leaf rustle, soft droplets and occasional quiet tactile clicks. It contains no music.

2. **Study Music — Cozy Rainy Library**  
   A fully modelled walnut study desk, open sculpted book, stacked books, brass lamp, ceramic tea mug, houseplant, arched rain-covered window, moon and distant trees. The original audio bed is peaceful felt-piano arpeggios and warm ambient chords. It contains no ASMR or sound effects.

Both backgrounds are 20-second seamless Blender animation loops repeated to one hour. The native Blender scene files are included with each video.

## Technical settings

- 1280 × 720 (720p), landscape 16:9
- 30 frames per second
- 60-minute final MP4 per project
- Blender Cycles CPU rendering, 24 samples with denoising
- Procedural textured materials, real mesh geometry, curves, lights, cameras and animated objects
- H.264 video and AAC stereo audio
- Original generated soundtracks; no third-party stock footage or AI-generation credits

## Run

The GitHub Actions workflow **FrameForge — Two Painterly 3D Ambient Videos** renders both projects in parallel. It first builds and renders each 20-second scene loop, creates its matching original audio bed, extends both to one hour, verifies the MP4 properties, and uploads an artifact containing the final video, editable .blend scene, optional .glb interchange file, audio master, audit reports and preview frames.

Run from **Actions → FrameForge — Two Painterly 3D Ambient Videos → Run workflow**.

## Source files

- ambient_worlds_cpu.py builds and renders the two distinct full-3D Blender scenes.
- make_ambient_audio.py composes the original ASMR soundscape and original study soundtrack.
- .github/workflows/ambient-dual-video.yml builds, verifies and uploads both videos.

The Blender .blend file is the editable source of truth. The 20-second rendered loop is also included for inspection or reuse.
