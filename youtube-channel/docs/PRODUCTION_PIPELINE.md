# Reusable Production Pipeline

## Overview

GitHub is the source of truth. Frameforge/FFmpeg assembles episodes. GitHub Actions validates packages and runs renders only when the runner has sufficient resources. Standard hosted runners are not guaranteed to be fast or free for long 3D renders.

## Folder convention

```text
episodes/
  EP001/
    README.md
    research/
      source_ledger.csv
      fact_check.md
    script/
      narration.md
    assets/
      manifest.csv
      thumbnail_concept.md
    edit/
      storyboard.csv
    output/
      captions.srt
      thumbnail.png
      render_report.json
    render_episode.py
    build_episode.py.gz.b64
```

Do not commit large raw video files, audio intermediates or private API keys. Keep MP4s as GitHub Actions artifacts or other approved storage. Store credentials in GitHub Actions Secrets and never print them in logs.

## Stage gates

### 1 — Topic approval
Record the central question, viewer promise, audience hypothesis, competing coverage, visual feasibility and what makes this treatment distinct.

### 2 — Research
Create a source ledger with claim ID, exact claim, primary URL, publisher, publication/update date, access date, supported claim, confidence and caveats. Prefer primary sources and clearly separate facts, estimates and interpretation.

### 3 — Script
Write for the ear. Mark factual statements with claim IDs. Verify names, dates, quantities and technical explanations. Avoid unsupported superlatives and sensational claims.

### 4 — Visual plan
Every narration beat needs a visual purpose: evidence footage, map, custom diagram, 3D cutaway, on-screen figure or deliberate transition. Use real footage for the real world and original graphics to explain invisible systems.

### 5 — Asset acquisition
Download one item at a time. Verify file integrity and usage terms. Record source URL, creator, license, attribution, date and intended use. If an asset fails, try a relevant fallback and document the substitution. Never use unrelated filler.

### 6 — Narration and sound
Generate narration only after script approval. Check pronunciation, pacing and intelligibility. Align scene durations to actual spoken phrases. Keep music below narration and use effects sparingly.

### 7 — Assembly
Build the timeline from a structured shot list. Keep the output strictly 1280×720 for landscape long-form or 720×1280 for vertical Shorts. Do not create 1080p or 4K intermediates or deliverables.

### 8 — Quality control

Automated checks:
- Video stream exists and is exactly 1280×720 for long-form.
- H.264 video and AAC audio are present.
- Measured frame rate and duration are reported without relabeling.
- Captions are valid and timestamps are ordered.
- No missing or zero-byte assets.
- Full MP4 decode succeeds.

Human checks:
- Watch the full render.
- Listen to the full narration mix.
- Verify factual graphics and maps.
- Confirm source/license manifest is complete.
- Check thumbnail/title accuracy and representative frames.

### 9 — Publishing package
Prepare title, thumbnail, description, chapters, captions, source notes and Shorts cut list. Upload only after explicit channel-owner approval; never auto-publish from a commit.

## GitHub workflow

1. Commit an episode brief, source ledger, script, storyboard and asset manifest.
2. GitHub Actions validates required files and the 720p-only configuration.
3. A human approves research, rights and script.
4. A render job runs on a properly provisioned runner.
5. The render output is stored as an artifact.
6. A human watches the final render and approves publication.

## Resource and cost controls

- Cache dependencies where possible.
- Download only approved assets, sequentially.
- Avoid parallel large downloads or renders that exhaust disk space.
- Track expected and actual MB for each source and final export.
- Delete temporary intermediates only after successful validation.
- Use proxy media where needed, but retain high-quality source media for final rendering.
- Never promise a render duration before benchmarking the actual runner and project.
