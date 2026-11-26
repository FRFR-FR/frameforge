# Underneath Everything — EP001 package

This is the complete source and production package for the pilot **The Secret Cables That Keep the Internet Alive**.

- brief.md — episode brief and editorial angle
- narration.md — full narration script used by the pilot
- source-ledger.md and source_ledger.csv — source references, dates, claims and caveats
- fact_check.md — claim-level verification and the ITU/ICPC statistic discrepancy
- storyboard.md and storyboard.csv — scene-by-scene shot list
- asset-manifest.csv — original asset and voice records
- render_episode.py — repeatable 720p renderer; CI target is 24 fps and measured output is checked
- source/build_episode.py.gz.b64 — compressed source builder restored by the renderer on a clean runner
- render_config.json — strict export settings and measured metadata
- output/captions.srt.gz.b64 — phrase-timed captions (167 cues), compressed to keep the repository text-only
- thumbnail-concept.md — thumbnail rationale and upgrade notes
- shorts-concepts.md — three Short concepts; no Shorts MP4s rendered
- report.md and production_report.md — actual export metadata, QC and upgrade list
- output/render_report.json — measured local-pilot metadata

## Render
Requires FFmpeg/ffprobe, eSpeak NG or eSpeak, Python 3, NumPy, OpenCV and Pillow. Run python render_episode.py. The script restores the compressed builder if necessary, synthesizes local fallback narration, creates procedural motion graphics, renders the MP4, captions and thumbnail, and writes a render report.

To restore the archived caption file: base64 -d output/captions.srt.gz.b64 | gzip -d > output/captions.srt.

**Export lock:** 1280×720, 16:9, H.264 + AAC. The delivered local pilot's measured frame rate is 18 fps. The CI renderer now targets 24 fps and will report the actual measured rate; it is not complete until a GitHub Actions artifact passes validation. No 1080p or 4K export is permitted.

The source package contains no third-party stock footage or music. The current local pilot is a vector/motion-graphics proof of pipeline, not a maximum-quality public release.
