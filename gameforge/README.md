# GAMEFORGE

GAMEFORGE is a code-first 3D game production system designed to generate tightly paced, story-led 5–10 hour games and package them for Android and Windows.

## Operating mode

- **Generation:** Full Autopilot.
- **Quality:** Adaptive to measured device performance.
- **Campaign:** 5–10 hours, story-relevant optional content, with a required vertical-slice gate.

## Implemented foundation

- [x] GameSpec schema, sample brief and deterministic workspace compiler
- [x] Godot 4.4.1 runtime template, boot scene and third-person capsule smoke arena
- [x] Adaptive quality profile and dynamic 3D resolution scaler foundations
- [x] Narrative state store, dialogue cue timeline, audio and VFX event buses
- [x] FrameForge cinematic manifest schema
- [x] Free offline natural-language brief-to-GameSpec provider
- [x] First-pass story bible, character arcs and chapter outline
- [x] Scene-card planner with convergent choices and persistent state keys
- [x] Narrative continuity validator for scene IDs, chapter bounds and choice-state references
- [x] Mechanic review plans with explicit prior-art and prototype gates
- [x] Unit tests and GitHub Actions validation, including Godot headless boot

## Still to build

- [ ] Richer semantic generation and iterative creative critique
- [ ] Full authored scenes, dialogue, character knowledge tracking and localisation
- [ ] Live market research with dated sources and confidence scoring
- [ ] Mechanic prior-art research and playable prototype scoring
- [ ] Original asset creation/import and scene-generation pipeline
- [ ] Full third-person camera, animation, interaction and combat systems
- [ ] FrameForge adapter implementation and cinematic round-trip tests
- [ ] Android APK and Windows EXE export workflows
- [ ] Physical low-end device benchmark suite and measured performance gates

## Run the offline autopilot

The default provider is deterministic, free and requires no API key or network access:

~~~bash
python -m pip install -r gameforge/generator/brief_compiler/requirements.txt
python gameforge/generator/autopilot/run.py \
  --brief "Create a painterly third-person mystery adventure about a lighthouse keeper and memory, with a 7 hour campaign." \
  --out build/lighthouse
~~~

It produces GAME_SPEC.json, STORY_BIBLE.json, SCENE_PLAN.json, MECHANIC_REVIEW.json, PIPELINE_REPORT.json and NEXT_STEPS.md. These are structured design artifacts, not a playable or release-ready game.

An optional OpenAI-compatible provider can be configured with GAMEFORGE_API_BASE, GAMEFORGE_MODEL and GAMEFORGE_API_KEY and selected with --provider openai-compatible. It may incur provider charges and is not required by CI.

## Runtime and cost reality

The first runtime uses open-source Godot 4.4.1; FrameForge remains the cutscene subsystem through a versioned manifest adapter. GitHub Actions has limited free CI capacity, not unlimited compute or free general-purpose AI inference. Android signing keys must be stored as local secrets or GitHub Actions Secrets, never committed. No system can guarantee virality or sales.
