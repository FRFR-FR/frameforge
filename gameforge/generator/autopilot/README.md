# GAMEFORGE Autopilot — stage 1

This stage accepts a plain-language brief and produces:
- GAME_SPEC.json — schema-validated project specification.
- STORY_BIBLE.json — first-pass protagonist/relationship model and chapter outline.
- SCENE_PLAN.json — three scene cards per chapter, convergent choices and persistent state keys.
- MECHANIC_REVIEW.json — candidate mechanics and prototype test plans.
- PIPELINE_REPORT.json — completed and outstanding production gates.

The scene-plan validator checks unique scene IDs, chapter bounds, declared choice-state keys, choice references and distinct options. It is a structural continuity gate, not a substitute for editorial review or a full narrative simulation.

## Free offline run

~~~bash
python -m pip install -r gameforge/generator/brief_compiler/requirements.txt
python gameforge/generator/autopilot/run.py \
  --brief "Create a painterly third-person mystery adventure about a lighthouse keeper and memory, with a 7 hour campaign." \
  --out build/lighthouse
~~~

The offline provider is deterministic, requires no API key and makes no network calls. It extracts broad genre/theme signals and creates a structured first pass; it is not a substitute for a frontier creative model.

## Optional model provider

Set GAMEFORGE_API_BASE, GAMEFORGE_MODEL and optionally GAMEFORGE_API_KEY, then run with --provider openai-compatible. Use environment variables or GitHub Actions Secrets; never commit API keys. The remote provider may incur charges and is not required by CI.

## Honest completion semantics

A generated outline is not a finished script. Scene cards are not authored scenes or dialogue. A mechanic idea is not a playable prototype. This stage does not perform live market research, generate assets, create a vertical slice, benchmark devices or export APK/EXE files. The report deliberately keeps those release gates false.
