# BROWN — Five-minute realistic 3D visual pilot

This workflow builds a separate, editable Blender project for the opening five-minute pilot. It is not the older 90-second block-built CPU prototype and it is not the two-hour feature render.

## Render specification

- Runtime: 300 seconds exactly
- Picture: 1280 × 720 (720p), 24 fps, 7,200 frames
- Renderer: Blender Cycles on CPU, denoising enabled
- Segments: five 60-second parts
- Parallel render limit: three parts at a time
- Output: H.264 MP4, silent visual draft

## What the scene builds

The Blender scene uses smooth, custom procedural 3D models with separate character roots and detailed facial, hair, clothing and footwear elements. It builds the civic registry, records desk, public-service corridor, access checkpoint, Vesper street, unspecified city interior, memory pavement, print-shop exterior and print-shop interior. It includes two sedans, a public-transit bus, public displays, service counters, paper records, phones/screens, coffee, school application, medical pouch, kettle, printing equipment and practical lighting.

The cast models are **concept models**, not approved likenesses. The novel does not supply canonical physical descriptions for every person. Skin/hair/clothing choices and body proportions in this procedural first pass are temporary design proposals; review the model sheet and rendered frame before using them as final canon.

The pilot follows the Prologue and Chapter 1 beats only. It does not invent a new action sequence. The broken-glass memory is sensory and non-graphic. Do not use the scene as a guide to real-world violence.

## Run and output

The GitHub Actions workflow `.github/workflows/brown-five-minute-pilot.yml` automatically starts when the pilot scene or workflow changes on `fix/two-hour-feature-film`. It:

1. Compiles the Blender script and builds the editable `.blend` file.
2. Renders a lighting-proof still.
3. Renders five 60-second sections, with no more than three render jobs running simultaneously.
4. Encodes and concatenates the parts.
5. Checks 1280×720, 24 fps and 300-second duration, then uploads the final silent visual pilot as a workflow artifact.

The final video is only considered technically complete when the assembly job passes. A successful render is not the same as author approval or visual-quality approval. Inspect character faces, hands, clothing intersections, environment detail, camera cuts, exposure, flicker and continuity before promoting the pilot to final production.

## Known limitations of this first procedural pass

- No recorded dialogue, narration, music or final sound mix is included; this is a silent visual pilot.
- Procedural concept models still need human art direction, model-sheet approval, topology/rig refinement and acting review.
- Twenty Cycles samples with denoising is the initial CPU render quality/performance setting; it may need a higher-sample re-render after visual inspection.
- This is a five-minute pilot asset pipeline only. It does not remove the separate approval gates for the complete two-hour feature.

No rendered file should be described as complete until the GitHub Actions assembly artifact exists and its QC report confirms the requested technical format.
