# BROWN Book One — Film Rebuild Specification

## Status: BLOCKED — do not render the existing prototype as the final film

The previously assembled two-hour MP4 is not approved as a finished adaptation. A successful encode, runtime, or artifact upload is not a creative-quality pass.

The source is the complete 609-page *BROWN — Book One* publication interior and its Book One story bible / 72-chapter plan. This is a full-book adaptation, not a 90-second adaptation of the Chapter 5–6 ambush. The story bible identifies 65 named characters and eight parts.

## Non-negotiable production order

1. **Source breakdown:** map all 72 chapters and the prologue to scenes, locations, characters, dialogue beats, transitions, and consequences. Maintain a source-to-scene traceability table. Do not invent a corridor ambush as a substitute for the book.
2. **Character preproduction before animation:** create a character bible and model sheets for every recurring speaking character. Approve front, side, three-quarter, full-body, facial-expression, clothing, hair, skin-tone, and distinguishing-detail views before rigging or animation. Preserve continuity across the entire film.
3. **Production character assets:** use detailed, anatomically coherent 3D models with layered clothing, hair, facial topology, expressive eyes and mouths, PBR skin/clothing materials, and consistent proportions. No blob figures, primitive-only people, or low-poly placeholders in final shots.
4. **Production rigs:** use full-body deformation rigs with articulated fingers, shoulders, elbows, wrists, spine, neck, facial controls, eyes, jaw, and feet. Include IK/FK switching, foot planting, hand/prop contact, and reusable action libraries. A 17-bone rigid-weighted box rig is a prototype and is disallowed for final animation.
5. **Story performance:** animate actions, not merely locomotion. Characters must handle objects, sit, stand, turn, gesture, argue, embrace, struggle, fight, flee, operate vehicles, react, fall, recover, and make consequential choices when the source scene calls for it. No looping walk cycles as scene content.
6. **Dialogue and sound:** script dialogue from the source, record or generate licensed character voices, time mouth shapes to speech, and build scene-specific ambience, effects, and score. Dialogue must be audible and intelligible; subtitles alone do not satisfy this requirement.
7. **Cinematic direction:** use purposeful shot/reverse-shot dialogue coverage, close-ups, wides, inserts, camera movement, action geography, readable staging, and varied pacing. Chase, fight, battle, siege, and war scenes must be staged only where supported by the book, with clear cause and effect.
8. **Ethical and narrative continuity:** Kaylen is the sole survivor of the Grave Choir ambush; Eamon's betrayal, Juno's notebook, Tovin's unfinished school application, and Leona's naming campaign must retain their later consequences. Reveal Nia's murder in stages without absolving Kaylen. Preserve Ethiopia's plural, imperfect politics. The continental war and the mass death statistic must be portrayed as catastrophe and moral collapse, never as a triumphant victory or collective blame.
9. **Review gates:** render character turntables and facial tests first; then a 60–90 second dialogue/action proof scene; then a 5-minute pilot; then chapter/sequence approvals. Only after those pass may full-length rendering begin.
10. **Technical validation:** verify frame rate, aspect ratio, duration, audio, lip-sync, character identity, prop continuity, shot coverage, and scene completeness. Perform human visual review of representative frames and full-sequence playback. A structural transform audit is not a visual-quality audit.

## Existing prototype diagnosis

The existing `blender_pipeline/brown_scene_cpu.py` is a short, procedural 90-second scene. It builds block-based characters from rigid-weighted boxes, uses a small 17-bone skeleton, gives most passengers restrained idle motion, and stages one vehicle ambush/explosion. Its own configuration describes a 90-second runtime. It cannot produce the requested complete two-hour, book-faithful film by simply increasing duration or re-rendering.

The existing 24-part MP4 must be treated as a rejected prototype, not as approved source material for the new cut. Do not reuse its repeated or low-quality footage to fill runtime.

## Delivery target

Preserve the previously requested two-hour runtime and the existing completed-file target unless the author changes it: `BROWN_Book_One_Complete_2h_720p20.mp4`, 1280×720, 20 fps, 24 sequential five-minute parts, followed by one final assembly. The target runtime is 7,200 seconds / 144,000 frames. Rendering must be staged and resumed from verified parts; the final assembly starts only after all approved parts pass QC.

**Current approval state: NOT APPROVED FOR FULL RENDER.**