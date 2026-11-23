# Ocean Nightmares — FrameForge production

This is the active project location. Do not use Senator Vids or Pixabay.

## Locked production contract
- 15:00, 1280×720, 30 fps, H.264 MP4.
- NOAA Ocean Exploration footage only.
- At least 50 unique clips, each visually verified as the narrated species.
- Asset-level rights/credit review and species review required for every clip.
- No substitutes, generic deep-sea shots, stock footage, or AI imagery.
- Liam Kokoro narration; CTA at 07:00.
- No smoke tests. The workflow only assembles the final full-length deliverable.

## Current gate
The manifest intentionally starts unapproved. A render must not begin until 50 distinct NOAA media assets have been downloaded, individually rights-reviewed and species-verified, and the narration MP3 is present. The workflow fails closed if any requirement is missing.

## Populate
For each clip in media_manifest.json, set species, NOAA page URL, direct media URL, credit text, rights_review=approved, species_review=approved, and approved=true. Download the corresponding video as media/<clip-id>.mp4. Place the final Liam narration at narration.mp3.

## Run
Use the GitHub Actions workflow **Ocean Nightmares — NOAA-only full render**. It validates the complete source set before assembling the final MP4. No preview or smoke-test render is produced.
