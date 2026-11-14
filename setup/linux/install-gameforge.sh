#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TOOLS="$HOME/.local/opt"
BIN="$HOME/.local/bin"
ANDROID_SDK="$HOME/Android/Sdk"
WORK="${TMPDIR:-/tmp}/gameforge-install"
BLENDER_VERSION="4.5.16"
GODOT_VERSION="4.4.1"
mkdir -p "$TOOLS" "$BIN" "$WORK"

need_cmd() { command -v "$1" >/dev/null 2>&1; }
download() {
  local url="$1" dest="$2"
  echo "Downloading $url"
  curl -fL --retry 3 --retry-delay 2 "$url" -o "$dest"
  test -s "$dest"
}

echo "GAMEFORGE setup — Ubuntu/Debian Linux"
if ! need_cmd apt-get; then
  echo "This installer targets Ubuntu/Debian." >&2
  exit 2
fi

sudo apt-get update
sudo apt-get install -y git curl ca-certificates wget unzip xz-utils ffmpeg openjdk-17-jdk

if need_cmd python3.12; then
  PYTHON="$(command -v python3.12)"
elif need_cmd python3.13; then
  PYTHON="$(command -v python3.13)"
else
  echo "Install Python 3.12 or 3.13 with venv and development headers, then rerun." >&2
  exit 2
fi
sudo apt-get install -y "$(basename "$PYTHON")-venv" "$(basename "$PYTHON")-dev" || true

# 1. Blender 4.5 LTS, pinned to the maintained Blender 4.x line.
BLENDER_ARCHIVE="$WORK/blender-$BLENDER_VERSION-linux-x64.tar.xz"
BLENDER_URL="https://download.blender.org/release/Blender4.5/blender-$BLENDER_VERSION-linux-x64.tar.xz"
download "$BLENDER_URL" "$BLENDER_ARCHIVE"
tar -xJf "$BLENDER_ARCHIVE" -C "$TOOLS"
BLENDER_DIR="$TOOLS/blender-$BLENDER_VERSION-linux-x64"
if [[ ! -x "$BLENDER_DIR/blender" ]]; then
  BLENDER_DIR="$(find "$TOOLS" -maxdepth 1 -type d -name "blender-$BLENDER_VERSION*" | head -n 1)"
fi
test -x "$BLENDER_DIR/blender"
ln -sfn "$BLENDER_DIR/blender" "$BIN/blender"

# 2. Godot 4.4.1 editor and matching export templates.
GODOT_DIR="$TOOLS/godot-$GODOT_VERSION"
GODOT_BIN="$GODOT_DIR/Godot_v$GODOT_VERSION-stable_linux.x86_64"
if [[ ! -x "$GODOT_BIN" ]]; then
  GODOT_ZIP="$WORK/Godot_v$GODOT_VERSION-stable_linux.x86_64.zip"
  download "https://github.com/godotengine/godot/releases/download/$GODOT_VERSION-stable/Godot_v$GODOT_VERSION-stable_linux.x86_64.zip" "$GODOT_ZIP"
  mkdir -p "$GODOT_DIR"
  unzip -oq "$GODOT_ZIP" -d "$GODOT_DIR"
  chmod +x "$GODOT_BIN"
fi
ln -sfn "$GODOT_BIN" "$BIN/godot"

TEMPLATE_HOME="$HOME/.local/share/godot/export_templates/$GODOT_VERSION.stable"
if [[ ! -f "$TEMPLATE_HOME/android_debug.apk" ]]; then
  TEMPLATE_ZIP="$WORK/Godot_v$GODOT_VERSION-stable_export_templates.tpz"
  download "https://github.com/godotengine/godot/releases/download/$GODOT_VERSION-stable/Godot_v$GODOT_VERSION-stable_export_templates.tpz" "$TEMPLATE_ZIP"
  TEMPLATE_TMP="$WORK/godot-templates"
  rm -rf "$TEMPLATE_TMP"; mkdir -p "$TEMPLATE_TMP"
  unzip -oq "$TEMPLATE_ZIP" -d "$TEMPLATE_TMP"
  TEMPLATE_SOURCE="$TEMPLATE_TMP/templates"
  [[ -d "$TEMPLATE_SOURCE" ]] || TEMPLATE_SOURCE="$TEMPLATE_TMP"
  mkdir -p "$TEMPLATE_HOME"
  cp -a "$TEMPLATE_SOURCE/." "$TEMPLATE_HOME/"
  printf '%s\n' "$GODOT_VERSION.stable" > "$TEMPLATE_HOME/version.txt"
