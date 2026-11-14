# GAMEFORGE Cutscene Studio — GitHub cloud run

**No local installation is required.** Do not install Blender, FFmpeg, Pocket TTS, WhisperX, Python or Godot to run the supported pipeline.

Use the [GAMEFORGE GitHub Cloud Pipeline](https://github.com/FRFR-FR/frameforge/actions/workflows/gameforge-cloud.yml):

1. Select the `gameforge-cutscene-integration` branch.
2. Make sure your cutscene JSON manifest is committed to the repository.
3. Enable `run_cutscene`, enter the manifest path and choose the resolution/quality profile.
4. Read `VOICE_LICENSES.md`. For dialogue, acknowledge that you reviewed the terms for the selected voice assets.
5. Start the workflow and download the `GAMEFORGE-Cutscene` artifact.

GitHub installs the required pinned Blender and Godot releases, FFmpeg, CPU PyTorch, Pocket TTS, WhisperX, Java and Android SDK components only on the runners that need them. The runner is temporary and is discarded after each job.

The scripts under `setup/` are optional convenience tooling for contributors who explicitly choose to develop locally. They are not part of the end-user workflow.
