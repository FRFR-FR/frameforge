# GAMEFORGE

GAMEFORGE is a code-first game production system whose normal build path runs on **GitHub-hosted runners**. You do not need to install Blender, Godot, Python packages, FFmpeg, Java or the Android SDK on your own computer to use the cloud pipeline.

## Run GAMEFORGE on GitHub

1. Open the [GAMEFORGE GitHub Cloud Pipeline](https://github.com/FRFR-FR/frameforge/actions/workflows/gameforge-cloud.yml).
2. Select the `gameforge-cutscene-integration` branch in the branch selector.
3. Press **Run workflow**. The default run validates the project and creates Android and Windows builds.
4. Download the resulting APK and EXE from the run's **Artifacts** section.

The workflow installs its required tools on fresh GitHub-hosted runners. Android and Windows builds run in separate jobs. Optional stages can generate a structured design pack or render a cutscene with original Blender characters, Kyutai speech, WhisperX alignment, subtitles and an MP4. For cutscenes, place the editor's JSON manifest in the repository, enter its repository-relative path, and review `cutscenes/VOICE_LICENSES.md` before enabling speech generation.

## What's in the engine

The Godot template contains the current runtime foundation: a third-person controller, camera, seeded blockout world, quests, dialogue, inventory, combat health, NPC state machine, save/load, accessibility, FrameForge cue dispatch and Android/Windows export presets. The code-first generator currently creates structured design artifacts; it does **not** yet compile an arbitrary natural-language brief into a complete, content-finished game.

The dedicated `gameforge/cutscenes/` subsystem is separate from the standalone FrameForge editor at the repository root. It authors cutscene manifests, creates original procedural Blender characters and rigs, generates allowlisted dialogue, aligns speech and exports a game-ready GLB plus a rendered video. Lip-shape mapping remains approximate and requires visual review.

## GitHub-only operating model

- The GitHub Actions workflow is the supported end-user build route. No local installation is required.
- GitHub-hosted runners are temporary: tools are installed for the job, outputs are uploaded as artifacts, and the runner is discarded afterwards.
- This repository is public, so standard GitHub-hosted runners are free to use. Standard public Ubuntu/Windows runners provide 4 CPUs and 16 GB RAM, not a GPU. Each hosted-runner job is limited to 6 hours.
- GitHub still applies artifact and cache storage limits. The cloud pipeline retains build artifacts for 7 days; download important outputs before they expire.
- Android output is a debug APK for testing. The Windows EXE is not Authenticode-signed. A production Android release-signing flow still needs a release keystore stored as GitHub Actions Secrets.
- Long CPU renders can hit runner time or storage limits. The cutscene format is capped at 1080p, 30 FPS and 10 minutes, but those caps are not a guarantee that every maximum-length render will finish within a hosted job.

References: [GitHub Actions runners](https://docs.github.com/en/actions/how-tos/write-workflows/choose-where-workflows-run/choose-the-runner-for-a-job), [Actions limits](https://docs.github.com/en/actions/reference/limits), [Actions billing and usage](https://docs.github.com/en/actions/concepts/billing-and-usage).

## Current completion boundary

The GitHub-hosted validation, Android/Windows export and optional cutscene-render jobs are now defined in the repository. A passing workflow proves that its executed jobs passed; it does not mean the entire planned autonomous game-generation system is finished. GAMEFORGE still needs a complete authored vertical slice, richer character and environment generation, gameplay QA, device profiling, and a production signing/release process.
