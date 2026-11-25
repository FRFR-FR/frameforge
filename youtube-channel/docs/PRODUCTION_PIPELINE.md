# Reusable Production Pipeline

## Overview

The workflow is designed around GitHub as the source of truth and Frameforge/FFmpeg for assembly. GitHub Actions should orchestrate validation and lightweight jobs; long renders should run on a suitable runner or external machine with sufficient disk, memory and render capacity. Standard hosted GitHub runners are not a guaranteed free solution for lengthy 3D renders.

## Folder convention for each episode

```text
episodes/
  EP001/
    brief.md
    research/
      sources.csv
      fact_check.md
    script/
      narration.md
      approved_script.md
    assets/
      manifest.csv
      maps/
      graphics/
      footage/
      audio/
    edit/
      shot_list.csv
      timeline.json
    output/
      final.mp4
      captions.srt
      thumbnail.png
```

Do not commit large raw video files or private API keys to Git. Use Git LFS or external storage only when appropriate; store credentials in GitHub Actions Secrets and never print them in logs.

## Stage gates

### Gate 1 — Topic approval
Record:
- Working title and central question.
- Target viewer and why the subject matters.
- Search/browse demand evidence and competing videos.
- What makes this treatment different.
- Feasibility of finding legal footage and explaining the topic accurately.

Reject topics that depend on sensational claims or footage that cannot be licensed.

### Gate 2 — Research
Create a source ledger with:
- Claim ID.
- Exact claim.
- Primary source URL.
- Publisher/organization.
- Publication or update date.
- Access date.
- Confidence and notes.

Prefer primary sources: submarine cable operators, International Telecommunication Union, International Cable Protection Committee, regulators, research papers and reputable technical organizations. Secondary explainers may help with context but should not be the sole source for important technical claims.

### Gate 3 — Script
- Write for the ear, not like an essay.
- Use a curiosity-driven opening and deliver the promised answer.
- Mark every factual statement with a claim ID or source note.
- Separate established facts from estimates and interpretation.
- Avoid unsupported superlatives and precise statistics without dates and sources.
- Read aloud and remove repetitive wording.

### Gate 4 — Visual plan
Every narration paragraph gets a visual purpose:
- Evidence footage.
- Location/map.
- Custom 2D diagram.
- 3D cutaway or motion graphic.
- On-screen number or label.
- Intentional pause or transition.

Use footage to show the real world and custom graphics to explain the invisible. Do not stretch one clip across unrelated narration.

### Gate 5 — Asset acquisition
Manifest columns:
`asset_id,filename,asset_type,source_url,creator,license,attribution,download_date,episode_use,verified_by`

Download one item at a time, verify file integrity, record license information, and use a documented fallback search if an asset is unavailable. Never silently substitute unrelated footage.

### Gate 6 — Narration and sound
- Generate narration only after script approval.
- Listen for pronunciation of technical terms, unnatural emphasis and pacing.
- Align scene durations to spoken phrases, not a single global speed change.
- Keep narration intelligible over music.
- Use sound effects sparingly and only when they support the scene.

### Gate 7 — Assembly
- Build the timeline from a structured shot list.
- Prefer native footage frame rates when practical, then conform to the 30 fps master.
- Use motion graphics for maps, cable routes and technical explanations.
- Keep a consistent typography and lower-third system.
- Render a low-resolution review copy before the final master.

### Gate 8 — Quality control
Automated checks:
- Video stream exists and is 1920×1080 at intended frame rate.
- Audio stream exists and has expected duration.
- No missing or zero-byte assets.
- Captions are valid and timestamps are ordered.
- Final duration is within the approved episode range.
- No unintended black/silent gaps.

Human checks:
- Watch the full render.
- Listen to the full narration mix.
- Verify every factual graphic and map.
- Confirm source/license manifest is complete.
- Check thumbnail/title accuracy.

### Gate 9 — Publishing package
Prepare final title, thumbnail, description, chapters, captions, source notes and Shorts cut list. Upload manually or through an approved YouTube integration only after explicit channel-owner review.

## Suggested GitHub workflow

1. A pull request adds or updates an episode brief, script and asset manifest.
2. GitHub Actions validates required files, CSV headers, SRT syntax and media metadata where media is available.
3. A human approves research, rights and script.
4. A render job runs on a properly provisioned runner.
5. The render output is stored as an artifact or transferred to approved storage.
6. A human watches the final render and approves publication.

Do not automatically publish from a commit. Keep a human approval step.

## Resource and cost controls

- Cache dependencies where possible.
- Download only approved assets.
- Avoid parallel large downloads or renders that exhaust disk space.
- Track expected and actual MB for each source and final export.
- Delete temporary intermediates only after successful validation.
- Use proxy media for editing when needed; retain high-quality source media for final rendering.
- Do not promise a render duration until the actual runner, footage volume and 3D complexity have been benchmarked.
