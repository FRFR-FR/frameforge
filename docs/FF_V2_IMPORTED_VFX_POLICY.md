# FrameForge V2 — Imported VFX-first production policy

**Default for production-quality VFX:** import suitable, externally authored VFX footage or assets with a verified free-use licence. Do not recreate a matching fire, smoke, sparks, debris, energy, particle, weather or lens-effect asset with repository-authored procedural drawing when a suitable imported asset is available.

## Priority order

1. User-supplied assets with documented permission or an identified licence.
2. External free-use VFX footage and assets from providers whose individual asset page and applicable licence have been checked.
3. Openly licensed 3D assets and simulations downloaded from their creator/provider, with the model, texture and animation licences recorded separately.
4. Repository-authored procedural graphics only when no suitable licence-compatible imported asset is available, or when the user explicitly requests a custom stylised effect.

A procedural preview is not an acceptable substitute for a requested professional VFX asset when a suitable imported asset can be sourced.

## Source checks

For every imported asset, record its exact title, creator, item-page URL, licence name and licence URL; whether it is available without payment; any account/API requirement; intended use (including monetised YouTube/commercial use); restrictions; attribution; source resolution; frame rate; file size; and review date.

- Pixabay Content License: assets are free to use and adapt without attribution, subject to prohibited-use clauses and additional third-party rights. Do not redistribute an asset as a standalone file. Avoid misleading or deceptive use. Recognisable people can raise additional privacy/personality-rights questions.
- FX Elements free VFX: its free VFX pages state that selected assets are free for personal and commercial projects under its royalty-free licence. Check the individual item and licence agreement before use.
- Mixkit: check the individual clip page. An item marked Restricted License is for personal use only and must not be treated as cleared for monetised or commercial work. The individual item licence controls.

## Import and storage

- Download source binaries into a temporary render workspace such as artifacts/imported-vfx/.
- Do not commit stock VFX binaries to this repository unless the asset licence explicitly permits redistribution and the project has a clear reason to store them.
- Prefer a provider API or documented download endpoint. Do not bypass account gates, paywalls, anti-bot controls or download restrictions.
- Keep source URLs, licence data, creator details and attribution in a machine-readable manifest and in delivery credits.
- Never log API keys or include them in repository files, video frames or credits.
- Pin importer dependencies and validate file type, dimensions, frame rate and duration before compositing.
- Where the provider requests or benefits from credit, show an on-screen credit and include it in CREDITS.txt, even when the licence does not require attribution.

## Cut-outs and selective grading

Background removal must produce a genuine alpha channel. A red/blue/green grade intended for a person or object must be applied to that isolated alpha layer, never to the full rectangular source image. Keep the original background on a separate ungraded layer. Include a transparent PNG cut-out in the delivery package when requested.

For recognisable public figures, clearly identify simulated visual effects as simulated. Do not imply that a staged visual effect is authentic news or documentary footage.

## Publication gate

A render succeeding does not itself prove publication rights. A publication package must preserve its rights/provenance dossier and must not label uncertain assets as free or cleared.

The default production route is imported VFX plus compositing. Procedural VFX modules remain available as optional fallbacks, previews or explicitly requested custom effects; they are no longer the preferred production source when suitable external VFX is available.
