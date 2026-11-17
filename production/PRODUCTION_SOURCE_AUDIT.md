# BROWN — Book One production source audit

**Status:** SOURCE RECONCILIATION REQUIRED — NOT APPROVED FOR FINAL LOCK  
**Branch:** `fix/two-hour-feature-film`  
**Purpose:** prevent the feature-film adaptation from being built against stale or incomplete source-status metadata.

## Verified source records

The project Library contains the following user-owned source material:

- `BROWN_Book_One_Opening_Manuscript.pdf` — includes the prologue and opening chapters.
- `BROWN_Book_One_Manuscript_Chapters_1-40.docx/.pdf`
- `BROWN_Book_One_Manuscript_Chapters_1-47.docx/.pdf`
- `BROWN_Book_One_Manuscript_Chapters_1-61.pdf`
- `BROWN_Book_One_Chapters_62-72.docx/.pdf`
- `BROWN_Book_One_Story_Bible_and_72_Chapter_Plan.pdf/.docx`
- `BROWN_Book_One_Story_Bible_and_Chapter_Roadmap.pdf/.docx`

The story-bible document describes Chapters 9–72 as roadmap summaries and states that the opening prose was only Chapters 1–8. Later Library manuscript files now cover Chapters 1–61 and Chapters 62–72. Therefore the current `production/story_breakdown.json` source-status statement is stale and must not be treated as authoritative for the current manuscript inventory.

## Adaptation rules

1. Use the latest complete manuscript text for story events and dialogue. Use the story bible for world rules, character arcs, chronology, and continuity—not to override later completed prose.
2. Reconcile overlapping manuscript exports by chapter and compare text before choosing a canonical passage. Do not concatenate duplicate chapter ranges.
3. Preserve the novel's moral framing: Kaylen's responsibility is not erased by manipulation or trauma; violence is not glamorised; victims remain individuals, not spectacle.
4. Keep the opening pilot within the Prologue and Chapter 1 source material. Do not foreshadow with invented scenes or dialogue.
5. Every proposed expansion, visual metaphor, screen insert, transition, and sound bridge must be tagged as an adaptation choice. Any new plot fact or spoken line requires author approval.
6. Character appearance details absent from source descriptions remain **TBD**. Design briefs may propose silhouette, costume language, palette, and performance principles, but must not silently convert guesses into canon.
7. All art and animation specifications in this branch are provisional until the author approves the character model sheets, turnarounds, facial tests, and pilot.

## Pilot scope

- Working title: **BROWN — Book One | Five-minute visual pilot**
- Runtime: 300 seconds exactly
- Frame: 1280×720, 24 fps, 7,200 frames
- Visual direction: painterly, expressive 3D/2.5D hybrid; graphic shape design, textured brushwork, dynamic but legible motion, deliberate held poses, strong staging and motivated camera movement.
- References for broad craft qualities only: energetic graphic action, painterly lighting and expressive character animation. Do not copy any protected character designs, shots, or signature assets.
- Initial cast focus: Kaylen Atlee, Registry Clerk (if retained after source check), and the Grave Choir members visible in the opening print-shop passage.
- No final render is authorised by this document. It is a review package, not proof that animation has rendered.

## Immediate blockers

- Reconcile source exports and update the scene breakdown.
- Author-approve character appearance concepts.
- Create model sheets, turnarounds, rigs, facial tests, environment assets, props, and sound assets.
- Complete a five-minute pilot render and visual/audio QC before enabling the 120-segment feature render.
