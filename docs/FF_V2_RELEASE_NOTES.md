# FrameForge V2.0.0 — release notes

**Release track:** V2 release candidate. The annotated tag and GitHub Release are published only when the manual **FrameForge V2 Publish Release** workflow is explicitly dispatched from `main`.

## What is included

### Editing and compositing
- Versioned project/asset schemas and validation.
- Local media import, asset library, editable multi-track timeline and local recovery.
- Canvas 2D compositor, transforms, keyframes, masks, mattes, blend modes, procedural graphics and effects.
- Optional WebGL shader pipeline and local Three.js GLB/glTF scene workflow.
- Portable Blender handoff and multi-track audio mastering.

### Research and production direction
- Production briefs, niche profiles, reference dossiers, narration-to-shot planning and evidence/rights tracking.
- Reusable shot recipes, public-media discovery adapters, procedural SVG/particle graphics, audio rights records and editable shot assembly.
- Human review remains part of source selection and final publication; rights metadata is not an independent legal determination.

### Rendering, QA and handoff
- Resumable browser frame queue with IndexedDB persistence and PNG chunk ZIP export.
- Local FFmpeg H.264 profiles, validated chunk merger, FFprobe/FFmpeg technical QA, contact-sheet/audio-waveform review and delivery packager.
- Android/mobile quick navigation and documentation.
- Cost-capped, manually dispatched GitHub Actions for small validation, merge/export and QA/package operations.

### Anger-rise cut-out VFX

A new keyframable `anger-rise` clip effect supports transparent PNG cut-outs. Animate intensity from 0 to 1 for a warm red tint that rises bottom-to-top; the final threshold triggers a short explosion/flash/shock-ring burst, with procedural flames and embers along the bottom edge. Tint strength, flame height and trigger threshold are configurable. The tint pass preserves the cut-out alpha. Use media with documented reuse permission.

### Two completed pilot builds
- **Entertainment / power scaling:** Solar Sentinel vs Rift Warden. Original procedural character art, animated comparison graphics, illustrative (not canon) profile values, and scenario-dependent conclusion.
- **Cybersecurity:** Pause, Check, Verify, Report. Original fictional inbox/UI, safe independent-verification flow, and source-linked defensive awareness advice.

Both demo MP4s were built as 1280×720, 24 FPS, 12-second H.264/AAC files on a standard CPU runner. Their delivery packages include project metadata, original SVG assets, narration script, QA report and review aids. The audio track is original synthesized interface/transition SFX; the supplied narration scripts are **not** recorded or synthesized into the MP4s. A human should record and mix the voiceover before publication.

## Known limitations

- The browser render queue is local to the open browser tab/device. It is resumable from IndexedDB while the stored data remains available; it is not a cloud renderer or background job.
- Long or high-resolution exports should use a local computer with Python, FFmpeg and ffprobe. GitHub Actions jobs are short, bounded demonstrations and consume whatever finite quota applies to the repository.
- Browser storage can be evicted. Export V2 JSON and back up every original source asset separately; imported media Blobs are not embedded into the project JSON.
- 3D model pixel rendering requires WebGL. Browser codec, GPU, memory and storage limits vary.
- QA checks stream metadata, decode integrity, black/frozen-frame heuristics and audio levels; false positives and false negatives are possible. It does not replace human visual/audio review or a full perceptual AV-sync audit.
- The pilot MP4s are concise workflow demonstrations, not finished long-form channel episodes. They need recorded narration and subjective editorial review.
- Open media rights and attribution remain the user's responsibility to document and verify. An approved metadata record is not legal advice.
- No unlimited free GitHub runner/storage allocation is promised. Workflows do not switch to paid compute automatically.

## Verification

- Latest Foundation Validation: [run 46150580593](https://github.com/FRFR-FR/frameforge/actions/runs/46150580593) — 77 JavaScript tests and 52 Python tests passed.
- Latest Browser Smoke: [run 46150580603](https://github.com/FRFR-FR/frameforge/actions/runs/46150580603) — editor, audio, director, production, render-queue and mobile smoke tests passed, including the new anger-rise VFX.
- Latest Pages deployment: [run 46150580658](https://github.com/FRFR-FR/frameforge/actions/runs/46150580658) — successful.
- Pilot Builds and QA: [run 46146137635](https://github.com/FRFR-FR/frameforge/actions/runs/46146137635) — both 720p MP4s passed full decode and technical QA without black/frozen segments or QA/rights warnings. The two video files are 1.52 MB and 1.36 MB; the combined artifact is 6.46 MB and expires on 2026-12-01 at 12:46 UTC.

The manual release workflow blocks publication unless the latest Foundation Validation, Pilot Builds/QA and Browser Smoke runs on `main` succeeded. It then re-runs the Python and JavaScript core suites on the release commit and validates both pilot projects before creating the annotated tag and GitHub Release. The release publisher is ready but has not been dispatched, so no `v2.0.0` tag or GitHub Release exists yet.

See [the progress log](FF_V2_PROGRESS.md), [handover guide](FF_V2_HANDOVER.md), [mobile guide](FF_V2_MOBILE.md), [manual Actions guide](FF_V2_MANUAL_ACTIONS.md) and [render/QA/delivery guide](FF_V2_RENDERING_QA_DELIVERY.md).
