# FrameForge — Mechanical Watch 30s Explainer

This project contains the narration and voice comparison workflow for the self-contained Three.js animation delivered separately.

## Assets and timing

- Duration: exactly 30 seconds in the PCM master
- Narration: 81 words at approximately 2.7 words/sec
- CTA: starts at exactly 10.00 seconds
- Main voice: Kokoro Echo (am_echo)
- Separate TTS sample line: "This tiny balance wheel swings back and forth, keeping a mechanical watch ticking with remarkable precision."

## Generate Kokoro Echo narration

Open **Actions → FrameForge — Mechanical Watch TTS Comparison → Run workflow**. The workflow generates:
- `watch-narration-echo.mp3` and WAV master
- `watch-tts-sample-kokoro-echo.mp3`
- `watch-tts-sample-espeak-ng.mp3`

The workflow runs Kokoro locally on the GitHub Actions CPU runner; no paid speech API is used.

## Compare other FrameForge engines

The FrameForge TTS Studio also includes F5-TTS and Orpheus:
- [F5-TTS sample notebook](https://colab.research.google.com/github/FRFR-FR/frameforge/blob/main/tts_studio/mechanical_watch_f5_sample.ipynb)
- [Orpheus sample notebook](https://colab.research.google.com/github/FRFR-FR/frameforge/blob/main/tts_studio/mechanical_watch_orpheus_sample.ipynb)

Both notebooks use the exact same short sample sentence. F5-TTS uses the newly generated Echo narration as its voice reference, so its sample is an F5-generated Echo-style clone. Orpheus uses its built-in English voice `leo`. Orpheus's official vLLM route requires a CUDA GPU; a free Colab GPU may be available but is not guaranteed.

## Licensing / free-use notes

- Kokoro: the model weights are Apache-2.0 and can be self-hosted without an API fee.
- F5-TTS: the code is MIT, but the official F5-TTS v1 Base weights are CC-BY-NC-4.0 (non-commercial). Do not use those weights for monetized/commercial output without separate permission.
- Orpheus: the repository declares Apache-2.0. The model uses a Llama 3.2 base, so follow the applicable Llama Community License terms as well.
- eSpeak NG: GPL-3.0-or-later, local and free; this is a simpler, robotic-sounding baseline.

"Free" here means no model/API fee when self-hosted. Compute availability is separate: free Colab GPU allocation is limited and not guaranteed.
