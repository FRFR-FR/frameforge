# BROWN Book One — Feature-film production pipeline

## Superseding delivery target

This production plan supersedes the earlier 24 × 5-minute / 2-hour delivery layout. The latest detailed instruction is **240 × 1-minute segments**, which equals **4 hours** total. At 24 fps and 1280 × 720, that is 345,600 frames. The queue permits a maximum of **three segment renders at once**. The 24 fps master contains 1,440 frames per segment and 345,600 frames overall.

The phrase “2-minute segments” conflicted with “240 one-minute segments”; the exact requested count is being treated as authoritative. The resulting master filename is:

    BROWN_Book_One_Complete_4h_720p20.mp4

## Visual target

Use an original, highly stylised 3D feature-animation language with:
- expressive, anatomically coherent characters and strong readable silhouettes;
- fast, fluid, physically legible action with anticipation, impact, follow-through and recovery;
- nuanced facial acting, eye-lines, articulated hands and accurate lip-sync;
- overlapping body mechanics and secondary motion in hair, clothing, accessories and carried objects;
- carefully staged fights, pursuits, vehicle action and large-scale conflict only where the source material requires them;
- purposeful camera choreography, clear geography, shot/reverse-shot dialogue coverage, close-ups, inserts and cinematic wides;
- painterly material treatment, considered colour scripting, rich environments, atmospheric perspective, detailed skies/clouds, motivated volumetric light and production-quality compositing.

Do not reproduce shots or character designs from reference films. Borrow only broad craft principles. Minecraft/block characters, blob figures, primitive-only people, low-poly placeholders, repeated footage and walk-cycle filler are prohibited in final scenes.

## Strict pre-animation order

1. Add the two original source documents to the repository:
   - production/source/BROWN_Book_One_Publication_Interior.pdf
   - production/source/BROWN_Book_One_Story_Bible_and_72_Chapter_Plan.pdf
2. Complete production/story_breakdown.json from the story-breakdown template. Cover the prologue and all 72 chapters. Each scene must contain source-derived action, dialogue beats, character IDs, location IDs, asset IDs and continuity consequences. No scene may be invented just to fill runtime.
3. Complete production/asset_registry.json from the asset-registry template. Every source-required asset must have a unique ID, an actual file, a review-evidence file and approved status.
4. Design and review the complete recurring-character library. The story bible lists 65 named characters. Each character needs a model sheet, turntable, full model, full-body rig and facial test before animation begins. Use distinct identities, accurate proportions, layered clothing, detailed hair, expressive facial topology and reusable controls.
5. Design all story-required locations and environments, interiors/exteriors, vehicles, props and objects, food/tableware, costumes, vegetation/terrain/water, skies/clouds/weather, crowds, effects, voices, music and sound. Reuse a designed asset only when continuity supports doing so.
6. Build and validate the full-length Blender master scene and audio mix at the paths in featurefilm_manifest.json. Every referenced asset must be linked and checked. The master scene must cover frames 1–345600 and have a camera for every shot.
7. Approve full-body/facial deformation rigs and action tests. The animation library must support acting, handling props, sitting/standing, gestures, dialogue, conflict, recovery, facial expression and secondary motion—not just locomotion.
8. Produce and review a 60–90-second dialogue/action proof, then a five-minute pilot. Check the actual rendered playback, not only a technical report.
9. Record the required signed visual-QC approvals in production/approvals.json, with real evidence files. Do not set approval booleans merely to bypass the gate.

## Files to create from templates

Copy the templates and populate them at these exact paths:

- featurefilm_pipeline/templates/story_breakdown.template.json → production/story_breakdown.json
- featurefilm_pipeline/templates/asset_registry.template.json → production/asset_registry.json
- featurefilm_pipeline/templates/approvals.template.json → production/approvals.json

Keep large art/model files in Git LFS or another repository-accessible asset store. The workflow checks that referenced files exist and that review records are complete; it does not pretend that an empty registry is a designed asset library.

## Render and recovery behaviour

The new workflow is .github/workflows/brown-featurefilm-240.yml.

- Changing pipeline files runs an automatic preflight.
- Committing the final production/approvals.json also runs a preflight. If—and only if—every source, scene, asset, rig, audio, pilot and visual-QC requirement passes, the queue starts automatically.
- A manual workflow_dispatch can run preflight or render.
- The render matrix has 240 unique one-minute jobs and max-parallel: 3.
- Each job renders 1,440 frames, encodes a 60-second 720p H.264 segment at 24 fps, adds the matching 60-second audio slice, validates audio/video streams and retries up to three times. Retry attempts lower the Blender/encoder thread cap (8, then 4, then 2) to mitigate resource-pressure failures without reducing resolution or changing the quality profile.
- Retries clear only disposable generated frames and partial MP4 output. They never alter the source book, approved assets, animation, or production settings.
- If a deterministic Blender/model/scene error remains after three attempts, the job uploads its logs and stops. It does not make arbitrary code or artistic changes that could corrupt the film.
- Final assembly cannot start until all 240 segment jobs pass. The assembler verifies every segment's frame count, resolution, frame rate, duration and audio before concatenation, then verifies the 4-hour final file.

## Honest production limits

The pipeline and queue are now defined, but they are not the same as finished assets or a finished film. The current repository still contains only the old 90-second prototype; it does not yet contain the source PDFs, the complete 65-character model library, approved environments/props, the feature-film master scene, the full-length audio mix or the approved five-minute pilot. Therefore the rendering gate must remain closed.

GitHub-hosted CPU runners can execute Blender, but they do not guarantee feature-studio rendering throughput or automatically invent production-quality models and performances. The technical workflow can retry transient render/encoding failures and report persistent failures; it cannot safely fix every artistic or deterministic modelling error without a corrected asset or scene. Human visual review remains essential before the full film is approved.
