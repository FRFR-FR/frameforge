# GAMEFORGE Cutscene Studio — local installation

Use the automated installer from the repository root:

- Windows 10/11: `Set-ExecutionPolicy -Scope Process Bypass`, then `./setup/windows/Install-GAMEFORGE.ps1`.
- Ubuntu/Debian: `bash setup/linux/install-gameforge.sh`.

See [setup/README.md](../../setup/README.md) for the installer details and verification steps.

The toolchain installs Git, Python 3.12/3.13, Blender 4.5.16 LTS, Godot 4.4.1 and matching export templates, FFmpeg/libass, Kyutai Pocket TTS, WhisperX, OpenJDK 17 and Android SDK packages.

## First render

After installation and first model download:

```bash
python gameforge/cutscenes/run_cutscene.py \
  --project gameforge/cutscenes/config/default_project.json \
  --out build/cutscene
```

The expected deliverables are an MP4, editable Blender project, rigged character GLB, alignment report, SRT/ASS subtitles and render report. Output is limited to 720p or 1080p, maximum 30 FPS and 10 minutes per cutscene.

The installer can prefetch the Pocket TTS weights, all nine allowlisted voice assets and the WhisperX English aligner after you explicitly confirm that you have reviewed and accepted their model/voice terms. If you defer that step, run setup/fetch_models.py from the repository root using the .venv Python. Do not commit model caches, Python virtual environments, generated frames, Android signing keys or passwords.
