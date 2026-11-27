# Underneath Everything — documentary production pipeline

## Editorial and visual standard

- Every episode must be a distinct research-led cinematic documentary.
- Real, relevant, moving B-roll is the visual foundation: target 75–85% of runtime; hard release-candidate minimum 70%.
- Use only the minimum rights-cleared footage needed. Pixabay API requests must be cached for 24 hours, made sequentially, and kept within the published API policy. No systematic bulk downloads.
- NOAA Ocean Exploration video is public domain and should be credited to NOAA Ocean Exploration or NOAA when used. OOI Regional Cabled Array archive video may be reused with proper attribution. Other sources require documented reuse rights.
- Search topic-specific terms and relevant fallbacks. Verify every clip against its intended scene. Record source page, creator, license/credit, download date, query, intended use, relevance and full-decode result.
- Never describe generic stock as a particular event, factory, location or proprietary process without evidence.
- Use dynamic 3D, animated maps and diagrams only where a camera cannot show the mechanism. Keep explanatory motion graphics to 15–25% of runtime; text/diagram-only cards normally below 10%.
- No static slide presentation, title-card sequence, still-photo zooms, repeated infographic panels or unrelated filler.

## Brand

- Red #D62839, white #FFFFFF, blue #1746A2, deep navy #102B52.
- Preserve footage's natural colours.
- Use a thin red top rule, one small channel bug, short chapter labels over moving footage and readable subtitles with restrained navy/blue backplates.
- No decorative text walls or unnecessary labels.

## Narration

- Kokoro English pipeline, voice ID am_echo (American English male Echo).
- Save separate narration WAV and compressed MP3; record provider, voice ID, durations and file sizes.
- Split long scripts into paragraph-sized sections, then synthesize naturally with clean pauses.
- Never silently substitute eSpeak, Cartesia or another provider. If Kokoro fails, report the exact error and stop audio approval. A clearly labelled temporary preview is not an approved narration master.

## Technical export lock

- Long-form final: exactly 1280×720, 16:9, MP4 H.264 video and AAC audio.
- Shorts, if rendered: exactly 720×1280.
- Never export 1080p or 4K. Keep all intermediate encoded video at 720p or lower.
- Target 24–30 fps only when the actual runner supports it reliably. Report measured ffprobe fps; never fake or relabel it.
- Target 8–12 minutes only when natural narration supports it. Never stretch shots or pad.
- Large media stays out of normal Git history; use GitHub Actions artifacts or another approved artifact store.

## Quality control and release

- Run ffprobe, full-file decode and audio checks.
- Inspect representative frames throughout the episode and create per-clip B-roll contact sheets for human relevance review.
- Detect frozen/repeated shots; enforce no more than two uses per source clip.
- Measure B-roll share from actual timeline durations, not estimates.
- Report clip count, license records, narration WAV/MP3 sizes, runtime, measured fps, codec, resolution, file size MB, thumbnail, subtitle and Shorts status, Git commit, artifact link, blockers and next steps.
- Never auto-publish. Human approval is required.
