# GAMEFORGE Cutscene Studio — local installation

This is the installation list for the first real prototype. The browser editor only authors cutscene data; Blender, Pocket TTS, WhisperX and FFmpeg do the actual rendering and synchronisation.

## Required for the cutscene prototype

1. **Git** — clone the repository and check out `gameforge-cutscene-integration`.
2. **Python 3.12** — create an isolated virtual environment for the TTS and alignment tools.
3. **Blender 4.x** — install the desktop application and make `blender` available on PATH. The pipeline uses Blender's Python API and its glTF exporter.
4. **FFmpeg + FFprobe** — both commands must be available on PATH. The FFmpeg build must include the `ass` subtitle filter (libass), because final subtitles are burnt into the MP4 with a transparent background.
5. **Kyutai Pocket TTS** — installed from the repository requirements. Its first run downloads the model and voice assets.
6. **WhisperX** — installed separately for audio-grounded forced alignment. It downloads the English alignment model on first use; speaker diarisation and a Hugging Face token are not required.

## Also required for a playable GAMEFORGE game prototype

7. **Godot Engine 4.4.1** — open and run the GAMEFORGE project, import the rigged character GLB, and test dialogue/cutscene playback. Install the matching Godot export templates through the editor.

## Optional until platform export/testing

8. **Android build tools** — needed only when exporting an APK: OpenJDK, Android SDK command-line tools, platform-tools, build-tools and the Android platform level required by the Godot export templates. Configure the SDK/JDK paths in Godot Editor Settings.
9. **Windows export templates** — install the matching Godot templates before exporting a Windows executable.
10. **An Android test phone** — required for real low-end performance measurements. Emulator or desktop performance is not proof that a weaker physical phone will meet the target.

## Windows PowerShell setup

From the repository root:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r gameforge/cutscenes/requirements.txt
python -m pip install whisperx
```

Install Blender, FFmpeg and Godot separately. Add the Blender and FFmpeg executable folders to PATH. On Windows, the normal PyTorch wheels are CPU-only for Pocket TTS; a CUDA installation is not required.

## Ubuntu / Debian setup

```bash
sudo apt-get update
sudo apt-get install -y blender ffmpeg
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install --extra-index-url https://download.pytorch.org/whl/cpu -r gameforge/cutscenes/requirements.txt
python -m pip install --extra-index-url https://download.pytorch.org/whl/cpu whisperx
```

Use the PyTorch CPU wheel index on Linux. Kyutai notes that the default PyPI install can otherwise download several gigabytes of CUDA runtime wheels even though Pocket TTS is designed to run on CPU. Do not install CUDA for this pipeline.

## Verify the installation

```bash
python --version
blender --version
ffmpeg -version
ffprobe -version
ffmpeg -filters | grep ass
python -c "from pocket_tts import TTSModel; print('Pocket TTS import OK')"
python -c "import whisperx; print('WhisperX import OK')"
```

Then check Godot 4.4.1 opens `gameforge/runtime/godot_template/project.godot`.

## First cutscene render

After the software above is installed:

```bash
python gameforge/cutscenes/run_cutscene.py \
  --project gameforge/cutscenes/config/default_project.json \
  --out build/cutscene
```

The expected deliverables are an MP4, editable Blender project, rigged character GLB, alignment report, SRT subtitles, ASS subtitles and render report. The pipeline enforces 1280×720 or 1920×1080, maximum 30 FPS and maximum 10 minutes per cutscene.

## Hardware and storage notes

A modern multi-core CPU and 16 GB RAM is a sensible minimum for the first desktop prototype; 32 GB RAM is preferable for larger scenes and 1080p renders. A dedicated GPU is not required for the Blender CPU render or Pocket TTS. The TTS and forced-alignment model caches need extra disk space, and first-time model downloads require an internet connection.

Do not commit model weights, cache directories, generated render frames, API keys, Android signing keys or passwords to Git. GitHub Actions minutes, artifact storage and runner time are limited; the 1080p cap controls output dimensions but does not make long CPU renders instant or unlimited.

## Character import and runtime lip-sync

The Blender pipeline writes `GAMEFORGE_Cutscene_Characters.glb`. Import this into Godot. Attach `scripts/cutscene_character_lip_sync.gd` to each character root, set its `skeleton_path` to the imported Skeleton3D, and add that root to the group `gameforge_character_<character_id>`. The runtime audio director then sends aligned jaw cues to the matching character while the audio playback clock drives both subtitles and lip-sync.

The current character-to-viseme mapping is an approximation from WhisperX character timings, not a native phoneme stream. Review the face animation against the actual audio before treating it as final-quality lip-sync.
