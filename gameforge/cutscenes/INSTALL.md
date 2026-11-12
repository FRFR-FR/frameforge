# GAMEFORGE Cutscene Studio — local installation

## Required

1. **Git** — clone the repository and pull the `gameforge-cutscene-integration` branch.
2. **Python 3.11 or 3.12** — create a virtual environment for the cutscene tools.
3. **Blender 4.x** — install the desktop Blender application; the command `blender --version` must work in a terminal. The scene builder uses Blender's Python API.
4. **FFmpeg + FFprobe** — install both; `ffmpeg -version` and `ffprobe -version` must work.
5. **Kyutai Pocket TTS** — install the Python package and download its model/voice files on first use.
6. **WhisperX** — needed for forced word/character alignment and accurate subtitle/viseme timing. Install the CPU build first; no diarisation token is needed because GAMEFORGE already knows which character owns each line.

## Suggested setup (Windows PowerShell)

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r gameforge/cutscenes/requirements.txt
python -m pip install whisperx
```

Install Blender and FFmpeg separately and add their executable directories to PATH. WhisperX has additional PyTorch/model requirements; follow its current installation instructions if pip reports a platform conflict.

## Suggested setup (Ubuntu / Debian)

```bash
sudo apt-get update
sudo apt-get install -y blender ffmpeg
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r gameforge/cutscenes/requirements.txt
python -m pip install whisperx
```

For CPU-only PyTorch on Linux, follow Kyutai's CPU installation notes to avoid pulling CUDA libraries. The exact command depends on your Python/PyTorch platform combination. Do not install CUDA unless you intend to use a supported GPU workflow.

## Verify tools

```bash
python --version
blender --version
ffmpeg -version
ffprobe -version
python -c "from pocket_tts import TTSModel; print('Pocket TTS import OK')"
python -c "import whisperx; print('WhisperX import OK')"
```

The first Pocket TTS and WhisperX runs download model assets. Allow disk space for Python/PyTorch packages and model caches. Do not commit model weights, cache directories, API keys, or signing keys to Git.

## Important distinction

Blender is needed to build and render original rigged 3D characters. Godot is needed to open and run the game itself. The browser editor is for arranging the cutscene manifest and previewing scene composition; it is not a substitute for Blender, TTS, audio alignment, or Godot.
