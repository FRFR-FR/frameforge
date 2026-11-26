# Episode 001 — Production report

**Channel:** Underneath Everything  
**Episode:** The Secret Cables That Keep the Internet Alive  
**Status:** Original 720p pilot is a superseded technical rough cut. The B-roll-first/Kokoro rebuild generated the Echo narration successfully, but final video rendering was skipped in the first attempt because the repository Actions secret `PIXABAY_API_KEY` was empty.

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

This pilot uses original procedural vector/motion-graphic scenes with gentle camera movement. It does not contain licensed real-world documentary footage. Narration uses a locally generated eSpeak fallback because Cartesia credentials were not available in the render environment. The SRT captions are phrase-timed estimates based on the narration sections, not word-level transcription. This is a working pilot/proof of pipeline, not the final release.

## Research

The narration is grounded in the International Telecommunication Union's 2025 Global Connectivity Report, ITU-T Recommendations G.971 (12/2024) and G.978 (05/2025), plus the International Cable Protection Committee's public media FAQ. See `source-ledger.md` and `fact_check.md` in this episode folder.

Important wording caveat: the ITU's “over 99%” figure refers to **international data flows**, not all internet traffic or every internet connection.

## Shorts

Three Shorts concepts are prepared in the episode brief. No separate Shorts video files have been rendered yet.

## Release status

The MP4 has not been uploaded to YouTube. A human review and approval is required before publication. The standalone MP4, SRT, thumbnail and compact source pack were provided in the ChatGPT conversation; the MP4 is not committed to Git history.

## First replacement render attempt — 26 November 2026

- Kokoro-82M voice: `am_echo` (Echo); narration WAV, MP3 and sentence-timed SRT generated successfully by GitHub Actions.
- B-roll download: skipped. The job log showed `PIXABAY_API_KEY` was empty; no real footage was downloaded.
- Video render and full-video QC: skipped because footage was unavailable. No new MP4 was produced by that attempt.
- New visual identity committed to the shared renderer: red `#D62839`, white `#FFFFFF`, blue `#1746A2`, navy `#102B52`. Natural footage colours are preserved.
- Keep `PIXABAY_API_KEY` private; never paste it into chat or commit it to the repository.
- First-attempt workflow run: https://github.com/FRFR-FR/frameforge/actions/runs/45804386715
- Kokoro narration artifact: https://github.com/FRFR-FR/frameforge/actions/runs/45804386715/artifacts/15109785204

## Second replacement render request — 26 November 2026

This Episode 1 report update is intended to trigger the footage-first GitHub Actions workflow on branch `youtube-docs/hidden-worlds-blueprint`. The new attempt must not be marked complete unless it downloads topic-relevant B-roll, renders an H.264/AAC MP4 at exactly 1280×720 and 24 fps, meets the 70% minimum moving-footage gate, and passes a full-file FFmpeg decode check. If the secret remains unavailable or footage selection fails, the workflow must report the blocker and must not substitute slides or unrelated stock footage.