fi

# 3. OpenJDK 17 and Android command-line SDK.
export JAVA_HOME="/usr/lib/jvm/java-17-openjdk-amd64"
export PATH="$JAVA_HOME/bin:$PATH"
export ANDROID_HOME="$ANDROID_SDK"
export ANDROID_SDK_ROOT="$ANDROID_SDK"
mkdir -p "$ANDROID_SDK/cmdline-tools"
ANDROID_ZIP="$WORK/commandlinetools-linux-15859902_latest.zip"
download "https://dl.google.com/android/repository/commandlinetools-linux-15859902_latest.zip" "$ANDROID_ZIP"
echo "4e4c464f145a7512b57d088ac6c278c03c9eea610886b35a5e0804e74eedf583  $ANDROID_ZIP" | sha256sum -c -
ANDROID_LATEST="$ANDROID_SDK/cmdline-tools/latest"
rm -rf "$ANDROID_LATEST"; mkdir -p "$ANDROID_LATEST"
unzip -oq "$ANDROID_ZIP" -d "$WORK/android-sdk-tools"
cp -a "$WORK/android-sdk-tools/cmdline-tools/." "$ANDROID_LATEST/"
export PATH="$BIN:$ANDROID_LATEST/bin:$ANDROID_SDK/platform-tools:$PATH"
SDKMANAGER="$ANDROID_LATEST/bin/sdkmanager"
yes | "$SDKMANAGER" --sdk_root="$ANDROID_SDK" --licenses >/dev/null
"$SDKMANAGER" --sdk_root="$ANDROID_SDK" --install \
  "platform-tools" "build-tools;34.0.0" "platforms;android-34" \
  "cmdline-tools;latest" "cmake;3.10.2.4988404" "ndk;23.2.8568313"

# Persist per-user tool and SDK paths.
PROFILE_LINE='export PATH="$HOME/.local/bin:$PATH"'
grep -Fqx "$PROFILE_LINE" "$HOME/.profile" 2>/dev/null || echo "$PROFILE_LINE" >> "$HOME/.profile"
grep -Fqx 'export ANDROID_HOME="$HOME/Android/Sdk"' "$HOME/.profile" 2>/dev/null || echo 'export ANDROID_HOME="$HOME/Android/Sdk"' >> "$HOME/.profile"
grep -Fqx 'export ANDROID_SDK_ROOT="$ANDROID_HOME"' "$HOME/.profile" 2>/dev/null || echo 'export ANDROID_SDK_ROOT="$ANDROID_HOME"' >> "$HOME/.profile"
grep -Fqx 'export JAVA_HOME="/usr/lib/jvm/java-17-openjdk-amd64"' "$HOME/.profile" 2>/dev/null || echo 'export JAVA_HOME="/usr/lib/jvm/java-17-openjdk-amd64"' >> "$HOME/.profile"

# 4. CPU-only Pocket TTS and WhisperX dependencies.
VENV="$ROOT/.venv"
"$PYTHON" -m venv "$VENV"
"$VENV/bin/python" -m pip install --upgrade pip
"$VENV/bin/python" -m pip install --extra-index-url https://download.pytorch.org/whl/cpu -r "$ROOT/gameforge/cutscenes/requirements.txt"
"$VENV/bin/python" -m pip install --extra-index-url https://download.pytorch.org/whl/cpu whisperx
"$VENV/bin/python" -m pip check

# Optional first-run model downloads. Require explicit confirmation after the user
# has reviewed the Kyutai model and voice-specific licence terms.
read -r -p "Have you reviewed and accepted the Kyutai model/voice terms? Type YES to download TTS weights, all nine voices and the WhisperX aligner now: " MODEL_CONSENT
if [[ "$MODEL_CONSENT" == "YES" ]]; then
  "$VENV/bin/python" "$ROOT/setup/fetch_models.py"
else
  echo "Model weights not downloaded yet. Run .venv/bin/python setup/fetch_models.py after accepting the model/voice terms."
fi

# 5. Final verification.
"$VENV/bin/python" "$ROOT/setup/verify_install.py" \
  --python "$VENV/bin/python" --blender "$BIN/blender" --godot "$BIN/godot" \
  --android-sdk "$ANDROID_SDK"

echo
echo "GAMEFORGE toolchain installation completed."
echo "In Godot Editor Settings > Export > Android set:"
echo "  Java SDK: $JAVA_HOME"
echo "  Android SDK: $ANDROID_SDK"
echo "TTS/alignment model weights download on first use; check model terms before the first run."
