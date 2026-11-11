"""Tests for GAMEFORGE's offline autonomous design pipeline."""
import json, tempfile, unittest
from pathlib import Path
from run import make_mechanic_review, make_story_bible, run_pipeline
from providers import OfflineCreativeProvider

class AutopilotTests(unittest.TestCase):
    def setUp(self):
        self.brief="Create a painterly mystery adventure called 'The Glass Harbour' about memory and family, 7 hours."
        self.spec=OfflineCreativeProvider().generate_spec(self.brief)
    def test_offline_provider_produces_spec(self):
        self.assertEqual(self.spec["title"],"The Glass Harbour")
        self.assertEqual(self.spec["campaign"]["target_hours"],7)
        self.assertEqual(self.spec["platforms"],["android","windows"])
    def test_story_outline_chapter_count(self):
        story=make_story_bible(self.spec,self.brief)
        self.assertEqual(len(story["chapter_outline"]),self.spec["campaign"]["chapters"])
        self.assertEqual(story["status"],"outline_generated_not_scripted_or_playtested")
    def test_mechanics_do_not_claim_novelty(self):
        review=make_mechanic_review(self.spec)
        self.assertEqual(review["status"],"ideas_only_no_playable_prototypes")
        self.assertEqual(review["candidates"][0]["review"]["prior_art_status"],"not_researched")
    def test_pipeline_writes_artifacts_and_keeps_release_false(self):
        with tempfile.TemporaryDirectory() as directory:
            out=run_pipeline(self.brief,Path(directory)/"game","offline")
            expected={"GAME_SPEC.json","STORY_BIBLE.json","MECHANIC_REVIEW.json","PIPELINE_REPORT.json","NEXT_STEPS.md"}
            self.assertTrue(expected.issubset({p.name for p in out.iterdir()}))
            report=json.loads((out/"PIPELINE_REPORT.json").read_text())
            self.assertFalse(report["release_ready"])
            self.assertIn("android_apk_export",report["not_completed"])

if __name__=="__main__": unittest.main()
