# FrameForge V2 — Zero-Cost and Media-Rights Policy

**Applies to:** all V2 code, workflows, dependencies, generated assets and production packages.

## 1. Zero mandatory spend

The core V2 workflow must not require payment to operate.

Prohibited as required dependencies:
- Paid subscriptions or licences for editing, 3D, compositing or rendering.
- Paid AI/LLM APIs or per-request research services.
- Paid image-generation or video-generation services.
- Paid stock-media libraries or paid asset marketplaces.
- Paid cloud rendering, GPU rental or premium GitHub runners.
- Any workflow that silently falls back to a billable service.

Preferred tools are free/open-source software such as Blender, FFmpeg, Three.js and Python libraries whose licences permit the intended use.

"Free software" does not mean unlimited compute, unlimited bandwidth, unlimited storage or zero electricity/hardware cost. GitHub-hosted automation and artifacts are subject to account/repository/platform limits and policies. Every render workflow must use the free capacity actually available, and stop safely at limits. The project must never silently enable billing or switch to paid infrastructure.

## 2. Optional free-tier services

A provider that has a free tier may be integrated only as an optional adapter. Before adding it, document:
- Whether an account or API key is required.
- Whether a payment method is required.
- The published free quota and relevant restrictions, if verified at implementation time.
- Rate limits and data-retention implications.
- A manual/local fallback that does not require the provider.

Do not store secrets in project files, source code, public logs or manifests. No API key is assumed to exist.

## 3. Dependency policy

- Prefer open-source dependencies with clear upstream licence information.
- Pin versions for reproducible builds; update deliberately, not implicitly.
- Record third-party dependencies and licences in the relevant documentation.
- Do not add a dependency that requires a paid account or license for normal V2 use.
- Avoid loading runtime dependencies from an uncontrolled CDN in the production render path; bundle or pin them.
- For imported fonts, models, textures, audio and code, preserve their licence and attribution records.

## 4. Asset-source classification

Every media asset must have a source classification:
- `user_supplied`: supplied by the user; this label does not itself prove the user owns all rights.
- `procedural`: authored by FrameForge code or the user's own project code.
- `public_domain`: a documented public-domain basis has been checked.
- `open_license`: a specific open licence and its conditions have been recorded.
- `permissioned`: written/explicit permission is recorded.
- `paid_license`: a licence was purchased outside the FrameForge operating budget; this must never be required for the core workflow.
- `unknown`: source or rights basis is unknown.

## 5. Rights-review states

- `pending`: not reviewed yet.
- `approved`: a named reviewer has recorded a specific basis for the intended use.
- `restricted`: the asset can be used only under recorded restrictions.
- `rejected`: do not use in the production.
- `unknown`: no reliable conclusion is available.

A URL, search result, publicly viewable page, creator credit or watermark is not sufficient proof of permission. An asset cannot be automatically marked approved simply because it downloads successfully.

Where attribution is required, store the exact attribution text and include it in the delivery package/video description draft as appropriate. Keep the original licence/source URL and review date.

## 6. Copyrighted entertainment footage and characters

Fan analysis, criticism and commentary may involve copyrighted characters, stills or footage. The system must not assume that a short clip, a screenshot, a PNG cut-out or a transformation effect is automatically lawful to reuse. Fair-use/fair-dealing exceptions depend on jurisdiction and context and cannot be guaranteed by software.

For each copyrighted or potentially copyrighted asset:
- Prefer user-supplied material with clear permission or a defensible legal basis reviewed by the user.
- Keep the source and intended commentary/criticism context recorded.
- Use only what is necessary for the intended analysis.
- Do not remove watermarks or access controls.
- Do not circumvent paywalls or download restrictions.
- Flag unverified/restricted material for manual review and prevent it from being labelled "free to use".

## 7. Publication gate

A production may be rendered as a private working draft with unreviewed assets only when clearly marked as such. A publication package must include a rights/provenance report and should not pass its automated release gate while required rights reviews or attributions are missing.

The gate is a workflow safeguard, not legal advice or a guarantee that the final video is non-infringing.
