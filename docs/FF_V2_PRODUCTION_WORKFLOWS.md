# FrameForge V2 — Production workflows (steps 36–40)

This guide covers the production-workflow panel added to the V2 timeline workspace. It turns the reviewed shot plan into editable project data; it does not create a finished MP4.

## Step 36 — Reusable shot recipes

The production panel includes nine editable starting recipes:

- Character reveal
- Side-by-side comparison
- Step-by-step explainer
- Technical diagram
- Map / spatial sequence
- Chronological timeline
- Evidence callout
- Gameplay / UI overlay
- Documentary scene

A recipe adds a composition, media priority, camera language, visual action, motion treatment, effects, transition, overlay guidance and a duration scale to the selected narration beat. Users can change the layout, duration scale and transition length. The original narration start/end frames are preserved; the chosen assembly duration is stored separately as `recipe_duration_frames`. Users can continue editing the plan before assembly.

## Step 37 — Free/open media source adapters

The current adapter strategy deliberately separates catalogue discovery, downloading and rights approval.

| Source | Integration in this batch | Important handling |
|---|---|---|
| [Openverse API](https://api.openverse.org/v1/) | In-app search for images and audio; up to eight results per request | Captures result title, creator, source page, licence name/URL and attribution text. Anonymous use is supported, but rate limits and pagination restrictions apply. Do not scrape or try to evade those limits. |
| [Wikimedia Commons MediaWiki API](https://www.mediawiki.org/wiki/API:Imageinfo) | In-app search; file pages can return image, audio or video metadata | Captures per-file creator, file/source URLs, licence metadata and attribution fields. Review the individual file description page. |
| [Poly Haven](https://polyhaven.com/) | Manual browser workflow | Its HDRIs, textures and models are CC0. The live API is free, but integrating it in an application requires a distinct User-Agent and a visible Poly Haven credit. This static browser workflow links to the catalogue instead of making API calls that cannot set a product-specific User-Agent. |
| [Internet Archive](https://archive.org/) | Manual browser workflow | Item rights statements vary. An archive search result or public item page is not, by itself, proof of a reuse licence. |
| Freesound | No API adapter in this batch | The Freesound API's free access is limited to non-commercial use; commercial API use requires separate licensing. Do not assume a sound's presence on Freesound makes it reusable for a commercial production. |

The in-app search is user-initiated and capped at eight results. It does not automatically download the media. Select a result, inspect its original file/description page, download the media manually, then import the local file through the V2 asset importer. The importer validates the media file and records provider, creator, source URL, licence name/URL, attribution and user-entered restrictions where supplied. The asset's rights state is **pending** after import; a source result is never automatically approved.

Manual local import remains the fallback for all other sources. An imported file stays in the browser's IndexedDB; project JSON keeps asset metadata and references, not the binary media itself.

## Step 38 — Procedural assets and motion graphics

The panel creates original code-generated artwork without paid image-generation services:

- Editable SVG clips for atmospheric backgrounds, comparisons, process/system diagrams, schematic maps, timelines, source callouts, bar charts and key-idea badges.
- Seeded particle clips with selectable presets (sparks, dust, embers, magic and confetti), configurable count, and a repeatable seed.
- User-entered chart labels and values. When no values are entered, the bar chart visibly labels itself as illustrative sample data, not factual data.
- Map graphics are labelled schematic/not to scale; timeline graphics instruct the editor to verify dates against sources; evidence cards carry a source/pinpoint verification reminder.

SVG text is escaped and passed through the shared SVG safety validator. The generated SVG or particle settings remain part of an editable timeline clip. These are original visual treatments, not source evidence. Actual-footage, official-screenshot and source-document requirements are not replaced with decorative artwork.

## Step 39 — Audio catalogue, rights and attribution

Audio assets can be assigned as voiceover, music or sound effects. The audio catalogue records licence name/URL, attribution requirements, credit text, source/provider and restrictions or usage limits. Imported audio remains pending until the existing Research & Visual Director rights-review workflow records a decision with a documented basis and reviewer.

The audio package report:

- Blocks assets that are not rights-approved.
- Blocks an attribution-required asset when the credit text is missing.
- Produces a credit text block for approved assets.
- Exports per-asset usage limits separately so that limitations such as non-commercial use, attribution placement or scope are not lost.

Approval with limits preserves those limits in the report; it does not make restricted use unrestricted. The report is a metadata gate, not independent licence verification or legal advice. Check the exact licence and the intended distribution/use for every file.

## Step 40 — Shot assembly and production orchestrator

Choose **Assemble editable draft timeline** after creating and reviewing the shot plan. The orchestrator:

1. Reads the timed shot beats and their linked asset IDs.
2. Adds linked still/video clips to the appropriate editable tracks.
3. Adds linked audio assets to voiceover/music/SFX tracks using their recorded role.
4. Applies supported recipe transitions and clip effects to assembled visual clips.
5. Creates procedural SVG artwork only for beats whose media mix requests procedural 2D and whose evidence requirement does not require actual footage or an official screenshot.
6. Stores timed audio cue descriptions and records every beat that lacks a suitable visual asset.

A required source-footage or official-screenshot shot is never silently replaced by a generic clip or an illustrative diagram. The orchestrator records that beat in `project.extensions.production_orchestration.unfilled_beats` and marks the draft as needing assets. The JavaScript and Python structural validators allow such a project to be saved only when the missing beat is explicitly recorded. The director's readiness report continues to block it until the required source media and its rights review are complete.

The result is an editable timeline/project draft with clip IDs, timed cue metadata, rights blockers and unfilled-beat records. It is not a flattened video. Full-sequence rendering, resumable chunks and final export remain later roadmap work (steps 41–43).

## Use the production panel

1. Open the V2 multi-track timeline and create a production brief/shot plan in **Research & Visual Director**.
2. Open **Production workflows · Steps 36–40**.
3. Select a shot beat and recipe, adjust timing/layout options and apply it.
4. Search Openverse or Wikimedia Commons, inspect the selected source page and licence, download it manually, enter any applicable credit/restrictions, then import the local file. Or use a manual catalogue link/local import.
5. Create procedural SVG or particle clips where those treatments fit the shot plan.
6. Select each audio asset, record its licence and use limits, and save metadata. Complete the existing rights review before packaging credits.
7. Assemble the editable draft timeline. Review unfilled beats, evidence requirements and all rights blockers before considering a render.

## Verification

Verified on commit `34ac979ce91fd0fdea064d1740f9fa2b874efbb5`:

- [Foundation Validation run 46136634856 — success](https://github.com/FRFR-FR/frameforge/actions/runs/46136634856): 74 JavaScript tests passed; 31 Python tests passed; syntax, schema, semantic and FFmpeg integration checks passed.
- [Browser Smoke run 46136634866 — success](https://github.com/FRFR-FR/frameforge/actions/runs/46136634866): V2, audio, research-director and production Chromium smoke tests passed. The production test exercised recipe application, procedural SVG, local WAV import, the pending-audio package gate, timeline assembly, explicitly unfilled required footage and IndexedDB reload.

## Boundaries

- Search results are not licences. The user must inspect the original item page and make a documented rights decision.
- Catalogue discovery is limited to eight results per request; no automatic download or bulk scraping is implemented.
- Poly Haven and Internet Archive use manual browser paths; Freesound's API is not integrated into this commercial-safe workflow.
- Procedural visuals are illustrations, not historical/factual proof.
- Audio rights and restrictions are user-recorded metadata; no external rights service checks them.
- Audio cues are preserved as timed production metadata. Unless an actual audio asset is linked to a beat, the orchestrator does not invent an SFX clip.
- Imported media binaries remain in local IndexedDB, separate from project JSON.
- The V2 editor still has no automatic full-sequence MP4 render in this batch.
