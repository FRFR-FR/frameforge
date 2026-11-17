#!/usr/bin/env bash
set -uo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
CHAR_SCRIPT="$ROOT/character-source/gameforge/characters/build_character_test.py"
WORLD_SCRIPT="$ROOT/world-source/gameforge/worlds/build_world.py"
BLENDER="${BLENDER_BIN:?BLENDER_BIN must point to Blender}"
cd "$ROOT"

build_once() {
  rm -rf build/pvp-assets
  rm -f gameforge/pvp/assets/characters/*.glb gameforge/pvp/assets/weapons/*.glb
  rm -f gameforge/pvp/assets/characters/*.json gameforge/pvp/assets/previews/*.png gameforge/pvp/assets/map/*
  mkdir -p build/pvp-assets/character-source build/pvp-assets/world
  mkdir -p gameforge/pvp/assets/characters gameforge/pvp/assets/weapons
  mkdir -p gameforge/pvp/assets/map gameforge/pvp/assets/previews

  test -s "$CHAR_SCRIPT" || { echo "Character source script missing: $CHAR_SCRIPT" >&2; return 1; }
  test -s "$WORLD_SCRIPT" || { echo "World source script missing: $WORLD_SCRIPT" >&2; return 1; }
  test -x "$BLENDER" || { echo "Blender is not executable: $BLENDER" >&2; return 1; }

  # This generator parses sys.argv[1:] and therefore must NOT receive Blender's -- separator.
  "$BLENDER" --background --factory-startup --python-exit-code 1 \
    --python "$CHAR_SCRIPT" \
    --output-dir "$ROOT/build/pvp-assets/character-source" --samples 48 || return 1
  test -s "$ROOT/build/pvp-assets/character-source/GAMEFORGE_LOOMGLASS_10_Character_Lab.blend" || {
    echo "Character generator did not create its Blender scene at the requested path." >&2; return 1;
  }
  test "$(find "$ROOT/build/pvp-assets/character-source/characters" -maxdepth 1 -name '*.glb' -type f | wc -l)" -eq 10 || {
    echo "Character generator did not create exactly ten source GLBs." >&2; return 1;
  }
  test "$(find "$ROOT/build/pvp-assets/character-source/previews" -maxdepth 1 -name '*_720p.png' -type f | wc -l)" -eq 10 || {
    echo "Character generator did not create ten individual 720p previews." >&2; return 1;
  }

  "$BLENDER" --background "$ROOT/build/pvp-assets/character-source/GAMEFORGE_LOOMGLASS_10_Character_Lab.blend" \
    --python-exit-code 1 --python "$ROOT/gameforge/pvp/tools/add_character_emotes.py" -- \
    --output-dir "$ROOT/gameforge/pvp/assets/characters" \
    --audit "$ROOT/gameforge/pvp/assets/characters/CHARACTER_RIG_AUDIT.json" || return 1
  test "$(find "$ROOT/gameforge/pvp/assets/characters" -maxdepth 1 -name '*.glb' -type f | wc -l)" -eq 10 || {
    echo "Emote export stage did not create ten final rigged character GLBs." >&2; return 1;
  }
  cp "$ROOT"/build/pvp-assets/character-source/previews/*_720p.png \
    "$ROOT/gameforge/pvp/assets/previews/" || return 1

  "$BLENDER" --background --factory-startup --python-exit-code 1 \
    --python "$WORLD_SCRIPT" -- \
    --output-dir "$ROOT/build/pvp-assets/world" --seed 42017 --grid 129 --samples 32 || return 1
  test -s "$ROOT/build/pvp-assets/world/GAMEFORGE_Loomwild_Environment.glb" || {
    echo "World generator did not create the Loomwild GLB." >&2; return 1;
  }
  test -s "$ROOT/build/pvp-assets/world/GAMEFORGE_Loomwild_Audit.json" || {
    echo "World generator did not create its audit." >&2; return 1;
  }
  cp "$ROOT/build/pvp-assets/world/GAMEFORGE_Loomwild_Environment.glb" \
    "$ROOT/gameforge/pvp/assets/map/" || return 1
  cp "$ROOT/build/pvp-assets/world/GAMEFORGE_Loomwild_Audit.json" \
    "$ROOT/gameforge/pvp/assets/map/" || return 1

  "$BLENDER" --background --factory-startup --python-exit-code 1 \
    --python "$ROOT/gameforge/pvp/tools/build_weapons.py" -- \
    --output-dir "$ROOT/gameforge/pvp/assets/weapons" \
    --preview "$ROOT/gameforge/pvp/assets/previews/WEAPONS_1280x720.png" || return 1
  test "$(find "$ROOT/gameforge/pvp/assets/weapons" -maxdepth 1 -name '*.glb' -type f | wc -l)" -eq 10 || {
    echo "Weapon authoring stage did not create ten GLBs." >&2; return 1;
  }
  test -s "$ROOT/gameforge/pvp/assets/weapons/WEAPON_AUDIT.json" || return 1
  test -s "$ROOT/gameforge/pvp/assets/previews/WEAPONS_1280x720.png" || return 1
  cp "$ROOT/gameforge/pvp/assets/weapons/WEAPON_AUDIT.json" "$ROOT/build/pvp-assets/" || return 1

  python3 "$ROOT/gameforge/pvp/tools/validate_assets.py" --root "$ROOT/gameforge/pvp" || return 1
  test -s "$ROOT/gameforge/pvp/ASSET_VALIDATION.json" || return 1
  cp "$ROOT/gameforge/pvp/ASSET_VALIDATION.json" "$ROOT/build/pvp-assets/" || return 1
  return 0
}

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
