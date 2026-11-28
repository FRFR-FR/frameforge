"""Regression tests for FrameForge V2 project and rights metadata foundations."""
from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
PROJECT_SCHEMA_PATH = ROOT / "schemas" / "frameforge-project-v2.schema.json"
MANIFEST_SCHEMA_PATH = ROOT / "schemas" / "media-asset-manifest-v1.schema.json"
PROJECT_EXAMPLE_PATH = ROOT / "examples" / "frameforge-project-v2.example.json"
MANIFEST_EXAMPLE_PATH = ROOT / "examples" / "media-asset-manifest.example.json"
DIRECTOR_EXAMPLE_PATH = ROOT / "examples" / "frameforge-research-director.example.json"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class FrameForgeFoundationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.project_schema = read_json(PROJECT_SCHEMA_PATH)
        cls.manifest_schema = read_json(MANIFEST_SCHEMA_PATH)
        Draft202012Validator.check_schema(cls.project_schema)
        Draft202012Validator.check_schema(cls.manifest_schema)
        cls.project_validator = Draft202012Validator(cls.project_schema, format_checker=FormatChecker())
        cls.manifest_validator = Draft202012Validator(cls.manifest_schema, format_checker=FormatChecker())
        cls.project = read_json(PROJECT_EXAMPLE_PATH)
        cls.manifest = read_json(MANIFEST_EXAMPLE_PATH)

    def run_validator(self, script: str, payload: dict) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as tmp:
            file_path = Path(tmp) / "input.json"
            file_path.write_text(json.dumps(payload), encoding="utf-8")
            return subprocess.run(
                [sys.executable, str(ROOT / "tools" / script), str(file_path)],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

    def test_project_schema_is_valid_draft_2020_12(self) -> None:
        self.assertEqual(self.project_schema["$schema"], "https://json-schema.org/draft/2020-12/schema")

    def test_manifest_schema_is_valid_draft_2020_12(self) -> None:
        self.assertEqual(self.manifest_schema["$schema"], "https://json-schema.org/draft/2020-12/schema")

    def test_project_example_passes_schema_and_semantic_validator(self) -> None:
        self.assertEqual(list(self.project_validator.iter_errors(self.project)), [])
        result = subprocess.run(
            [sys.executable, str(ROOT / "tools" / "validate_project.py"), str(PROJECT_EXAMPLE_PATH)],
            cwd=ROOT, text=True, capture_output=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_manifest_example_passes_schema_and_validator(self) -> None:
        self.assertEqual(list(self.manifest_validator.iter_errors(self.manifest)), [])
        result = subprocess.run(
            [sys.executable, str(ROOT / "tools" / "validate_media_manifest.py"), str(MANIFEST_EXAMPLE_PATH)],
            cwd=ROOT, text=True, capture_output=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_research_director_example_passes_schema_and_semantic_validation(self) -> None:
        payload = read_json(DIRECTOR_EXAMPLE_PATH)
        self.assertEqual(list(self.project_validator.iter_errors(payload)), [])
        result = subprocess.run(
            [sys.executable, str(ROOT / "tools" / "validate_project.py"), str(DIRECTOR_EXAMPLE_PATH)],
            cwd=ROOT, text=True, capture_output=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_evidence_shot_rejects_unverified_or_unsourced_claim(self) -> None:
        payload = read_json(DIRECTOR_EXAMPLE_PATH)
        payload["research"]["claims"][0]["verification_status"] = "unverified"
        result = self.run_validator("validate_project.py", payload)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("cannot present an unverified or unsourced claim as evidence", result.stdout)

    def test_shot_plan_rejects_missing_asset_reference(self) -> None:
        payload = read_json(DIRECTOR_EXAMPLE_PATH)
        payload["shot_plan"]["beats"][0]["asset_ids"] = ["asset-not-in-project"]
        result = self.run_validator("validate_project.py", payload)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("references missing asset", result.stdout)

    def test_reference_video_is_reference_only(self) -> None:
        payload = read_json(DIRECTOR_EXAMPLE_PATH)
        payload["research"]["reference_videos"][0]["reference_only"] = False
        result = self.run_validator("validate_project.py", payload)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("reference_only", result.stdout)

    def test_approved_asset_review_needs_basis_reviewer_and_date(self) -> None:
        payload = read_json(DIRECTOR_EXAMPLE_PATH)
        review = payload["rights_review"]["asset_reviews"][0]
        review.pop("reviewer", None)
        self.assertTrue(list(self.project_validator.iter_errors(payload)))

    def test_unknown_project_schema_version_is_rejected(self) -> None:
        payload = copy.deepcopy(self.project)
        payload["schema_version"] = 1
        self.assertTrue(list(self.project_validator.iter_errors(payload)))

    def test_project_rejects_dangling_asset_reference(self) -> None:
        payload = copy.deepcopy(self.project)
        payload["sequences"][0]["tracks"][0]["clips"][0]["asset_id"] = "does-not-exist"
        result = self.run_validator("validate_project.py", payload)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("references missing asset", result.stdout)

    def test_project_rejects_clip_outside_sequence_duration(self) -> None:
        payload = copy.deepcopy(self.project)
        payload["sequences"][0]["tracks"][0]["clips"][0]["duration_frames"] = 500
        result = self.run_validator("validate_project.py", payload)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("ends after sequence", result.stdout)

    def test_project_rejects_duplicate_asset_ids(self) -> None:
        payload = copy.deepcopy(self.project)
        payload["assets"].append(copy.deepcopy(payload["assets"][0]))
        result = self.run_validator("validate_project.py", payload)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Duplicate asset id", result.stdout)

    def test_project_rejects_approved_asset_without_review_evidence(self) -> None:
        payload = copy.deepcopy(self.project)
        rights = payload["assets"][0]["rights"]
        rights.pop("review_basis")
        rights.pop("reviewed_by")
        rights.pop("reviewed_at")
        self.assertTrue(list(self.project_validator.iter_errors(payload)))

    def test_attribution_required_needs_attribution_text(self) -> None:
        payload = copy.deepcopy(self.manifest)
        rights = payload["assets"][0]["rights"]
        rights["attribution_required"] = True
        self.assertTrue(list(self.manifest_validator.iter_errors(payload)))

    def test_manifest_duplicate_ids_are_rejected(self) -> None:
        payload = copy.deepcopy(self.manifest)
        payload["assets"].append(copy.deepcopy(payload["assets"][0]))
        result = self.run_validator("validate_media_manifest.py", payload)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Duplicate asset id", result.stdout)

    def test_pending_asset_is_not_silently_approved(self) -> None:
        payload = copy.deepcopy(self.manifest)
        pending = payload["assets"][1]
        self.assertEqual(pending["rights"]["status"], "pending")
        self.assertNotIn("review_basis", pending["rights"])
        self.assertEqual(list(self.manifest_validator.iter_errors(payload)), [])

    def test_project_validator_handles_malformed_collections_without_crashing(self) -> None:
        payload = copy.deepcopy(self.project)
        payload["assets"] = "not-an-array"
        payload["research"] = "not-an-object"
        result = self.run_validator("validate_project.py", payload)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("FRAMEFORGE PROJECT VALIDATION FAILED", result.stdout)
        self.assertNotIn("Traceback", result.stdout + result.stderr)

    def test_manifest_validator_handles_malformed_assets_without_crashing(self) -> None:
        payload = copy.deepcopy(self.manifest)
        payload["assets"] = "not-an-array"
        result = self.run_validator("validate_media_manifest.py", payload)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("FRAMEFORGE MEDIA MANIFEST VALIDATION FAILED", result.stdout)
        self.assertNotIn("Traceback", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
