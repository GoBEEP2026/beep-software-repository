import subprocess
from unittest.mock import patch
import copy
import json
import tempfile
import unittest
from pathlib import Path
from validate_reference_lifecycle import validate_reference_lifecycle
import validate_reference_lifecycle as module_under_test

class TestReferenceLifecycle(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.folder = Path(self.temp_dir.name)

        self.previous_path = self.folder / "previous.json"
        self.current_path = self.folder / "current.json"

        self.home = {
            "test_home_id": "BEEP-HOME-001",
            "test_home_version": "1.0.0",
            "status": "APPROVED",
            "reference_files": [
                {
                    "filename": "sample-home.xml",
                    "sha256": "a" * 64
                }
            ],
            "approval": {
                "approved_by": "B.E.E.P. Board of Directors",
                "approval_date": "2026-11-17",
                "approval_record": "TEST-APPROVAL-001",
                "board_resolution_reference": "TEST-BOARD-RES-001"
            }
        }

    def validate(self, current_home):
        previous = {"reference_homes": [self.home]}
        current = {"reference_homes": [current_home]}

        self.previous_path.write_text(
            json.dumps(previous), encoding="utf-8"
        )
        self.current_path.write_text(
            json.dumps(current), encoding="utf-8"
        )

        return validate_reference_lifecycle(
            self.previous_path,
            self.current_path
        )

    def test_unchanged_approved_home_accepted(self):
        errors = self.validate(copy.deepcopy(self.home))
        self.assertEqual(errors, [])

    def test_removing_approved_home_rejected(self):
        self.previous_path.write_text(
            json.dumps({"reference_homes": [self.home]}),
            encoding="utf-8"
        )
        self.current_path.write_text(
            json.dumps({"reference_homes": []}),
            encoding="utf-8"
        )

        errors = validate_reference_lifecycle(
            self.previous_path,
            self.current_path
        )

        self.assertTrue(
            any("cannot be removed" in error for error in errors)
        )

    def test_modifying_approved_checksum_rejected(self):
        current = copy.deepcopy(self.home)
        current["reference_files"][0]["sha256"] = "b" * 64

        errors = self.validate(current)

        
        self.assertTrue(
            any(
                "Approved or retired reference home metadata cannot be modified"
                in error
                for error in errors
            )
        )


    def test_modifying_retired_home_metadata_rejected(self):
        self.home["status"] = "RETIRED"
        self.home["conditioned_floor_area_ft2"] = 2200

        current = copy.deepcopy(self.home)
        current["conditioned_floor_area_ft2"] = 2500

        errors = self.validate(current)

        self.assertTrue(
            any(
                "Approved or retired reference home metadata "
                "cannot be modified" in error
                for error in errors
            )
        )

    def test_development_cannot_skip_review(self):
        self.home["status"] = "DEVELOPMENT"

        current = copy.deepcopy(self.home)
        current["status"] = "APPROVED"

        errors = self.validate(current)

        self.assertTrue(
            any(
                "Invalid lifecycle transition from "
                "DEVELOPMENT to APPROVED" in error
                for error in errors
            )
        )

    def test_modified_approved_file_rejected(self):
        repo = self.folder / "repo"
        home_dir = repo / "test-homes"
        home_dir.mkdir(parents=True)

        reference_file = home_dir / "sample-home.xml"
        reference_file.write_bytes(b"original approved content")

        subprocess.run(
            ["git", "init", "-q", str(repo)],
            check=True,
        )
        subprocess.run(
            ["git", "add", "."],
            cwd=repo,
            check=True,
        )
        subprocess.run(
            [
                "git", "-c", "user.name=BEEP Test",
                "-c", "user.email=test@example.invalid",
                "commit", "-q", "-m", "Baseline",
            ],
            cwd=repo,
            check=True,
        )

        base_commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=repo,
            text=True,
        ).strip()

        self.home["status"] = "APPROVED"

        self.previous_path.write_text(
            json.dumps({"reference_homes": [self.home]}),
            encoding="utf-8",
        )

        reference_file.write_bytes(b"unauthorized changed content")

        with patch.object(
            module_under_test.Path,
            "resolve",
            return_value=home_dir / "validate_reference_lifecycle.py",
        ):
            errors = module_under_test.validate_approved_file_history(
                self.previous_path,
                base_commit,
            )

        self.assertTrue(
            any(
                "reference file cannot be modified" in error
                for error in errors
            )
        )

    def test_new_reference_home_cannot_start_approved(self):
        new_home = copy.deepcopy(self.home)
        new_home["test_home_id"] = "BEEP-HOME-002"
        new_home["status"] = "APPROVED"

        self.previous_path.write_text(
            json.dumps({"reference_homes": []}),
            encoding="utf-8",
        )

        self.current_path.write_text(
            json.dumps({"reference_homes": [new_home]}),
            encoding="utf-8",
        )

        errors = validate_reference_lifecycle(
            self.previous_path,
            self.current_path,
        )

        self.assertTrue(
            any(
                "New reference home must begin in DEVELOPMENT"
                in error
                for error in errors
            )
        )

    def test_duplicate_reference_home_version_rejected(self):
        first_home = copy.deepcopy(self.home)
        second_home = copy.deepcopy(self.home)

        self.previous_path.write_text(
            json.dumps({"reference_homes": []}),
            encoding="utf-8",
        )

        self.current_path.write_text(
            json.dumps({
                "reference_homes": [
                    first_home,
                    second_home,
                ]
            }),
            encoding="utf-8",
        )

        errors = validate_reference_lifecycle(
            self.previous_path,
            self.current_path,
        )

        self.assertTrue(
            any(
                "Current registry contains duplicate "
                "reference home version" in error
                for error in errors
            )
        )


if __name__ == "__main__":
    unittest.main()
