# FrameForge V2 research intake and visual director

This module implements roadmap steps 31–35 in the V2 project workflow. It runs locally in the browser and writes its data into the existing V2 JSON project. It does not require a paid research API, a paid LLM, a media-generation service, a private-content scraper or a third-party rendering service.

## Step 31 — Production brief

The brief records topic, niche, audience, platform, target duration, tone, desired style, visual direction, narration/script, research questions, ambiguities/assumptions to resolve and production/legal/platform restrictions.

The brief is stored in `creative_brief`. Research questions are also copied into `research.research_questions` so the dossier can be reviewed independently.

A brief is an intake record, not a statement that the topic's facts have been checked. Unknown definitions, ambiguous names/dates and unresolved assumptions should be added to the ambiguity list before shot planning.

## Step 32 — Research and reference-video dossier

Public research sources are recorded with URL, title, publisher, publication date, retrieval date, source type, access state, confidence and notes. Claims refer to source IDs rather than duplicating URLs. The dossier also records confidence notes and visual-format observations.

Public reference videos can be stored with URL, title, creator, platform, publication/retrieval dates, access status, observations and notes. These records are always `reference_only: true`.

**Reference-video boundary:** a reference can inform broad format observations such as pacing, hook structure or diagram use. It does not grant permission to reproduce a creator's exact edit, protected expression, footage, audio, branding, graphics or character art. Login-only and blocked pages are recorded as such; the local module does not fetch them or bypass access restrictions.

Web research remains assistant-led or user-supplied. The local editor is a dossier/record-keeping tool; it does not autonomously browse, scrape pages, verify citations or infer publication rights. When research is performed externally, record the exact public source, dates, observations, confidence and what claim it supports.

## Step 33 — Niche visual style profiles

The module includes editable starting profiles for:
- Cybersecurity
- History
- Science
- Mysteries/investigations
- Finance
- Gaming
- Entertainment/power scaling
- General/unclassified

Each profile suggests visual language, preferred media, pacing, camera language, sound language and no-go rules. The selected profile is copied into `visual_style_profile` and saved with the project. Users can change every field or switch to a custom profile. The profile is guidance, not a rigid template.

## Step 34 — Narration-to-shot visual director

The first-pass planner splits the narration into sentence/paragraph beats, distributes the requested duration across those beats in proportion to their word counts and records frame-accurate start/end frames using the sequence frame rate.

Each shot stores:
- Narration and visual purpose
- Suggested media mix (for example, character cut-out, source footage, procedural 2D, 3D, diagram, typography, maps, screenshots or gameplay)
- Visual role and evidence requirement
- Camera movement, visual actions and VFX/motion-treatment notes
- Asset requirements and optional linked project asset IDs
- Incoming/outgoing transition notes and SFX/audio cues
- Linked research claim IDs

The current director is deliberately a deterministic, rule-assisted first draft. It is not a general autonomous AI, does not invent verified facts, does not fetch stock footage, and does not decide that an asset is legally reusable. Review and edit every shot. If the requested target duration cannot allocate at least one frame to each generated beat, the planner reports an error rather than producing zero-length shots.

## Step 35 — Evidence and rights review

Research claims are classified as factual, comparative, interpretation, opinion or illustrative. A claim also stores source IDs, confidence, verification status, evidence requirement and uncertainty/caveat notes. Optional pinpoint evidence locations can be stored per source with a page/section/timecode locator, page reference, excerpt, notes and numeric start/end seconds for media clips. Each location must belong to a source ID already cited by that claim, and the end time cannot precede the start time. The claim editor accepts one locator per line in the form `SOURCE_ID | page 12, paragraph 2` or `SOURCE_ID | 00:01:23–00:01:41`; the latter is retained as an easy-to-review locator label, while numeric start/end values are available in the project data for precise media offsets.

A shot may be marked as illustration, reconstruction, opinion or demonstration without claiming that the image itself proves a fact. Shots marked factual/comparative evidence must link to at least one claim. The claim must be classified factual/comparative, marked verified by the reviewer and supported by a source marked publicly accessible.

Per-shot evidence requirements include:
- `source_document`
- `actual_footage`
- `official_screenshot`
- `sourced_data`
- `user_review`
- `none`

A shot marked as requiring actual footage must include `source_footage` in its media mix and link an imported video asset. An official screenshot requirement must include screenshot media and a linked image asset. Data-led shots should include a diagram/chart and verified source-linked claims. The review gate checks linked assets and all imported project assets for documented rights status.

Imported media is not automatically approved. For each asset, the rights panel records a reviewer-entered decision, basis, intended use, permission reference, attribution text, restrictions and review date. An approval requires a documented basis, reviewer and date. The editor cannot determine whether that basis is legally sufficient; the user remains responsible for confirming ownership, licence terms, permission or another defensible legal basis. Assets marked restricted, rejected, pending or unknown cannot pass the review gate.

The final review result is stored in `rights_review`; shot-plan status is updated to `approved` only when blockers and warnings are clear. `approved_with_limits` is distinct from full approval. This is a workflow guardrail, not legal advice or a guarantee against copyright claims.

## Data shape and compatibility

The features are optional additions to schema version 2:
- `creative_brief.narration_script`, `research_questions`, `ambiguities_to_resolve`, `restrictions`
- `research.sources`, `research.claims`, `research.reference_videos`, `research.confidence_notes`, `research.visual_style_observations`
- `visual_style_profile`
- `shot_plan`
- `rights_review`

Existing V2 projects are normalised in memory when the director opens; existing project fields are preserved. New project data continues to use the version 2 schema. The JSON Schema and semantic validator check references among sources, claims, shot beats, assets and rights reviews.

## Example and verification

The schema example [frameforge-research-director.example.json](../examples/frameforge-research-director.example.json) demonstrates a sourced firewall definition from NIST SP 800-41 Rev. 1, an optional pinpoint source locator, a reference-only format entry, a cybersecurity visual profile, an evidence-linked shot and a documented rights review for original procedural artwork.

Run the local checks with:

```bash
node --test tests/ff-v2-director.test.js
python -m unittest tests.test_ff_v2_foundations -v
python tools/validate_project.py examples/frameforge-research-director.example.json
```

The browser acceptance test is [ff-v2-director-browser-smoke.js](../tests/ff-v2-director-browser-smoke.js). It exercises brief intake, source/reference records, pinpoint source-location entry, profile editing, timed shot generation, evidence linking, asset rights review and persistence after reload.
