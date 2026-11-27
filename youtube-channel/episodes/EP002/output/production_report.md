# EP002 production report — 27 November 2026

**Episode:** EP002 — The Machine That Prints the World's Most Advanced Chips  
**Status:** Research, script and Kokoro Echo narration are prepared. The corrected B-roll-first render workflow is being repaired. No final video or release candidate exists.

## Latest render attempts

- Run 45950349025 failed during system dependency installation because the runner could not locate libgles2-mesa0. That package was removed from the dependency list in commit c6ba6c8.
- Run 45950562769 passed dependency installation and Kokoro narration generation, but B-roll acquisition failed in section_01. The strict requirement that every Pixabay tag set match both the subject and context groups yielded zero accepted clips after the relevant fallback searches.
- Run 45952122512 successfully installed rendering/TTS dependencies, then failed in the episode-selection step because GitHub expression placeholders in the workflow had been written with literal backslashes. The artifact name consequently also contained a backslash. Both expression issues are being corrected.
- The Kokoro WAV and MP3 were generated successfully in run 45950562769. The audio-only artifact is available at https://github.com/FRFR-FR/frameforge/actions/runs/45950562769/artifacts/15177081241.
- Measured narration from that artifact: 699.25 seconds (11:39.25), Kokoro-82M, voice am_echo (Echo), American English, 24 kHz WAV source.
- Narration WAV: 33.56 MB. Compressed MP3: 16.78 MB. A timed SRT sidecar has also been generated from the actual Kokoro sentence timestamps for the audio package.
- No B-roll clips were accepted and no final video, burned-in subtitle master, thumbnail render or final QC report was produced by those runs.

## Correction now being applied

- Remove literal backslashes from all GitHub Actions expression placeholders so episode selection, artifact paths and artifact naming resolve correctly.
- Keep topic-specific searches and scene-specific relevance groups, but allow clearly labelled context-only footage where the shot genuinely shows a relevant cleanroom, optical process, robotics or manufacturing environment.
- Subject-specific footage ranks above context-only footage; the renderer requires at least ten subject-specific clips and subject-specific footage in at least eight of ten sections.
- AI-generated, synthetic and animated Pixabay clips are excluded from real-world B-roll.
- Context-only clips are never presented as evidence of a named factory, proprietary tool or exact process.
- Only the minimum clips needed for the two-use cap are downloaded. Search responses remain cached for 24 hours and requests remain sequential.
- Three-frame contact sheets are generated for every clip so the actual visual content can be inspected. Third-party rights review remains a human gate.

## Current production gates

- Research and original script: prepared; primary-source ledger and fact-check refreshed 27 November 2026.
- Narration: Kokoro-82M, English pipeline, Echo voice ID am_echo; WAV and MP3 generation succeeded in the earlier run.
- B-roll: pending corrected acquisition; no clip count or coverage percentage is claimed yet.
- 3D: ten conceptual 12-second animated cutaways are planned; they are clearly marked as reconstructions, not proprietary factory footage.
- Master: exactly 1280×720, 16:9, H.264/AAC; measured 24 fps only if the runner supports it reliably.
- Subtitles: timed SRT sidecar and readable burned-in subtitles are required.
- QC: full decode, audio-level check, timeline-based B-roll percentage, two-use source cap, freeze detection, representative-frame contact sheet and per-clip visual-review sheets are required.
- Thumbnail: original vector concept; rendered PNG pending.
- Shorts: concepts only; no vertical file generated.
- Auto-publishing: disabled; human approval remains mandatory.

**Release decision:** NOT APPROVED. Do not describe EP002 as complete until relevant footage is acquired, all clips are visually checked, the master passes every QC gate and a human approves it.
