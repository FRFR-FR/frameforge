# EP001 Render Recipe

## Runner dependencies
- FFmpeg and ffprobe
- eSpeak NG (or eSpeak compatibility wrapper)
- Python 3
- NumPy
- OpenCV headless
- Pillow
- DejaVu Sans fonts

## Source
The procedural scene builder is stored in source/build_episode.py.gz.b64. The root render_episode.py restores it before importing.

## Run
From this episode folder, run:

    python render_episode.py

The renderer writes output/Underneath_Everything_EP001_720p.mp4, output/captions.srt, output/thumbnail.png and output/render_report.json.

## Export gate
- Exactly 1280×720, 16:9.
- H.264 video and AAC audio, 48 kHz stereo.
- Report the measured frame rate exactly; do not relabel or fake it.
- Runtime must match narration and story; do not pad scenes to hit a quota.
- Full FFmpeg decode must pass.
- Keep large MP4s out of Git history; use GitHub Actions artifacts.

## Current pilot limitation
The verified local pilot is 18 fps. A 24 fps frame-by-frame re-render attempt in the local CPU session did not complete. The GitHub Actions renderer will test 24 fps; it is not considered complete until an actual artifact passes all checks.
