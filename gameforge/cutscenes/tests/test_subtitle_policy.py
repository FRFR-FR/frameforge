from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class SubtitlePolicyTests(unittest.TestCase):
    def test_ass_subtitle_template_is_outline_only_and_transparent(self):
        source = (ROOT / "audio" / "assemble_audio.py").read_text(encoding="utf-8")
        self.assertIn("Style: Default,Arial,48", source)
        self.assertIn("&HFF000000", source)  # fully transparent ASS background alpha
        self.assertIn(",1,3,1,2,", source)    # outline style, 3px outline, small shadow

    def test_editor_has_only_requested_voice_ids(self):
        source = (ROOT / "editor" / "editor.js").read_text(encoding="utf-8")
        for voice in ("eponine", "george", "azelma", "bill_boerst", "jean",
                      "michael", "peter_yearsley", "stuart_bell", "charles"):
            self.assertIn(voice, source)
        self.assertNotIn('["alba"', source)

    def test_ui_has_hard_1080p_limit(self):
        source = (ROOT / "editor" / "index.html").read_text(encoding="utf-8")
        self.assertIn("1920 × 1080", source)
        self.assertNotIn("3840", source)


if __name__ == "__main__":
    unittest.main()
