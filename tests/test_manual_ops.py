from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.manual_ops import (
    ensure_manifest_matches_project, input_path, repo_path,
    validate_frame_budget, validate_frame_dimensions, validate_input_size,
)


class ManualOperationsGuardTests(unittest.TestCase):
    def test_repo_path_rejects_parent_traversal(self) -> None:
        with self.assertRaises(ValueError):
            repo_path("../outside-frameforge", must_exist=False)

    def test_render_inputs_must_stay_in_render_input(self) -> None:
        with self.assertRaises(ValueError):
            input_path("examples/frameforge-project-v2.example.json")

    def test_render_inputs_accept_render_input_subdirectory(self) -> None:
        candidate = input_path("render-input/chunks", must_exist=False)
        self.assertTrue(candidate.name == "chunks")

    def test_frame_budget_is_hard_capped(self) -> None:
        validate_frame_budget(240, 240)
        with self.assertRaises(ValueError):
            validate_frame_budget(241, 240)
        with self.assertRaises(ValueError):
            validate_frame_budget(2, 481)

    def test_manual_export_resolution_is_capped(self) -> None:
        validate_frame_dimensions(1280, 720)
        validate_frame_dimensions(720, 1280)
        with self.assertRaises(ValueError):
            validate_frame_dimensions(1920, 1080)

    def test_project_and_manifest_ids_must_match(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            project = Path(folder) / "project.json"
            manifest = Path(folder) / "manifest.json"
            project.write_text('{"project":{"id":"project-a"}}', encoding="utf-8")
            manifest.write_text('{"project_id":"project-a"}', encoding="utf-8")
            ensure_manifest_matches_project(project, manifest)
            manifest.write_text('{"project_id":"project-b"}', encoding="utf-8")
            with self.assertRaises(ValueError):
                ensure_manifest_matches_project(project, manifest)

    def test_input_byte_budget(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            small = Path(folder) / "small.zip"
            small.write_bytes(b"x" * 32)
            self.assertEqual(validate_input_size([small], 64), 32)
            with self.assertRaises(ValueError):
                validate_input_size([small], 16)


if __name__ == "__main__":
    unittest.main()
