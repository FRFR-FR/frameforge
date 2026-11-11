# GAMEFORGE Autopilot — stage 1

This stage accepts a plain-language brief and produces:
- GAME_SPEC.json — schema-validated project specification.
- STORY_BIBLE.json — first-pass protagonist/relationship model and chapter outline.
- MECHANIC_REVIEW.json — candidate mechanics and prototype test plans.
- PIPELINE_REPORT.json — completed and outstanding production gates.

## Free offline run

~~~bash
python -m pip install -r gameforge/generator/brief_compiler/requirements.txt
python gameforge/generator/autopilot/run.py \
  --brief "Create a painterly third-person mystery adventure about a lighthouse keeper and memory, with a 7 hour campaign." \
  --out build/lighthouse
~~~

The offline provider is deterministic, requires no API key and makes no network calls. It is a useful starter, not a substitute for a frontier creative model: it extracts broad genre/theme signals and creates a structured first pass.

## Optional model provider

Set GAMEFORGE_API_BASE, GAMEFORGE_MODEL and optionally GAMEFORGE_API_KEY, then run with --provider openai-compatible. Use environment variables or GitHub Actions Secrets; never commit API keys. The remote provider may incur charges and is not required by CI.

## Honest completion semantics

A generated outline is not a finished script. A mechanic idea is not a playable prototype. This stage does not perform live market research, generate assets, create a vertical slice, benchmark devices or export APK/EXE files. The report deliberately keeps those release gates false.
