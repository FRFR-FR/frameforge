# GAMEFORGE

GAMEFORGE is a code-first 3D game production system designed to generate tightly paced, story-led 5–10 hour games and package them for Android and Windows.

## Operating mode

- **Generation:** Full Autopilot — the system makes creative and technical decisions without requiring approval for every step.
- **Quality:** Adaptive — each target device receives the highest quality profile it can sustain within measured performance budgets.
- **Campaign:** 5–10 hours, story-relevant optional content only, with a required vertical-slice gate.

## Implemented foundation

- [x] Architecture and production blueprint
- [x] GameSpec JSON schema and example project brief
- [x] Full-autopilot/adaptive defaults
- [x] Godot 4.4.1 project template and boot scene
- [x] Playable third-person capsule controller smoke arena
- [x] Conservative Android/desktop quality profiles
- [x] Dynamic 3D resolution scaler foundation
- [x] Narrative state store and dialogue cue timeline
- [x] Audio and VFX event dispatch foundations
- [x] FrameForge cinematic manifest schema
- [x] Deterministic GameSpec validation/workspace compiler
- [x] GitHub Actions schema, compiler and Godot headless validation workflow

## Still to build

- [ ] Automated natural-language brief-to-GameSpec creative provider
- [ ] Narrative and character-arc generation with continuity validation
- [ ] Mechanic ideation, prior-art research and playable prototype scoring
- [ ] Original asset creation/import and scene-generation pipeline
- [ ] Full third-person camera, animation, interaction and combat systems
- [ ] FrameForge adapter implementation and cinematic round-trip tests
- [ ] Dialogue voice/viseme timing and localisation pipeline
- [ ] Android APK and Windows EXE export workflows
- [ ] Physical low-end device benchmark suite and measured performance gates

## Runtime decision

The first production runtime uses Godot 4.4.1 (GDScript-only template) as the open-source runtime. GAMEFORGE supplies the generator, narrative/mechanics systems, project compiler, validation, optimisation policy and build automation. FrameForge remains the dedicated cutscene subsystem and is integrated through a versioned manifest adapter.

## Build and cost reality

GitHub hosts the source and offers limited free CI capacity; it is not unlimited free rendering or compute. Build workflows must be quota-aware and support local builds. Android signing keys must be stored as GitHub Actions Secrets or locally, never committed. No system can guarantee virality, sales or search placement.

## First compiler experiment

```bash
python -m pip install -r gameforge/generator/brief_compiler/requirements.txt
python gameforge/generator/brief_compiler/compile.py \
  --spec gameforge/examples/sample-game-spec.json \
  --out build/sample-game
```

This validates a structured GameSpec and creates a reproducible workspace. It does not yet produce a complete game.

Read [SPEC.md](SPEC.md) for architecture and [runtime template](runtime/godot_template) for the first engine code.
