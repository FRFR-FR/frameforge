# EP002 production report — 27 November 2026

**Episode:** EP002 — The Machine That Prints the World's Most Advanced Chips  
**Status:** Research, script and Kokoro narration are prepared. B-roll acquisition is being corrected. No final video or release candidate exists.

## Latest render attempts

- Run 45950349025 failed during system dependency installation because the runner could not locate libgles2-mesa0. That package was removed from the dependency list in commit c6ba6c8.
- Run 45950562769 then passed dependency installation and Kokoro narration generation, but B-roll acquisition failed in section_01. The strict requirement that every Pixabay tag set match both the subject and context groups yielded zero accepted clips after the relevant fallback searches.
- The Kokoro WAV and MP3 were generated successfully in run 45950562769. The audio-only artifact is available at https://github.com/FRFR-FR/frameforge/actions/runs/45950562769/artifacts/15177081241.
- No B-roll clips were accepted, so no final video, thumbnail render, subtitle master or final QC report was created by that run.

## Correction now being applied

- Keep topic-specific searches and scene-specific relevance groups, but allow clearly labelled context-only footage where the shot genuinely shows a relevant cleanroom, optical process, robotics or manufacturing environment.
- Subject-specific footage ranks above context-only footage; the renderer requires at least ten subject-specific clips and subject-specific footage in at least eight of ten sections.
- AI-generated, synthetic and animated Pixabay clips are excluded from real-world B-roll.
- Context-only clips are never presented as evidence of a named factory, proprietary tool or exact process.
- Only the minimum clips needed for the two-use cap are downloaded. Search responses remain cached for 24 hours and requests remain sequential.
- Three-frame contact sheets are generated for every clip so the actual visual content can be inspected. Third-party rights review remains a human gate.

## Current production gates

- Research and original script: prepared; primary-source ledger and fact-check refreshed 27 November 2026.
- Narration: Kokoro-82M, English pipeline, Echo voice ID am_echo; WAV and MP3 generation succeeded in the latest run, and will be regenerated with timed SRT in the corrected workflow.
- B-roll: pending corrected acquisition; no clip count or coverage percentage is claimed yet.
- 3D: ten conceptual 12-second animated cutaways are planned; they are clearly marked as reconstructions, not proprietary factory footage.
- Master: exactly 1280×720, 16:9, H.264/AAC; measured 24 fps only if the runner supports it reliably.
- Subtitles: timed SRT sidecar and readable burned-in subtitles are required.
- QC: full decode, audio-level check, timeline-based B-roll percentage, two-use source cap, freeze detection, representative-frame contact sheet and per-clip visual-review sheets are required.
- Thumbnail: original vector concept; rendered PNG pending.
- Shorts: concepts only; no vertical file generated.
- Auto-publishing: disabled; human approval remains mandatory.

**Release decision:** NOT APPROVED. Do not describe EP002 as complete until relevant footage is acquired, all clips are visually checked, the master passes every QC gate and a human approves it.
