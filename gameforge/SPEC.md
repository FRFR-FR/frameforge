# GAMEFORGE — Engine Architecture & Production Blueprint

> Working codename: GAMEFORGE. This document defines the intended architecture for a code-first, story-led 3D game factory built around open-source tooling and GitHub automation. It is a foundation/specification, not a claim that a complete AAA engine or automated hit-prediction system already exists.

## Product promise

A user gives one natural-language brief ("make a game"). The generator turns it into a playable, testable, optimised 3D project with:
- a coherent 5–10 hour main campaign, authored characters, emotional arcs, purposeful missions and a deliberate ending;
- original mechanics selected for the story, not filler side-content;
- code-driven movement, physics tuning, camera, animation state, cutscenes, dialogue, audio, VFX, SFX and gameplay scripting;
- Android APK and Windows desktop exports, with quality/performance profiles for weaker devices;
- reproducible builds and downloadable artifacts from GitHub Actions.

The system must never promise virality, millions of sales, guaranteed search ranking or a genuinely unprecedented mechanic. It instead scores hypotheses, tests them with players, and reports uncertainty.

## Repository relationship

- Existing cutscene system: [FRFR-FR/frameforge](https://github.com/FRFR-FR/frameforge).
- FrameForge remains a separate cinematic/cutscene subsystem. Its current FF3D renderer is a custom CPU-based renderer; it is not treated as a complete game runtime or skeletal animation engine.
- GAMEFORGE integrates FrameForge through a versioned adapter and interchange format. Do not replace, silently fork, or break FrameForge's existing editor and pipelines.
- This branch is a foundation branch inside the FrameForge repository because a separate repository-creation API was not available in the current GitHub connection. Once a dedicated GAMEFORGE repository is created, move this directory/specification there and keep FrameForge as a dependency.

## Core technical choices

### Runtime
Use **Godot 4.x (MIT-licensed, pinned to a tested release)** as the first production runtime rather than attempting to write a modern 3D renderer, physics engine, animation system and Android platform layer from scratch. This is the practical route to A/AA-scope projects with a small team and no engine licence fee.

- Primary authoring: typed GDScript for generated gameplay systems; optional C++ GDExtension modules only for measured bottlenecks.
- Rendering: Compatibility renderer as the baseline for broad Android/older-GPU support; Mobile renderer as an opt-in quality tier after device testing. Avoid assuming Forward+ will run well on low-end phones.
- Physics: Godot physics for general rigid bodies; deterministic, fixed-step custom controllers for player movement and bespoke mechanics where repeatability matters.
- Content: glTF 2.0 scenes/assets, imported with reproducible settings; compressed textures, mesh LODs, baked lighting where appropriate, occlusion and visibility ranges.
- Audio: Godot audio buses, event-driven SFX, streamed music, voice/dialogue assets, and subtitle/phoneme timing metadata.
- Scripting: sandboxed project templates and typed, generated gameplay modules. Generated scripts must pass static checks and tests before being included.

Godot is the runtime foundation, not the generator's creative brain. GAMEFORGE owns the project schema, story systems, procedural authoring, quality gates, optimisation and build orchestration.

## System architecture

1. **Brief compiler** — converts a prompt into a validated GameSpec: genre, player fantasy, theme, audience, content boundaries, target platforms, 5–10 hour runtime, accessibility, art direction and performance budget.
2. **Market signal researcher** — collects dated public signals (store reviews, community discussions, search interest where accessible, genre saturation and player complaints). Store source, date, sample size and confidence. Never treat scraped anecdotes as representative population data.
3. **Opportunity model** — ranks player problems and underserved mechanics by demand evidence, feasibility, novelty risk, production cost and testability. Novelty is a hypothesis requiring prior-art research, not a claim of "never done before".
4. **Narrative architect** — builds premise, theme, protagonist flaw/need, supporting cast, opposing values, relationship changes, chapter beats, choice consequences and ending. Every major mission must change character, reveal story or test the theme.
5. **Mechanic laboratory** — proposes 3–5 mechanics, prototypes the strongest one, defines player verbs, feedback, failure states, accessibility alternatives and a measurable fun test.
6. **World & art director** — creates a distinct visual grammar (shape language, material rules, palette, lighting, motion language, UI and environmental storytelling). Use a style bible and reference-board similarity checks to reduce accidental imitation.
7. **Scene compiler** — converts the chapter/mission graph into Godot scenes, resources, navigation, interaction zones, animation state machines and data-driven encounter definitions.
8. **Performance governor** — enforces per-device budgets and generates Low/Balanced/High profiles; selects LODs, texture sizes, shadow quality, effects, crowd counts, resolution scale and audio quality.
9. **Cinematic bridge** — sends FrameForge a cutscene manifest: shot list, camera transforms, actor IDs, rig/pose references, action curves, dialogue lines, timestamps, subtitles, audio cues, VFX cues and export settings. Receives rendered clips plus a timing manifest; game runtime handles transitions, subtitles, audio continuity and fallback playback.
10. **Build & QA farm** — runs lint, unit tests, scene validation, deterministic gameplay tests, asset checks, performance smoke tests and platform exports. Publishes APK/EXE artifacts only after gates pass.

## Story and campaign rules

- Main campaign target: 5–10 hours, with an explicit chapter/mission time budget.
- No padding quests. Optional content must deepen a relationship, reveal a meaningful world detail or offer a distinct mechanical experiment.
- Each major character gets: desire, fear, contradiction, coping strategy, relationship pressure, irreversible choice and visible change.
- Dialogue is state-aware. Choices update a typed narrative-state model; later scenes read that state instead of relying on fragile string flags.
- Every cutscene must have a gameplay or emotional purpose and a skippable/replayable path.
- Build a vertical slice before generating a full campaign: 15–30 minutes proving the core loop, protagonist, signature mechanic, art direction and performance.

## Original-mechanic pipeline

The generator should not output random gimmicks. It should:
1. mine player complaints and unmet needs;
2. translate a need into a player verb or systemic rule;
3. search for prior art and adjacent implementations;
4. prototype at greybox fidelity;
5. test comprehension, agency, repeatability and emotional effect;
6. retain, revise or discard based on evidence.

A mechanic is promoted only if it is understandable, creates meaningful decisions, fits the narrative theme and survives playtesting. Maintain a mechanic registry with references and novelty confidence.

## Dialogue, animation and audio synchronisation

Use one timeline as the source of truth. Each cue has a stable ID, start time, duration, speaker, line ID, subtitle, voice asset, phoneme/viseme track (if available), facial/body animation, camera cue, SFX and VFX events. Support time-stretch-safe cue groups, pause/resume, skip, localisation and missing-voice fallbacks. Do not sync dialogue by guessing from audio duration at runtime.

## Performance targets

Targets are budgets to validate, not guarantees across every device.

| Profile | Baseline target | Policy |
|---|---|---|
| Android Low | 30 FPS target | Compatibility renderer, low draw calls, baked lighting, limited transparencies, reduced resolution/effects, aggressive LOD |
| Android Balanced | 30–60 FPS target | Dynamic resolution and scalable shadows/effects |
| PC Low | 30 FPS target | Scalable settings, conservative VRAM |
| PC High | 60 FPS target | Higher shadows, effects, textures and view distance |

Every scene gets budgets for triangles, materials, draw calls, texture memory, audio voices, particles, CPU frame time and GPU frame time. Use real device profiling; emulator success is not proof of low-end phone performance. Keep gameplay readable at 30 FPS and test input latency.

## GitHub-only workflow and honest cost model

- Source, issue tracking, versioning, CI and release artifacts can live on GitHub.
- GitHub Actions free usage is quota-limited and subject to plan/runner rules. Large 3D renders and long Android builds can exceed free minutes/storage. The project must cache dependencies, use incremental builds, cap job duration and offer local build scripts.
- No paid hosted API is required by the architecture. Market research can use public sources and optional user-supplied datasets. Any model/API integration must be optional and clearly labelled as potentially paid; a deterministic local rules engine must always exist.
- Android signing keys belong in GitHub Actions Secrets or local secure storage. Never commit keystores, passwords, API tokens or private signing material.
- Android SDK/NDK and export templates must be installed by pinned setup steps. User must provide a signing key for distributable signed APKs; debug APKs can be built without one.
- Windows EXE builds run on Windows runners. Android APK builds run on supported Linux/Windows runners with pinned Android tooling.

## Suggested repository layout

```
gameforge/
  README.md
  SPEC.md
  schemas/
    game-spec.schema.json
    narrative-state.schema.json
    cinematic-manifest.schema.json
  generator/
    brief_compiler/
    market_signals/
    narrative/
    mechanics/
    art_direction/
    scene_compiler/
    performance/
  runtime/
    godot_template/
    addons/gameforge/
    controllers/
    dialogue/
    audio/
    vfx/
    save_system/
  integrations/
    frameforge/
      manifest.schema.json
      adapter/
      examples/
  templates/
    story_campaign/
    action_adventure/
    narrative_adventure/
  tests/
    unit/
    scenes/
    performance/
    golden_projects/
  tools/
    validate_project.py
    profile_budget.py
    package_assets.py
  .github/workflows/
    validate.yml
    build-windows.yml
    build-android.yml
```

## CI release gates

1. Validate JSON schemas and project structure.
2. Run GDScript lint/static analysis and unit tests.
3. Import all assets headlessly; fail on missing resources.
4. Run scene and dialogue timeline checks.
5. Run gameplay smoke tests and save/load tests.
6. Check project asset/performance budgets.
7. Export Windows build and Android APK.
8. Attach artifacts to a GitHub Release only when all required gates pass.
9. Store build metadata: engine version, commit SHA, export preset, target profile, test results and known limitations.

## First implementation milestones

**M0 — Foundation:** repository layout, schemas, Godot version pin, CI validation, sample project.

**M1 — Playable core:** third-person controller, camera, interaction system, save/load, basic enemy/NPC state, one greybox level, input remapping.

**M2 — Narrative stack:** character-state model, branching dialogue, subtitles, voice cue timeline, mission graph and save compatibility.

**M3 — FrameForge bridge:** cinematic manifest schema, export/import adapter, timing validation, in-game playback and dialogue continuity tests.

**M4 — Visual identity:** one original art-direction system, lighting/material pipeline, animation rig rules, VFX/SFX event bus and UI.

**M5 — Optimisation:** low-end Android profile, LOD/texture pipeline, memory budgets, device matrix and profiling reports.

**M6 — Generator:** prompt-to-GameSpec, story/mechanic generation, deterministic project compiler and quality scoring.

**M7 — Release automation:** signed Android release workflow, Windows EXE packaging, release notes and reproducible artifact manifests.

## Non-negotiable quality principles

- No claim of guaranteed sales, virality or search placement.
- No full-game generation before a vertical slice is validated.
- No invented market statistics; every trend claim needs a source and date.
- No generated code ships without validation and tests.
- No feature is called "optimised" without measured profiles on representative hardware.
- No cutscene is considered integrated until audio, subtitles, animation and playback timing are tested together.
- Prefer a smaller finished game with strong pacing over a huge unfinished world.
