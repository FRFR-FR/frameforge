# FrameForge V2 — Upgrade Progress

**Canonical roadmap:** [FF_V2_50_STEP_ROADMAP.md](FF_V2_50_STEP_ROADMAP.md)  
**Current completed batch:** Steps 1–5  
**Last updated:** 2026-11-28

## Batch 1–5 status

| Step | Deliverable | Status | Verification |
|---:|---|---|---|
| 1 | Baseline repository/application/workflow audit | Complete | Reviewed source entry points and all 25 workflow YAML files; audit report committed |
| 2 | V2 architecture and zero-cost/media-rights policy | Complete | Architecture, cost and rights policy documents committed |
| 3 | Automated foundation validation | Complete | GitHub Actions run 46107639884 succeeded; all 12 unit tests passed |
| 4 | Versioned project format | Complete | Draft 2020-12 project schema validated; example project passes schema and semantic checks |
| 5 | Media provenance/rights manifest | Complete | Draft 2020-12 manifest schema validated; sample manifest passes; duplicate IDs and incomplete approvals are rejected |

## Step 1 — Audit

Created [FF_V2_BASELINE_AUDIT.md](FF_V2_BASELINE_AUDIT.md). It documents current application entry points, the existing Canvas and FF3D limits, Blender and FFmpeg production paths, the 25 workflow inventory, operational risks and baseline verification commands.

## Step 2 — Architecture and cost policy

Created:
- [FF_V2_ARCHITECTURE.md](FF_V2_ARCHITECTURE.md)
- [FF_V2_COST_AND_RIGHTS_POLICY.md](FF_V2_COST_AND_RIGHTS_POLICY.md)

The core production path has no mandatory paid API, AI-generation, stock-media, editing subscription or cloud-render service. Free compute, storage and artifact quotas remain finite; workflows must stop safely rather than silently incur charges.

## Step 3 — Test foundation

Created:
- [requirements-dev.txt](../requirements-dev.txt)
- [tests/test_ff_v2_foundations.py](../tests/test_ff_v2_foundations.py)
- [ff-v2-foundation-tests.yml](../.github/workflows/ff-v2-foundation-tests.yml)

GitHub Actions run: [46107639884 — success](https://github.com/FRFR-FR/frameforge/actions/runs/46107639884).

Result from the workflow log: **12 tests passed**. Both example validators also passed. The workflow uses read-only repository permissions, is path-scoped and does not invoke any video-render workflow.

The run emitted an upstream maintenance warning that checkout/setup-python actions currently target a deprecated Node 20 runtime and were forced to Node 24 by the runner. The test job itself completed successfully; action-version maintenance should be reviewed as part of a later maintenance step.

## Step 4 — Versioned project schema

Created:
- [frameforge-project-v2.schema.json](../schemas/frameforge-project-v2.schema.json)
- [frameforge-project-v2.example.json](../examples/frameforge-project-v2.example.json)
- [opening-grid.svg](../examples/assets/opening-grid.svg)
- [validate_project.py](../tools/validate_project.py)

The schema defines project metadata, output settings, assets, source/rights metadata, sequences, tracks, clips, transforms, keyframes, effects, transitions and optional research/creative-brief fields. The validator checks schema rules, duplicate identifiers, missing asset/sequence references, sequence frame bounds and evidence-source/claim references.

The existing browser editor's version-1 project format has **not** been migrated or replaced. Migration is a later implementation task and must be explicit.

## Step 5 — Media rights manifest

Created:
- [media-asset-manifest-v1.schema.json](../schemas/media-asset-manifest-v1.schema.json)
- [media-asset-manifest.example.json](../examples/media-asset-manifest.example.json)
- [validate_media_manifest.py](../tools/validate_media_manifest.py)

The format records source classification, source URL, creator/provider, acquisition time, technical metadata, licence/permission basis, attribution and reviewer state. Approved assets require a review basis, reviewer and review timestamp; attribution-required assets must include attribution text. The sample includes a deliberately pending placeholder to demonstrate that unknown rights are not silently approved.

## Important limits / not yet done

- The V2 editor UI, multi-track timeline, compositor, VFX engine, transitions, audio mixer and integrated render controller have not yet been implemented.
- The example project is a schema fixture, not proof of a production-ready V2 editor or renderer.
- The rights validator checks metadata completeness; it does not determine legal rights or provide legal advice.
- This batch did not run Blender renders or alter existing production workflows.
- Step completion is based on the recorded acceptance tests, not on visual-production capability.

## Next batch

Wait for the user to request the next batch. Do not start steps 6–10 automatically.
