# Underneath Everything — Visual Asset Policy

**Effective:** 28 November 2026  
**Applies to:** every episode, beginning with the EP002 rebuild.

## Hard rule: one source asset, one appearance

A stock image or stock video may appear **once maximum in the entire episode**. The limit is global, not per scene or per chapter. Re-encoding, cropping, changing speed, mirroring, changing colour, or using another segment of the same source file does not create a new asset. Record and enforce uniqueness using the original source URL and a SHA-256 hash of the downloaded source.

Still images are not moving B-roll. Do not use still photos with Ken Burns movement to fill timeline duration. Stock stills may be used for research/review or a separately approved thumbnail, not as documentary runtime footage.

## Relevance gate

Every proposed shot must be reviewed visually against its specific storyboard beat before it can be used. Metadata tags and search-result titles are not sufficient evidence.

Required manifest fields:
- source_url, creator, license, license_url
- downloaded_at, search_query, intended_scene
- source_sha256, media_type, motion_verified
- visual_review_status (APPROVED / REJECTED / PENDING)
- visual_review_note, visual_reviewed_at

Only APPROVED moving footage whose visible content directly matches the intended beat may enter the edit. PENDING, REJECTED, context-only, unrelated or uncertain footage is excluded. A generic cleanroom, factory, laser or semiconductor clip must not be described as a specific manufacturer's machine, a specific factory or a particular incident unless its provenance proves that claim.

An opening shot about laser-produced tin plasma must show that process or use an original 3D reconstruction. A tractor, agriculture, medical equipment, coffee machine, conference slide or unrelated industrial clip is an automatic rejection.

## 3D fallback

When a topic-specific search and a relevant fallback search fail to produce a suitable, licensed, moving clip, create an original animated 3D explanatory scene. Use Three.js through the supplied Offline Three.js MP4 Studio or the approved Three.js render runner.

3D scenes must explain a real mechanism or spatial relationship that footage cannot show clearly. Use purposeful camera movement, moving physical components, lighting, depth, particles and timing linked to narration. Do not replace missing footage with static text, diagrams, slide decks, still frames, or repeated infographic panels.

Label reconstructions as conceptual where appropriate. Never claim an animation is a recording of a proprietary machine interior. Keep the distinction clear between measured source facts and illustrative geometry.

## Footage / animation balance and reporting

The historic production target remains 75–85% relevant moving real-world B-roll, with 70% as the hard minimum for a release candidate. Calculate this using actual timeline durations, not clip counts or a target plan. Count only footage passing the relevance, rights, motion, visual-review and single-use gates.

Report the actual share of:
- approved unique moving B-roll
- original animated 3D explanatory scenes
- text/diagram-only visual elements

If the footage minimum cannot be reached without generic filler or reusing an asset, do not pad the edit and do not call it a release candidate. Complete the ready-to-render package, use matched 3D explanations where needed, and state the measured shortfall and blocker.

## Brand and delivery

Use red #D62839, white #FFFFFF, blue #1746A2, and deep navy #102B52 for restrained labels, channel bug, chapter accents and caption backplates. Preserve natural footage colours. Final landscape master remains exactly 1280×720, 16:9, H.264 + AAC. Do not export 1080p or 4K.

Keep the Kokoro Echo narration requirement, subtitles, rights records, FFmpeg/ffprobe full-decode checks, representative-frame review and human release approval. Never auto-publish to YouTube.
