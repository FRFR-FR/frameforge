from __future__ import annotations
import sys, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from contracts import load_json, validate_project, render_policy, allowed_voice_ids


class CutsceneContractTests(unittest.TestCase):
    def setUp(self):
        self.project = load_json(ROOT / "config" / "default_project.json")

    def test_voice_allowlist_is_exact(self):
        self.assertEqual(allowed_voice_ids(), {
            "eponine", "george", "azelma", "bill_boerst", "jean",
            "michael", "peter_yearsley", "stuart_bell", "charles"
        })
        validate_project(self.project)

    def test_voice_is_locked_to_character(self):
        self.project["dialogue"][0]["voice"] = "eponine"
        with self.assertRaisesRegex(ValueError, "does not match"):
            validate_project(self.project)

    def test_1080p_is_maximum(self):
        self.project["render"]["width"] = 2560
        self.project["render"]["height"] = 1440
        with self.assertRaisesRegex(ValueError, "1920x1080"):
            validate_project(self.project)

    def test_only_720p_or_1080p(self):
        self.project["render"]["width"] = 1600
        self.project["render"]["height"] = 900
        with self.assertRaisesRegex(ValueError, "exactly 1280x720"):
            validate_project(self.project)

    def test_30_fps_cap(self):
        self.project["render"]["fps"] = 60
        with self.assertRaisesRegex(ValueError, "30 FPS"):
            validate_project(self.project)

    def test_non_allowlisted_voice_is_rejected(self):
        self.project["dialogue"][0]["voice"] = "alba"
        with self.assertRaisesRegex(ValueError, "allowlist"):
            validate_project(self.project)

    def test_adaptive_profile_bounds_cpu_threads_and_samples(self):
        policy = render_policy(self.project, cpu_count=64)
        self.assertEqual(policy["device"], "CPU")
        self.assertLessEqual(policy["threads"], 4)
        self.assertLessEqual(policy["samples"], 16)
        self.assertEqual(policy["width"], 1280)
        self.assertEqual(policy["height"], 720)


if __name__ == "__main__":
    unittest.main()
