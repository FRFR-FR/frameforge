# GAMEFORGE

GAMEFORGE is a code-first 3D game production system designed to generate tightly paced, story-led 5–10 hour games and package them for Android and Windows.

This folder is the initial architecture foundation. It is not yet a functioning game engine or automatic game generator.

## Current status

- [x] Architecture and production blueprint
- [ ] GameSpec and cinematic manifest schemas
- [ ] Godot runtime template and sample playable vertical slice
- [ ] FrameForge manifest adapter
- [ ] Dialogue/audio/animation timeline
- [ ] Performance profiles and device tests
- [ ] Automated Android APK and Windows EXE builds
- [ ] Prompt-to-game generation pipeline

## Design decision

The first runtime will use a pinned, open-source Godot 4 release. GAMEFORGE will provide the generator, narrative/mechanics systems, project compiler, validation and build automation. FrameForge remains the dedicated cutscene subsystem and is integrated through a stable manifest adapter. Existing FrameForge functionality is not replaced.

Read [SPEC.md](SPEC.md) for the full architecture, performance targets, workflow and milestones.

## Important

GitHub is free for source hosting and offers limited free CI capacity; it is not unlimited free compute/rendering. Build workflows must be quota-aware and support local builds. No system can guarantee a game will go viral or sell millions of copies. GAMEFORGE will use evidence, prototypes and playtests to improve the odds, not promise outcomes.
