#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
CHAR_SCRIPT="$ROOT/character-source/gameforge/characters/build_character_test.py"
WORLD_SCRIPT="$ROOT/world-source/gameforge/worlds/build_world.py"
BLENDER="$BLENDER_BIN"
cd "$ROOT"
test -s "$CHAR_SCRIPT"
test -s "$WORLD_SCRIPT"
test -x "$BLENDER"

build_once() (
  set -euo pipefail
  rm -rf build/pvp-assets
  rm -f gameforge/pvp/assets/characters/*.glb gameforge/pvp/assets/weapons/*.glb
  rm -f gameforge/pvp/assets/previews/*.png gameforge/pvp/assets/map/*
  mkdir -p build/pvp-assets/character-source build/pvp-assets/world
  mkdir -p gameforge/pvp/assets/characters gameforge/pvp/assets/weapons
  mkdir -p gameforge/pvp/assets/map gameforge/pvp/assets/previews

  "$BLENDER" --background --factory-startup --python-exit-code 1 \
    --python "$CHAR_SCRIPT" -- \
    --output-dir "$ROOT/build/pvp-assets/character-source" --samples 48

  "$BLENDER" --background "$ROOT/build/pvp-assets/character-source/GAMEFORGE_LOOMGLASS_10_Character_Lab.blend" \
    --python "$ROOT/gameforge/pvp/tools/add_character_emotes.py" -- \
    --output-dir "$ROOT/gameforge/pvp/assets/characters" \
    --audit "$ROOT/gameforge/pvp/assets/characters/CHARACTER_RIG_AUDIT.json"

  cp "$ROOT"/build/pvp-assets/character-source/previews/*_720p.png \
    "$ROOT/gameforge/pvp/assets/previews/"

  "$BLENDER" --background --factory-startup --python-exit-code 1 \
    --python "$WORLD_SCRIPT" -- \
    --output-dir "$ROOT/build/pvp-assets/world" --seed 42017 --grid 129 --samples 32

  cp "$ROOT/build/pvp-assets/world/GAMEFORGE_Loomwild_Environment.glb" \
    "$ROOT/gameforge/pvp/assets/map/"
  cp "$ROOT/build/pvp-assets/world/GAMEFORGE_Loomwild_Audit.json" \
    "$ROOT/gameforge/pvp/assets/map/"

  "$BLENDER" --background --factory-startup --python-exit-code 1 \
    --python "$ROOT/gameforge/pvp/tools/build_weapons.py" -- \
    --output-dir "$ROOT/gameforge/pvp/assets/weapons" \
    --preview "$ROOT/gameforge/pvp/assets/previews/WEAPONS_1280x720.png"

  cp "$ROOT/gameforge/pvp/assets/weapons/WEAPON_AUDIT.json" "$ROOT/build/pvp-assets/"
  python3 "$ROOT/gameforge/pvp/tools/validate_assets.py" --root "$ROOT/gameforge/pvp"
  cp "$ROOT/gameforge/pvp/ASSET_VALIDATION.json" "$ROOT/build/pvp-assets/"
)

for attempt in 1 2; do
  echo "Generated asset build attempt $attempt/2"
  if build_once; then
    echo "All generated assets passed validation."
    exit 0
  fi
  if [[ "$attempt" -eq 1 ]]; then
    echo "Asset build failed. Clearing generated files and automatically rebuilding once."
  fi
done

echo "Asset rebuild failed twice. Review the Blender and audit logs above." >&2
exit 1
