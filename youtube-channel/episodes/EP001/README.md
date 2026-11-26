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
- thumbnail-concept.md — thumbnail rationale and upgrade notes
- shorts-concepts.md — three Short concepts; no Shorts MP4s rendered
- report.md and production_report.md — actual export metadata, QC and upgrade list
- output/render_report.json — measured local-pilot metadata

## Rebuild — footage-first red/white/blue version (no captions)
The old 8:54 pilot is a rough procedural-graphics proof, not the public-release master. The replacement renderer uses Kokoro `am_echo`, moving rights-documented B-roll, short chapter lower-thirds over footage, and a restrained red `#D62839`, white `#FFFFFF`, blue `#1746A2`, navy `#102B52` identity. Footage stays naturally coloured; the palette is used only for on-screen labels and accents. Spoken-word captions and subtitle tracks are not used.

Requires FFmpeg/ffprobe, Python 3.11, Kokoro, and the configured footage source. Run the GitHub Actions workflow `.github/workflows/render-documentary-720p.yml` with `EP001`. The workflow writes a narration WAV/MP3 and SRT even when footage is unavailable; it must skip final rendering rather than substitute static slides. The renderer outputs exactly 1280×720, H.264/AAC, 24 fps if the runner meets validation. Captions are permanently disabled: no burned-in subtitles, SRT/VTT sidecars, or subtitle streams are generated.

**Export lock:** 1280×720, 16:9, H.264 + AAC. The delivered local pilot's measured frame rate is 18 fps. The CI renderer now targets 24 fps and will report the actual measured rate; it is not complete until a GitHub Actions artifact passes validation. No 1080p or 4K export is permitted.

The first local pilot contains no real-world B-roll and uses eSpeak; it is superseded as a visual/audio master. The replacement run has generated Kokoro Echo narration, but its first B-roll stage was skipped because the `PIXABAY_API_KEY` Actions secret was empty. Therefore no footage-led 720p replacement master has been produced yet. Do not publish the old pilot as though it meets the new visual standard.
