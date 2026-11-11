# GAMEFORGE

GAMEFORGE is a code-first 3D game production system designed to generate tightly paced, story-led 5–10 hour games and package them for Android and Windows.

## Operating mode

- **Generation:** Full Autopilot — the system makes creative and technical decisions without requiring approval for every step.
- **Quality:** Adaptive — each target device receives the highest quality profile it can sustain within measured performance budgets.
- **Campaign:** 5–10 hours, story-relevant optional content only, with a required vertical-slice gate.

## Current implementation

- [x] Architecture and production blueprint
- [x] GameSpec JSON schema
- [x] Full-autopilot/adaptive defaults
- [x] Godot project template and boot scene
- [x] Third-person controller foundation
- [x] Narrative state and dialogue timeline foundations
- [x] FrameForge cinematic manifest schema
- [x] Initial GitHub Actions validation workflow
- [ ] Godot headless import and runtime tests
- [ ] FrameForge adapter implementation and round-trip tests
- [ ] Asset generation/import pipeline
- [ ] Market signal collection and evidence scoring
- [ ] Narrative/mechanics compiler
- [ ] Android APK and Windows EXE export workflows
- [ ] Low-end physical-device benchmark suite

## Runtime decision

The first production runtime uses a pinned open-source Godot 4 release. GAMEFORGE supplies the generator, narrative/mechanics systems, project compiler, validation, optimisation policy and build automation. FrameForge remains the dedicated cutscene subsystem and is integrated through a versioned manifest adapter.

## Build and cost reality

GitHub hosts the source and offers limited free CI capacity; it is not unlimited free rendering or compute. Build workflows must be quota-aware and support local builds. Android signing keys must be stored as GitHub Actions Secrets or locally, never committed. No system can guarantee virality, sales or search placement.

Read [SPEC.md](SPEC.md) for architecture and [runtime template](runtime/godot_template) for the first engine code.
