# GAMEFORGE toolchain installer

Run the installer from a fresh checkout of the `gameforge-cutscene-integration` branch. The scripts install:

- Python 3.12 (Windows) / Python 3.12 or 3.13 (Ubuntu/Debian)
- Blender 4.5.16 LTS
- Godot 4.4.1 and its matching export templates
- FFmpeg + FFprobe with ASS/libass subtitle filter support
- OpenJDK 17
- Android SDK command-line tools, Platform 34, Build Tools 34.0.0, platform-tools, CMake and NDK r23c
- Kyutai Pocket TTS and WhisperX in a project-local `.venv`

The scripts download official tool packages, verify Google's Android command-line tools SHA-256 checksum, create the Python environment and run a verification script. They do not install CUDA. Linux Pocket TTS dependencies use the PyTorch CPU wheel index.

## Windows 10/11 (PowerShell)

Open Windows Terminal in the repository root. Run as Administrator if Windows requests it:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\setup\windows\Install-GAMEFORGE.ps1
```

For a cutscene-only desktop setup without Android:

```powershell
.\setup\windows\Install-GAMEFORGE.ps1 -SkipAndroid
```

Windows requires Microsoft's `winget` package manager for Git, Python and FFmpeg. The script installs Blender and Godot from pinned official releases and uses Android command-line tools without requiring Android Studio.

## Ubuntu / Debian

```bash
bash setup/linux/install-gameforge.sh
```

The Linux script uses apt for system packages and installs Blender, Godot, export templates, Android SDK command-line tools, Pocket TTS and WhisperX. It writes `$HOME/.local/bin` and Android/Java environment settings to `~/.profile`; open a new terminal after installation.

## First-time model files

The installer asks for explicit confirmation before downloading model weights. After reviewing and accepting the Kyutai model and voice-specific terms, type YES at that prompt to fetch the Pocket TTS model, all nine approved voices and the WhisperX English aligner. To defer this, run .venv/bin/python setup/fetch_models.py later (Windows: .venv\\Scripts\\python.exe setup\\fetch_models.py). The fetched model files stay in your local cache; do not commit them to Git.

## Verify the installation

```bash
.venv/bin/python setup/verify_install.py
```

On Windows:

```powershell
.\.venv\Scripts\python.exe setup\verify_install.py
```

The verifier checks Blender 4.5, Godot 4.4.1, Python 3.12/3.13, FFmpeg/libass, Java 17, Pocket TTS, WhisperX and CPU-only PyTorch. Pass `--android-sdk <path>` to verify Android SDK packages too.

## Godot Android settings

Open Godot 4.4.1 and set Editor Settings → Export → Android:
- Java SDK Path: the installed OpenJDK 17 directory.
- Android Sdk Path: `%LOCALAPPDATA%\Android\Sdk` on Windows or `$HOME/Android/Sdk` on Linux.

The Android prerequisites follow the Godot 4.4 documentation. Matching Godot export templates are installed by these scripts.

## Important

These scripts install on the computer where they run. They cannot remotely install software on another computer. They require internet access, sufficient disk space and permission to install system applications. Committing these scripts to GitHub does not itself install software.
