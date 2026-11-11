# GAMEFORGE

GAMEFORGE is a code-first 3D game production system designed to generate tightly paced, story-led 5–10 hour games and package them for Android and Windows.

## Operating mode

- **Generation:** Full Autopilot.
- **Quality:** Adaptive to measured device performance.
- **Campaign:** 5–10 hours, story-relevant optional content, with a required vertical-slice gate.
- **Runtime:** Godot 4.4.1 (GDScript) with FrameForge cinematic manifests and runtime cue dispatch.

## Implemented foundation

- [x] GameSpec schema, sample brief and deterministic workspace compiler
- [x] Full-autopilot offline brief provider and optional OpenAI-compatible provider
- [x] Story bible, chapter outline, scene cards and convergent persistent choices
- [x] Scene continuity validation and mechanic prior-art/prototype gates
- [x] Production director with milestone gates and project risk register
- [x] Godot 4.4.1 runtime template and playable capsule smoke arena
- [x] Seeded procedural 3D blockout world generator
- [x] Third-person spring-arm camera foundation
- [x] Character controller, interaction raycast, quest director and combat health component
- [x] Basic NPC state-machine foundation (idle, patrol, chase, return)
- [x] Adaptive 3D resolution manager
- [x] FrameForge manifest validator/adapter and runtime cinematic cue dispatcher
- [x] Android and Windows export presets and manual GitHub Actions export workflow
- [x] Runtime smoke test, static integration checks and CI validation

## Remaining production work

- [ ] Full authored dialogue, character knowledge model, voice generation and lip-sync
- [ ] Advanced original asset generation, rigging, animation and art direction pipeline
- [ ] Production-grade procedural level generation, navigation and streaming
- [ ] Complete combat, enemy tactics, inventory, save/load, UI and accessibility systems
- [ ] FrameForge live project/API round-trip and cinematic camera/actor animation binding
- [ ] Market research connectors with dated, sourced evidence and confidence scoring
- [ ] Mechanic prior-art research and playable prototype scoring
- [ ] Physical low-end Android device benchmark matrix and performance budgets
- [ ] Release signing, crash reporting, packaging validation and store-ready release process
- [ ] Full automated playtesting, visual regression and gameplay blocker detection

## Run the offline autopilot

The default provider is deterministic, free and requires no API key or network access:

~~~bash
python -m pip install -r gameforge/generator/brief_compiler/requirements.txt
python gameforge/generator/autopilot/run.py \
  --brief "Create a painterly third-person mystery adventure about a lighthouse keeper and memory, with a 7 hour campaign." \
  --out build/lighthouse
~~~

It produces GAME_SPEC.json, STORY_BIBLE.json, SCENE_PLAN.json, MECHANIC_REVIEW.json, PRODUCTION_PLAN.json, PIPELINE_REPORT.json and NEXT_STEPS.md. These are structured design artifacts, not a playable or release-ready game.

## Run the runtime

Open `gameforge/runtime/godot_template/project.godot` in Godot 4.4.1. The demo boots a seeded procedural blockout arena, player capsule, third-person camera, quest director and adaptive quality manager. It is a functional prototype foundation, not a finished game.

## Export builds

Use Actions → **GAMEFORGE export builds** → Run workflow. Choose Android APK, Windows EXE, or both. The Android workflow exports a debug APK for device testing; it is not store-ready or release-signed. A release signing workflow must use private keystore credentials supplied through GitHub Secrets. The Windows build is an unsigned executable artifact.

## Cost and reliability

GitHub Actions has limited free minutes/storage, not unlimited compute. The offline provider requires no paid inference. The optional remote model provider may incur charges. No engine can guarantee virality, sales, store ranking or millions of downloads; GAMEFORGE treats those as hypotheses to validate through research and playtesting.
