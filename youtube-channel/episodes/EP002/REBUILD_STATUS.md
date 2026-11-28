# EP002 rebuild status — visual direction changed

**Status: rebuild required; no public-release master exists.**

The earlier working render contains visibly irrelevant footage (including a tractor in the opening scene), repeated source usage and freeze events. It is withdrawn from release consideration. Keep the old 720p and compressed files as untouched historical QA copies only; do not edit them in place or publish them.

## New mandatory rules

- One stock image or video source may appear once maximum in the whole episode.
- A clip is eligible only after human visual approval for the exact scene.
- Context-only, PENDING, REJECTED and generic clips are excluded.
- If no relevant rights-cleared moving clip is available, use the corresponding original Three.js animated diagram.
- The opening is laser-produced tin plasma, never generic factory or agricultural footage.
- The MP4 Studio landscape export must be patched to exactly 1280×720 before use.
- Existing Kokoro-82M / am_echo narration remains the required approved voice.
- Burn in the captions and include the SRT sidecar.
- No release approval until timeline coverage, rights, audio, full decode, freeze/repeated-shot QC and representative-frame review pass.

## Three.js scene source

threejs/ep002_threejs_master.mjs is ready for the supplied offline converter. It contains ten distinct conceptual sequences. It is not an MP4 render and is not proof of final QC.

## Current blockers

1. The supplied converter does not include 1280×720 landscape or a 720p-only export lock.
2. The previous B-roll set has not passed visual approval; unreviewed clips are not eligible.
3. The local environment could not unpack the two uploaded ZIP skill packages in this run, so their internal instructions have not been verified. The MP4 Studio HTML itself was inspected directly.
4. The new scene timing weights are approximate; exact Kokoro section durations must replace them before release render.
