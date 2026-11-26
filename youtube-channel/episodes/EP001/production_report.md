# Episode 001 — Production report

**Channel:** Underneath Everything  
**Episode:** The Secret Cables That Keep the Internet Alive  
**Status:** Original 720p pilot is a superseded technical rough cut. The B-roll-first/Kokoro rebuild generated the Echo narration successfully, but final video rendering was skipped because the repository Actions secret `PIXABAY_API_KEY` was empty.

## Export facts

| Property | Verified result |
|---|---|
| File | Underneath_Everything_EP001_720p.mp4 |
| Resolution | 1280 × 720 (720p) |
| Aspect ratio | 16:9 |
| Container | MP4 |
| Video | H.264 |
| Frame rate | 18 fps |
| Audio | AAC, 48 kHz, stereo |
| Duration | 534.67 seconds (8:54.67) |
| File size | 66.76 MB |
| Full decode | Passed |
| Captions | 167 ordered SRT cues |
| Thumbnail | 1280 × 720 concept created |

## Visual and audio disclosure

This pilot uses original procedural vector/motion-graphic scenes with gentle camera movement. It does not contain licensed real-world documentary footage. Narration uses a locally generated eSpeak fallback because Cartesia credentials were not available in the render environment. The SRT captions are phrase-timed estimates based on the narration sections, not word-level transcription. This is a working pilot/proof of pipeline, not yet the maximum-quality final release.

## Research

The narration is grounded in the International Telecommunication Union's 2025 Global Connectivity Report, ITU-T Recommendations G.971 (12/2024) and G.978 (05/2025), plus the International Cable Protection Committee's public media FAQ. See `research_sources.md` in this episode folder.

Important wording caveat: the ITU's “over 99%” figure refers to **international data flows**, not all internet traffic or every internet connection.

## Shorts

Three Shorts concepts are prepared in the episode brief. No separate Shorts video files have been rendered yet.

## Release status

The MP4 has not been uploaded to YouTube. A human review and approval is required before publication. The standalone MP4, SRT, thumbnail and compact source pack were provided in the ChatGPT conversation; the MP4 is not committed to Git history.


## Replacement render attempt — 26 November 2026

- Kokoro-82M voice: `am_echo` (Echo); narration WAV, MP3 and sentence-timed SRT generated successfully by GitHub Actions.
- B-roll download: skipped. The job log showed `PIXABAY_API_KEY` was empty; no real footage was downloaded.
- Video render and full-video QC: skipped because footage was unavailable. No new MP4 exists from this run.
- New visual identity committed to the shared renderer: red `#D62839`, white `#FFFFFF`, blue `#1746A2`, navy `#102B52`. Natural footage colours are preserved.
- Action needed: configure `PIXABAY_API_KEY` under the repository's **Settings → Secrets and variables → Actions**. Keep the key private; never paste it into chat or commit it to the repository.
- Workflow run: https://github.com/FRFR-FR/frameforge/actions/runs/45804386715
- Kokoro narration artifact: https://github.com/FRFR-FR/frameforge/actions/runs/45804386715/artifacts/15109785204
