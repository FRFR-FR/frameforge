"""Fast static contract checks for GAMEFORGE runtime modules."""
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
RUNTIME=ROOT/"runtime"/"godot_template"
REQUIRED=[
 "scripts/world_generator.gd","scripts/third_person_camera.gd","scripts/interaction_component.gd",
 "scripts/quest_director.gd","scripts/combat_component.gd","scripts/npc_brain.gd",
 "scripts/frameforge_player.gd","scripts/quality_manager.gd","export_presets.cfg",
 "tests/runtime_smoke.gd"
]
for relative in REQUIRED:
    path=RUNTIME/relative
    assert path.is_file() and path.stat().st_size > 40, f"Missing or empty runtime module: {relative}"
main=(RUNTIME/"scripts"/"main.gd").read_text(encoding="utf-8")
for token in ("WorldGenerator","CameraRig","QualityManager","QuestDirector","GeneratedWorld"):
    assert token in main, f"Main scene does not integrate {token}"
presets=(RUNTIME/"export_presets.cfg").read_text(encoding="utf-8")
for platform in ('name="Android"','name="Windows Desktop"'):
    assert platform in presets, f"Missing export preset {platform}"
print("GAMEFORGE runtime static contracts passed.")
