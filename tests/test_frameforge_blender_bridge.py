import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "frameforge_blender_bridge",
    ROOT / "tools" / "frameforge_blender_bridge.py",
)
BRIDGE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BRIDGE)


class FrameForgeBlenderBridgeTests(unittest.TestCase):
    def test_example_manifest_is_valid_and_has_animation_and_contact(self):
        manifest = BRIDGE.read_manifest(ROOT / "examples" / "frameforge-3d-scene.example.json")
        self.assertEqual(manifest["format"], "frameforge-blender-scene")
        self.assertEqual(len(manifest["objects"]), 2)
        cube = next(item for item in manifest["objects"] if item["id"] == "moving-cube")
        self.assertEqual(len(cube["keyframes"]), 3)
        self.assertTrue(any(item["type"] == "ground_contact" for item in cube["constraints"]))
        self.assertTrue(any(item["type"] == "aabb_collision" for item in cube["constraints"]))

    def test_invalid_schema_version_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "bad.json"
            path.write_text(json.dumps({"format": "frameforge-blender-scene", "schema_version": 9, "settings": {}}))
            with self.assertRaises(ValueError):
                BRIDGE.read_manifest(path)

    def test_model_asset_paths_must_be_relative_and_present(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "scene.json"
            payload = {
                "format": "frameforge-blender-scene",
                "schema_version": 1,
                "settings": {"width": 320, "height": 180, "fps": 24},
                "models": [{"asset_path": "../outside.glb"}]
            }
            path.write_text(json.dumps(payload))
            with self.assertRaises((ValueError, FileNotFoundError)):
                BRIDGE.read_manifest(path)

    def test_vector_and_material_colour_conversions_are_stable(self):
        self.assertEqual(BRIDGE.xyz([1, 2, 3]), (1.0, 2.0, 3.0))
        self.assertEqual(BRIDGE.hex_rgba("#abc"), (170 / 255, 187 / 255, 204 / 255, 1.0))
        with self.assertRaises(ValueError):
            BRIDGE.xyz([1, 2])


if __name__ == "__main__":
    unittest.main()
